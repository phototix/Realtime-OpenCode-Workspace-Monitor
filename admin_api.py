#!/usr/bin/env python3
import http.server
import json
import subprocess
import os
import signal
import sys
from urllib.parse import urlparse

DATA_DIR = os.path.expanduser('~/.opencode-dashboard/data')
PID_FILE = os.path.join(DATA_DIR, 'daemon.pid')
ACTIVITY_FILE = os.path.join(DATA_DIR, 'activity.log')

def log(msg):
    try:
        ts = __import__('datetime').datetime.now().strftime('%H:%M:%S')
        with open(ACTIVITY_FILE, 'a') as f:
            f.write(f'[{ts}] {msg}\n')
    except:
        pass

_attach_url = None
def get_attach_url():
    global _attach_url
    if _attach_url:
        return _attach_url
    try:
        r = subprocess.run(['lsof', '-i', '-P', '-n'], capture_output=True, text=True, timeout=5)
        for line in r.stdout.split('\n'):
            if 'OpenCode' in line and '(LISTEN)' in line:
                parts = line.split()
                for p in parts:
                    if ':' in p and len(p.split(':')[1]) == 5:
                        try:
                            port = int(p.split(':')[1])
                            _attach_url = f'http://127.0.0.1:{port}'
                            return _attach_url
                        except:
                            pass
    except:
        pass
    _attach_url = 'http://127.0.0.1:51384'
    return _attach_url

class AdminHandler(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _json(self, data, status=200):
        self.send_response(status)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/stop-session':
            sid = body.get('id', '')
            if not sid:
                self._json({'ok': False, 'message': 'Missing session id'}, 400)
                return
            try:
                cwd = body.get('directory') or None
                r = subprocess.run(['opencode', 'session', 'stop', sid], capture_output=True, text=True, timeout=15, cwd=cwd)
                if r.returncode == 0:
                    log(f"Admin: stopped session {sid}")
                    self._json({'ok': True, 'message': 'Session stopped'})
                else:
                    self._json({'ok': False, 'message': r.stderr.strip() or 'Unknown error'}, 500)
            except subprocess.TimeoutExpired:
                self._json({'ok': False, 'message': 'Timeout stopping session'}, 500)
            except Exception as e:
                self._json({'ok': False, 'message': str(e)}, 500)

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
                self._json({'ok': False, 'message': str(e)}, 500)

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
                self._json({'ok': False, 'message': str(e)}, 500)

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
                cmd = ['opencode', 'run', '-s', sid, '--attach', attach]
                if model:
                    cmd.extend(['-m', model])
                if mode_val:
                    cmd.extend(['--agent', mode_val])
                cmd.append(message)
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=cwd)
                if r.returncode == 0:
                    log(f"Admin: instructed session {sid}")
                    self._json({'ok': True, 'message': 'Instruction sent'})
                else:
                    self._json({'ok': False, 'message': r.stderr.strip()[:200] or 'Unknown error'}, 500)
            except subprocess.TimeoutExpired:
                self._json({'ok': False, 'message': 'Timeout sending instruction'}, 500)
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
                cmd = ['opencode', 'run', '--attach', attach]
                if title:
                    cmd.extend(['--title', title])
                if model:
                    cmd.extend(['-m', model])
                if mode_val:
                    cmd.extend(['--agent', mode_val])
                if directory:
                    cmd.extend(['--dir', directory])
                cmd.append(message)
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=cwd)
                if r.returncode == 0:
                    log(f"Admin: new session started \"{title or message[:40]}\"")
                    self._json({'ok': True, 'message': 'Session started'})
                else:
                    self._json({'ok': False, 'message': (r.stderr.strip()[:200] or r.stdout.strip()[:200] or 'Unknown error')[:200]}, 500)
            except subprocess.TimeoutExpired:
                self._json({'ok': False, 'message': 'Timeout starting session'}, 500)
            except Exception as e:
                self._json({'ok': False, 'message': str(e)[:200]}, 500)

        elif path == '/api/models':
            try:
                # Fetch opencode models
                r = subprocess.run(['opencode', 'models'], capture_output=True, text=True, timeout=15)
                opencode_models = []
                if r.returncode == 0:
                    for line in r.stdout.strip().split('\n'):
                        line = line.strip()
                        if line and '/' in line:
                            opencode_models.append({'id': line, 'provider': 'opencode'})

                # Fetch Ollama models
                ollama_models = []
                try:
                    rr = subprocess.run(
                        ['curl', '-s', '--max-time', '5', 'https://ollama.brandon.my/api/tags'],
                        capture_output=True, text=True, timeout=10
                    )
                    if rr.returncode == 0:
                        ollama_data = json.loads(rr.stdout)
                        for m in ollama_data.get('models', []):
                            ollama_models.append({'id': m['name'], 'provider': 'ollama'})
                except:
                    pass

                self._json({'ok': True, 'models': opencode_models + ollama_models})
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
        parsed = urlparse(self.path)
        path = parsed.path
        if path == '/api/models':
            self.do_POST()
        elif path == '/api/ping':
            self.do_POST()
        else:
            self._json({'ok': False, 'message': 'Not found'}, 404)

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
    server = http.server.HTTPServer(('127.0.0.1', port), AdminHandler)
    server.serve_forever()
