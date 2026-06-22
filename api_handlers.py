#!/usr/bin/env python3
"""Queue dispatch handlers for admin API actions."""
import subprocess
import json
import os
import signal
import sys
import time
import base64
import re
import secrets
import stat
import threading

from server_config import (
    DATA_DIR, PID_FILE, STATIC_DIR, API_KEY_FILE, CRON_FILE, CONFIG_FILE,
    NOTIFICATION_PROVIDERS_FILE, WORKFLOWS_FILE, WORKFLOW_INSTANCES_FILE,
    _get_api_key, _set_api_key, _safe_agent_name, strip_ansi,
    _get_session_lock, _check_engine, get_engine_restarted,
    get_attach_url, engine_is_reachable, log, _error_id,
    _load_notifications, _save_notifications,
    _load_notification_providers, _save_notification_providers,
    _load_workflows, _save_workflows,
    _load_workflow_instances, _save_workflow_instances,
    _workflow_lock,
)
from queue import _load_queue, _save_queue

def _handle_stop_session(body: dict) -> tuple:
    sid = body.get('id', '')
    if not sid:
        return False, {'ok': False, 'message': 'Missing session id'}
    try:
        cwd = body.get('directory') or None
        r = subprocess.run(['opencode', 'session', 'delete', sid], capture_output=True, text=True, timeout=15, cwd=cwd)
        err = r.stderr.strip()
        if r.returncode == 0 or 'not found' in err.lower():
            log(f"Admin: deleted session {sid}" if r.returncode == 0 else f"Admin: session {sid} already removed")
            return True, {'ok': True, 'message': 'Session deleted'}
        return False, {'ok': False, 'message': err or 'Unknown error'}
    except subprocess.TimeoutExpired:
        return False, {'ok': False, 'message': 'Timeout stopping session'}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_session_instruct(body: dict) -> tuple:
    sid = body.get('id', '')
    message = re.sub(r'^[\s"\']+|[\s"\']+$', '', body.get('message', ''))
    directory = body.get('directory', '')
    model = body.get('model', '')
    mode_val = body.get('mode', '')
    fork_val = body.get('fork', body.get('branch', False))
    if not sid or not message:
        return False, {'ok': False, 'message': 'Missing session id or message'}
    _get_session_lock(sid).acquire()
    try:
        cwd = directory or None
        password = os.environ.get('OPENCODE_SERVER_PASSWORD', '')
        engine_restarted = get_engine_restarted()
        attach = _check_engine()
        if not attach:
            msg = 'OpenCode engine is not reachable — please relaunch the app.'
            if engine_restarted:
                msg += ' (Engine was restarted)'
            log(f"Admin: engine not reachable")
            return False, {'ok': False, 'message': msg, 'code': 'engine_unreachable', 'error_id': _error_id()}
        if engine_restarted:
            log(f"Admin: engine restart detected, session {sid} invalid")
            return False, {'ok': False, 'message': 'OpenCode engine was restarted — all prior sessions are invalid. Create a new case.', 'code': 'engine_restarted'}
        def _build_cmd(fork=False):
            c = ['opencode', 'run']
            c.extend(['-s', sid])
            if fork:
                c.extend(['--fork'])
            c.extend(['--attach', attach])
            if password:
                c.extend(['-p', password])
            if model:
                c.extend(['-m', model])
            if mode_val:
                c.extend(['--agent', mode_val])
            return c
        cmd = _build_cmd(fork=fork_val)
        r = subprocess.run(cmd, input=message, capture_output=True, text=True, timeout=180, cwd=cwd)
        if r.returncode == 0:
            log(f"Admin: instructed session {sid}")
            return True, {'ok': True, 'message': 'Instruction sent'}
        err_text = strip_ansi(r.stderr.strip() or r.stdout.strip()[:200] or 'Unknown error')[:200]
        if 'not found' in err_text.lower():
            log(f"Admin: session {sid} not found, falling back to continue last")
            cmd_fallback = ['opencode', 'run', '-c', '--attach', attach]
            if password:
                cmd_fallback.extend(['-p', password])
            if model:
                cmd_fallback.extend(['-m', model])
            if mode_val:
                cmd_fallback.extend(['--agent', mode_val])
            r2 = subprocess.run(cmd_fallback, input=message, capture_output=True, text=True, timeout=120, cwd=cwd)
            if r2.returncode == 0:
                log(f"Admin: created new session from continue (was {sid})")
                return True, {'ok': True, 'message': 'This case has ended — a new case was created with your instruction.'}
            fb_err = strip_ansi(r2.stderr.strip() or r2.stdout.strip()[:200] or 'Unknown error')[:200]
            log(f"Admin: fallback continue also failed: {fb_err[:100]}")
            return False, {'ok': False, 'message': fb_err}
        if model and ('Model not found' in err_text or 'UnknownError' in err_text):
            log(f"Admin: retrying session {sid} without model")
            model = ''
            cmd_retry = ['opencode', 'run', '-s', sid]
            if fork_val:
                cmd_retry.append('--fork')
            cmd_retry.extend(['--attach', attach])
            if password:
                cmd_retry.extend(['-p', password])
            if mode_val:
                cmd_retry.extend(['--agent', mode_val])
            r3 = subprocess.run(cmd_retry, input=message, capture_output=True, text=True, timeout=180, cwd=cwd)
            if r3.returncode == 0:
                log(f"Admin: instructed session {sid} (retry without model)")
                return True, {'ok': True, 'message': 'Instruction sent (model ignored, using default)'}
            err_text = strip_ansi(r3.stderr.strip() or r3.stdout.strip()[:200] or 'Unknown error')[:200]
        log(f"Admin: instruct failed: {err_text[:100]}")
        return False, {'ok': False, 'message': err_text}
    except subprocess.TimeoutExpired:
        log("Admin: instruct timeout")
        return False, {'ok': False, 'message': 'Timeout sending instruction'}
    except Exception as e:
        log(f"Admin: instruct unexpected error: {str(e)[:200]}")
        return False, {'ok': False, 'message': str(e)[:200]}
    finally:
        _get_session_lock(sid).release()

def _handle_session_answer(body: dict) -> tuple:
    sid = body.get('id', '')
    answers = body.get('answers', [])
    if not sid or not answers:
        return False, {'ok': False, 'message': 'Missing session id or answers'}
    _get_session_lock(sid).acquire()
    try:
        cwd = body.get('directory') or None
        password = os.environ.get('OPENCODE_SERVER_PASSWORD', '')
        engine_restarted = get_engine_restarted()
        attach = _check_engine()
        if not attach:
            msg = 'OpenCode engine is not reachable — cannot send answer.'
            if engine_restarted:
                msg += ' (Engine was restarted)'
            log(f"Admin: answer failed — engine not reachable")
            return False, {'ok': False, 'message': msg, 'code': 'engine_unreachable', 'error_id': _error_id()}
        if engine_restarted:
            log(f"Admin: engine restart detected, session {sid} invalid for answer")
            return False, {'ok': False, 'message': 'Session no longer available — the engine was restarted.', 'code': 'engine_restarted'}
        answer_text = 'I choose: ' + '; '.join(str(a) for a in answers)
        cmd = ['opencode', 'run', '-s', sid, '--attach', attach]
        if password:
            cmd.extend(['-p', password])
        cmd.append(answer_text)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=cwd)
        if r.returncode == 0:
            log(f"Admin: answered session {sid}")
            return True, {'ok': True, 'message': 'Answer sent'}
        if engine_restarted or 'Session not found' in (r.stderr or ''):
            log(f"Admin: session {sid} stale for answer (engine restart)")
            return False, {'ok': False, 'message': 'Session no longer available — the engine was restarted.', 'code': 'engine_restarted'}
        if r.returncode == 124 or 'already running' in (r.stderr or '').lower() or 'already active' in (r.stderr or '').lower():
            log(f"Admin: session {sid} already busy, answer queued")
            return True, {'ok': True, 'message': 'Session is busy — answer will be picked up when ready'}
        return False, {'ok': False, 'message': (r.stderr.strip() or r.stdout.strip()[:200] or 'Unknown error')[:200]}
    except subprocess.TimeoutExpired:
        return False, {'ok': False, 'message': 'Timeout sending answer'}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}
    finally:
        _get_session_lock(sid).release()

def _handle_new_session(body: dict) -> tuple:
    title = body.get('title', '')
    message = re.sub(r'^[\s"\']+|[\s"\']+$', '', body.get('message', ''))
    directory = body.get('directory', '')
    model = body.get('model', '')
    mode_val = body.get('mode', '')
    fresh = body.get('fresh', False)
    workflow_id = body.get('workflow_id', '')
    if not message:
        return False, {'ok': False, 'message': 'Missing message'}
    try:
        cwd = directory or None
        password = os.environ.get('OPENCODE_SERVER_PASSWORD', '')
        attach = _check_engine()
        if not attach:
            msg = 'OpenCode engine is not reachable — please relaunch the app.'
            log(f"Admin: new session failed — engine not reachable")
            return False, {'ok': False, 'message': msg, 'code': 'engine_unreachable', 'error_id': _error_id()}
        engine_restarted = get_engine_restarted()
        cmd = ['opencode', 'run']
        if fresh:
            cmd.extend(['--attach', attach, '--format', 'json'])
        elif engine_restarted:
            cmd.extend(['-c', '--attach', attach])
        else:
            status_file = os.path.join(DATA_DIR, 'status.json')
            last_sid = None
            if os.path.exists(status_file):
                try:
                    with open(status_file) as f:
                        sd = json.load(f)
                    for s in sd.get('sessions', []):
                        if s.get('state') == 'complete':
                            last_sid = s['id']
                            break
                except Exception:
                    pass
            if last_sid:
                cmd.extend(['-s', last_sid, '--attach', attach])
            else:
                cmd.extend(['-c', '--attach', attach])
        if password:
            cmd.extend(['-p', password])
        if directory:
            cmd.extend(['--dir', directory])
        if title:
            cmd.extend(['--title', title])
        if model:
            cmd.extend(['-m', model])
        if mode_val:
            cmd.extend(['--agent', mode_val])
        if not fresh:
            cmd.append(message)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=cwd)
        except subprocess.TimeoutExpired:
            log(f"Admin: session creation timed out (120s), retrying once...")
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=cwd)
            except subprocess.TimeoutExpired:
                return False, {'ok': False, 'message': 'Timeout starting session'}
        session_id = None
        workflow_id = body.get('workflow_id', '')
        if fresh:
            # Parse session ID: try JSON first, then regex fallback
            try:
                import json as _j2
                _d = _j2.loads(r.stdout)
                session_id = _d.get('sessionID', '')
            except Exception:
                import re as _r2
                _m2 = _r2.search(r'(?:sessionID|Session\s*ID|session\s*id)[:"\s]+"?([a-z0-9_]{10,})"?', r.stdout, re.IGNORECASE)
                if _m2:
                    session_id = _m2.group(1)
                else:
                    eid = _error_id()
                    log(f"Fresh session: no sessionID in stdout [{eid}]: {r.stdout[:200]}")
            if session_id:
                # Step 2: Send real message via -s (auth/model/agent already set in Step 1)
                retry_count = body.get('retry_count', 0)
                msg_cmd = ['opencode', 'run', '-s', session_id, '--attach', attach]
                msg_cmd.append(message)
                r2 = subprocess.run(msg_cmd, capture_output=True, text=True, timeout=120, cwd=cwd)
                if r2.returncode != 0 and retry_count < 3:
                    eid = _error_id()
                    backoff = [10, 30, 60][retry_count]
                    retry_item = {
                        'id': 'q_' + secrets.token_hex(6),
                        'type': 'new-session',
                        'payload': {**body, 'retry_count': retry_count + 1},
                        'retry_at': time.time() + backoff,
                        'status': 'queued',
                        'result': None,
                        'error': None,
                        'created_at': time.time(),
                    }
                    queue = _load_queue()
                    queue.append(retry_item)
                    _save_queue(queue)
                    log(f"Session creation retry {retry_count+1}/3 in {backoff}s: {session_id[:16]}... [{eid}]")
                    return True, {'ok': True, 'message': f'Session queued, retry in {backoff}s', 'session_id': session_id}
                if r2.returncode != 0:
                    log(f"Admin: session created but message delivery failed: {session_id[:16]}... [{_error_id()}]")
                log(f"Admin: fresh session started \"{title or message[:40]}\" ({session_id[:16]}...)")
                result = {'ok': True, 'message': 'Session started', 'session_id': session_id}
                if workflow_id:
                    try:
                        wf_ok, wf_res = _handle_workflow_attach({'session_id': session_id, 'workflow_id': workflow_id})
                        if wf_ok:
                            result['workflow'] = 'attached'
                        else:
                            result['workflow_error'] = wf_res.get('message', '')
                    except Exception as e:
                        result['workflow_error'] = str(e)[:100]
                return True, result
            return False, {'ok': False, 'message': 'Failed to parse session ID'}
        if r.returncode == 0:
            try:
                import re as _re3
                m3 = _re3.search(r'(?:Session|session|ID|id)[:\s]+([a-z0-9_]{10,})', r.stdout)
                if m3:
                    session_id = m3.group(1)
            except Exception:
                pass
            log(f"Admin: new session started \"{title or message[:40]}\"")
            result = {'ok': True, 'message': 'Session started', 'session_id': session_id or ''}
            if workflow_id and session_id:
                try:
                    wf_ok, wf_res = _handle_workflow_attach({'session_id': session_id, 'workflow_id': workflow_id})
                    if wf_ok:
                        result['workflow'] = 'attached'
                    else:
                        result['workflow_error'] = wf_res.get('message', '')
                except Exception as e:
                    result['workflow_error'] = str(e)[:100]
            return True, result
        return False, {'ok': False, 'message': (r.stderr.strip() or r.stdout.strip()[:200] or 'Unknown error')[:200]}
    except subprocess.TimeoutExpired:
        return False, {'ok': False, 'message': 'Timeout starting session'}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_provider_logout(body: dict) -> tuple:
    name = body.get('provider', '')
    if not name:
        return False, {'ok': False, 'message': 'Missing provider name'}
    try:
        r = subprocess.run(['opencode', 'providers', 'logout', name], capture_output=True, text=True, timeout=15)
        log(f"Admin: logged out from {name}")
        return True, {'ok': True, 'message': 'Logged out'}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_provider_login(body: dict) -> tuple:
    url = body.get('url', '')
    try:
        cmd = ['opencode', 'providers', 'login']
        if url:
            cmd.append(url)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        log("Admin: provider login initiated")
        return True, {'ok': True, 'message': 'Login initiated', 'instruction': 'A browser window may have opened to complete login. If not, check the terminal.'}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_ollama_add(body: dict) -> tuple:
    url = body.get('url', '').strip()
    if not url:
        return False, {'ok': False, 'message': 'Missing URL'}
    ollama_config = os.path.join(DATA_DIR, 'ollama_config.json')
    existing = []
    if os.path.exists(ollama_config):
        with open(ollama_config) as f:
            existing = json.load(f)
    if any(o['url'] == url for o in existing):
        return False, {'ok': False, 'message': 'URL already added'}
    existing.append({'url': url})
    with open(ollama_config, 'w') as f:
        json.dump(existing, f, indent=2)
    log(f"Admin: added Ollama URL {url}")
    return True, {'ok': True, 'message': 'Ollama URL added'}

def _handle_ollama_remove(body: dict) -> tuple:
    url = body.get('url', '').strip()
    if not url:
        return False, {'ok': False, 'message': 'Missing URL'}
    ollama_config = os.path.join(DATA_DIR, 'ollama_config.json')
    if os.path.exists(ollama_config):
        with open(ollama_config) as f:
            existing = json.load(f)
        existing = [o for o in existing if o['url'] != url]
        with open(ollama_config, 'w') as f:
            json.dump(existing, f, indent=2)
    log(f"Admin: removed Ollama URL {url}")
    return True, {'ok': True, 'message': 'Ollama URL removed'}

def _handle_super_staff_create(body: dict) -> tuple:
    name = body.get('name', '').strip()
    if not name:
        return False, {'ok': False, 'message': 'Missing name'}
    description = body.get('description', '').strip()
    gender = body.get('gender', 'male')
    mode_val = body.get('mode', 'build')
    model = body.get('model', '')
    agent_path = body.get('path', os.path.expanduser('~'))
    try:
        staff_file = os.path.join(DATA_DIR, 'super_staff.json')
        staff = []
        if os.path.exists(staff_file):
            with open(staff_file) as f:
                staff = json.load(f)
        agent_dir = os.path.join(agent_path, '.opencode', 'agents')
        os.makedirs(agent_dir, exist_ok=True)
        safe_name = _safe_agent_name(name)
        if not safe_name:
            return False, {'ok': False, 'message': 'Invalid name'}
        agent_file = os.path.join(agent_dir, safe_name + '.json')
        agent_config = {
            'name': name,
            'description': description,
            'mode': 'all',
            'model': model or None,
            'permissions': ['*'],
        }
        with open(agent_file, 'w') as f:
            json.dump(agent_config, f, indent=2)
        staff.append({'name': name, 'description': description, 'gender': gender, 'mode': mode_val, 'model': model, 'path': agent_path, 'created': __import__('time').time()})
        with open(staff_file, 'w') as f:
            json.dump(staff, f, indent=2)
        log(f"Admin: created super staff '{name}'")
        return True, {'ok': True, 'message': f'Agent {name} created'}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_super_staff_delete(body: dict) -> tuple:
    name = body.get('name', '').strip()
    if not name:
        return False, {'ok': False, 'message': 'Missing name'}
    try:
        staff_file = os.path.join(DATA_DIR, 'super_staff.json')
        if os.path.exists(staff_file):
            with open(staff_file) as f:
                staff = json.load(f)
            staff = [s for s in staff if s['name'] != name]
            with open(staff_file, 'w') as f:
                json.dump(staff, f, indent=2)
        log(f"Admin: deleted super staff '{name}'")
        return True, {'ok': True, 'message': f'Agent {name} deleted'}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_super_staff_update(body: dict) -> tuple:
    original_name = body.get('originalName', '').strip()
    name = body.get('name', '').strip()
    if not original_name or not name:
        return False, {'ok': False, 'message': 'Missing name'}
    description = body.get('description', '').strip()
    gender = body.get('gender', 'male')
    mode_val = body.get('mode', 'build')
    model = body.get('model', '')
    agent_path = body.get('path', os.path.expanduser('~'))
    try:
        staff_file = os.path.join(DATA_DIR, 'super_staff.json')
        if os.path.exists(staff_file):
            with open(staff_file) as f:
                staff = json.load(f)
            for s in staff:
                if s['name'] == original_name:
                    s['name'] = name
                    s['description'] = description
                    s['gender'] = gender
                    s['mode'] = mode_val
                    s['model'] = model
                    s['path'] = agent_path
                    break
            with open(staff_file, 'w') as f:
                json.dump(staff, f, indent=2)
        safe_name = _safe_agent_name(name)
        if not safe_name:
            return False, {'ok': False, 'message': 'Invalid name'}
        agent_dir = os.path.join(agent_path, '.opencode', 'agents')
        agent_file = os.path.join(agent_dir, safe_name + '.json')
        agent_config = {
            'name': name,
            'description': description,
            'mode': 'all',
            'model': model or None,
            'permissions': ['*'],
        }
        os.makedirs(agent_dir, exist_ok=True)
        with open(agent_file, 'w') as f:
            json.dump(agent_config, f, indent=2)
        if name != original_name:
            old_file = os.path.join(agent_dir, _safe_agent_name(original_name) + '.json')
            if os.path.exists(old_file):
                os.remove(old_file)
            assign_file = os.path.join(DATA_DIR, 'case_assignments.json')
            if os.path.exists(assign_file):
                try:
                    with open(assign_file) as f:
                        assignments = json.load(f)
                    changed = False
                    for sid in assignments:
                        if assignments[sid] == original_name:
                            assignments[sid] = name
                            changed = True
                    if changed:
                        with open(assign_file, 'w') as f:
                            json.dump(assignments, f, indent=2)
                except Exception:
                    pass
        log(f"Admin: updated super staff '{original_name}' -> '{name}'")
        return True, {'ok': True, 'message': f'Agent {name} updated'}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_super_staff_assign(body: dict) -> tuple:
    session_id = body.get('sessionId', '').strip()
    staff_name = body.get('staffName', '').strip()
    if not session_id:
        return False, {'ok': False, 'message': 'Missing session ID'}
    assign_file = os.path.join(DATA_DIR, 'case_assignments.json')
    assignments = {}
    if os.path.exists(assign_file):
        try:
            with open(assign_file) as f:
                assignments = json.load(f)
        except Exception:
            pass
    if staff_name:
        assignments[session_id] = staff_name
    else:
        assignments.pop(session_id, None)
    with open(assign_file, 'w') as f:
        json.dump(assignments, f, indent=2)
    log(f"Admin: {'assigned' if staff_name else 'unassigned'} staff '{staff_name}' to session {session_id[:16]}")
    return True, {'ok': True, 'message': f"Staff {'assigned' if staff_name else 'unassigned'}"}

def _handle_rename_session(body: dict) -> tuple:
    sid = body.get('id', '')
    new_title = body.get('title', '').strip()
    if not sid or not new_title:
        return False, {'ok': False, 'message': 'Missing id or title'}
    try:
        import sqlite3
        db_path = os.path.expanduser('~/.local/share/opencode/opencode.db')
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE session SET title = ? WHERE id = ?", (new_title, sid))
        conn.commit()
        conn.close()
        log(f"Admin: renamed session {sid[:16]} → \"{new_title}\"")
        return True, {'ok': True, 'message': 'Case renamed'}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_restart_daemon(body: dict) -> tuple:
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE) as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, signal.SIGTERM)
        subprocess.Popen(
            ['nohup', 'bash', os.path.expanduser('~/.opencode-dashboard/daemon.sh')],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        log("Admin: daemon restarted")
        return True, {'ok': True, 'message': 'Daemon restarted'}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_kill_daemon(body: dict) -> tuple:
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE) as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, signal.SIGKILL)
            os.remove(PID_FILE)
        log("Admin: daemon killed")
        return True, {'ok': True, 'message': 'Daemon killed'}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_upload_photo(body: dict) -> tuple:
    data_url = body.get('dataUrl', '')
    if not data_url or not data_url.startswith('data:image/'):
        return False, {'ok': False, 'message': 'Invalid image data'}
    header, _, b64 = data_url.partition(',')
    try:
        img_data = base64.b64decode(b64)
        dest = os.path.join(STATIC_DIR, 'assets', 'profile_photo.png')
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(img_data)
        return True, {'ok': True, 'url': '/assets/profile_photo.png?t=' + str(int(time.time()))}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_remove_photo(body: dict) -> tuple:
    dest = os.path.join(STATIC_DIR, 'assets', 'profile_photo.png')
    if os.path.exists(dest):
        os.remove(dest)
    return True, {'ok': True}

def _handle_save_boss_name(body: dict) -> tuple:
    name = (body.get('name') or '').strip()
    if not name:
        return False, {'ok': False, 'message': 'Missing name'}
    try:
        # Read existing config or start fresh
        cfg = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
        cfg['boss_name'] = name
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)
        return True, {'ok': True}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_notifications_send(body: dict) -> tuple:
    message = (body.get('message') or '').strip()
    ntf_type = body.get('type', 'info')
    if not message:
        return False, {'ok': False, 'message': 'Missing message'}
    try:
        items = _load_notifications()
        items.insert(0, {
            'id': 'ntf_' + secrets.token_hex(8),
            'message': message,
            'type': ntf_type if ntf_type in ('info', 'warning', 'error', 'success') else 'info',
            'created_at': time.time(),
            'dismissed': False
        })
        _save_notifications(items)
        log(f"Notification sent: {message[:60]}")
        return True, {'ok': True}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_notifications_dismiss(body: dict) -> tuple:
    ntf_id = body.get('id', '')
    if not ntf_id:
        return False, {'ok': False, 'message': 'Missing id'}
    try:
        items = _load_notifications()
        for i in items:
            if i['id'] == ntf_id:
                i['dismissed'] = True
                break
        _save_notifications(items)
        return True, {'ok': True}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _format_event_message(event_type: str, event_data: dict, provider_name: str) -> str:
    if event_type == 'state_change':
        title = event_data.get('title', '?')
        old_state = event_data.get('old_state', '?')
        new_state = event_data.get('new_state', '?')
        return f'\U0001f504 Case \'{title}\': {old_state} \u2192 {new_state}'
    if event_type == 'user_interaction':
        count = event_data.get('count', 1)
        titles = event_data.get('titles', [])
        if count == 1 and titles:
            return f'\U0001f4ac Case \'{titles[0]}\' needs your response'
        return f'\U0001f4ac {count} cases need your response'
    if event_type == 'desks_full':
        count = event_data.get('worker_count', 0)
        return f'\U0001faa9 All 6 desks occupied ({count} workers active)'
    if event_type == 'no_active_cases':
        duration = event_data.get('duration', 0)
        return f'\u23f0 No active cases for {duration}s'
    return f'Notification from {provider_name}'

def _send_webhook(provider: dict, test_message: str = '', event_data: dict = None) -> tuple:
    url = provider.get('webhook_url', '').strip()
    ptype = provider.get('type', 'custom')
    name = provider.get('name', 'Notification')
    if event_data:
        event_type = event_data.get('event_type', '')
        message = _format_event_message(event_type, event_data, name)
    else:
        message = test_message or f'Test notification from {name}'
    if not url:
        return False, 'Webhook URL is empty'
    if ptype == 'slack':
        payload = json.dumps({'text': message, 'username': 'MyDora Dashboard'})
    elif ptype == 'discord':
        payload = json.dumps({'content': message})
    else:
        payload = json.dumps({'message': message, 'provider': name, 'event': event_data or {}, 'timestamp': time.time()})
    try:
        r = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
             '-X', 'POST', '-H', 'Content-Type: application/json',
             '-d', payload, url],
            capture_output=True, text=True, timeout=10
        )
        code = r.stdout.strip()
        if code.startswith('2'):
            return True, f'Webhook sent (HTTP {code})'
        return False, f'Webhook failed (HTTP {code}): {r.stderr[:100]}'
    except subprocess.TimeoutExpired:
        return False, 'Webhook timed out'
    except Exception as e:
        return False, f'Webhook error: {str(e)[:100]}'

def _handle_notification_providers_create(body: dict) -> tuple:
    name = body.get('name', '').strip()
    ptype = body.get('type', 'custom')
    webhook_url = body.get('webhook_url', '').strip()
    if not name:
        return False, {'ok': False, 'message': 'Missing provider name'}
    if not webhook_url:
        return False, {'ok': False, 'message': 'Missing webhook URL'}
    if ptype not in ('slack', 'discord', 'custom'):
        return False, {'ok': False, 'message': 'Invalid provider type'}
    providers = _load_notification_providers()
    scopes = body.get('scopes', {})
    default_scopes = {
        'state_change': scopes.get('state_change', True),
        'user_interaction': scopes.get('user_interaction', True),
        'desks_full': scopes.get('desks_full', False),
        'no_active_cases': scopes.get('no_active_cases', False),
    }
    provider = {
        'id': 'np_' + secrets.token_hex(6),
        'name': name,
        'type': ptype,
        'webhook_url': webhook_url,
        'enabled': True,
        'scopes': default_scopes,
        'gap_sec': max(60, int(body.get('gap_sec', 300))),
        'no_active_timeout': max(60, int(body.get('no_active_timeout', 300))),
        'created_at': time.time(),
        'failure_count': 0,
        'last_error': '',
        'last_failure_at': None,
        'last_success_at': None,
    }
    providers.append(provider)
    _save_notification_providers(providers)
    log(f"Notification provider created: {name} ({ptype})")
    return True, {'ok': True, 'provider': provider}

def _handle_notification_providers_update(body: dict) -> tuple:
    provider_id = body.get('id', '')
    if not provider_id:
        return False, {'ok': False, 'message': 'Missing provider id'}
    providers = _load_notification_providers()
    found = next((p for p in providers if p['id'] == provider_id), None)
    if not found:
        return False, {'ok': False, 'message': 'Provider not found'}
    if 'name' in body:
        found['name'] = body['name'].strip()
    if 'webhook_url' in body:
        found['webhook_url'] = body['webhook_url'].strip()
    if 'type' in body:
        ptype = body['type']
        if ptype in ('slack', 'discord', 'custom'):
            found['type'] = ptype
    if 'enabled' in body:
        found['enabled'] = bool(body['enabled'])
    if 'gap_sec' in body:
        found['gap_sec'] = max(60, int(body['gap_sec']))
    if 'no_active_timeout' in body:
        found['no_active_timeout'] = max(60, int(body['no_active_timeout']))
    if 'scopes' in body:
        s = body['scopes']
        current = found.get('scopes', {})
        for k in ('state_change', 'user_interaction', 'desks_full', 'no_active_cases'):
            if k in s:
                current[k] = bool(s[k])
        found['scopes'] = current
    _save_notification_providers(providers)
    log(f"Notification provider updated: {found['name']}")
    return True, {'ok': True, 'provider': found}

def _handle_notification_providers_delete(body: dict) -> tuple:
    provider_id = body.get('id', '')
    if not provider_id:
        return False, {'ok': False, 'message': 'Missing provider id'}
    providers = _load_notification_providers()
    providers = [p for p in providers if p['id'] != provider_id]
    _save_notification_providers(providers)
    log(f"Notification provider deleted: {provider_id}")
    return True, {'ok': True, 'message': 'Provider deleted'}

def _handle_notification_providers_test(body: dict) -> tuple:
    provider_id = body.get('id', '')
    if not provider_id:
        return False, {'ok': False, 'message': 'Missing provider id'}
    providers = _load_notification_providers()
    provider = next((p for p in providers if p['id'] == provider_id), None)
    if not provider:
        return False, {'ok': False, 'message': 'Provider not found'}
    ok, msg = _send_webhook(provider, f'Test notification from {provider["name"]} at {time.strftime("%H:%M:%S")}')
    log(f"Notification provider test: {provider['name']} -> {'ok' if ok else 'fail'}: {msg}")
    if ok:
        return True, {'ok': True, 'message': msg}
    return False, {'ok': False, 'message': msg}

def _handle_notification_providers_send_webhook(body: dict) -> tuple:
    provider_id = body.get('provider_id', '')
    event_type = body.get('event_type', '')
    event_data = body.get('event_data', {})
    if not provider_id or not event_type:
        return False, {'ok': False, 'message': 'Missing provider_id or event_type'}
    providers = _load_notification_providers()
    provider = next((p for p in providers if p['id'] == provider_id), None)
    if not provider:
        return False, {'ok': False, 'message': 'Provider not found'}
    if not provider.get('enabled'):
        return False, {'ok': False, 'message': 'Provider is disabled'}
    full_data = {'event_type': event_type, **event_data}
    ok, msg = _send_webhook(provider, event_data=full_data)
    retry_count = body.get('retry_count', 0)

    # Update provider failure tracking
    if ok:
        provider['failure_count'] = 0
        provider['last_error'] = ''
        provider['last_success_at'] = time.time()
        provider['last_failure_at'] = None
    else:
        provider['failure_count'] = provider.get('failure_count', 0) + 1
        provider['last_error'] = msg[:200]
        provider['last_failure_at'] = time.time()
    _save_notification_providers(providers)

    log(f"Notification dispatch {event_type} -> {provider['name']}: {'ok' if ok else 'fail'}: {msg[:80]}")
    if ok:
        return True, {'ok': True, 'message': msg}

    # Retry with exponential backoff
    if retry_count < 3:
        backoff = [30, 120, 300][retry_count]
        retry_item = {
            'id': 'q_' + secrets.token_hex(6),
            'type': 'notification-providers/send-webhook',
            'payload': {
                'provider_id': provider_id,
                'event_type': event_type,
                'event_data': event_data,
                'retry_count': retry_count + 1,
            },
            'retry_at': time.time() + backoff,
            'status': 'queued',
            'result': None,
            'error': None,
            'created_at': time.time(),
        }
        queue = _load_queue()
        queue.append(retry_item)
        _save_queue(queue)
        log(f"Notif retry {retry_count+1}/3 in {backoff}s: {event_type} -> {provider['name']}")
        return True, {'ok': True, 'message': f'Retry queued (+{backoff}s)'}

    # Exhausted retries — auto-disable
    provider['enabled'] = False
    provider['last_error'] = 'Auto-disabled after 3 failed attempts'
    _save_notification_providers(providers)
    log(f"Notif provider '{provider['name']}' auto-disabled after 3 failed attempts")
    return False, {'ok': False, 'message': msg}

def _handle_api_key_regenerate(body: dict) -> tuple:
    new_key = secrets.token_urlsafe(32)
    try:
        with open(API_KEY_FILE, 'w') as _f:
            _f.write(new_key + '\n')
        os.chmod(API_KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
        _set_api_key(new_key)
        log('Admin: API key regenerated')
        return True, {'ok': True, 'key': new_key}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_cron_jobs_create(body: dict) -> tuple:
    name = body.get('name', '').strip()
    interval_sec = int(body.get('interval_sec', 300))
    action = body.get('action', {})
    if not name or not action.get('message', '').strip():
        return False, {'ok': False, 'message': 'Missing name or message'}
    from cron import _load_cron_jobs, _save_cron_jobs
    jobs = _load_cron_jobs()
    new_job = {
        'id': 'cron_' + __import__('uuid').uuid4().hex[:12],
        'name': name,
        'interval_sec': max(60, interval_sec),
        'last_run': 0,
        'last_status': None,
        'enabled': True,
        'action': action,
        'created': time.time()
    }
    jobs.append(new_job)
    _save_cron_jobs(jobs)
    log(f"Admin: created cron job '{name}'")
    return True, {'ok': True, 'job': new_job}

def _handle_cron_jobs_update(body: dict) -> tuple:
    job_id = body.get('id', '')
    name = body.get('name', '').strip()
    interval_sec = int(body.get('interval_sec', 300))
    action = body.get('action', {})
    if not job_id or not name or not action.get('message', '').strip():
        return False, {'ok': False, 'message': 'Missing id, name or message'}
    from cron import _load_cron_jobs, _save_cron_jobs
    jobs = _load_cron_jobs()
    for j in jobs:
        if j['id'] == job_id:
            j['name'] = name
            j['interval_sec'] = max(60, interval_sec)
            j['action'] = action
            break
    _save_cron_jobs(jobs)
    return True, {'ok': True, 'message': 'Cron job updated'}

def _handle_cron_jobs_delete(body: dict) -> tuple:
    job_id = body.get('id', '')
    if not job_id:
        return False, {'ok': False, 'message': 'Missing id'}
    from cron import _load_cron_jobs, _save_cron_jobs
    jobs = _load_cron_jobs()
    jobs = [j for j in jobs if j['id'] != job_id]
    _save_cron_jobs(jobs)
    return True, {'ok': True, 'message': 'Cron job deleted'}

def _handle_cron_jobs_toggle(body: dict) -> tuple:
    job_id = body.get('id', '')
    if not job_id:
        return False, {'ok': False, 'message': 'Missing id'}
    from cron import _load_cron_jobs, _save_cron_jobs
    jobs = _load_cron_jobs()
    for j in jobs:
        if j['id'] == job_id:
            j['enabled'] = not j.get('enabled', True)
            break
    _save_cron_jobs(jobs)
    return True, {'ok': True, 'message': 'Toggled'}

def _run_workflow_stage(wf_instance: dict) -> tuple:
    """Execute the current pending stage for a workflow instance."""
    session_id = wf_instance['session_id']
    workflow_id = wf_instance['workflow_id']
    workflows = _load_workflows()
    wf = next((w for w in workflows if w['id'] == workflow_id), None)
    if not wf:
        return False, 'Workflow definition not found'

    current_id = wf_instance.get('current_node')
    if not current_id:
        return False, 'No current node set'

    node = next((n for n in wf['nodes'] if n['id'] == current_id), None)
    if not node:
        return False, f'Node {current_id} not found in workflow'

    staff_name = node.get('staff_ic', '')
    staff_mode = ''
    staff_model = ''
    staff_desc = ''
    if staff_name:
        staff_file = os.path.join(DATA_DIR, 'super_staff.json')
        if os.path.exists(staff_file):
            try:
                with open(staff_file) as f:
                    all_staff = json.load(f)
                found = next((s for s in all_staff if s['name'] == staff_name), None)
                if found:
                    staff_mode = found.get('mode', '')
                    staff_model = found.get('model', '')
                    staff_desc = found.get('description', '')
            except Exception:
                pass

    # Fetch last response from the session to prepend as context
    last_response = ''
    status_path = os.path.join(DATA_DIR, 'status.json')
    if os.path.exists(status_path):
        try:
            with open(status_path) as f:
                sd = json.load(f)
            all_sessions = sd.get('all_sessions', sd.get('sessions', []))
            sdata = next((s for s in all_sessions if s.get('id') == session_id), None)
            if sdata:
                lt = sdata.get('last_text', '') or ''
                if lt:
                    last_response = lt[:2000]
        except Exception:
            pass

    # Build message with previous response context + staff scope + instructions
    parts = []
    if last_response:
        parts.append(f"Response to: {last_response}")
    if staff_desc:
        parts.append(staff_desc)
    if node.get('instructions', ''):
        parts.append(node['instructions'])
    message = '\n\n'.join(parts) if parts else node.get('instructions', '')

    cmd = ['opencode', 'run', '-s', session_id]
    if staff_model:
        cmd.extend(['-m', staff_model])
    if staff_mode:
        cmd.extend(['--agent', staff_mode])
    cmd.append(message)

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        log(f"[WF STAGE] cmd={' '.join(cmd[-4:])}, rc={r.returncode}, stderr={r.stderr[:100] if r.stderr else 'none'}")
        if r.returncode == 0:
            log(f"Workflow: stage '{node.get('name', current_id)}' started for session {session_id[:16]}")
            return True, 'Stage started'
        err_text = strip_ansi(r.stderr.strip() or r.stdout.strip()[:200] or 'Unknown error')[:200]
        if staff_model and ('Model not found' in err_text or 'UnknownError' in err_text):
            cmd_nomodel = [c for c in cmd if c not in ('-m', staff_model)]
            r2 = subprocess.run(cmd_nomodel, capture_output=True, text=True, timeout=180)
            if r2.returncode == 0:
                log(f"Workflow: stage '{node.get('name', current_id)}' started (no model)")
                return True, 'Stage started (model ignored)'
            err_text = strip_ansi(r2.stderr.strip() or r2.stdout.strip()[:200] or 'Unknown error')[:200]
        return False, err_text
    except subprocess.TimeoutExpired:
        return False, 'Timeout starting stage'
    except Exception as e:
        return False, str(e)[:200]

def _handle_workflow_save(body: dict) -> tuple:
    """Create or update a workflow definition."""
    wf = body.get('workflow', {})
    if not wf.get('id') or not wf.get('name') or not wf.get('nodes'):
        return False, {'ok': False, 'message': 'Missing id, name, or nodes'}
    workflows = _load_workflows()
    existing = next((w for w in workflows if w['id'] == wf['id']), None)
    now = time.time()
    if existing:
        existing.update(wf)
        existing['updated'] = now
    else:
        wf['created'] = now
        wf['updated'] = now
        workflows.append(wf)
    _save_workflows(workflows)
    log(f"Workflow saved: {wf['name']} ({wf['id']})")
    return True, {'ok': True, 'workflow': wf}

def _handle_workflow_delete(body: dict) -> tuple:
    """Delete a workflow definition."""
    wf_id = body.get('id', '')
    if not wf_id:
        return False, {'ok': False, 'message': 'Missing workflow id'}
    workflows = _load_workflows()
    workflows = [w for w in workflows if w['id'] != wf_id]
    _save_workflows(workflows)
    log(f"Workflow deleted: {wf_id}")
    return True, {'ok': True, 'message': 'Workflow deleted'}

def _handle_workflow_attach(body: dict) -> tuple:
    """Attach a workflow to a session and start stage 1."""
    session_id = body.get('session_id', '')
    workflow_id = body.get('workflow_id', '')
    log(f"[WF ATTACH] Called with session_id={session_id[:16] if session_id else '?'}, workflow_id={workflow_id[:16] if workflow_id else '?'}")
    if not session_id or not workflow_id:
        return False, {'ok': False, 'message': 'Missing session_id or workflow_id'}
    workflows = _load_workflows()
    wf = next((w for w in workflows if w['id'] == workflow_id), None)
    if not wf:
        return False, {'ok': False, 'message': 'Workflow not found'}
    nodes = wf.get('nodes', [])
    if not nodes:
        return False, {'ok': False, 'message': 'Workflow has no nodes'}
    edges = wf.get('edges', [])
    has_incoming = {e['to'] for e in edges}
    first = next((n for n in nodes if n['id'] not in has_incoming), nodes[0])
    node_states = {}
    for n in nodes:
        node_states[n['id']] = {'status': 'pending'}
    instance = {
        'session_id': session_id,
        'workflow_id': workflow_id,
        'status': 'running',
        'current_node': first['id'],
        'node_states': node_states,
        'paused': False,
        'started_at': time.time(),
        '_activate_on_complete': True,
    }
    with _workflow_lock:
        instances = _load_workflow_instances()
        instances = [i for i in instances if i['session_id'] != session_id]
        instances.append(instance)
        _save_workflow_instances(instances)
        log(f"[WF ATTACH] Instance saved (pending, _activate_on_complete)")
    return True, {'ok': True, 'message': 'Workflow attached', 'instance': instance}

def _handle_workflow_advance(body: dict) -> tuple:
    """Advance to the next stage in the workflow."""
    session_id = body.get('session_id', '')
    if not session_id:
        return False, {'ok': False, 'message': 'Missing session_id'}
    with _workflow_lock:
        instances = _load_workflow_instances()
        instance = next((i for i in instances if i['session_id'] == session_id), None)
        if not instance:
            return False, {'ok': False, 'message': 'No workflow instance for this session'}
        if instance['status'] == 'completed':
            return False, {'ok': False, 'message': 'Workflow already completed'}
        workflows = _load_workflows()
        wf = next((w for w in workflows if w['id'] == instance['workflow_id']), None)
        if not wf:
            return False, {'ok': False, 'message': 'Workflow definition not found'}
        nodes = wf.get('nodes', [])
        edges = wf.get('edges', [])
        current_id = instance.get('current_node')
        node_states = instance.get('node_states', {})

        # Mark current node as completed
        if current_id and current_id in node_states:
            node_states[current_id]['status'] = 'completed'
            node_states[current_id]['completed_at'] = time.time()

        # Find next node via edges
        next_id = None
        for e in edges:
            if e['from'] == current_id:
                next_id = e['to']
                break
        if not next_id:
            instance['status'] = 'completed'
            instance['current_node'] = None
            _save_workflow_instances(instances)
            log(f"Workflow completed for session {session_id[:16]}")
            return True, {'ok': True, 'message': 'Workflow completed'}

        # Start next stage
        instance['current_node'] = next_id
        node_states[next_id]['status'] = 'running'
        _save_workflow_instances(instances)
    ok, msg = _run_workflow_stage(instance)
    if ok:
        log(f"Workflow advanced: session {session_id[:16]} -> stage '{next_id}'")
        return True, {'ok': True, 'message': 'Advanced to next stage'}
    with _workflow_lock:
        instances = _load_workflow_instances()
        inst = next((i for i in instances if i['session_id'] == session_id), None)
        if inst:
            ns = inst.get('node_states', {})
            if next_id in ns:
                ns[next_id]['status'] = 'failed'
            inst['status'] = 'failed'
            _save_workflow_instances(instances)
    return False, {'ok': False, 'message': msg}

def _handle_workflow_pause(body: dict) -> tuple:
    """Toggle pause/resume on a workflow instance."""
    session_id = body.get('session_id', '')
    if not session_id:
        return False, {'ok': False, 'message': 'Missing session_id'}
    with _workflow_lock:
        instances = _load_workflow_instances()
        instance = next((i for i in instances if i['session_id'] == session_id), None)
        if not instance:
            return False, {'ok': False, 'message': 'No workflow instance for this session'}
        instance['paused'] = not instance.get('paused', False)
        _save_workflow_instances(instances)
        state = 'paused' if instance['paused'] else 'resumed'
    log(f"Workflow {state} for session {session_id[:16]}")
    return True, {'ok': True, 'message': f'Workflow {state}', 'paused': instance['paused']}

def _handle_cron_jobs_run(body: dict) -> tuple:
    job_id = body.get('id', '')
    if not job_id:
        return False, {'ok': False, 'message': 'Missing id'}
    from cron import _load_cron_jobs, _save_cron_jobs, _run_cron_job
    jobs = _load_cron_jobs()
    found = None
    for j in jobs:
        if j['id'] == job_id:
            found = j
            break
    if not found:
        return False, {'ok': False, 'message': 'Job not found'}
    found['last_run'] = 0
    found['_running'] = True
    _save_cron_jobs(jobs)
    threading.Thread(target=_run_cron_job, args=(found,), daemon=True).start()
    log(f"Admin: triggered cron job '{found.get('name', '?')}'")
    return True, {'ok': True, 'message': 'Job triggered'}
