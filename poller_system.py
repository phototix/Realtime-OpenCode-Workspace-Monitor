#!/usr/bin/env python3
import os
import json
import subprocess
import time
import multiprocessing

from poller_config import data_dir, prev_pids_file, log_activity_py

def _parse_time_to_seconds(raw: str) -> int:
    if not raw:
        return 0
    try:
        parts = raw.strip().split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        pass
    return 0

def parse_ps_output(cpu_core_count: int):
    proc_list = []
    agent_list = []
    main_pid = 0
    main_elapsed = 'N/A'
    total_cpu = 0.0
    total_mem_mb = 0.0
    cpu_load_pct = 0
    try:
        r = subprocess.run([
            'ps', '-eo', 'pid,ppid,pcpu,rss,etime,comm,args', '--no-headers'
        ], capture_output=True, text=True, timeout=10)
        for line in r.stdout.splitlines():
            parts = line.split(None, 6)
            if len(parts) < 7:
                continue
            pid = int(parts[0])
            ppid = int(parts[1])
            pcpu = float(parts[2] or 0)
            rss_kb = float(parts[3] or 0)
            etime = parts[4]
            comm = parts[5]
            args = parts[6]
            cpu = pcpu
            mem_mb = round(rss_kb / 1024, 1)
            total_cpu += cpu
            total_mem_mb += mem_mb
            item = {
                'pid': pid,
                'ppid': ppid,
                'cpu': round(cpu, 1),
                'mem_mb': mem_mb,
                'elapsed': etime,
                'command': args,
                'name': comm,
                'type': 'engine' if 'server.py' in args or 'poller.py' in args or 'daemon.sh' in args else 'agent',
                'status': 'running',
                'virtual': False,
            }
            proc_list.append(item)
            agent_list.append(item.copy())
            if 'server.py' in args and main_pid == 0:
                main_pid = pid
                main_elapsed = etime
    except Exception as e:
        log_activity_py(f'poller_system parse_ps_output failed: {e}')
    cpu_load_pct = min(100, int(round(total_cpu)))
    return proc_list, agent_list, main_pid, main_elapsed, round(total_cpu, 1), round(total_mem_mb, 1), cpu_load_pct

def get_disk_stats():
    try:
        r = subprocess.run(['df', '-h', data_dir], capture_output=True, text=True, timeout=5)
        lines = r.stdout.splitlines()
        if len(lines) >= 2:
            cols = lines[1].split()
            if len(cols) >= 5:
                return cols[3], cols[1]
    except Exception:
        pass
    return '0', '0'

def get_mem_total_gb():
    try:
        r = subprocess.run(['free', '-m'], capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            if line.lower().startswith('mem:'):
                cols = line.split()
                if len(cols) >= 2:
                    return round(float(cols[1]) / 1024, 1)
    except Exception:
        pass
    return 0.0

def detect_engine_restart(main_pid: int):
    status_path = os.path.join(data_dir, 'status.json')
    if not os.path.exists(status_path):
        return None
    try:
        with open(status_path) as f:
            old = json.load(f)
        prev = old.get('summary', {}).get('main_pid')
        if prev and main_pid and prev != main_pid:
            return old.get('timestamp')
    except Exception:
        pass
    return None

def load_prev_agents():
    if not os.path.exists(prev_pids_file):
        return []
    try:
        with open(prev_pids_file) as f:
            return json.load(f)
    except Exception:
        return []

def save_prev_pids(agent_list):
    try:
        with open(prev_pids_file, 'w') as f:
            json.dump([a for a in agent_list if a.get('status') != 'finished'], f, indent=2)
    except Exception:
        pass
