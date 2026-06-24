#!/usr/bin/env python3
"""Cron job scheduling and execution for the MyDora dashboard."""
import json
import os
import subprocess
import threading
import time

from server_config import (
    DATA_DIR, CRON_FILE, ACTIVITY_FILE, CONFIG_FILE,
    _cron_lock, _safe_agent_name, _safe_path, _safe_shell_arg,
    strip_ansi, get_attach_url, log
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
        attach = get_attach_url()
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
        cmd.extend(['--attach', attach])
        password = os.environ.get('OPENCODE_SERVER_PASSWORD', '')
        if password:
            cmd.extend(['-p', password])
        if action.get('model'):
            cmd.extend(['-m', action['model']])
        message = action.get('message', '')
        # Prepend project instruction if set
        proj_inst = ''
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE) as f:
                    pc = json.load(f)
                    if pc.get('project_instruction'):
                        proj_inst = pc['project_instruction']
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
