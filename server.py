#!/usr/bin/env python3
import http.server
import json
import os
import sys
import urllib.parse
import threading
import time
import secrets

from server_config import (
    DATA_DIR, STATIC_DIR, PID_FILE, NOTIFICATIONS_FILE,
    NOTIFICATION_PROVIDERS_FILE,
    STAFF_FILE, ASSIGNMENTS_FILE,
    _get_api_key, log, _error_id,
    _load_notifications, _load_notification_providers
)
from cron import _cron_runner, _load_cron_jobs
from queue import _queue_processor, _load_queue, _save_queue, _register_handler

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
        return self.headers.get('X-API-Key', '') == _get_api_key()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/api/queue':
            if not self._check_api_key():
                self._json({'ok': False, 'message': 'Unauthorized', 'error_id': _error_id()}, 401)
                return
            typ = body.get('type', '')
            payload = body.get('payload', {})
            if not typ:
                self._json({'ok': False, 'message': 'Missing type', 'error_id': _error_id()}, 400)
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
                    except Exception:
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

            if path == '/api/notification-providers':
                items = _load_notification_providers()
                self._json({'ok': True, 'providers': items})
                return

            if path == '/api/notifications/messages':
                if not self._check_api_key():
                    self._json({'ok': False, 'message': 'Unauthorized'}, 401)
                    return
                items = _load_notifications()
                pending = [{'id': i['id'], 'message': i['message'], 'type': i.get('type', 'info'), 'created_at': i.get('created_at')} for i in items if not i.get('dismissed')]
                self._json({'ok': True, 'notifications': pending})
                return

            if path == '/api/super-staff':
                staff = []
                if os.path.exists(STAFF_FILE):
                    try:
                        with open(STAFF_FILE) as f:
                            staff = json.load(f)
                    except Exception:
                        pass
                self._json({'ok': True, 'staff': staff})
                return

            if path == '/api/super-staff-assignments':
                assignments = {}
                if os.path.exists(ASSIGNMENTS_FILE):
                    try:
                        with open(ASSIGNMENTS_FILE) as f:
                            assignments = json.load(f)
                    except Exception:
                        pass
                self._json({'ok': True, 'assignments': assignments})
                return

            if path == '/api/cron-jobs':
                jobs = _load_cron_jobs()
                self._json({'ok': True, 'jobs': jobs})
                return

            if path == '/api/api-key':
                ak = _get_api_key()
                masked = (ak[:6] + '…' + ak[-4:]) if len(ak) > 10 else '****'
                self._json({'ok': True, 'key': ak, 'masked': masked})
                return

            if path == '/api/providers':
                providers = []
                ollama_list = []
                try:
                    import subprocess
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
                        except Exception:
                            o['status'] = 'offline'
                            o['models'] = 0
                    self._json({'ok': True, 'providers': providers, 'ollama': ollama_list})
                except Exception as e:
                    self._json({'ok': False, 'message': str(e)[:200]}, 500)
                return

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
    from api_handlers import (
        _handle_stop_session, _handle_session_instruct, _handle_session_answer,
        _handle_new_session, _handle_provider_logout, _handle_provider_login,
        _handle_ollama_add, _handle_ollama_remove,
        _handle_super_staff_create, _handle_super_staff_delete,
        _handle_super_staff_update, _handle_super_staff_assign,
        _handle_rename_session, _handle_restart_daemon, _handle_kill_daemon,
        _handle_upload_photo, _handle_remove_photo, _handle_save_boss_name,
        _handle_api_key_regenerate,
        _handle_notifications_send, _handle_notifications_dismiss,
        _handle_notification_providers_create,
        _handle_notification_providers_delete,
        _handle_notification_providers_test,
        _handle_cron_jobs_create, _handle_cron_jobs_update,
        _handle_cron_jobs_delete, _handle_cron_jobs_toggle, _handle_cron_jobs_run,
    )

    for typ, handler in [
        ('stop-session', _handle_stop_session),
        ('session-instruct', _handle_session_instruct),
        ('session-answer', _handle_session_answer),
        ('new-session', _handle_new_session),
        ('provider-logout', _handle_provider_logout),
        ('provider-login', _handle_provider_login),
        ('ollama-add', _handle_ollama_add),
        ('ollama-remove', _handle_ollama_remove),
        ('super-staff-create', _handle_super_staff_create),
        ('super-staff-delete', _handle_super_staff_delete),
        ('super-staff-update', _handle_super_staff_update),
        ('super-staff-assign', _handle_super_staff_assign),
        ('rename-session', _handle_rename_session),
        ('restart-daemon', _handle_restart_daemon),
        ('kill-daemon', _handle_kill_daemon),
        ('upload-photo', _handle_upload_photo),
        ('remove-photo', _handle_remove_photo),
        ('save-boss-name', _handle_save_boss_name),
        ('api-key/regenerate', _handle_api_key_regenerate),
        ('notifications-send', _handle_notifications_send),
        ('notifications-dismiss', _handle_notifications_dismiss),
        ('notification-providers/create', _handle_notification_providers_create),
        ('notification-providers/delete', _handle_notification_providers_delete),
        ('notification-providers/test', _handle_notification_providers_test),
        ('cron-jobs/create', _handle_cron_jobs_create),
        ('cron-jobs/update', _handle_cron_jobs_update),
        ('cron-jobs/delete', _handle_cron_jobs_delete),
        ('cron-jobs/toggle', _handle_cron_jobs_toggle),
        ('cron-jobs/run', _handle_cron_jobs_run),
    ]:
        _register_handler(typ, handler)

    threading.Thread(target=_cron_runner, daemon=True).start()
    threading.Thread(target=_queue_processor, daemon=True).start()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5500
    server = http.server.ThreadingHTTPServer(('127.0.0.1', port), UnifiedHandler)
    print(f"Dashboard server running on http://localhost:{port}")
    server.serve_forever()
