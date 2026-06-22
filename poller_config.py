#!/usr/bin/env python3
"""Shared configuration and utilities for the poller."""
import json
import os
from datetime import datetime, timezone

data_dir = os.path.expanduser('~/.opencode-dashboard/data')
config_file = os.path.join(os.path.dirname(data_dir), 'config.json')
activity_file = os.path.join(data_dir, 'activity.log')
status_file = os.path.join(data_dir, 'status.json')
prev_pids_file = os.path.join(data_dir, 'prev_pids.json')
session_details_file = os.path.join(data_dir, 'session_details.json')
export_lock_file = os.path.join(data_dir, 'export.lock')
assignments_file = os.path.join(data_dir, 'case_assignments.json')
staff_file_path = os.path.join(data_dir, 'super_staff.json')
os.makedirs(data_dir, exist_ok=True)

def log_activity_py(msg: str) -> None:
    try:
        with open(activity_file, 'a') as f:
            ts = datetime.now().strftime('%H:%M:%S')
            f.write(f'[{ts}] {msg}\n')
        with open(activity_file) as f:
            lines = f.readlines()
        if len(lines) > 100:
            tmp = activity_file + '.tmp'
            with open(tmp, 'w') as f:
                f.writelines(lines[-100:])
            os.replace(tmp, activity_file)
    except Exception:
        pass

timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

skip_utils = {
    'find', 'sort', 'head', 'du', 'ps', 'sleep', 'cat', 'curl', 'wc', 'rg',
    'awk', 'sed', 'echo', 'printf', 'mkdir', 'touch', 'rm', 'mv', 'cp', 'tr',
    'cut', 'xargs', 'comm', 'diff', 'patch', 'tar', 'gzip', 'gunzip', 'zip',
    'unzip', 'git'
}

adjectives = [
    'cosmic', 'mighty', 'swift', 'brave', 'calm', 'eager', 'fancy', 'grand',
    'happy', 'jolly', 'keen', 'lively', 'merry', 'noble', 'proud', 'quiet',
    'rapid', 'sharp', 'tidy', 'vivid', 'warm', 'zesty', 'amber', 'bliss',
    'crisp', 'dusk', 'ember', 'frost', 'gleam', 'haze', 'iris', 'jade',
    'lunar', 'mist', 'nova', 'onyx', 'pearl', 'ripple', 'solar', 'twist',
    'umbra', 'vapor', 'whim', 'zen'
]
nouns = [
    'engine', 'fox', 'hawk', 'wolf', 'bear', 'deer', 'owl', 'swan', 'wren',
    'heron', 'elm', 'oak', 'pine', 'maple', 'ash', 'willow', 'coral', 'ridge',
    'peak', 'vale', 'brook', 'lake', 'stone', 'cloud', 'storm', 'comet',
    'orbit', 'prism', 'beacon', 'pilot', 'sailor', 'knight', 'rogue', 'sage',
    'spark', 'whisper', 'echo', 'pulse', 'drift', 'glide', 'bloom', 'root',
    'node', 'core', 'cell', 'gear', 'quill', 'flame'
]

_codename_cache: dict[int, str] = {}
def generate_codename(pid: int = 0) -> str:
    if pid in _codename_cache:
        return _codename_cache[pid]
    idx = (pid * 7 + 13) % len(adjectives)
    idx2 = (pid * 31 + 7) % len(nouns)
    cn = f'{adjectives[idx]}-{nouns[idx2]}'
    _codename_cache[pid] = cn
    return cn
