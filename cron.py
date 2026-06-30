#!/usr/bin/env python3
"""Cron job scheduling and execution for the MyDora dashboard."""
import json
import os
import subprocess
import threading
import time

from server_config import (
    DATA_DIR, CRON_FILE, ACTIVITY_FILE,
    _cron_lock, _safe_agent_name, _safe_path, _safe_shell_arg,
    strip_ansi, log, _load_project_instructions, _save_project_instructions
)

def _load_cron_jobs() -> list:
    if not os.path.exists(CRON_FILE):
        return []
    try:
        with _cron_lock:
            with open(CRON_FILE) as f:
                return json.load(f)
    except Exception:
        return []

def _save_cron_jobs(jobs: list) -> None:
    with _cron_lock:
        with open(CRON_FILE, 'w') as f:
            json.dump(jobs, f, indent=2)

def _run_cron_job(job: dict) -> None:
    status = 'unknown'
    try:
        action = job.get('action', {})
        cwd = action.get('directory') or None
        if cwd and not _safe_path(cwd):
            status = 'fail: invalid directory path'
            log(f"Cron job '{job.get('name', '?')}': {status}")
            return
        cmd = ['opencode', 'run']
        if action.get('type') == 'session' and action.get('session_id'):
            cmd.extend(['-s', action['session_id']])
            if action.get('fork', False):
                cmd.extend(['--fork'])
        else:
            cmd.extend(['-c'])
        password = os.environ.get('OPENCODE_SERVER_PASSWORD', '')
        if password:
            cmd.extend(['-p', password])
        if action.get('model'):
            cmd.extend(['-m', action['model']])
        message = action.get('message', '')
        # Read project instruction from opencode DB (survives engine restart)
        proj_inst = ''
        session_id = action.get('session_id', '')
        try:
            import sqlite3
            _db = os.path.expanduser('~/.local/share/opencode/opencode.db')
            _conn = sqlite3.connect(_db)
            _row = _conn.execute("SELECT json_extract(metadata, '$.project_instruction') FROM session WHERE id = ?", (session_id,)).fetchone()
            _conn.close()
            if _row and _row[0]:
                proj_inst = _row[0]
        except Exception:
            pass
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
                                s_desc = s.get('description', '')
                                if s_desc:
                                    message = s_desc + '\n\nInstructions:\n' + message
                                break
                except Exception:
                    pass
        elif action.get('mode'):
            cmd.extend(['--agent', action['mode']])
        if action.get('directory'):
            cmd.extend(['--dir', action['directory']])
        if proj_inst:
            message = proj_inst + '\n\n' + message
        cmd.append(message)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=cwd)
        if r.returncode != 0:
            err = strip_ansi((r.stderr or '')[:200]).lower()
            if 'not found' in err and action.get('session_id'):
                sid = action['session_id']
                import sqlite3
                _db = os.path.expanduser('~/.local/share/opencode/opencode.db')
                _exists = False
                try:
                    _c = sqlite3.connect(_db)
                    _exists = _c.execute("SELECT 1 FROM session WHERE id=?", (sid,)).fetchone() is not None
                    _c.close()
                except Exception:
                    pass
                if not _exists:
                    log(f"Cron: session {sid[:16]} not in DB, falling back to -c")
                    cmd2 = ['opencode', 'run', '-c']
                    if password:
                        cmd2.extend(['-p', password])
                    if action.get('model'):
                        cmd2.extend(['-m', action['model']])
                    if staff_name:
                        cmd2.extend(['--agent', action.get('mode', 'build')])
                    elif action.get('mode'):
                        cmd2.extend(['--agent', action['mode']])
                    cmd2.append(message)
                    r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=600, cwd=cwd)
                    if r2.returncode == 0:
                        log(f"Cron: fallback -c succeeded for '{job.get('name', '?')}'")
                        status = 'done'
                    else:
                        err2 = strip_ansi(r2.stderr.strip()[:100] or r2.stdout.strip()[:100] or 'unknown')
                        status = 'fail: ' + err2
        if status == 'unknown':
            status = 'done' if r.returncode == 0 else 'fail: ' + strip_ansi(r.stderr.strip()[:100] or r.stdout.strip()[:100] or 'unknown')
    except subprocess.TimeoutExpired:
        status = 'fail: timeout (>10m)'
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
        except Exception:
            pass

_cron_event = threading.Event()

def signal_cron() -> None:
    """Wake up the cron runner for immediate tick."""
    _cron_event.set()

def _cron_runner() -> None:
    while True:
        try:
            _cron_event.wait(30)
            _cron_event.clear()
            jobs = _load_cron_jobs()
            if not isinstance(jobs, list):
                continue
            now = time.time()
            # Reset stale _running flags from crashed runs
            _stale = False
            for job in jobs:
                if job.get('_running') and job.get('last_run', 0) == 0:
                    job.pop('_running', None)
                    _stale = True
            if _stale:
                _save_cron_jobs(jobs)
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
        except Exception:
            _cron_event.wait(30)
            _cron_event.clear()
