#!/usr/bin/env python3
"""System data collection: process parsing, CPU/memory/disk, engine detection."""
import subprocess
import json
import os
import time
import multiprocessing
from datetime import datetime, timezone

from poller_config import (
    data_dir, status_file, session_details_file, prev_pids_file,
    log_activity_py, timestamp, skip_utils, generate_codename
)

def parse_ps_output(cpu_core_count: int) -> tuple:
    """Run ps axo and return (proc_list, agent_list, main_pid, main_elapsed, total_cpu, total_mem_mb, cpu_load_pct).
    Computes system CPU from the single ps pass — no second ps aux needed."""
    result = subprocess.run(
        ['ps', 'axo', 'pid,ppid,pcpu,rss,etime,args'],
        capture_output=True, text=True, timeout=30
    )
    lines = result.stdout.strip().split('\n')[1:]

    proc_list = []
    agent_list = []

    # Compute system-wide CPU from ALL lines in this single pass
    system_cpu_total = 0.0
    for line in lines:
        parts = line.split(None, 5)
        if len(parts) >= 3:
            try:
                system_cpu_total += float(parts[2])
            except Exception:
                pass
    cpu_load_pct = round(system_cpu_total / cpu_core_count, 1) if cpu_core_count else 0

    # Find NodeService PID first
    node_pid = None
    for line2 in lines:
        if 'NodeService' in line2 and 'opencode' in line2.lower():
            try:
                node_pid = int(line2.split(None, 10)[1])
            except Exception:
                pass
            break

    for line in lines:
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        pid = int(parts[0])
        ppid = int(parts[1])
        cpu = float(parts[2])
        rss_kb = int(parts[3])
        mem_mb = round(rss_kb / 1024, 1)
        elapsed_raw = parts[4]
        cmd = parts[5]

        name = os.path.basename(cmd.split()[0]) if cmd.split() else '?'
        cmd_lower = cmd.lower()

        if 'grep' in cmd:
            continue
        if 'daemon.sh' in cmd or '/poller.py' in cmd:
            continue
        if name in skip_utils:
            continue
        if 'opencode session list' in cmd or 'opencode export' in cmd or 'opencode.workspace' in cmd:
            continue

        is_opencode = 'opencode' in cmd_lower or 'smart-git-update' in cmd
        is_browser_sync = 'browser-sync' in cmd_lower or 'live-server' in cmd_lower
        is_new_agent_cmd = is_browser_sync or ('npm exec' in cmd and '3000' in cmd)
        is_direct_child = node_pid is not None and ppid == node_pid

        if not is_opencode and not is_new_agent_cmd and not is_direct_child:
            continue

        proc_list.append({
            'pid': pid, 'ppid': ppid, 'name': name[:40],
            'cpu': cpu, 'mem_mb': mem_mb, 'elapsed': elapsed_raw
        })

        if 'smart-git-update' in cmd:
            agent_type = 'agent'
            agent_name = 'Git Updater Agent'
        elif '/Contents/MacOS/OpenCode' in cmd and 'Helper' not in cmd:
            continue
        elif 'NodeService' in cmd:
            agent_type = 'engine'
            agent_name = 'Brandon'
        elif 'Helper (Renderer)' in cmd:
            continue
        elif 'Helper' in cmd and 'GPU' in cmd:
            agent_type = 'helper'
            agent_name = 'GPU Process'
        elif 'Helper' in cmd and 'Audio' in cmd:
            continue
        elif 'Helper' in cmd and 'network' in cmd:
            continue
        elif 'Crashpad' in cmd or 'crashpad' in cmd:
            continue
        elif 'browser-sync' in cmd_lower:
            agent_type = 'agent'
            agent_name = 'Web Server Agent'
        elif 'npm exec' in cmd and '3000' in cmd:
            agent_type = 'agent'
            agent_name = 'NPM Exec Agent'
        elif 'opencode' in cmd_lower and 'Helper' in cmd:
            continue
        else:
            agent_type = 'agent'
            agent_name = name[:30]

        agent_list.append({
            'pid': pid, 'ppid': ppid, 'name': agent_name, 'type': agent_type,
            'cpu': cpu, 'mem_mb': mem_mb, 'elapsed': elapsed_raw,
            'command': cmd[:200]
        })

    total_cpu = round(sum(a['cpu'] for a in agent_list), 1)
    total_mem_mb = round(sum(a['mem_mb'] for a in agent_list))
    main_pids = [a['pid'] for a in agent_list if a['type'] == 'engine']
    main_pid = main_pids[0] if main_pids else 0
    main_elapsed = ''
    if main_pid:
        main_elapsed = subprocess.run(
            ['ps', '-o', 'etime=', '-p', str(main_pid)],
            capture_output=True, text=True
        ).stdout.strip()

    return proc_list, agent_list, main_pid, main_elapsed, total_cpu, total_mem_mb, cpu_load_pct

def get_disk_stats() -> tuple:
    """Return (disk_free, disk_total) for root partition."""
    try:
        disk = subprocess.run(
            ['df', '-h', '/'], capture_output=True, text=True, timeout=10
        ).stdout.strip().split('\n')
        disk_parts = disk[1].split() if len(disk) > 1 else ['?', '?', '?', '?']
        return (disk_parts[3] if len(disk_parts) > 3 else '?',
                disk_parts[1] if len(disk_parts) > 1 else '?')
    except Exception:
        return '?', '?'

def get_mem_total_gb() -> float:
    """Return total system memory in GB."""
    try:
        r = subprocess.run(
            ['sysctl', '-n', 'hw.memsize'],
            capture_output=True, text=True, timeout=10
        ).stdout.strip()
        return round(int(r) / 1024**3, 1) if r.isdigit() else 0
    except Exception:
        return 0

def detect_engine_restart(main_pid: int) -> str | None:
    """Check if engine PID changed since last poll. Returns restart timestamp or None."""
    engine_restarted_at = None
    prev_main_pid = 0
    if os.path.exists(status_file):
        try:
            with open(status_file) as f:
                prev_data = json.load(f)
            prev_main_pid = prev_data.get('summary', {}).get('main_pid', 0)
            if prev_main_pid > 0 and main_pid and prev_main_pid != main_pid:
                engine_restarted_at = timestamp
                log_activity_py(f"Engine restart detected: PID {prev_main_pid} -> {main_pid}")
                if os.path.exists(session_details_file):
                    try:
                        os.remove(session_details_file)
                    except Exception:
                        pass
        except Exception:
            pass
    return engine_restarted_at

def load_prev_agents() -> list:
    """Load previous agent PIDs for cycle-to-cycle comparison."""
    prev_agents = []
    if os.path.exists(prev_pids_file):
        try:
            with open(prev_pids_file) as f:
                all_prev = json.load(f)
            prev_agents = [
                p for p in all_prev
                if p.get('name', '').lower() not in skip_utils
                and 'opencode session list' not in p.get('command', '')
                and 'opencode export' not in p.get('command', '')
                and p.get('command', '') != '(opencode)'
            ]
        except Exception:
            pass
    return prev_agents

def save_prev_pids(agent_list: list) -> None:
    """Save current agent PIDs for next cycle."""
    try:
        tmp = prev_pids_file + '.tmp'
        with open(tmp, 'w') as f:
            to_save = []
            for a in agent_list:
                if a.get('status') == 'finished':
                    continue
                cmd = a.get('command', '')
                if 'opencode session list' in cmd or 'opencode export' in cmd or cmd == '(opencode)':
                    continue
                to_save.append({
                    'pid': a['pid'], 'ppid': a.get('ppid', 0),
                    'name': a['name'], 'type': a['type'], 'command': cmd
                })
            json.dump(to_save, f)
        os.replace(tmp, prev_pids_file)
    except Exception:
        pass
