#!/usr/bin/env python3
import http.server
import json
import subprocess
import os
import signal
import sys
import urllib.parse
import mimetypes
import threading
import time
import base64
import secrets
import stat

_session_locks = {}
_session_locks_guard = threading.Lock()

def _get_session_lock(sid):
    with _session_locks_guard:
        if sid not in _session_locks:
            _session_locks[sid] = threading.Lock()
        return _session_locks[sid]

DATA_DIR = os.path.expanduser('~/.opencode-dashboard/data')
PID_FILE = os.path.join(DATA_DIR, 'daemon.pid')
ACTIVITY_FILE = os.path.join(DATA_DIR, 'activity.log')
CRON_FILE = os.path.join(DATA_DIR, 'cron_jobs.json')
QUEUE_FILE = os.path.join(DATA_DIR, 'request_queue.json')
STATIC_DIR = os.path.expanduser('~/.opencode-dashboard')
API_KEY_FILE = os.path.join(DATA_DIR, 'api_key')

def _load_or_generate_api_key():
    key = os.environ.get('DASHBOARD_API_KEY', '').strip()
    if key:
        return key
    if os.path.exists(API_KEY_FILE):
        try:
            with open(API_KEY_FILE) as _f:
                key = _f.read().strip()
            if key:
                return key
        except Exception:
            pass
    key = secrets.token_urlsafe(32)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(API_KEY_FILE, 'w') as _f:
        _f.write(key + '\n')
    os.chmod(API_KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
    print(f'\n[Dashboard] New API key generated \u2014 copy this to your Android app Settings > API Key:\n  {key}\n  (saved to {API_KEY_FILE})\n', flush=True)
    return key

_API_KEY = _load_or_generate_api_key()

import re

def _safe_agent_name(name):
    return re.sub(r'[^a-z0-9_\-]', '', name.replace(' ', '_').lower())
_ansi_re = re.compile('\x1b\\[[0-9;]*[a-zA-Z]')

def strip_ansi(s):
    return _ansi_re.sub('', s)

def log(msg):
    try:
        ts = __import__('datetime').datetime.now().strftime('%H:%M:%S')
        with open(ACTIVITY_FILE, 'a') as f:
            f.write(f'[{ts}] {msg}\n')
    except:
        pass

_attach_cache = {'url': '', 'time': 0}
def get_attach_url(force=False):
    now = time.time()
    if not force and now - _attach_cache.get('time', 0) < 30 and _attach_cache.get('url'):
        return _attach_cache['url']
    try:
        r = subprocess.run(['lsof', '-iTCP', '-sTCP:LISTEN', '-P', '-n'], capture_output=True, text=True, timeout=3)
        for line in r.stdout.split('\n'):
            if 'OpenCode' in line:
                parts = line.split()
                for p in parts:
                    if ':' in p and len(p.split(':')[1]) == 5:
                        try:
                            port = int(p.split(':')[1])
                            _attach_cache['url'] = f'http://127.0.0.1:{port}'
                            _attach_cache['time'] = now
                            return _attach_cache['url']
                        except:
                            pass
    except:
        pass
    _attach_cache['url'] = 'http://127.0.0.1:51384'
    _attach_cache['time'] = now
    return _attach_cache['url']

def _check_engine(attach=None):
    password = os.environ.get('OPENCODE_SERVER_PASSWORD', '')
    if attach is None:
        attach = get_attach_url()
    if engine_is_reachable(attach, password):
        return attach
    attach = get_attach_url(force=True)
    if engine_is_reachable(attach, password):
        return attach
    return None

def get_engine_restarted():
    status_path = os.path.join(DATA_DIR, 'status.json')
    if os.path.exists(status_path):
        try:
            with open(status_path) as f:
                sd = json.load(f)
            return sd.get('summary', {}).get('engine_restarted_at')
        except:
            pass
    return None

def engine_is_reachable(url, password=''):
    if not url:
        return False
    try:
        cmd = ['curl', '-s', '--max-time', '3', '-o', '/dev/null', '-w', '%{http_code}']
        if password:
            cmd.extend(['-u', f'opencode:{password}'])
        cmd.append(url.rstrip('/') + '/api/ping')
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return r.returncode == 0 and r.stdout.strip().startswith('2')
    except:
        return False

def _load_cron_jobs():
    if not os.path.exists(CRON_FILE):
        return []
    try:
        with open(CRON_FILE) as f:
            return json.load(f)
    except:
        return []

def _save_cron_jobs(jobs):
    with open(CRON_FILE, 'w') as f:
        json.dump(jobs, f, indent=2)

def _run_cron_job(job):
    status = 'unknown'
    try:
        attach = get_attach_url()
        action = job.get('action', {})
        cwd = action.get('directory') or None
        cmd = ['opencode', 'run']
        if action.get('type') == 'session' and action.get('session_id'):
            cmd.extend(['-s', action['session_id']])
            if action.get('fork', False):
                cmd.extend(['--fork'])
        else:
            cmd.extend(['-c'])
        cmd.extend(['--attach', attach])
        password = os.environ.get('OPENCODE_SERVER_PASSWORD', '')
        if password:
            cmd.extend(['-p', password])
        if action.get('model'):
            cmd.extend(['-m', action['model']])
        staff_name = action.get('staff', '')
        if staff_name:
            sf_path = os.path.join(DATA_DIR, 'super_staff.json')
            if os.path.exists(sf_path):
                try:
                    with open(sf_path) as f:
                        for s in json.load(f):
                            if s.get('name') == staff_name:
                                s_mode = s.get('mode', '')
                                if s_mode:
                                    cmd.extend(['--agent', s_mode])
                                s_model = s.get('model', '')
                                if s_model and not action.get('model'):
                                    cmd.extend(['-m', s_model])
                                break
                except:
                    pass
        elif action.get('mode'):
            cmd.extend(['--agent', action['mode']])
        if action.get('directory'):
            cmd.extend(['--dir', action['directory']])
        message = action.get('message', '')
        cmd.append(message)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=cwd)
        status = 'done' if r.returncode == 0 else 'fail: ' + strip_ansi(r.stderr.strip()[:100] or r.stdout.strip()[:100] or 'unknown')
    except subprocess.TimeoutExpired:
        status = 'fail: timeout (>5m)'
    except Exception as e:
        status = 'fail: ' + str(e)[:100]
    finally:
        try:
            jobs = _load_cron_jobs()
            for j in jobs:
                if j['id'] == job['id']:
                    j['last_run'] = time.time()
                    j['last_status'] = status
                    j.pop('_running', None)
                    break
            _save_cron_jobs(jobs)
            log(f"Cron job '{job.get('name', '?')}': {status}")
        except:
            pass

def _cron_runner():
    while True:
        try:
            time.sleep(30)
            jobs = _load_cron_jobs()
            if not isinstance(jobs, list):
                continue
            now = time.time()
            for job in jobs:
                if not job.get('enabled', True):
                    continue
                last_run = job.get('last_run', 0)
                interval = job.get('interval_sec', 300)
                if now - last_run < interval:
                    continue
                if job.get('_running'):
                    continue
                job['_running'] = True
                _save_cron_jobs(jobs)
                threading.Thread(target=_run_cron_job, args=(job,), daemon=True).start()
        except:
            pass

# ── QUEUE INFRASTRUCTURE ──

_queue_lock = threading.Lock()

def _load_queue():
    if not os.path.exists(QUEUE_FILE):
        return []
    try:
        with open(QUEUE_FILE) as f:
            items = json.load(f)
        now = time.time()
        items = [i for i in items if now - i.get('created_at', 0) < 300 or i.get('status') in ('processing', 'queued')]
        return items
    except:
        return []

def _save_queue(items):
    with _queue_lock:
        now = time.time()
        items = [i for i in items if now - i.get('created_at', 0) < 300 or i.get('status') in ('processing', 'queued')]
        try:
            with open(QUEUE_FILE, 'w') as f:
                json.dump(items, f, indent=2)
        except:
            pass

# ── QUEUE DISPATCH HANDLERS ──

def _handle_stop_session(body):
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

def _handle_session_instruct(body):
    sid = body.get('id', '')
    message = body.get('message', '')
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
            msg = 'OpenCode engine is not reachable \u2014 please relaunch the app.'
            if engine_restarted:
                msg += ' (Engine was restarted)'
            log(f"Admin: engine not reachable")
            return False, {'ok': False, 'message': msg, 'code': 'engine_unreachable'}
        if engine_restarted:
            log(f"Admin: engine restart detected, session {sid} invalid")
            return False, {'ok': False, 'message': 'OpenCode engine was restarted \u2014 all prior sessions are invalid. Create a new case.', 'code': 'engine_restarted'}
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
            c.append(message)
            return c
        cmd = _build_cmd(fork=fork_val)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=cwd)
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
            cmd_fallback.append(message)
            r2 = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=120, cwd=cwd)
            if r2.returncode == 0:
                log(f"Admin: created new session from continue (was {sid})")
                return True, {'ok': True, 'message': 'This case has ended \u2014 a new case was created with your instruction.'}
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
            cmd_retry.append(message)
            r3 = subprocess.run(cmd_retry, capture_output=True, text=True, timeout=60, cwd=cwd)
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

def _handle_session_answer(body):
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
            msg = 'OpenCode engine is not reachable \u2014 cannot send answer.'
            if engine_restarted:
                msg += ' (Engine was restarted)'
            log(f"Admin: answer failed \u2014 engine not reachable")
            return False, {'ok': False, 'message': msg, 'code': 'engine_unreachable'}
        if engine_restarted:
            log(f"Admin: engine restart detected, session {sid} invalid for answer")
            return False, {'ok': False, 'message': 'Session no longer available \u2014 the engine was restarted.', 'code': 'engine_restarted'}
        answer_text = 'I choose: ' + '; '.join(str(a) for a in answers)
        cmd = ['opencode', 'run', '-s', sid, '--attach', attach]
        if password:
            cmd.extend(['-p', password])
        cmd.append(answer_text)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=cwd)
        if r.returncode == 0:
            log(f"Admin: answered session {sid}")
            return True, {'ok': True, 'message': 'Answer sent'}
        if engine_restarted or 'Session not found' in (r.stderr or ''):
            log(f"Admin: session {sid} stale for answer (engine restart)")
            return False, {'ok': False, 'message': 'Session no longer available \u2014 the engine was restarted.', 'code': 'engine_restarted'}
        if r.returncode == 124 or 'already running' in (r.stderr or '').lower() or 'already active' in (r.stderr or '').lower():
            log(f"Admin: session {sid} already busy, answer queued")
            return True, {'ok': True, 'message': 'Session is busy \u2014 answer will be picked up when ready'}
        return False, {'ok': False, 'message': (r.stderr.strip() or r.stdout.strip()[:200] or 'Unknown error')[:200]}
    except subprocess.TimeoutExpired:
        return False, {'ok': False, 'message': 'Timeout sending answer'}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}
    finally:
        _get_session_lock(sid).release()

def _handle_new_session(body):
    title = body.get('title', '')
    message = body.get('message', '')
    directory = body.get('directory', '')
    model = body.get('model', '')
    mode_val = body.get('mode', '')
    if not message:
        return False, {'ok': False, 'message': 'Missing message'}
    try:
        cwd = directory or None
        password = os.environ.get('OPENCODE_SERVER_PASSWORD', '')
        attach = _check_engine()
        if not attach:
            msg = 'OpenCode engine is not reachable \u2014 please relaunch the app.'
            log(f"Admin: new session failed \u2014 engine not reachable")
            return False, {'ok': False, 'message': msg, 'code': 'engine_unreachable'}
        engine_restarted = get_engine_restarted()
        cmd = ['opencode', 'run']
        if engine_restarted:
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
                except:
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
        if r.returncode == 0:
            log(f"Admin: new session started \"{title or message[:40]}\"")
            return True, {'ok': True, 'message': 'Session started'}
        return False, {'ok': False, 'message': (r.stderr.strip() or r.stdout.strip()[:200] or 'Unknown error')[:200]}
    except subprocess.TimeoutExpired:
        return False, {'ok': False, 'message': 'Timeout starting session'}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_provider_logout(body):
    name = body.get('provider', '')
    if not name:
        return False, {'ok': False, 'message': 'Missing provider name'}
    try:
        r = subprocess.run(['opencode', 'providers', 'logout', name], capture_output=True, text=True, timeout=15)
        log(f"Admin: logged out from {name}")
        return True, {'ok': True, 'message': 'Logged out'}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_provider_login(body):
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

def _handle_ollama_add(body):
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

def _handle_ollama_remove(body):
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

def _handle_super_staff_create(body):
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

def _handle_super_staff_delete(body):
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

def _handle_super_staff_update(body):
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
                except:
                    pass
        log(f"Admin: updated super staff '{original_name}' -> '{name}'")
        return True, {'ok': True, 'message': f'Agent {name} updated'}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_super_staff_assign(body):
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
        except:
            pass
    if staff_name:
        assignments[session_id] = staff_name
    else:
        assignments.pop(session_id, None)
    with open(assign_file, 'w') as f:
        json.dump(assignments, f, indent=2)
    log(f"Admin: {'assigned' if staff_name else 'unassigned'} staff '{staff_name}' to session {session_id[:16]}")
    return True, {'ok': True, 'message': f"Staff {'assigned' if staff_name else 'unassigned'}"}

def _handle_rename_session(body):
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
        log(f"Admin: renamed session {sid[:16]} \u2192 \"{new_title}\"")
        return True, {'ok': True, 'message': 'Case renamed'}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_restart_daemon(body):
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

def _handle_kill_daemon(body):
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

def _handle_upload_photo(body):
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

def _handle_remove_photo(body):
    dest = os.path.join(STATIC_DIR, 'assets', 'profile_photo.png')
    if os.path.exists(dest):
        os.remove(dest)
    return True, {'ok': True}

def _handle_save_boss_name(body):
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

def _handle_api_key_regenerate(body):
    new_key = secrets.token_urlsafe(32)
    try:
        with open(API_KEY_FILE, 'w') as _f:
            _f.write(new_key + '\n')
        os.chmod(API_KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
        global _API_KEY
        _API_KEY = new_key
        log('Admin: API key regenerated')
        return True, {'ok': True, 'key': new_key}
    except Exception as e:
        return False, {'ok': False, 'message': str(e)[:200]}

def _handle_cron_jobs_create(body):
    name = body.get('name', '').strip()
    interval_sec = int(body.get('interval_sec', 300))
    action = body.get('action', {})
    if not name or not action.get('message', '').strip():
        return False, {'ok': False, 'message': 'Missing name or message'}
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

def _handle_cron_jobs_update(body):
    job_id = body.get('id', '')
    name = body.get('name', '').strip()
    interval_sec = int(body.get('interval_sec', 300))
    action = body.get('action', {})
    if not job_id or not name or not action.get('message', '').strip():
        return False, {'ok': False, 'message': 'Missing id, name or message'}
    jobs = _load_cron_jobs()
    for j in jobs:
        if j['id'] == job_id:
            j['name'] = name
            j['interval_sec'] = max(60, interval_sec)
            j['action'] = action
            break
    _save_cron_jobs(jobs)
    return True, {'ok': True, 'message': 'Cron job updated'}

def _handle_cron_jobs_delete(body):
    job_id = body.get('id', '')
    if not job_id:
        return False, {'ok': False, 'message': 'Missing id'}
    jobs = _load_cron_jobs()
    jobs = [j for j in jobs if j['id'] != job_id]
    _save_cron_jobs(jobs)
    return True, {'ok': True, 'message': 'Cron job deleted'}

def _handle_cron_jobs_toggle(body):
    job_id = body.get('id', '')
    if not job_id:
        return False, {'ok': False, 'message': 'Missing id'}
    jobs = _load_cron_jobs()
    for j in jobs:
        if j['id'] == job_id:
            j['enabled'] = not j.get('enabled', True)
            break
    _save_cron_jobs(jobs)
    return True, {'ok': True, 'message': 'Toggled'}

def _handle_cron_jobs_run(body):
    job_id = body.get('id', '')
    if not job_id:
        return False, {'ok': False, 'message': 'Missing id'}
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

# Dispatch table
_QUEUE_HANDLERS = {
    'stop-session': _handle_stop_session,
    'session-instruct': _handle_session_instruct,
    'session-answer': _handle_session_answer,
    'new-session': _handle_new_session,
    'provider-logout': _handle_provider_logout,
    'provider-login': _handle_provider_login,
    'ollama-add': _handle_ollama_add,
    'ollama-remove': _handle_ollama_remove,
    'super-staff-create': _handle_super_staff_create,
    'super-staff-delete': _handle_super_staff_delete,
    'super-staff-update': _handle_super_staff_update,
    'super-staff-assign': _handle_super_staff_assign,
    'rename-session': _handle_rename_session,
    'restart-daemon': _handle_restart_daemon,
    'kill-daemon': _handle_kill_daemon,
    'upload-photo': _handle_upload_photo,
    'remove-photo': _handle_remove_photo,
    'save-boss-name': _handle_save_boss_name,
    'api-key/regenerate': _handle_api_key_regenerate,
    'cron-jobs/create': _handle_cron_jobs_create,
    'cron-jobs/update': _handle_cron_jobs_update,
    'cron-jobs/delete': _handle_cron_jobs_delete,
    'cron-jobs/toggle': _handle_cron_jobs_toggle,
    'cron-jobs/run': _handle_cron_jobs_run,
}

def _queue_dispatch(item):
    typ = item.get('type', '')
    body = item.get('payload', {})
    handler = _QUEUE_HANDLERS.get(typ)
    if not handler:
        return False, {'ok': False, 'message': f'Unknown queue type: {typ}'}
    return handler(body)

def _queue_processor():
    while True:
        try:
            items = _load_queue()
            found = None
            for i in items:
                if i.get('status') == 'queued':
                    found = i
                    break
            if found:
                found['status'] = 'processing'
                _save_queue(items)
                try:
                    ok, result = _queue_dispatch(found)
                except Exception as e:
                    ok, result = False, {'ok': False, 'message': str(e)[:200]}
                found['status'] = 'done' if ok else 'failed'
                found['result'] = result
                if not ok:
                    found['error'] = str(result.get('message', 'Unknown error'))[:200]
                _save_queue(items)
                log(f"Queue {found['id']}: {found['type']} \u2192 {'done' if ok else 'failed'}")
            else:
                time.sleep(1)
        except:
            time.sleep(1)

class UnifiedHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def list_directory(self, path):
        self.send_error(403, 'Directory listing denied')

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _check_api_key(self):
        return self.headers.get('X-API-Key', '') == _API_KEY

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/api/queue':
            if not self._check_api_key():
                self._json({'ok': False, 'message': 'Unauthorized'}, 401)
                return
            typ = body.get('type', '')
            payload = body.get('payload', {})
            if not typ:
                self._json({'ok': False, 'message': 'Missing type'}, 400)
                return
            item = {
                'id': 'q_' + secrets.token_hex(6),
                'type': typ,
                'payload': payload,
                'status': 'queued',
                'result': None,
                'error': None,
                'created_at': time.time()
            }
            items = _load_queue()
            items.append(item)
            _save_queue(items)
            self._json({'queueId': item['id'], 'status': 'queued'}, 202)
            return

        self._json({'ok': False, 'message': 'Use POST /api/queue'}, 404)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith('/api/'):
            if path == '/api/ping':
                daemon_alive = False
                if os.path.exists(PID_FILE):
                    try:
                        with open(PID_FILE) as f:
                            pid = int(f.read().strip())
                        os.kill(pid, 0)
                        daemon_alive = True
                    except:
                        pass
                self._json({'ok': True, 'daemon_alive': daemon_alive, 'timestamp': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')})
                return

            if path == '/api/notifications':
                status_path = os.path.join(DATA_DIR, 'status.json')
                if os.path.exists(status_path):
                    with open(status_path) as f:
                        data = json.load(f)
                    all_sessions = data.get('all_sessions', []) or []
                    summary = {
                        'version': int(os.path.getmtime(status_path) * 1000),
                        'sessions': [{'id': s.get('id'), 'title': s.get('title', ''), 'state': s.get('state', ''), 'updated': s.get('updated')} for s in all_sessions]
                    }
                    self._json(summary)
                else:
                    self._json({'version': 0, 'sessions': []})
                return

            if path == '/api/super-staff':
                staff_file = os.path.join(DATA_DIR, 'super_staff.json')
                staff = []
                if os.path.exists(staff_file):
                    try:
                        with open(staff_file) as f:
                            staff = json.load(f)
                    except:
                        pass
                self._json({'ok': True, 'staff': staff})
                return

            if path == '/api/super-staff-assignments':
                assign_file = os.path.join(DATA_DIR, 'case_assignments.json')
                assignments = {}
                if os.path.exists(assign_file):
                    try:
                        with open(assign_file) as f:
                            assignments = json.load(f)
                    except:
                        pass
                self._json({'ok': True, 'assignments': assignments})
                return

            if path == '/api/cron-jobs':
                jobs = _load_cron_jobs()
                self._json({'ok': True, 'jobs': jobs})
                return

            if path == '/api/api-key':
                masked = (_API_KEY[:6] + '\u2026' + _API_KEY[-4:]) if len(_API_KEY) > 10 else '****'
                self._json({'ok': True, 'key': _API_KEY, 'masked': masked})
                return

            if path == '/api/providers':
                providers = []
                ollama_list = []
                try:
                    auth_file = os.path.expanduser('~/.local/share/opencode/auth.json')
                    if not os.path.exists(auth_file):
                        auth_file = os.path.expanduser('~/Library/Application Support/opencode/auth.json')
                    if os.path.exists(auth_file):
                        with open(auth_file) as f:
                            auth_data = json.load(f)
                        for name, info in auth_data.items():
                            providers.append({
                                'name': name,
                                'type': info.get('type', 'unknown'),
                                'status': 'active'
                            })
                    ollama_config = os.path.join(DATA_DIR, 'ollama_config.json')
                    if os.path.exists(ollama_config):
                        with open(ollama_config) as f:
                            ollama_list = json.load(f)
                    else:
                        ollama_list = [{'url': 'https://ollama.brandon.my'}]
                    for o in ollama_list:
                        try:
                            rr = subprocess.run(['curl', '-s', '--max-time', '3', o['url'] + '/api/tags'],
                                capture_output=True, text=True, timeout=5)
                            if rr.returncode == 0:
                                o_data = json.loads(rr.stdout)
                                o['status'] = 'online'
                                o['models'] = len(o_data.get('models', []))
                            else:
                                o['status'] = 'offline'
                                o['models'] = 0
                        except:
                            o['status'] = 'offline'
                            o['models'] = 0
                    self._json({'ok': True, 'providers': providers, 'ollama': ollama_list})
                except Exception as e:
                    self._json({'ok': False, 'message': str(e)[:200]}, 500)
                return

            # Queue polling: GET /api/queue/<id>
            if path.startswith('/api/queue/'):
                qid = path[len('/api/queue/'):]
                if not qid:
                    self._json({'ok': False, 'message': 'Missing queue ID'}, 400)
                    return
                items = _load_queue()
                for i in items:
                    if i['id'] == qid:
                        self._json({
                            'status': i['status'],
                            'result': i.get('result'),
                            'error': i.get('error'),
                            'created_at': i.get('created_at')
                        })
                        return
                self._json({'ok': False, 'message': 'Queue item not found'}, 404)
                return

            self._json({'ok': False, 'message': 'Not found'}, 404)
            return

        try:
            super().do_GET()
        except Exception as e:
            log(f"Static file error: {e}")
            self.send_error(500, 'Internal Server Error')

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    threading.Thread(target=_cron_runner, daemon=True).start()
    threading.Thread(target=_queue_processor, daemon=True).start()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5500
    server = http.server.ThreadingHTTPServer(('127.0.0.1', port), UnifiedHandler)
    print(f"Dashboard server running on http://localhost:{port}")
    server.serve_forever()
