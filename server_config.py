#!/usr/bin/env python3
import json
import subprocess
import os
import secrets
import stat
import threading
import time
import re

_SESSION_LOCKS: dict[str, threading.Lock] = {}
_SESSION_LOCKS_GUARD = threading.Lock()

def _get_session_lock(sid: str) -> threading.Lock:
    with _SESSION_LOCKS_GUARD:
        if sid not in _SESSION_LOCKS:
            _SESSION_LOCKS[sid] = threading.Lock()
        return _SESSION_LOCKS[sid]

DATA_DIR = os.path.expanduser('~/.opencode-dashboard/data')
PID_FILE = os.path.join(DATA_DIR, 'daemon.pid')
ACTIVITY_FILE = os.path.join(DATA_DIR, 'activity.log')
CRON_FILE = os.path.join(DATA_DIR, 'cron_jobs.json')
QUEUE_FILE = os.path.join(DATA_DIR, 'request_queue.json')
NOTIFICATIONS_FILE = os.path.join(DATA_DIR, 'notifications.json')
NOTIFICATION_PROVIDERS_FILE = os.path.join(DATA_DIR, 'notification_providers.json')
STAFF_FILE = os.path.join(DATA_DIR, 'super_staff.json')
ASSIGNMENTS_FILE = os.path.join(DATA_DIR, 'case_assignments.json')
STATIC_DIR = os.path.expanduser('~/.opencode-dashboard')
API_KEY_FILE = os.path.join(DATA_DIR, 'api_key')

_cron_lock = threading.Lock()
_notifications_lock = threading.Lock()
_staff_lock = threading.Lock()
_assignments_lock = threading.Lock()

def _load_or_generate_api_key() -> str:
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
    print(f'\n[Dashboard] New API key generated — copy this to your Android app Settings > API Key:\n  {key}\n  (saved to {API_KEY_FILE})\n', flush=True)
    return key

_API_KEY: str = _load_or_generate_api_key()

_ANSI_RE = re.compile('\x1b\\[[0-9;]*[a-zA-Z]')

def _safe_agent_name(name: str) -> str:
    return re.sub(r'[^a-z0-9_\-]', '', name.replace(' ', '_').lower())

def strip_ansi(s: str) -> str:
    return _ANSI_RE.sub('', s)

def log(msg: str) -> None:
    try:
        ts = __import__('datetime').datetime.now().strftime('%H:%M:%S')
        with open(ACTIVITY_FILE, 'a') as f:
            f.write(f'[{ts}] {msg}\n')
    except Exception:
        pass

_attach_cache: dict[str, object] = {'url': '', 'time': 0}
def get_attach_url(force: bool = False) -> str:
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
                        except Exception:
                            pass
    except Exception:
        pass
    _attach_cache['url'] = 'http://127.0.0.1:51384'
    _attach_cache['time'] = now
    return _attach_cache['url']

def engine_is_reachable(url: str, password: str = '') -> bool:
    if not url:
        return False
    try:
        cmd = ['curl', '-s', '--max-time', '3', '-o', '/dev/null', '-w', '%{http_code}']
        if password:
            cmd.extend(['-u', f'opencode:{password}'])
        cmd.append(url.rstrip('/') + '/api/ping')
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False

def _check_engine(attach: str | None = None) -> str | None:
    password = os.environ.get('OPENCODE_SERVER_PASSWORD', '')
    if attach is None:
        attach = get_attach_url()
    if engine_is_reachable(attach, password):
        return attach
    attach = get_attach_url(force=True)
    if engine_is_reachable(attach, password):
        return attach
    return None

def get_engine_restarted() -> str | None:
    status_path = os.path.join(DATA_DIR, 'status.json')
    if os.path.exists(status_path):
        try:
            with open(status_path) as f:
                sd = json.load(f)
            return sd.get('summary', {}).get('engine_restarted_at')
        except Exception:
            pass
    return None

def _set_api_key(key: str) -> None:
    global _API_KEY
    _API_KEY = key

def _get_api_key() -> str:
    return _API_KEY

import re as _re

_INVALID_PATH_CHARS = _re.compile(r'[<>"|?*\x00-\x1f]')

def _safe_path(path: str) -> bool:
    """Reject paths containing dangerous characters or traversal patterns."""
    if not path or len(path) > 4096:
        return False
    if '..' in path.split(os.sep):
        return False
    if _INVALID_PATH_CHARS.search(path):
        return False
    return True

def _safe_shell_arg(arg: str) -> bool:
    """Reject args with potential shell metacharacters (defense-in-depth)."""
    if not arg:
        return True
    dangerous = set('`;$|&\\\n\r')
    return not any(c in arg for c in dangerous)

def _error_id() -> str:
    return 'e' + secrets.token_hex(6)

def _load_notifications() -> list:
    if not os.path.exists(NOTIFICATIONS_FILE):
        return []
    try:
        with open(NOTIFICATIONS_FILE) as f:
            items = json.load(f)
        return items
    except Exception:
        return []

def _save_notifications(items: list) -> None:
    try:
        with open(NOTIFICATIONS_FILE, 'w') as f:
            json.dump(items[:50], f, indent=2)
    except Exception:
        pass

def _load_notification_providers() -> list:
    if not os.path.exists(NOTIFICATION_PROVIDERS_FILE):
        return []
    try:
        with open(NOTIFICATION_PROVIDERS_FILE) as f:
            return json.load(f)
    except Exception:
        return []

def _save_notification_providers(items: list) -> None:
    try:
        with open(NOTIFICATION_PROVIDERS_FILE, 'w') as f:
            json.dump(items, f, indent=2)
    except Exception:
        pass
