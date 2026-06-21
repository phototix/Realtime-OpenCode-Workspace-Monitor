#!/usr/bin/env python3
"""Main orchestrator: collects system + session data and writes status.json."""
import json
import os
import subprocess
import time
import multiprocessing
from datetime import datetime, timezone

from poller_config import (
    data_dir, status_file, activity_file, session_details_file,
    prev_pids_file, skip_utils, log_activity_py, timestamp
)
from poller_system import (
    parse_ps_output, get_disk_stats, get_mem_total_gb,
    detect_engine_restart, load_prev_agents, save_prev_pids
)
from poller_sessions import (
    fetch_all_sessions, match_agents_to_sessions,
    build_active_sessions, manage_virtual_agents,
    enrich_session_details
)

# ── STEP 1: Collect system process data ──
cpu_core_count = multiprocessing.cpu_count()
proc_list, agent_list, main_pid, main_elapsed, total_cpu, total_mem_mb, cpu_load_pct = parse_ps_output(cpu_core_count)
disk_free, disk_total = get_disk_stats()
mem_total_gb = get_mem_total_gb()
engine_restarted_at = detect_engine_restart(main_pid)

# ── STEP 2: Fetch session list ──
all_sessions = fetch_all_sessions()

# ── STEP 3: Match agents to sessions ──
agent_list, agent_to_session = match_agents_to_sessions(agent_list, all_sessions)

# ── STEP 4: Build active session list ──
sessions = build_active_sessions(all_sessions, agent_to_session)

# ── STEP 5: Manage virtual agents ──
agent_list, sessions = manage_virtual_agents(agent_list, sessions, all_sessions)

# ── STEP 6: Session detail enrichment ──
detail_cache = {}
if os.path.exists(session_details_file):
    try:
        with open(session_details_file) as f:
            detail_cache = json.load(f)
    except Exception:
        pass
detail_cache = enrich_session_details(sessions, detail_cache)

# ── STEP 7: Load case assignments + super staff + todos ──
case_assignments = {}
if os.path.exists(os.path.join(data_dir, 'case_assignments.json')):
    try:
        with open(os.path.join(data_dir, 'case_assignments.json')) as f:
            case_assignments = json.load(f)
    except Exception:
        pass
super_staff_map = {}
if os.path.exists(os.path.join(data_dir, 'super_staff.json')):
    try:
        with open(os.path.join(data_dir, 'super_staff.json')) as f:
            for s in json.load(f):
                super_staff_map[s['name']] = s
    except Exception:
        pass
todos_map = {}
_db_path = os.path.expanduser('~/.local/share/opencode/opencode.db')
if os.path.exists(_db_path):
    try:
        import sqlite3
        _conn = sqlite3.connect(_db_path, timeout=2)
        for sid, content, status, priority, pos in _conn.execute('SELECT session_id, content, status, priority, position FROM todo ORDER BY session_id, position'):
            todos_map.setdefault(sid, []).append({'content': content, 'status': status, 'priority': priority, 'position': pos})
        _conn.close()
    except Exception:
        pass

# Apply cache to active sessions
for s in sessions:
    sid = s.get('id', '')
    cached = detail_cache.get(sid, {})
    s['slug'] = cached.get('slug', '')
    s['state'] = cached.get('state', '')
    s['last_user_prompt'] = cached.get('last_user_prompt', '')
    s['last_text'] = cached.get('last_text', '')
    s['tool_name'] = cached.get('tool_name', '')
    s['last_role'] = cached.get('last_role', '')
    s['last_mode'] = cached.get('last_mode', '')
    s['tokens'] = cached.get('tokens', 0)
    s['cost'] = cached.get('cost', 0)
    s['files_changed'] = cached.get('files_changed', 0)
    s['agent_type'] = cached.get('agent_type', '')
    s['model_id'] = cached.get('model_id', '')
    s['pending_questions'] = cached.get('pending_questions', [])
    assigned_name = case_assignments.get(sid, '')
    if assigned_name:
        s['assigned_staff'] = assigned_name
        staff_info = super_staff_map.get(assigned_name, {})
        s['staff_gender'] = staff_info.get('gender', 'male')
        s['staff_mode'] = staff_info.get('mode', '')
        s['staff_model'] = staff_info.get('model', '')
    session_todos = todos_map.get(sid, [])
    if session_todos:
        s['todos'] = session_todos

# Enrich all_sessions for admin panel
known_sids = {s['id'] for s in sessions}
all_sessions_enriched = []
for s in all_sessions:
    sid = s.get('id', '')
    cached = detail_cache.get(sid, {})
    enriched = {
        'id': sid,
        'title': s.get('title', ''),
        'updated': s.get('updated', 0),
        'directory': s.get('directory', ''),
        'agent': s.get('agent', ''),
        'slug': cached.get('slug', ''),
        'state': cached.get('state', ''),
        'last_user_prompt': cached.get('last_user_prompt', ''),
        'last_text': cached.get('last_text', ''),
        'tool_name': cached.get('tool_name', ''),
        'last_role': cached.get('last_role', ''),
        'last_mode': cached.get('last_mode', ''),
        'tokens': cached.get('tokens', 0),
        'cost': cached.get('cost', 0),
        'files_changed': cached.get('files_changed', 0),
        'agent_type': cached.get('agent_type', ''),
        'model_id': cached.get('model_id', ''),
        'pending_questions': cached.get('pending_questions', []),
        'active': sid in known_sids,
    }
    assigned_name = case_assignments.get(sid, '')
    if assigned_name:
        enriched['assigned_staff'] = assigned_name
        staff_info = super_staff_map.get(assigned_name, {})
        enriched['staff_gender'] = staff_info.get('gender', 'male')
        enriched['staff_mode'] = staff_info.get('mode', '')
        enriched['staff_model'] = staff_info.get('model', '')
    session_todos = todos_map.get(sid, [])
    if session_todos:
        enriched['todos'] = session_todos
    all_sessions_enriched.append(enriched)

# ── STEP 8: Session cleanup ──
now_ms = int(datetime.now().timestamp() * 1000)
five_min_ms = 5 * 60 * 1000
removed_titles = {
    s['title'] for s in sessions
    if s.get('state') == 'complete' and (now_ms - s.get('updated', 0)) > five_min_ms
}
sessions[:] = [s for s in sessions if s['title'] not in removed_titles]
for r_title in removed_titles:
    log_activity_py(f"Session completed: {r_title}")

for a in agent_list:
    if a.get('session_title') and a['session_title'] in removed_titles:
        a['session_title'] = ''

active_titles = {s['title'] for s in sessions}
agent_list[:] = [
    a for a in agent_list
    if not (a.get('virtual') and a.get('session_title')
            and a['session_title'] not in active_titles)
]

# Remove stale real agents: no session, cpu=0, running >2h
def _elapsed_hours(s):
    try:
        et = s.get('elapsed', '') or ''
        if ':' in et:
            parts = et.strip().split(':')
            if len(parts) == 3:
                return int(parts[0]) + int(parts[1]) / 60
            elif len(parts) == 2:
                return int(parts[0]) / 60
        return 0
    except Exception:
        return 0

for a in agent_list:
    if not a.get('virtual') and a['type'] != 'engine':
        st = a.get('session_title', '')
        if not st and a.get('cpu', 0) == 0 and _elapsed_hours(a) > 2:
            a['status'] = 'finished'

# Update session titles on agents from all_sessions
for a in agent_list:
    for s in sessions:
        if any(ma.get('pid') == a['pid'] for ma in s.get('agents', [])):
            a['session_title'] = s['title']
            break

# ── STEP 9: Attach agents to sessions ──
for s in sessions:
    title = s.get('title', '')
    matching = [
        a for a in agent_list
        if a.get('session_title') == title and not a.get('virtual') and a['type'] != 'engine'
    ]
    s['agents'] = []
    for m in matching:
        s['agents'].append({
            'pid': m['pid'],
            'ppid': m.get('ppid', 0),
            'name': m['name'],
            'cpu': m['cpu'],
            'mem_mb': m['mem_mb'],
            'elapsed': m['elapsed'],
            'command': m.get('command', '')[:120]
        })

# Log transient and unclaimed workers
brandon_pid2 = next((a['pid'] for a in agent_list if a['type'] == 'engine'), None)
transient_list = [
    a for a in agent_list
    if not a.get('virtual') and a['type'] != 'engine'
    and a.get('ppid') == brandon_pid2
    and not any(a['pid'] == ma['pid'] for s in sessions for ma in s.get('agents', []))
]
for a in transient_list:
    proc_name = os.path.basename(
        (a.get('command') or '').split()[0] if a.get('command') else '?'
    )
    if proc_name in skip_utils:
        log_activity_py(f"Transient: {proc_name} (PID {a['pid']}) · {a.get('elapsed', '?')}")
    else:
        log_activity_py(f"Unclaimed worker: {a.get('name', proc_name)} (PID {a['pid']}) · {a.get('elapsed', '?')}")

# Assign unclaimed Brandon children to sessions needing agents
unclaimed = [
    a for a in agent_list
    if not a.get('virtual') and a['type'] != 'engine'
    and a.get('status') != 'finished'
    and a['ppid'] == brandon_pid2
    and not any(a['pid'] == ma['pid'] for s in sessions for ma in s.get('agents', []))
    and os.path.basename(
        (a.get('command') or '').split()[0] if a.get('command') else ''
    ) not in skip_utils
]
sessions_sorted = sorted(sessions, key=lambda s: s.get('updated', 0), reverse=True)
for a in unclaimed:
    target = next((s for s in sessions_sorted if len(s.get('agents', [])) == 0), None)
    if not target:
        break
    target.setdefault('agents', []).append({
        'pid': a['pid'],
        'ppid': a.get('ppid', 0),
        'name': a.get('name', ''),
        'cpu': a['cpu'],
        'mem_mb': a['mem_mb'],
        'elapsed': a.get('elapsed', ''),
        'command': a.get('command', '')[:120]
    })

# Redistribute: release agents from completed sessions into thinking sessions
thinking_sessions = [
    s for s in sessions if s.get('state') in ('thinking', 'running-tools', '')
]
completed = [s for s in sessions if s.get('state') == 'complete' and s.get('agents')]
for s in completed:
    freed = s.get('agents', [])
    s['agents'] = []
    for w in freed:
        target = next(
            (ts for ts in thinking_sessions if len(ts.get('agents', [])) < 3),
            None
        )
        if target:
            target.setdefault('agents', []).append(w)
        else:
            s['agents'].append(w)

# ── STEP 10: Standalone agents ──
claimed_pids = {ma['pid'] for s in sessions for ma in s.get('agents', [])}
pid_to_name = {a['pid']: a.get('name') for a in agent_list}
standalone = []
for a in agent_list:
    if a.get('virtual') or a['type'] == 'engine' or a['pid'] in claimed_pids or a.get('status') == 'finished':
        continue
    proc_name = os.path.basename(
        (a.get('command') or '').split()[0] if a.get('command') else ''
    )
    if proc_name in skip_utils:
        log_activity_py(f"Standalone transient: {proc_name} (PID {a['pid']})")
        continue
    ppid = a.get('ppid', 0)
    parent_name = pid_to_name.get(ppid, '')
    standalone.append({
        'pid': a['pid'],
        'name': a.get('name', ''),
        'cpu': a['cpu'],
        'mem_mb': a['mem_mb'],
        'elapsed': a.get('elapsed', ''),
        'parent': parent_name or str(ppid)
    })

# ── STEP 11: Assemble payload ──
total_cost = sum(cached.get('cost', 0) for cached in detail_cache.values())
worker_pids = set()
for s in sessions:
    for w in s.get('agents', []):
        worker_pids.add(w['pid'])
worker_count = len(worker_pids) + len(standalone)

activities = []
if os.path.exists(activity_file):
    with open(activity_file) as f:
        alines = f.readlines()
        activities = [l.strip() for l in alines[-30:]]

# Build process hierarchy
child_map = {}
pid_to_agent = {}
for a in agent_list:
    pid_to_agent[a['pid']] = a
for a in agent_list:
    ppid = a.get('ppid', 0)
    if ppid in pid_to_agent and a['pid'] != ppid and ppid != 0:
        child_map.setdefault(ppid, []).append(a['pid'])
for a in agent_list:
    a['children'] = child_map.get(a['pid'], [])

root_pid = next((a['pid'] for a in agent_list if a['type'] == 'engine'), None)
tree_root = root_pid if root_pid else (agent_list[0]['pid'] if agent_list else 0)

# Keep recently finished agents for 2 cycles
prev_agents_data = load_prev_agents()
current_pids = {a['pid'] for a in agent_list}
recent_finished = []
for pa in prev_agents_data:
    if pa['pid'] not in current_pids:
        pa['status'] = 'finished'
        recent_finished.append(pa)
for rf in recent_finished[-5:]:
    if not any(a['pid'] == rf['pid'] for a in agent_list):
        agent_list.append(rf)

# Fetch available models
available_models = []
try:
    r = subprocess.run(
        ['opencode', 'models'], capture_output=True, text=True, timeout=15
    )
    if r.returncode == 0:
        for line in r.stdout.strip().split('\n'):
            line = line.strip()
            if line and '/' in line:
                available_models.append({'id': line, 'provider': 'opencode'})
except Exception:
    pass

# Read boss name
boss_name = 'Brandon'
try:
    bn_path = os.path.join(data_dir, 'boss_name.json')
    if os.path.exists(bn_path):
        with open(bn_path) as f:
            bn = json.load(f)
            if bn.get('name'):
                boss_name = bn['name']
except Exception:
    pass

payload = {
    'timestamp': timestamp,
    'summary': {
        'total_cost': total_cost,
        'worker_count': worker_count,
        'cpu_core_count': cpu_core_count,
        'cpu_load_pct': cpu_load_pct,
        'active_task_count': worker_count,
        'agent_count': len([a for a in agent_list if a.get('status') != 'finished']),
        'total_procs': len(proc_list),
        'main_pid': main_pid,
        'prev_main_pid': 0,
        'engine_restarted_at': engine_restarted_at,
        'uptime': main_elapsed or 'N/A',
        'total_cpu': total_cpu,
        'total_cpu_str': f'{total_cpu}%',
        'total_mem_mb': total_mem_mb,
        'total_mem_gb': round(total_mem_mb / 1024, 1),
        'disk_free': disk_free,
        'disk_total': disk_total,
        'mem_total_gb': mem_total_gb,
        'boss_name': boss_name,
    },
    'agents': agent_list,
    'standalone': standalone,
    'processes': proc_list,
    'tree_root': tree_root,
    'sessions': sessions,
    'all_sessions': all_sessions_enriched,
    'available_models': available_models,
    'activity_log': activities
}

# Write status.json atomically
try:
    tmp = status_file + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(payload, f, indent=2, default=str)
    os.replace(tmp, status_file)
except Exception:
    pass

# Save detail cache
try:
    tmp = session_details_file + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(detail_cache, f, indent=2, default=str)
    os.replace(tmp, session_details_file)
except Exception:
    pass

# Export lock cleanup
if os.path.exists(os.path.join(data_dir, 'export.lock')):
    try:
        lock_age = time.time() - os.path.getmtime(os.path.join(data_dir, 'export.lock'))
        if lock_age > 30:
            os.remove(os.path.join(data_dir, 'export.lock'))
    except Exception:
        pass

# Save PIDs for next cycle
save_prev_pids(agent_list)
