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
                cmd = ['opencode', 'run', '-s', sid, '--attach', attach]
                if password:
                    cmd.extend(['-p', password])
                if model:
                    cmd.extend(['-m', model])
                if mode_val:
                    cmd.extend(['--agent', mode_val])
                cmd.append(message)
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=20, cwd=cwd)
                if r.returncode == 0:
                    log(f"Admin: instructed session {sid}")
                    self._json({'ok': True, 'message': 'Instruction sent'})
                else:
                    err_text = strip_ansi(r.stderr.strip() or r.stdout.strip()[:200] or 'Unknown error')[:200]
                    # If model was the problem, retry without model
                    if model and ('Model not found' in err_text or 'UnknownError' in err_text):
                        log(f"Admin: retrying session {sid} without model")
                        cmd2 = ['opencode', 'run', '-s', sid, '--attach', attach]
                        if password:
                            cmd2.extend(['-p', password])
                        if mode_val:
                            cmd2.extend(['--agent', mode_val])
                        cmd2.append(message)
                        r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=15, cwd=cwd)
                        if r2.returncode == 0:
                            log(f"Admin: instructed session {sid} (retry without model)")
                            self._json({'ok': True, 'message': 'Instruction sent (model ignored, using default)'})
                            return
                        err_text = strip_ansi(r2.stderr.strip() or r2.stdout.strip()[:200] or 'Unknown error')[:200]
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
                answer_text = 'I choose: ' + '; '.join(str(a) for a in answers)
                cmd = ['opencode', 'run', '-s', sid, '--attach', attach, answer_text]
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=cwd)
                if r.returncode == 0:
                    log(f"Admin: answered session {sid}")
                    self._json({'ok': True, 'message': 'Answer sent'})
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
                    self._json({'ok': False, 'message': (r.stderr.strip() or r.stdout.strip()[:200] or 'Unknown error')[:200]}, 500)
            except subprocess.TimeoutExpired:
                self._json({'ok': False, 'message': 'Timeout starting session'}, 500)
            except Exception as e:
                self._json({'ok': False, 'message': str(e)[:200]}, 500)

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
            if path == '/api/ping':
                length = int(self.headers.get('Content-Length', 0))
                body = {}
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
