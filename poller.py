#!/usr/bin/env python3
import subprocess
import json
import os
import random
import time
import multiprocessing
from datetime import datetime, timezone

data_dir = os.path.expanduser('~/.opencode-dashboard/data')
activity_file = os.path.join(data_dir, 'activity.log')
status_file = os.path.join(data_dir, 'status.json')
prev_pids_file = os.path.join(data_dir, 'prev_pids.json')
session_details_file = os.path.join(data_dir, 'session_details.json')
export_lock_file = os.path.join(data_dir, 'export.lock')
os.makedirs(data_dir, exist_ok=True)

def log_activity_py(msg):
    try:
        with open(activity_file, 'a') as f:
            ts = datetime.now().strftime('%H:%M:%S')
            f.write(f'[{ts}] {msg}\n')
        with open(activity_file) as f:
            lines = f.readlines()
        if len(lines) > 100:
            with open(activity_file, 'w') as f:
                f.writelines(lines[-100:])
    except:
        pass

timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

# Load previous agent PIDs to detect short-lived agents
skip_utils = {'find', 'sort', 'head', 'du', 'ps', 'sleep', 'cat', 'curl', 'wc', 'rg', 'awk', 'sed', 'echo', 'printf', 'mkdir', 'touch', 'rm', 'mv', 'cp', 'tr', 'cut', 'xargs', 'comm', 'diff', 'patch', 'tar', 'gzip', 'gunzip', 'zip', 'unzip', 'git'}

prev_agents = []
if os.path.exists(prev_pids_file):
  try:
    with open(prev_pids_file) as f:
      all_prev = json.load(f)
    prev_agents = [p for p in all_prev 
  if p.get('name', '').lower() not in skip_utils
  and 'opencode session list' not in p.get('command', '')
  and 'opencode export' not in p.get('command', '')
  and p.get('command', '') != '(opencode)'
]
  except: pass

result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
lines = result.stdout.strip().split('\n')[1:]

proc_list = []
agent_list = []

for line in lines:
  parts = line.split(None, 10)
  if len(parts) < 11:
    continue
  cmd = parts[10]
  pid = int(parts[1])
  ppid_raw = subprocess.run(['ps', '-o', 'ppid=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()
  ppid = int(ppid_raw) if ppid_raw.isdigit() else 0
  cpu = float(parts[2])
  rss_kb = int(parts[5])
  mem_mb = round(rss_kb / 1024, 1)
  elapsed_raw = subprocess.run(['ps', '-o', 'etime=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()

  name = os.path.basename(cmd.split()[0]) if cmd.split() else '?'
  cmd_lower = cmd.lower()

  if 'grep' in cmd:
    continue
  if 'daemon.sh' in cmd or '/poller.py' in cmd:
    continue
  if name in skip_utils:
    continue

  # Find NodeService PID
  node_pid = None
  for line2 in lines:
    if 'NodeService' in line2 and 'opencode' in line2.lower():
      try: node_pid = int(line2.split(None, 10)[1])
      except: pass
      break

  # Skip poller's own opencode CLI queries
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
    # NodeService child but not a known type
    agent_type = 'agent'
    agent_name = name[:30]

  agent_list.append({
    'pid': pid, 'ppid': ppid, 'name': agent_name, 'type': agent_type,
    'cpu': cpu, 'mem_mb': mem_mb, 'elapsed': elapsed_raw,
    'command': cmd[:200]
  })

total_cpu = round(sum(a['cpu'] for a in agent_list), 1)
total_mem_mb = round(sum(a['mem_mb'] for a in agent_list))

disk = subprocess.run(['df', '-h', '/'], capture_output=True, text=True).stdout.strip().split('\n')
disk_parts = disk[1].split() if len(disk) > 1 else ['?', '?', '?', '?']
disk_free = disk_parts[3] if len(disk_parts) > 3 else '?'
disk_total = disk_parts[1] if len(disk_parts) > 1 else '?'

sysctl_r = subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True).stdout.strip()
mem_total_gb = round(int(sysctl_r) / 1024**3, 1) if sysctl_r.isdigit() else 0

main_pids = [a['pid'] for a in agent_list if a['type'] == 'engine']
main_pid = main_pids[0] if main_pids else 0
main_elapsed = ''
if main_pid:
  main_elapsed = subprocess.run(['ps', '-o', 'etime=', '-p', str(main_pid)], capture_output=True, text=True).stdout.strip()

# Fetch opencode session list and match to agents with codenames
adjectives = ['cosmic', 'mighty', 'swift', 'brave', 'calm', 'eager', 'fancy', 'grand', 'happy', 'jolly', 'keen', 'lively', 'merry', 'noble', 'proud', 'quiet', 'rapid', 'sharp', 'tidy', 'vivid', 'warm', 'zesty', 'amber', 'bliss', 'crisp', 'dusk', 'ember', 'frost', 'gleam', 'haze', 'iris', 'jade', 'lunar', 'mist', 'nova', 'onyx', 'pearl', 'ripple', 'solar', 'twist', 'umbra', 'vapor', 'whim', 'zen']
nouns = ['engine', 'fox', 'hawk', 'wolf', 'bear', 'deer', 'owl', 'swan', 'wren', 'heron', 'elm', 'oak', 'pine', 'maple', 'ash', 'willow', 'coral', 'ridge', 'peak', 'vale', 'brook', 'lake', 'stone', 'cloud', 'storm', 'comet', 'orbit', 'prism', 'beacon', 'pilot', 'sailor', 'knight', 'rogue', 'sage', 'spark', 'whisper', 'echo', 'pulse', 'drift', 'glide', 'bloom', 'root', 'node', 'core', 'cell', 'gear', 'quill', 'flame']

# Codenames for agents - stable per PID using hash
_codename_cache = {}
def generate_codename(pid=0):
  if pid in _codename_cache:
    return _codename_cache[pid]
  idx = (pid * 7 + 13) % len(adjectives)
  idx2 = (pid * 31 + 7) % len(nouns)
  cn = f'{adjectives[idx]}-{nouns[idx2]}'
  _codename_cache[pid] = cn
  return cn

# Fetch session list (JSON)
sessions = []
try:
  session_result = subprocess.run(
    ['opencode', 'session', 'list', '--format', 'json'],
    capture_output=True, text=True, timeout=10
  )
  all_sessions = json.loads(session_result.stdout)
except Exception:
  all_sessions = []

# Also check known project directories for project-scoped sessions
try:
  known_ids = {s['id'] for s in all_sessions}
  global_data_path = os.path.expanduser('~/Library/Application Support/ai.opencode.desktop/opencode.global.dat')
  if os.path.exists(global_data_path):
    with open(global_data_path) as f:
      gd = json.load(f)
    if 'server' in gd:
      server_config = json.loads(gd['server'])
      for proj in server_config.get('projects', {}).get('local', []):
        worktree = proj.get('worktree', '')
        if worktree and os.path.isdir(worktree):
          try:
            r = subprocess.run(
              ['opencode', 'session', 'list', '--format', 'json'],
              capture_output=True, text=True, timeout=10,
              cwd=worktree
            )
            proj_sessions = json.loads(r.stdout)
            for ps in proj_sessions:
              if ps.get('id') not in known_ids:
                all_sessions.append(ps)
                known_ids.add(ps['id'])
          except: pass
except Exception:
  pass

# Match agents to sessions and assign names
agent_to_session = {}
for a in agent_list:
  if a['type'] == 'engine':
    continue  # Brandon keeps his name
  name = a.get('name', '').lower()
  cmd = a.get('command', '').lower()
  title_lower = ''
  # Find matching session by keyword
  for s in all_sessions:
    t = s.get('title', '').lower()
    if 'git' in name or 'git' in cmd:
      if any(kw in t for kw in ['git', 'clone', 'repo', 'update']):
        title_lower = t
        agent_to_session[a['pid']] = s
        break
    elif 'agent' in name or 'browser' in cmd or 'server' in cmd or 'npm' in cmd:
      if any(kw in t for kw in ['homepage', 'marketing', 'page', 'site', 'web']):
        title_lower = t
        agent_to_session[a['pid']] = s
        break
  # Assign name
  if a['pid'] in agent_to_session:
    a['session_title'] = agent_to_session[a['pid']].get('title', '')
    a['name'] = generate_codename(a['pid'])
  elif a['type'] != 'engine' and a['name'] not in ('Brandon',):
    a['name'] = generate_codename(a['pid'])

# Also match existing virtual agents to sessions (by session_title)
for a in agent_list:
  if a.get('virtual') and a.get('session_title'):
    for s in all_sessions:
      if s.get('title') == a['session_title']:
        agent_to_session[a['pid']] = s
        break

# Build active sessions list: matched to agent OR within 10 min
now_ms = int(datetime.now().timestamp() * 1000)
thirty_min_ms = 30 * 60 * 1000
matched_sids = {s.get('id') for s in agent_to_session.values()}
for s in all_sessions:
  sid = s.get('id', '')
  updated = s.get('updated', 0)
  is_active = sid in matched_sids or (now_ms - updated) < thirty_min_ms
  if not is_active:
    continue
  sessions.append({
    'id': sid,
    'title': s.get('title', ''),
    'updated': updated,
    'active': True,
    'directory': s.get('directory', ''),
    'agent': s.get('agent', ''),
  })

# Create virtual agents for active sessions without a matching process
# Also track which session IDs have virtual agents so they persist
virtual_session_titles = set()
brandon_pid = next((a['pid'] for a in agent_list if a['type'] == 'engine'), None)
for s in sessions:
  title = s.get('title', '')
  sid = s.get('id', '')
  # Check if any existing agent matches this session
  has_agent = any(a.get('session_title') == title for a in agent_list)
  if not has_agent and brandon_pid:
    # Use a stable hash (Python's hash() is randomized per process)
    stable_hash = int.from_bytes(sid.encode('utf-8'), 'little')
    virtual_pid = -(stable_hash % 900000 + 100000)  # always negative, wider range
    # Don't duplicate if already added in previous cycle
    if not any(a['pid'] == virtual_pid for a in agent_list):
      agent_list.append({
        'pid': virtual_pid,
        'ppid': brandon_pid,
        'name': generate_codename(virtual_pid),
        'type': 'agent',
        'cpu': 0,
        'mem_mb': 0,
        'elapsed': 'active',
        'session_updated': s.get('updated', 0),
        'session_state': s.get('state', ''),
        'session_mode': s.get('last_mode', ''),
        'command': '',
        'session_title': title,
        'virtual': True
      })
    virtual_session_titles.add(title)

# Keep virtual agents alive only if their session is within the time window
now_ms = int(datetime.now().timestamp() * 1000)
thirty_min_ms = 30 * 60 * 1000
for a in agent_list:
  if a.get('virtual') and a.get('session_title'):
    if a['session_title'] not in virtual_session_titles:
      # Find the session
      session_obj = next((s for s in all_sessions if s.get('title') == a['session_title']), None)
      if session_obj:
        age = now_ms - session_obj.get('updated', 0)
        if age < thirty_min_ms:
          virtual_session_titles.add(a['session_title'])
          found = any(s.get('title') == a['session_title'] for s in sessions)
          if not found:
            sessions.append({
              'id': session_obj.get('id', ''),
              'title': session_obj.get('title', ''),
              'updated': session_obj.get('updated', 0),
              'active': True
            })

# --- Session detail enrichment ---
# Load detail cache
detail_cache = {}
if os.path.exists(session_details_file):
  try:
    with open(session_details_file) as f:
      detail_cache = json.load(f)
  except: pass

# Check if export is already running
export_running = os.path.exists(export_lock_file)
if export_running:
  try:
    lock_age = time.time() - os.path.getmtime(export_lock_file)
    if lock_age > 30:
      os.remove(export_lock_file)
      export_running = False
  except: export_running = False

# Find session that needs refresh (most recent without cache or with stale cache)
needs_refresh = None
for s in sessions:
  sid = s.get('id', '')
  updated = s.get('updated', 0)
  cached = detail_cache.get(sid, {})
  if cached.get('updated') != updated:
    needs_refresh = s
    break

if needs_refresh and not export_running:
  sid = needs_refresh['id']
  export_tmp = os.path.join(data_dir, f'export_{sid}.tmp')
  # Use session's directory as cwd if available (for project-scoped sessions)
  session_dir = needs_refresh.get('directory', '')
  if not session_dir or not os.path.isdir(session_dir):
    session_dir = None
  # Mark lock
  with open(export_lock_file, 'w') as f:
    f.write(sid)
  try:
    with open(export_tmp, 'w') as f:
      export_result = subprocess.run(
        ['opencode', 'export', sid],
        stdout=f, stderr=subprocess.DEVNULL, timeout=30,
        cwd=session_dir
      )
    # Read back and find JSON start (skip "Exporting session..." header)
    with open(export_tmp) as f:
      raw = f.read()
    json_start = raw.find('{')
    if json_start < 0:
      raise ValueError('No JSON in export output')
    export_data = json.loads(raw[json_start:])
    info = export_data.get('info', {})
    msgs = export_data.get('messages', [])

    # Extract session slug
    slug = info.get('slug', '')

    # Extract last message info
    last_msg = msgs[-1] if msgs else {}
    last_info = last_msg.get('info', {})
    finish = last_info.get('finish')
    last_role = last_info.get('role', '')
    last_mode = last_info.get('mode', '')
    last_parts = last_msg.get('parts', [])

    # Derive state from finish field
    if finish is None or finish == '':
      state = 'thinking'
    elif finish == 'tool-calls':
      state = 'running-tools'
    elif finish == 'stop':
      state = 'complete'
    elif finish == 'error':
      state = 'error'
    else:
      state = 'unknown'

    # Extract last text snippet (assistant)
    last_text = ''
    tool_name = ''
    for p in reversed(last_parts):
      if p.get('type') == 'text' and p.get('text', '').strip():
        last_text = p.get('text', '').strip()[:200]
        break
      elif p.get('type') == 'tool' and not tool_name:
        tool_name = p.get('name') or p.get('tool') or ''

    # Extract last user prompt
    last_user_prompt = ''
    for m in reversed(msgs):
      if m.get('info', {}).get('role') == 'user':
        for p in m.get('parts', []):
          if p.get('type') == 'text' and p.get('text', '').strip():
            last_user_prompt = p.get('text', '').strip()[:200]
            break
        if last_user_prompt:
          break

    # Tokens and cost (use session-level totals)
    tokens = info.get('tokens', {}) or {}
    total_tokens = tokens.get('input', 0) + tokens.get('output', 0)
    cost = info.get('cost', 0)

    # Session summary
    summary = info.get('summary', {})
    files_changed = summary.get('files', 0)

    # Agent type and model
    agent_type = info.get('agent', '')
    model_id = info.get('model', {}).get('id', '')

    detail_cache[sid] = {
      'updated': needs_refresh['updated'],
      'slug': slug,
      'state': state,
      'last_user_prompt': last_user_prompt,
      'last_text': last_text,
      'tool_name': tool_name,
      'last_role': last_role,
      'last_mode': last_mode,
      'tokens': total_tokens,
      'cost': cost,
      'files_changed': files_changed,
      'agent_type': agent_type,
      'model_id': model_id
    }
  except Exception as e:
    pass
  finally:
    if os.path.exists(export_lock_file):
      try: os.remove(export_lock_file)
      except: pass
    if os.path.exists(export_tmp):
      try: os.remove(export_tmp)
      except: pass

# Apply cache to sessions
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

# Enrich all_sessions with cache for admin panel (include every session, all states)
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
    'active': sid in known_sids,
  }
  all_sessions_enriched.append(enriched)

# Remove completed sessions idle >5 min
now_ms = int(datetime.now().timestamp() * 1000)
five_min_ms = 5 * 60 * 1000
removed_titles = {s['title'] for s in sessions if s.get('state') == 'complete' and (now_ms - s.get('updated', 0)) > five_min_ms}
sessions[:] = [s for s in sessions if s['title'] not in removed_titles]
for r_title in removed_titles:
  log_activity_py(f"Session completed: {r_title}")

# Clean up agents pointing to removed sessions
for a in agent_list:
  if a.get('session_title') and a['session_title'] in removed_titles:
    a['session_title'] = ''

# Remove virtual agents for removed sessions
active_titles = {s['title'] for s in sessions}
agent_list[:] = [a for a in agent_list if not (a.get('virtual') and a.get('session_title') and a['session_title'] not in active_titles)]

# Remove stale real agents: no session, cpu=0, running >2h (idled out)
for a in agent_list[:]:
  if not a.get('virtual') and a['type'] != 'engine' and not a.get('session_title'):
    if a.get('cpu', 0) == 0:
      elapsed_str = a.get('elapsed', '')
      if '02:' in elapsed_str or '03:' in elapsed_str:  # running >2h with no session
        log_activity_py(f"Idle worker removed: {a.get('name', '?')} (PID {a['pid']})")
        agent_list.remove(a)

# Update virtual agents with enriched session data
for a in agent_list:
  if a.get('virtual') and a.get('session_title'):
    for s in sessions:
      if s.get('title') == a['session_title']:
        a['session_state'] = s.get('state', '')
        a['session_mode'] = s.get('last_mode', '')
        break

# Save cache
with open(session_details_file, 'w') as f:
  json.dump(detail_cache, f, indent=2, default=str)

# Export lock file cleanup
if os.path.exists(export_lock_file):
  try:
    lock_age = time.time() - os.path.getmtime(export_lock_file)
    if lock_age > 30:
      os.remove(export_lock_file)
  except: pass

activities = []
if os.path.exists(activity_file):
  with open(activity_file) as f:
    alines = f.readlines()
    activities = [l.strip() for l in alines[-30:]]

current_pids = {a['pid'] for a in agent_list}

# Keep recently finished agents for 2 cycles so they don't blink out
recent_finished = []
for pa in prev_agents:
  if pa['pid'] not in current_pids:
    pa['status'] = 'finished'
    recent_finished.append(pa)

# Add recent finished to agent list (up to 5)
for rf in recent_finished[-5:]:
  if not any(a['pid'] == rf['pid'] for a in agent_list):
    agent_list.append(rf)

# Build process hierarchy: root (Brandon/NodeService) → children → grandchildren
root_pid = next((a['pid'] for a in agent_list if a['type'] == 'engine'), None)

# Build child map: ppid → [pid]
child_map = {}
pid_to_agent = {}
for a in agent_list:
  pid_to_agent[a['pid']] = a
for a in agent_list:
  ppid = a.get('ppid', 0)
  if ppid in pid_to_agent and a['pid'] != ppid and ppid != 0:
    child_map.setdefault(ppid, []).append(a['pid'])

# Attach children PIDs to each agent
for a in agent_list:
  a['children'] = child_map.get(a['pid'], [])

# Top-level nodes: root and any agents not under root
if root_pid:
  tree_root = root_pid
else:
  tree_root = agent_list[0]['pid'] if agent_list else 0

# Attach matching agents to each session.
# First pass: keyword-matched agents
for s in sessions:
  title = s.get('title', '')
  matching = [a for a in agent_list if a.get('session_title') == title and not a.get('virtual') and a['type'] != 'engine']
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

# Log transient Brandon children to activity log and skip them
brandon_pid2 = next((a['pid'] for a in agent_list if a['type'] == 'engine'), None)
transient_list = [a for a in agent_list
  if not a.get('virtual')
  and a['type'] != 'engine'
  and a.get('ppid') == brandon_pid2
  and not any(a['pid'] == ma['pid'] for s in sessions for ma in s.get('agents', []))
]
for a in transient_list:
  proc_name = os.path.basename((a.get('command') or '').split()[0] if a.get('command') else '?')
  if proc_name in skip_utils:
    log_activity_py(f"Transient: {proc_name} (PID {a['pid']}) · {a.get('elapsed', '?')}")
  else:
    log_activity_py(f"Unclaimed worker: {a.get('name', proc_name)} (PID {a['pid']}) · {a.get('elapsed', '?')}")

# Second pass: assign unclaimed Brandon children to sessions still needing agents.
unclaimed = [a for a in agent_list
  if not a.get('virtual')
  and a['type'] != 'engine'
  and a.get('status') != 'finished'
  and a['ppid'] == brandon_pid2
  and not any(a['pid'] == ma['pid'] for s in sessions for ma in s.get('agents', []))
  and os.path.basename((a.get('command') or '').split()[0] if a.get('command') else '') not in skip_utils
]
sessions_sorted = sorted(sessions, key=lambda s: s.get('updated', 0), reverse=True)
for a in unclaimed:
  # Assign to the first session without a real agent
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
thinking_sessions = [s for s in sessions if s.get('state') in ('thinking', 'running-tools', '')]
completed = [s for s in sessions if s.get('state') == 'complete' and s.get('agents')]
for s in completed:
  freed = s.get('agents', [])
  s['agents'] = []
  for w in freed:
    target = next((ts for ts in thinking_sessions if len(ts.get('agents', [])) < 3), None)
    if target:
      target.setdefault('agents', []).append(w)
    else:
      s['agents'].append(w)

# Standalone agents: non-virtual, non-engine, not matched to any session
session_titles = {s.get('title') for s in sessions}
claimed_pids = {ma['pid'] for s in sessions for ma in s.get('agents', [])}
pid_to_name = {a['pid']: a.get('name') for a in agent_list}
standalone = []
for a in agent_list:
  if a.get('virtual') or a['type'] == 'engine' or a['pid'] in claimed_pids or a.get('status') == 'finished':
    continue
  # Skip transient commands
  proc_name = os.path.basename((a.get('command') or '').split()[0] if a.get('command') else '')
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

total_cost = sum(cached.get('cost', 0) for cached in detail_cache.values())

# Count real workers: session agents + standalone (non-virtual, non-engine)
worker_pids = set()
for s in sessions:
  for a in s.get('agents', []):
    worker_pids.add(a['pid'])
worker_count = len(worker_pids) + len(standalone)
cpu_core_count = multiprocessing.cpu_count()

# Compute system-wide CPU usage from ps aux
system_cpu = 0
system_proc_count = 0
try:
  r = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
  for line in r.stdout.strip().split('\n')[1:]:
    parts = line.split(None, 10)
    if len(parts) >= 3:
      try:
        system_cpu += float(parts[2])
        system_proc_count += 1
      except: pass
except: pass
cpu_load_pct = round(system_cpu / cpu_core_count, 1) if cpu_core_count else 0
active_task_count = len(worker_pids) + len(standalone)

# Fetch available models for admin panel
available_models = []
try:
  r = subprocess.run(['opencode', 'models'], capture_output=True, text=True, timeout=15)
  if r.returncode == 0:
    for line in r.stdout.strip().split('\n'):
      line = line.strip()
      if line and '/' in line:
        available_models.append({'id': line, 'provider': 'opencode'})
  # Also fetch Ollama models
  try:
    rr = subprocess.run(['curl', '-s', '--max-time', '5', 'https://ollama.brandon.my/api/tags'], capture_output=True, text=True, timeout=10)
    if rr.returncode == 0:
      ollama_data = json.loads(rr.stdout)
      for m in ollama_data.get('models', []):
        available_models.append({'id': m['name'], 'provider': 'ollama'})
  except:
    pass
except:
  pass

payload = {
  'timestamp': timestamp,
  'summary': {
    'total_cost': total_cost,
    'worker_count': worker_count,
    'cpu_core_count': cpu_core_count,
    'cpu_load_pct': cpu_load_pct,
    'active_task_count': active_task_count,
    'agent_count': len([a for a in agent_list if a.get('status') != 'finished']),
    'total_procs': len(proc_list),
    'main_pid': main_pid,
    'uptime': main_elapsed or 'N/A',
    'total_cpu': total_cpu,
    'total_cpu_str': f'{total_cpu}%',
    'total_mem_mb': total_mem_mb,
    'total_mem_gb': round(total_mem_mb / 1024, 1),
    'disk_free': disk_free,
    'disk_total': disk_total,
    'mem_total_gb': mem_total_gb,
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

with open(status_file, 'w') as f:
  json.dump(payload, f, indent=2, default=str)

# Save current agent PIDs for next cycle
with open(prev_pids_file, 'w') as f:
  to_save = []
  for a in agent_list:
    if a.get('status') == 'finished': continue
    cmd = a.get('command', '')
    if 'opencode session list' in cmd or 'opencode export' in cmd or cmd == '(opencode)': continue
    to_save.append({'pid': a['pid'], 'ppid': a.get('ppid', 0), 'name': a['name'], 'type': a['type'], 'command': cmd})
  json.dump(to_save, f)
