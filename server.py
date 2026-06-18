#!/usr/bin/env python3
import http.server
import json
import subprocess
import os
import signal
import sys
import urllib.parse
import mimetypes

DATA_DIR = os.path.expanduser('~/.opencode-dashboard/data')
PID_FILE = os.path.join(DATA_DIR, 'daemon.pid')
ACTIVITY_FILE = os.path.join(DATA_DIR, 'activity.log')
STATIC_DIR = os.path.expanduser('~/.opencode-dashboard')

import re
_ansi_re = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

def strip_ansi(s):
    return _ansi_re.sub('', s)

def log(msg):
    try:
        ts = __import__('datetime').datetime.now().strftime('%H:%M:%S')
        with open(ACTIVITY_FILE, 'a') as f:
            f.write(f'[{ts}] {msg}\n')
    except:
        pass

def get_attach_url():
    try:
        r = subprocess.run(['lsof', '-i', '-P', '-n'], capture_output=True, text=True, timeout=5)
        for line in r.stdout.split('\n'):
            if 'OpenCode' in line and '(LISTEN)' in line:
                parts = line.split()
                for p in parts:
                    if ':' in p and len(p.split(':')[1]) == 5:
                        try:
                            port = int(p.split(':')[1])
                            return f'http://127.0.0.1:{port}'
                        except:
                            pass
    except:
        pass
    return 'http://127.0.0.1:51384'

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

class UnifiedHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/api/stop-session':
            sid = body.get('id', '')
            if not sid:
                self._json({'ok': False, 'message': 'Missing session id'}, 400)
                return
            try:
                cwd = body.get('directory') or None
                r = subprocess.run(['opencode', 'session', 'delete', sid], capture_output=True, text=True, timeout=15, cwd=cwd)
                if r.returncode == 0:
                    log(f"Admin: deleted session {sid}")
                    self._json({'ok': True, 'message': 'Session deleted'})
                else:
                    self._json({'ok': False, 'message': r.stderr.strip() or 'Unknown error'}, 500)
            except subprocess.TimeoutExpired:
                self._json({'ok': False, 'message': 'Timeout stopping session'}, 500)
            except Exception as e:
                self._json({'ok': False, 'message': str(e)[:200]}, 500)

        elif path == '/api/session-instruct':
            sid = body.get('id', '')
            message = body.get('message', '')
            directory = body.get('directory', '')
            model = body.get('model', '')
            mode_val = body.get('mode', '')
            if not sid or not message:
                self._json({'ok': False, 'message': 'Missing session id or message'}, 400)
                return
            try:
                cwd = directory or None
                attach = get_attach_url()
                password = os.environ.get('OPENCODE_SERVER_PASSWORD', '')

                # Check engine reachability before anything else
                engine_restarted = get_engine_restarted()
                if not engine_is_reachable(attach, password):
                    msg = 'OpenCode engine is not reachable — please relaunch the app.'
                    if engine_restarted:
                        msg += ' (Engine was restarted)'
                    log(f"Admin: engine not reachable at {attach}")
                    self._json({'ok': False, 'message': msg, 'code': 'engine_unreachable'}, 500)
                    return

                if engine_restarted:
                    log(f"Admin: engine restart detected, session {sid} invalid")
                    self._json({'ok': False, 'message': 'OpenCode engine was restarted — all prior sessions are invalid. Create a new case.', 'code': 'engine_restarted'}, 500)
                    return

                def _build_cmd(with_session=True):
                    c = ['opencode', 'run']
                    if with_session:
                        c.extend(['-s', sid])
                    else:
                        c.extend(['-c'])
                    c.extend(['--attach', attach])
                    if password:
                        c.extend(['-p', password])
                    if model:
                        c.extend(['-m', model])
                    if mode_val:
                        c.extend(['--agent', mode_val])
                    c.append(message)
                    return c

                cmd = _build_cmd(with_session=True)
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=cwd)
                if r.returncode == 0:
                    log(f"Admin: instructed session {sid}")
                    self._json({'ok': True, 'message': 'Instruction sent'})
                    return

                err_text = strip_ansi(r.stderr.strip() or r.stdout.strip()[:200] or 'Unknown error')[:200]

                # If session not found (completed/archived), fall back to continuing last session
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
                        self._json({'ok': True, 'message': 'This case has ended — a new case was created with your instruction.'})
                        return
                    fb_err = strip_ansi(r2.stderr.strip() or r2.stdout.strip()[:200] or 'Unknown error')[:200]
                    log(f"Admin: fallback continue also failed: {fb_err[:100]}")
                    self._json({'ok': False, 'message': fb_err}, 500)
                    return

                # If model was the problem, retry without model
                if model and ('Model not found' in err_text or 'UnknownError' in err_text):
                    log(f"Admin: retrying session {sid} without model")
                    model = ''
                    cmd_retry = ['opencode', 'run', '-s', sid, '--attach', attach]
                    if password:
                        cmd_retry.extend(['-p', password])
                    if mode_val:
                        cmd_retry.extend(['--agent', mode_val])
                    cmd_retry.append(message)
                    r3 = subprocess.run(cmd_retry, capture_output=True, text=True, timeout=60, cwd=cwd)
                    if r3.returncode == 0:
                        log(f"Admin: instructed session {sid} (retry without model)")
                        self._json({'ok': True, 'message': 'Instruction sent (model ignored, using default)'})
                        return
                    err_text = strip_ansi(r3.stderr.strip() or r3.stdout.strip()[:200] or 'Unknown error')[:200]

                log(f"Admin: instruct failed: {err_text[:100]}")
                self._json({'ok': False, 'message': err_text}, 500)
            except subprocess.TimeoutExpired:
                log("Admin: instruct timeout")
                self._json({'ok': False, 'message': 'Timeout sending instruction'}, 500)
            except Exception as e:
                log(f"Admin: instruct unexpected error: {str(e)[:200]}")
                self._json({'ok': False, 'message': str(e)[:200]}, 500)

        elif path == '/api/session-answer':
            sid = body.get('id', '')
            answers = body.get('answers', [])
            if not sid or not answers:
                self._json({'ok': False, 'message': 'Missing session id or answers'}, 400)
                return
            try:
                cwd = body.get('directory') or None
                attach = get_attach_url()
                password = os.environ.get('OPENCODE_SERVER_PASSWORD', '')
                engine_restarted = get_engine_restarted()

                if not engine_is_reachable(attach, password):
                    msg = 'OpenCode engine is not reachable — cannot send answer.'
                    if engine_restarted:
                        msg += ' (Engine was restarted)'
                    log(f"Admin: answer failed — engine not reachable at {attach}")
                    self._json({'ok': False, 'message': msg, 'code': 'engine_unreachable'}, 500)
                    return

                if engine_restarted:
                    log(f"Admin: engine restart detected, session {sid} invalid for answer")
                    self._json({'ok': False, 'message': 'Session no longer available — the engine was restarted.', 'code': 'engine_restarted'}, 500)
                    return

                answer_text = 'I choose: ' + '; '.join(str(a) for a in answers)
                cmd = ['opencode', 'run', '-s', sid, '--attach', attach]
                if password:
                    cmd.extend(['-p', password])
                cmd.append(answer_text)
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=cwd)
                if r.returncode == 0:
                    log(f"Admin: answered session {sid}")
                    self._json({'ok': True, 'message': 'Answer sent'})
                elif engine_restarted or 'Session not found' in (r.stderr or ''):
                    log(f"Admin: session {sid} stale for answer (engine restart)")
                    self._json({'ok': False, 'message': 'Session no longer available — the engine was restarted.', 'code': 'engine_restarted'}, 500)
                elif r.returncode == 124 or 'already running' in (r.stderr or '').lower() or 'already active' in (r.stderr or '').lower():
                    log(f"Admin: session {sid} already busy, answer queued")
                    self._json({'ok': True, 'message': 'Session is busy — answer will be picked up when ready'})
                else:
                    self._json({'ok': False, 'message': (r.stderr.strip() or r.stdout.strip()[:200] or 'Unknown error')[:200]}, 500)
            except subprocess.TimeoutExpired:
                self._json({'ok': False, 'message': 'Timeout sending answer'}, 500)
            except Exception as e:
                self._json({'ok': False, 'message': str(e)[:200]}, 500)

        elif path == '/api/new-session':
            title = body.get('title', '')
            message = body.get('message', '')
            directory = body.get('directory', '')
            model = body.get('model', '')
            mode_val = body.get('mode', '')
            if not message:
                self._json({'ok': False, 'message': 'Missing message'}, 400)
                return
            try:
                cwd = directory or None
                attach = get_attach_url()
                password = os.environ.get('OPENCODE_SERVER_PASSWORD', '')

                # Check engine reachability
                if not engine_is_reachable(attach, password):
                    msg = 'OpenCode engine is not reachable — please relaunch the app.'
                    log(f"Admin: new session failed — engine not reachable at {attach}")
                    self._json({'ok': False, 'message': msg, 'code': 'engine_unreachable'}, 500)
                    return

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
                    self._json({'ok': True, 'message': 'Session started'})
                else:
                    self._json({'ok': False, 'message': (r.stderr.strip() or r.stdout.strip()[:200] or 'Unknown error')[:200]}, 500)
            except subprocess.TimeoutExpired:
                self._json({'ok': False, 'message': 'Timeout starting session'}, 500)
            except Exception as e:
                self._json({'ok': False, 'message': str(e)[:200]}, 500)

        elif path == '/api/providers':
            providers = []
            ollama_list = []
            try:
                # AI providers from auth.json
                auth_file = os.path.expanduser('~/.local/share/opencode/auth.json')
                if os.path.exists(auth_file):
                    with open(auth_file) as f:
                        auth_data = json.load(f)
                    for name, info in auth_data.items():
                        providers.append({
                            'name': name,
                            'type': info.get('type', 'unknown'),
                            'status': 'active'
                        })
                # Ollama connections from config file
                ollama_config = os.path.join(DATA_DIR, 'ollama_config.json')
                if os.path.exists(ollama_config):
                    with open(ollama_config) as f:
                        ollama_list = json.load(f)
                else:
                    ollama_list = [{'url': 'https://ollama.brandon.my'}]
                # Probe each Ollama URL
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

        elif path == '/api/provider-logout':
            name = body.get('provider', '')
            if not name:
                self._json({'ok': False, 'message': 'Missing provider name'}, 400)
                return
            try:
                r = subprocess.run(['opencode', 'providers', 'logout', name], capture_output=True, text=True, timeout=15)
                log(f"Admin: logged out from {name}")
                self._json({'ok': True, 'message': 'Logged out'})
            except Exception as e:
                self._json({'ok': False, 'message': str(e)[:200]}, 500)

        elif path == '/api/provider-login':
            url = body.get('url', '')
            try:
                cmd = ['opencode', 'providers', 'login']
                if url:
                    cmd.append(url)
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                log("Admin: provider login initiated")
                self._json({'ok': True, 'message': 'Login initiated', 'instruction': 'A browser window may have opened to complete login. If not, check the terminal.'})
            except Exception as e:
                self._json({'ok': False, 'message': str(e)[:200]}, 500)

        elif path == '/api/ollama-add':
            url = body.get('url', '').strip()
            if not url:
                self._json({'ok': False, 'message': 'Missing URL'}, 400)
                return
            ollama_config = os.path.join(DATA_DIR, 'ollama_config.json')
            existing = []
            if os.path.exists(ollama_config):
                with open(ollama_config) as f:
                    existing = json.load(f)
            if any(o['url'] == url for o in existing):
                self._json({'ok': False, 'message': 'URL already added'}, 400)
                return
            existing.append({'url': url})
            with open(ollama_config, 'w') as f:
                json.dump(existing, f, indent=2)
            log(f"Admin: added Ollama URL {url}")
            self._json({'ok': True, 'message': 'Ollama URL added'})

        elif path == '/api/ollama-remove':
            url = body.get('url', '').strip()
            if not url:
                self._json({'ok': False, 'message': 'Missing URL'}, 400)
                return
            ollama_config = os.path.join(DATA_DIR, 'ollama_config.json')
            if os.path.exists(ollama_config):
                with open(ollama_config) as f:
                    existing = json.load(f)
                existing = [o for o in existing if o['url'] != url]
                with open(ollama_config, 'w') as f:
                    json.dump(existing, f, indent=2)
            log(f"Admin: removed Ollama URL {url}")
            self._json({'ok': True, 'message': 'Ollama URL removed'})

        elif path == '/api/super-staff':
            staff_file = os.path.join(DATA_DIR, 'super_staff.json')
            staff = []
            if os.path.exists(staff_file):
                try:
                    with open(staff_file) as f:
                        staff = json.load(f)
                except:
                    pass
            self._json({'ok': True, 'staff': staff})

        elif path == '/api/super-staff-create':
            name = body.get('name', '').strip()
            if not name:
                self._json({'ok': False, 'message': 'Missing name'}, 400)
                return
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
                # Create agent config in opencode project
                agent_dir = os.path.join(agent_path, '.opencode', 'agents')
                os.makedirs(agent_dir, exist_ok=True)
                agent_file = os.path.join(agent_dir, name.replace(' ', '_').lower() + '.json')
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
                self._json({'ok': True, 'message': f'Agent {name} created'})
            except Exception as e:
                self._json({'ok': False, 'message': str(e)[:200]}, 500)

        elif path == '/api/super-staff-delete':
            name = body.get('name', '').strip()
            if not name:
                self._json({'ok': False, 'message': 'Missing name'}, 400)
                return
            try:
                staff_file = os.path.join(DATA_DIR, 'super_staff.json')
                if os.path.exists(staff_file):
                    with open(staff_file) as f:
                        staff = json.load(f)
                    staff = [s for s in staff if s['name'] != name]
                    with open(staff_file, 'w') as f:
                        json.dump(staff, f, indent=2)
                log(f"Admin: deleted super staff '{name}'")
                self._json({'ok': True, 'message': f'Agent {name} deleted'})
            except Exception as e:
                self._json({'ok': False, 'message': str(e)[:200]}, 500)

        elif path == '/api/super-staff-update':
            original_name = body.get('originalName', '').strip()
            name = body.get('name', '').strip()
            if not original_name or not name:
                self._json({'ok': False, 'message': 'Missing name'}, 400)
                return
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
                # Update agent file on disk
                agent_dir = os.path.join(agent_path, '.opencode', 'agents')
                agent_file = os.path.join(agent_dir, name.replace(' ', '_').lower() + '.json')
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
                # Remove old agent file if name changed
                if name != original_name:
                    old_file = os.path.join(agent_dir, original_name.replace(' ', '_').lower() + '.json')
                    if os.path.exists(old_file):
                        os.remove(old_file)
                log(f"Admin: updated super staff '{original_name}' -> '{name}'")
                self._json({'ok': True, 'message': f'Agent {name} updated'})
            except Exception as e:
                self._json({'ok': False, 'message': str(e)[:200]}, 500)

        elif path == '/api/super-staff-assign':
            session_id = body.get('sessionId', '').strip()
            staff_name = body.get('staffName', '').strip()
            if not session_id:
                self._json({'ok': False, 'message': 'Missing session ID'}, 400)
                return
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
            self._json({'ok': True, 'message': f"Staff {'assigned' if staff_name else 'unassigned'}"})

        elif path == '/api/super-staff-assignments':
            assign_file = os.path.join(DATA_DIR, 'case_assignments.json')
            assignments = {}
            if os.path.exists(assign_file):
                try:
                    with open(assign_file) as f:
                        assignments = json.load(f)
                except:
                    pass
            self._json({'ok': True, 'assignments': assignments})

        elif path == '/api/restart-daemon':
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
                self._json({'ok': True, 'message': 'Daemon restarted'})
            except Exception as e:
                self._json({'ok': False, 'message': str(e)[:200]}, 500)

        elif path == '/api/kill-daemon':
            try:
                if os.path.exists(PID_FILE):
                    with open(PID_FILE) as f:
                        old_pid = int(f.read().strip())
                    os.kill(old_pid, signal.SIGKILL)
                    os.remove(PID_FILE)
                log("Admin: daemon killed")
                self._json({'ok': True, 'message': 'Daemon killed'})
            except Exception as e:
                self._json({'ok': False, 'message': str(e)[:200]}, 500)

        elif path == '/api/ping':
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

        else:
            self._json({'ok': False, 'message': 'Not found'}, 404)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith('/api/'):
            if path in ('/api/ping', '/api/providers', '/api/super-staff', '/api/super-staff-assignments'):
                self.do_POST()
            else:
                self._json({'ok': False, 'message': 'Use POST for this endpoint'}, 405)
        else:
            super().do_GET()

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5500
    server = http.server.HTTPServer(('', port), UnifiedHandler)
    print(f"Dashboard server running on http://localhost:{port}")
    server.serve_forever()
