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
    STAFF_FILE, ASSIGNMENTS_FILE, WORKFLOWS_FILE, WORKFLOW_INSTANCES_FILE,
    _get_api_key, log, _error_id,
    _load_notifications, _load_notification_providers,
    _save_notification_providers,
    _load_workflows, _save_workflows,
    _load_workflow_instances, _save_workflow_instances,
    _workflow_lock,
)
from cron import _cron_runner, _load_cron_jobs
from queue import _queue_processor, _load_queue, _save_queue, _register_handler

_notif_prev = {}  # {session_id: {state, has_questions}}
_notif_last_sent = {}  # {provider_id: timestamp}
_notif_was_full = False
_notif_no_active_since = None

def _notification_dispatcher():
    global _notif_prev, _notif_last_sent, _notif_was_full, _notif_no_active_since
    while True:
        try:
            time.sleep(10)
            status_path = os.path.join(DATA_DIR, 'status.json')
            if not os.path.exists(status_path):
                continue
            with open(status_path) as f:
                status = json.load(f)
            sessions = status.get('sessions') or status.get('all_sessions') or []
            summary = status.get('summary') or {}
            cpu_cores = summary.get('cpu_core_count', 10)

            providers = _load_notification_providers()
            enabled = [p for p in providers if p.get('enabled') and p.get('scopes')]
            if not enabled:
                _notif_prev = {s['id']: {'state': s.get('state'), 'has_questions': bool(s.get('pending_questions'))} for s in sessions}
                continue

            events = []

            # 1. State changes
            current_map = {}
            for s in sessions:
                sid = s.get('id', '')
                state = s.get('state', '')
                has_q = bool(s.get('pending_questions'))
                current_map[sid] = {'state': state, 'has_questions': has_q}
                prev = _notif_prev.get(sid)
                if prev and prev.get('state') != state and prev.get('state') is not None:
                    events.append(('state_change', {
                        'title': s.get('title', s.get('slug', sid)),
                        'old_state': prev.get('state', ''),
                        'new_state': state,
                        'last_text': (s.get('last_text') or '')[:500],
                    }))
            _notif_prev = current_map

            # 2. User interaction (new pending questions)
            pending_sessions = [s for s in sessions if s.get('pending_questions')]
            prev_pending = any(
                v.get('has_questions') for v in _notif_prev.values()
            ) if _notif_prev else False
            if pending_sessions and not prev_pending:
                events.append(('user_interaction', {
                    'count': len(pending_sessions),
                    'titles': [s.get('title', '?') for s in pending_sessions[:5]],
                }))

            # 3. Desks full
            active_workers = len(sessions)
            is_full = active_workers >= min(6, cpu_cores)
            if is_full and not _notif_was_full:
                events.append(('desks_full', {'worker_count': active_workers}))
            _notif_was_full = is_full

            # 4. No active cases
            active_count = sum(1 for s in sessions if s.get('state') in ('thinking', 'running-tools'))
            if active_count == 0:
                if _notif_no_active_since is None:
                    _notif_no_active_since = time.time()
                elapsed = time.time() - _notif_no_active_since
                for p in enabled:
                    timeout = p.get('no_active_timeout', 300)
                    if (elapsed >= timeout and
                        p['id'] not in _notif_last_sent and
                        p.get('scopes', {}).get('no_active_cases')):
                        events.append(('no_active_cases', {
                            'duration': int(elapsed),
                        }))
                        _notif_last_sent[p['id']] = time.time()
            else:
                _notif_no_active_since = None

            # Enqueue events to matching providers
            for event_type, event_data in events:
                for p in enabled:
                    if not p.get('scopes', {}).get(event_type):
                        continue
                    gap = p.get('gap_sec', 300)
                    last = _notif_last_sent.get(p['id'], 0)
                    if time.time() - last < gap:
                        continue
                    item = {
                        'id': 'q_' + secrets.token_hex(6),
                        'type': 'notification-providers/send-webhook',
                        'payload': {
                            'provider_id': p['id'],
                            'event_type': event_type,
                            'event_data': event_data,
                        },
                        'status': 'queued',
                        'result': None,
                        'error': None,
                        'created_at': time.time(),
                    }
                    queue = _load_queue()
                    queue.append(item)
                    _save_queue(queue)
                    _notif_last_sent[p['id']] = time.time()
                    log(f"Notif dispatch queued: {event_type} -> {p['name']}")

        except Exception as e:
            log(f"Notif dispatcher error: {e}")

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

        if path == '/favicon.ico':
            photo = os.path.join(STATIC_DIR, 'assets', 'profile_photo.png')
            if os.path.exists(photo):
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.send_header('Cache-Control', 'max-age=3600')
                self.end_headers()
                with open(photo, 'rb') as _f:
                    self.wfile.write(_f.read())
                return
            super().do_GET()
            return

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

            if path == '/api/status':
                status_path = os.path.join(DATA_DIR, 'status.json')
                if os.path.exists(status_path):
                    try:
                        with open(status_path) as f:
                            data = json.load(f)
                        data['ok'] = True
                        self._json(data)
                    except Exception as e:
                        self._json({'ok': False, 'message': str(e)[:200]}, 500)
                else:
                    self._json({'ok': False, 'message': 'Status file not found'}, 404)
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

            if path == '/api/logs':
                lines_count = 200
                if os.path.exists(ACTIVITY_FILE):
                    try:
                        with open(ACTIVITY_FILE) as f:
                            all_lines = f.readlines()
                        log_lines = [l.rstrip('\n') for l in all_lines if l.strip()][-lines_count:]
                        log_lines.reverse()
                        self._json({'ok': True, 'lines': log_lines})
                    except Exception as e:
                        self._json({'ok': False, 'message': str(e)[:200]}, 500)
                else:
                    self._json({'ok': True, 'lines': []})
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

            if path == '/api/workflows':
                workflows = _load_workflows()
                self._json({'ok': True, 'workflows': workflows})
                return

            if path == '/api/workflow-instances':
                instances = _load_workflow_instances()
                self._json({'ok': True, 'instances': instances})
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
        _handle_new_session,
        _handle_provider_logout, _handle_provider_login,
        _handle_ollama_add, _handle_ollama_remove,
        _handle_super_staff_create, _handle_super_staff_delete,
        _handle_super_staff_update, _handle_super_staff_assign,
        _handle_rename_session, _handle_restart_daemon, _handle_kill_daemon,
        _handle_upload_photo, _handle_remove_photo, _handle_save_boss_name,
        _handle_save_project_instruction,
        _handle_api_key_regenerate,
        _handle_notifications_send, _handle_notifications_dismiss,
        _handle_notification_providers_create,
        _handle_notification_providers_delete,
        _handle_notification_providers_test,
        _handle_notification_providers_update,
        _handle_notification_providers_send_webhook,
        _handle_cron_jobs_create, _handle_cron_jobs_update,
        _handle_cron_jobs_delete, _handle_cron_jobs_toggle, _handle_cron_jobs_run,
        _handle_session_clear_tasks, _handle_session_clear_questions,
        _handle_workflow_save, _handle_workflow_delete,
        _handle_workflow_attach, _handle_workflow_advance, _handle_workflow_pause,
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
        ('save-project-instruction', _handle_save_project_instruction),
        ('api-key/regenerate', _handle_api_key_regenerate),
        ('notifications-send', _handle_notifications_send),
        ('notifications-dismiss', _handle_notifications_dismiss),
        ('notification-providers/create', _handle_notification_providers_create),
        ('notification-providers/delete', _handle_notification_providers_delete),
        ('notification-providers/test', _handle_notification_providers_test),
        ('notification-providers/update', _handle_notification_providers_update),
        ('notification-providers/send-webhook', _handle_notification_providers_send_webhook),
        ('cron-jobs/create', _handle_cron_jobs_create),
        ('cron-jobs/update', _handle_cron_jobs_update),
        ('cron-jobs/delete', _handle_cron_jobs_delete),
        ('cron-jobs/toggle', _handle_cron_jobs_toggle),
        ('cron-jobs/run', _handle_cron_jobs_run),
        ('session-clear-tasks', _handle_session_clear_tasks),
        ('session-clear-questions', _handle_session_clear_questions),
        ('workflow-save', _handle_workflow_save),
        ('workflow-delete', _handle_workflow_delete),
        ('workflow-attach', _handle_workflow_attach),
        ('workflow-advance', _handle_workflow_advance),
        ('workflow-pause', _handle_workflow_pause),
    ]:
        _register_handler(typ, handler)

    def _workflow_watcher():
        from api_handlers import _run_workflow_stage
        log("[WF WATCHER] Started")
        while True:
            try:
                time.sleep(15)
                instances = _load_workflow_instances()
                log(f"[WF WATCHER] Tick: {len(instances)} instance(s)")
                if instances:
                    for inst in instances:
                        log(f"[WF WATCHER] Instance: session={inst.get('session_id','?')[:16]}, status={inst.get('status')}, node={inst.get('current_node')}")
                status_path = os.path.join(DATA_DIR, 'status.json')
                if not os.path.exists(status_path):
                    continue
                with open(status_path) as f:
                    status = json.load(f)
                all_sessions = status.get('all_sessions') or status.get('sessions') or []
                session_map = {s.get('id', ''): s for s in all_sessions}
                changed = False
                for inst in instances:
                    if inst.get('status') != 'running' or inst.get('paused'):
                        continue
                    current_id = inst.get('current_node')
                    if not current_id:
                        continue
                    node_states = inst.get('node_states', {})
                    current_state = node_states.get(current_id, {}).get('status')
                    # Handle _activate_on_complete: pending branch nodes wait for session to finish
                    if current_state == 'pending' and inst.get('_activate_on_complete'):
                        session_check = session_map.get(inst['session_id'])
                        if session_check and session_check.get('state') in ('complete', 'error'):
                            node_states[current_id]['status'] = 'running'
                            inst.pop('_activate_on_complete', None)
                            _save_workflow_instances(instances)
                            threading.Thread(target=lambda i=dict(inst): _run_workflow_stage(i), daemon=True).start()
                            log(f"Workflow watcher: activated branch node '{current_id}' for session {inst['session_id'][:16]}")
                        continue
                    if current_state != 'running':
                        continue
                    session = session_map.get(inst['session_id'])
                    if not session:
                        continue
                    s_state = session.get('state', '')
                    # Fallback: if poller hasn't exported yet, do a direct check
                    if not s_state:
                        try:
                            r = subprocess.run(
                                ['opencode', 'export', inst['session_id']],
                                capture_output=True, text=True, timeout=15,
                                cwd=session.get('directory') or None
                            )
                            if r.returncode == 0:
                                finish_match = __import__('re').search(r'"finish"\s*:\s*"([^"]+)"', r.stdout)
                                if finish_match:
                                    finish = finish_match.group(1)
                                    s_state = 'complete' if finish in ('stop', 'length') else 'error' if finish == 'error' else 'running-tools' if finish == 'tool-calls' else 'thinking'
                        except Exception:
                            pass
                    if s_state in ('complete', 'error'):
                            with _workflow_lock:
                                # Re-read inside lock to avoid races
                                instances = _load_workflow_instances()
                                inst = next((i for i in instances if i.get('session_id') == inst.get('session_id')), None)
                                if not inst: continue
                                node_states = inst.get('node_states', {})
                                current_id = inst.get('current_node')
                                if node_states.get(current_id, {}).get('status') != 'running': continue
                                node_states[current_id]['status'] = 'completed' if s_state == 'complete' else 'failed'
                                node_states[current_id]['completed_at'] = time.time()
                                workflows = _load_workflows()
                                wf = next((w for w in workflows if w['id'] == inst['workflow_id']), None)
                                next_ids = []
                                if wf:
                                    for e in wf.get('edges', []):
                                        if e['from'] == current_id:
                                            next_ids.append(e['to'])
                                if next_ids:
                                    # First edge: advance the original instance
                                    next_id = next_ids[0]
                                    inst['current_node'] = next_id
                                    node_states[next_id] = node_states.get(next_id, {'status': 'running'})
                                    node_states[next_id]['status'] = 'running'
                                    _save_workflow_instances(instances)
                                    threading.Thread(target=lambda i=dict(inst): _run_workflow_stage(i), daemon=True).start()
                                    log(f"Workflow watcher: auto-advancing session {inst['session_id'][:16]} -> stage '{next_id}'")
                                    # Remaining edges: queue as pending forks (not started yet)
                                    for branch_id in next_ids[1:]:
                                        branch_states = {}
                                        for n in wf.get('nodes', []):
                                            branch_states[n['id']] = {'status': 'pending'}
                                        fork_inst = {
                                            'session_id': inst['session_id'],
                                            'workflow_id': inst['workflow_id'],
                                            'status': 'running',
                                            'current_node': branch_id,
                                            'node_states': branch_states,
                                            'paused': False,
                                            'started_at': time.time(),
                                            '_activate_on_complete': True,
                                        }
                                        instances.append(fork_inst)
                                        _save_workflow_instances(instances)
                                        log(f"Workflow watcher: queued branch {branch_id} for session {inst['session_id'][:16]}")
                                else:
                                    inst['current_node'] = None
                                    node_states[current_id]['status'] = 'completed'
                                    node_states[current_id]['completed_at'] = time.time()
                                    # Check if there are pending branches to activate
                                    activated_branch = False
                                    for other in instances:
                                        if other.get('session_id') == inst.get('session_id') and other.get('status') == 'running':
                                            ns = other.get('node_states', {})
                                            cn = other.get('current_node')
                                            if cn and ns.get(cn, {}).get('status') == 'pending':
                                                ns[cn]['status'] = 'running'
                                                _save_workflow_instances(instances)
                                                threading.Thread(target=lambda i=dict(other): _run_workflow_stage(i), daemon=True).start()
                                                log(f"Workflow watcher: activating branch {cn} for session {inst['session_id'][:16]}")
                                                activated_branch = True
                                                break
                                    if not activated_branch:
                                        # All branches done — trigger summary and mark completed
                                        inst['_pending_summary'] = True
                                        _save_workflow_instances(instances)
                                        threading.Thread(target=lambda sid=inst['session_id']: (
                                            subprocess.run(
                                                ['opencode', 'run', '-s', sid, 'Summarize what was accomplished in this session end to end. Cover all stages, key outcomes, decisions, and results. Be concise.'],
                                                capture_output=True, text=True, timeout=120
                                            ), None
                                        ), daemon=True).start()
                                        log(f"Workflow watcher: summary triggered for session {inst['session_id'][:16]}")
                                    else:
                                        _save_workflow_instances(instances)
                                    # Handle _pending_summary: check if session has last_text yet
                                    for pend_inst in instances:
                                        if pend_inst.get('_pending_summary') and pend_inst.get('status') == 'running':
                                            psession = session_map.get(pend_inst['session_id'])
                                            if psession:
                                                lt = psession.get('last_text', '') or ''
                                                if lt and len(lt) > 20:
                                                    pend_inst['summary'] = lt[:5000]
                                                    pend_inst['status'] = 'completed'
                                                    pend_inst['_pending_summary'] = False
                                                    _save_workflow_instances(instances)
                                                    log(f"Workflow watcher: summary saved for session {pend_inst['session_id'][:16]}")
            except Exception as e:
                log(f"Workflow watcher error: {e}")

    threading.Thread(target=_cron_runner, daemon=True).start()
    threading.Thread(target=_queue_processor, daemon=True).start()
    threading.Thread(target=_notification_dispatcher, daemon=True).start()
    threading.Thread(target=_workflow_watcher, daemon=True).start()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5500
    server = http.server.ThreadingHTTPServer(('127.0.0.1', port), UnifiedHandler)
    print(f"Dashboard server running on http://localhost:{port}")
    server.serve_forever()
