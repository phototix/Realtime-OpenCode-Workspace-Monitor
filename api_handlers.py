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
    DATA_DIR, PID_FILE, STATIC_DIR, API_KEY_FILE, CRON_FILE,
    NOTIFICATION_PROVIDERS_FILE,
    _get_api_key, _set_api_key, _safe_agent_name, strip_ansi,
    _get_session_lock, _check_engine, get_engine_restarted,
    get_attach_url, engine_is_reachable, log, _error_id,
    _load_notifications, _save_notifications,
    _load_notification_providers, _save_notification_providers
)

def _handle_stop_session(body: dict) -> tuple:
    sid = body.get('id', '')
    if not sid:
        return False, {'ok': False, 'message': 'Missing session id'}
    try:
        cwd = body.get('directory') or None
        r = subprocess.run(['opencode', 'session', 'delete', sid], capture_output=True, text=True, timeout=15, cwd=cwd)
        if r.returncode == 0:
            log(f"Admin: deleted session {sid}")
            return True, {'ok': True, 'message': 'Session deleted'}
        return False, {'ok': False, 'message': r.stderr.strip() or 'Unknown error'}
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
        if title:
            cmd.extend(['--title', title])
        if model:
            cmd.extend(['-m', model])
        if mode_val:
            cmd.extend(['--agent', mode_val])
        if directory:
            cmd.extend(['--dir', directory])
        cmd.append(message)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=cwd)
        if fresh:
            session_created = '"sessionID"' in r.stdout or r.returncode == 0
            if session_created:
                log(f"Admin: fresh session started \"{title or message[:40]}\"")
                return True, {'ok': True, 'message': 'Session started'}
            return False, {'ok': False, 'message': (r.stderr.strip() or r.stdout.strip()[:200] or 'Unknown error')[:200]}
        if r.returncode == 0:
            log(f"Admin: new session started \"{title or message[:40]}\"")
            return True, {'ok': True, 'message': 'Session started'}
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
        dest = os.path.join(DATA_DIR, 'boss_name.json')
        with open(dest, 'w') as f:
            json.dump({'name': name}, f)
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

def _send_webhook(provider: dict, test_message: str = '') -> tuple:
    url = provider.get('webhook_url', '').strip()
    ptype = provider.get('type', 'custom')
    name = provider.get('name', 'Notification')
    message = test_message or f'Test notification from {name}'
    if not url:
        return False, 'Webhook URL is empty'
    if ptype == 'slack':
        payload = json.dumps({'text': message, 'username': 'MyDora Dashboard'})
    elif ptype == 'discord':
        payload = json.dumps({'content': message})
    else:
        payload = json.dumps({'message': message, 'provider': name, 'timestamp': time.time()})
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
    provider = {
        'id': 'np_' + secrets.token_hex(6),
        'name': name,
        'type': ptype,
        'webhook_url': webhook_url,
        'enabled': True,
        'created_at': time.time()
    }
    providers.append(provider)
    _save_notification_providers(providers)
    log(f"Notification provider created: {name} ({ptype})")
    return True, {'ok': True, 'provider': provider}

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
