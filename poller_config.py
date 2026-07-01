#!/usr/bin/env python3
import json
import os
import hashlib
from datetime import datetime, timezone

data_dir = os.path.expanduser('~/.opencode-dashboard/data')
config_file = os.path.join(data_dir, 'config.json')
status_file = os.path.join(data_dir, 'status.json')
activity_file = os.path.join(data_dir, 'activity.log')
session_details_file = os.path.join(data_dir, 'session_details.json')
prev_pids_file = os.path.join(data_dir, 'prev_pids.json')
export_lock_file = os.path.join(data_dir, 'export.lock')
staff_file_path = os.path.join(data_dir, 'super_staff.json')
assignments_file = os.path.join(data_dir, 'case_assignments.json')
skip_utils = {
    'find', 'sort', 'head', 'du', 'ps', 'sleep', 'cat', 'curl', 'wc', 'mkdir', 'touch',
    'rm', 'mv', 'cp', 'zsh', 'bash', 'sh', 'rg', 'grep', 'awk', 'sed', 'echo', 'printf',
    'node', 'python', 'python3'
}

def timestamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def log_activity_py(message: str) -> None:
    try:
        os.makedirs(data_dir, exist_ok=True)
        with open(activity_file, 'a') as f:
            f.write(f'[{datetime.now().strftime("%H:%M:%S")}] {message}\n')
    except Exception:
        pass

def generate_codename(pid: int) -> str:
    seed = hashlib.sha256(str(pid).encode('utf-8')).hexdigest()
    return 'Agent-' + seed[:6]
