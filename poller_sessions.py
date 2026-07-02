#!/usr/bin/env python3
"""Session data collection: list, virtual agents, export enrichment, case assignments."""
import subprocess
import json
import os
import time
import sqlite3
from datetime import datetime, timezone

from poller_config import (
    data_dir, status_file, session_details_file, export_lock_file,
    assignments_file, staff_file_path, log_activity_py, timestamp,
    generate_codename
)

def _opencode_bin():
    for candidate in (
        os.path.expanduser('~/.opencode/bin/opencode'),
        '/home/webbypage/.opencode/bin/opencode',
        '/root/.opencode/bin/opencode',
    ):
        if candidate and os.path.exists(candidate):
            return candidate
    r = subprocess.run(['bash', '-lc', 'command -v opencode'], capture_output=True, text=True, timeout=5)
    path = (r.stdout or '').strip()
    return path or 'opencode'

def fetch_all_workspaces() -> list:
    """Fetch all registered OpenCode workspaces from the local SQLite DB."""
    db_path = os.path.expanduser('~/.local/share/opencode/opencode.db')
    workspaces = []
    seen = set()
    if not os.path.exists(db_path):
        return workspaces
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT id, worktree, vcs, name, icon_url, icon_color, time_updated, time_created FROM project ORDER BY COALESCE(time_updated, time_created) DESC"
        ).fetchall()
        for row in rows:
            pid, worktree, vcs, name, icon_url, icon_color, time_updated, time_created = row
            directory = worktree or ''
            if not directory or directory in seen:
                continue
            seen.add(directory)
            workspaces.append({
                'id': pid,
                'directory': directory,
                'worktree': directory,
                'name': name or os.path.basename(directory.rstrip('/')) or directory,
                'vcs': vcs or '',
                'icon_url': icon_url or '',
                'icon_color': icon_color or '',
                'time_updated': time_updated or time_created or 0,
            })
        conn.close()
    except Exception:
        pass

    # Merge in any directories seen from live sessions so the UI never loses them.
    try:
        for s in fetch_all_sessions():
            directory = s.get('directory', '')
            if directory and directory not in seen:
                seen.add(directory)
                workspaces.append({
                    'id': s.get('project_id', '') or s.get('id', ''),
                    'directory': directory,
                    'worktree': directory,
                    'name': os.path.basename(directory.rstrip('/')) or directory,
                    'vcs': '',
                    'icon_url': '',
                    'icon_color': '',
                    'time_updated': s.get('updated', 0),
                })
    except Exception:
        pass
    return workspaces

def fetch_all_sessions() -> list:
    """Fetch session list from opencode CLI, including project-scoped sessions."""
    sessions = []
    try:
        r = subprocess.run(
            [_opencode_bin(), 'session', 'list', '--format', 'json'],
            capture_output=True, text=True, timeout=10
        )
        all_sessions = json.loads(r.stdout)
    except Exception:
        all_sessions = []

    # Check known project directories for project-scoped sessions
    try:
        known_ids = {s['id'] for s in all_sessions}
        global_data_path = os.path.expanduser(
            '~/Library/Application Support/ai.opencode.desktop/opencode.global.dat'
        )
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
                                [_opencode_bin(), 'session', 'list', '--format', 'json'],
                                capture_output=True, text=True, timeout=10,
                                cwd=worktree
                            )
                            proj_sessions = json.loads(r.stdout)
                            for ps in proj_sessions:
                                if ps.get('id') not in known_ids:
                                    all_sessions.append(ps)
                                    known_ids.add(ps['id'])
                        except Exception:
                            pass
    except Exception:
        pass

    return all_sessions

def match_agents_to_sessions(
    agent_list: list, all_sessions: list
) -> tuple:
    """Match agents to sessions by keyword heuristics. Returns (agent_list, agent_to_session)."""
    agent_to_session = {}
    for a in agent_list:
        if a['type'] == 'engine':
            continue
        name = a.get('name', '').lower()
        cmd = a.get('command', '').lower()
        for s in all_sessions:
            t = s.get('title', '').lower()
            if 'git' in name or 'git' in cmd:
                if any(kw in t for kw in ['git', 'clone', 'repo', 'update']):
                    agent_to_session[a['pid']] = s
                    break
            elif 'agent' in name or 'browser' in cmd or 'server' in cmd or 'npm' in cmd:
                if any(kw in t for kw in ['homepage', 'marketing', 'page', 'site', 'web']):
                    agent_to_session[a['pid']] = s
                    break
        if a['pid'] in agent_to_session:
            a['session_title'] = agent_to_session[a['pid']].get('title', '')
            a['name'] = generate_codename(a['pid'])
        elif a['type'] != 'engine' and a['name'] not in ('Brandon',):
            a['name'] = generate_codename(a['pid'])

    # Match virtual agents to sessions by title
    for a in agent_list:
        if a.get('virtual') and a.get('session_title'):
            for s in all_sessions:
                if s.get('title') == a['session_title']:
                    agent_to_session[a['pid']] = s
                    break

    return agent_list, agent_to_session

def build_active_sessions(all_sessions: list, agent_to_session: dict) -> list:
    """Build active session list: matched to agent or updated within 30 min."""
    now_ms = int(datetime.now().timestamp() * 1000)
    thirty_min_ms = 30 * 60 * 1000
    matched_sids = {s.get('id') for s in agent_to_session.values()}
    sessions = []
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
    return sessions

def manage_virtual_agents(
    agent_list: list, sessions: list, all_sessions: list
) -> tuple:
    """Create/remove virtual agents for active sessions without a real process match."""
    virtual_session_titles = set()
    brandon_pid = next((a['pid'] for a in agent_list if a['type'] == 'engine'), None)

    for s in sessions:
        title = s.get('title', '')
        sid = s.get('id', '')
        has_agent = any(a.get('session_title') == title for a in agent_list)
        if not has_agent and brandon_pid:
            stable_hash = int.from_bytes(sid.encode('utf-8'), 'little')
            virtual_pid = -(stable_hash % 900000 + 100000)
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

    # Keep virtual agents alive only if their session is within 30 min
    now_ms = int(datetime.now().timestamp() * 1000)
    thirty_min_ms = 30 * 60 * 1000
    for a in agent_list:
        if a.get('virtual') and a.get('session_title'):
            if a['session_title'] not in virtual_session_titles:
                session_obj = next(
                    (s for s in all_sessions if s.get('title') == a['session_title']),
                    None
                )
                if session_obj:
                    age = now_ms - session_obj.get('updated', 0)
                    if age < thirty_min_ms:
                        virtual_session_titles.add(a['session_title'])
                        found = any(
                            s.get('title') == a['session_title'] for s in sessions
                        )
                        if not found:
                            sessions.append({
                                'id': session_obj.get('id', ''),
                                'title': session_obj.get('title', ''),
                                'updated': session_obj.get('updated', 0),
                                'active': True
                            })

    return agent_list, sessions

def enrich_session_details(sessions: list, detail_cache: dict) -> tuple:
    """Fetch export data for sessions that need refresh. Returns updated detail_cache."""
    export_running = os.path.exists(export_lock_file)
    if export_running:
        try:
            lock_age = time.time() - os.path.getmtime(export_lock_file)
            if lock_age > 15:
                os.remove(export_lock_file)
                export_running = False
        except Exception:
            export_running = False

    needs_refresh = []
    for s in sessions:
        sid = s.get('id', '')
        updated = s.get('updated', 0)
        cached = detail_cache.get(sid, {})
        if cached.get('updated') != updated:
            needs_refresh.append(s)
            if len(needs_refresh) >= 2:
                break

    if needs_refresh and not export_running:
        # Prioritize sessions with unanswered questions so they appear in UI faster
        needs_refresh.sort(key=lambda s: 0 if any(not q.get('answered') for q in detail_cache.get(s.get('id', ''), {}).get('pending_questions', [])) else 1)
        session_to_fetch = needs_refresh[0]
        sid = session_to_fetch['id']
        export_tmp = os.path.join(data_dir, f'export_{sid}.tmp')
        session_dir = session_to_fetch.get('directory', '')
        if not session_dir or not os.path.isdir(session_dir):
            session_dir = None
        with open(export_lock_file, 'w') as f:
            f.write(sid)
        try:
            with open(export_tmp, 'w') as f:
                subprocess.run(
                    [_opencode_bin(), 'export', sid],
                    stdout=f, stderr=subprocess.DEVNULL, timeout=30,
                    cwd=session_dir
                )
            with open(export_tmp) as f:
                raw = f.read()
            json_start = raw.find('{')
            if json_start < 0:
                raise ValueError('No JSON in export output')
            export_data = json.loads(raw[json_start:])
            if not isinstance(export_data, dict):
                raise ValueError('Export data is not an object')
            info = export_data.get('info', {})
            msgs = export_data.get('messages', [])
            if not isinstance(info, dict):
                info = {}
            if not isinstance(msgs, list):
                msgs = []
            # Guard against non-dict messages
            msgs = [m for m in msgs if isinstance(m, dict)]

            slug = info.get('slug', '')
            last_msg = msgs[-1] if msgs else {}
            last_info = last_msg.get('info', {})
            if not isinstance(last_info, dict):
                last_info = {}
            finish = last_info.get('finish')
            last_role = last_info.get('role', '')
            last_mode = last_info.get('mode', '')
            last_parts = last_msg.get('parts', [])

            if finish is None or finish == '':
                state = 'thinking'
            elif finish == 'tool-calls':
                state = 'running-tools'
            elif finish == 'stop' or finish == 'length':
                state = 'complete'
            elif finish == 'error':
                state = 'error'
            else:
                state = 'unknown'

            last_text = ''
            tool_name = ''
            if isinstance(last_parts, list):
                for p in reversed(last_parts):
                    if not isinstance(p, dict):
                        continue
                    if p.get('type') == 'text' and p.get('text', '').strip():
                        last_text = p.get('text', '').strip()
                        break
                    elif p.get('type') == 'tool' and not tool_name:
                        tool_name = p.get('name') or p.get('tool') or ''

            pending_questions = []
            if isinstance(msgs, list):
                for m in reversed(msgs):
                    if not isinstance(m, dict):
                        continue
                    parts = m.get('parts', [])
                    if not isinstance(parts, list):
                        continue
                    for p in reversed(parts):
                        if not isinstance(p, dict):
                            continue
                        if p.get('type') == 'tool' and (p.get('name') or p.get('tool')) == 'question':
                            state_val = p.get('state', {})
                            if not isinstance(state_val, dict):
                                state_val = {}
                            inp = state_val.get('input', {})
                            if not isinstance(inp, dict):
                                inp = {}
                            questions = inp.get('questions', [])
                            if not isinstance(questions, list):
                                questions = []
                            metadata = state_val.get('metadata', {})
                            if not isinstance(metadata, dict):
                                metadata = {}
                            answers_data = metadata.get('answers', [])
                            if not isinstance(answers_data, list):
                                answers_data = []
                            already_answered = bool(answers_data)
                            for qi, q in enumerate(questions):
                                if not isinstance(q, dict):
                                    continue
                                q_entry = {
                                    'header': q.get('header', ''),
                                    'question': q.get('question', ''),
                                    'options': [],
                                    'answered': already_answered,
                                }
                                options = q.get('options', [])
                                if isinstance(options, list):
                                    q_entry['options'] = [{'label': o.get('label', ''), 'description': o.get('description', '')} for o in options if isinstance(o, dict)]
                                if already_answered:
                                    matched = [a for a in answers_data if isinstance(a, dict) and a.get('questionIndex') == qi]
                                    if matched:
                                        q_entry['selected_indices'] = matched[0].get('optionIndices', [])
                                pending_questions.append(q_entry)
                            break
                    if pending_questions:
                        break

            last_user_prompt = ''
            if isinstance(msgs, list):
                for m in reversed(msgs):
                    if not isinstance(m, dict):
                        continue
                    m_info = m.get('info', {})
                    if isinstance(m_info, dict) and m_info.get('role') == 'user':
                        parts = m.get('parts', [])
                        if isinstance(parts, list):
                            for p in parts:
                                if not isinstance(p, dict):
                                    continue
                                if p.get('type') == 'text' and p.get('text', '').strip():
                                    last_user_prompt = p.get('text', '').strip()
                                    break
                        if last_user_prompt:
                            break

            tokens = info.get('tokens', {}) or {}
            if not isinstance(tokens, dict):
                tokens = {}
            total_tokens = tokens.get('input', 0) + tokens.get('output', 0)
            cost = info.get('cost', 0)
            summary = info.get('summary', {})
            if not isinstance(summary, dict):
                summary = {}
            files_changed = summary.get('files', 0)
            agent_type = info.get('agent', '')
            model_info = info.get('model', {})
            if not isinstance(model_info, dict):
                model_info = {}
            model_id = model_info.get('id', '')

            detail_cache[sid] = {
                'updated': session_to_fetch['updated'],
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
                'model_id': model_id,
                'pending_questions': pending_questions
            }
        except Exception as e:
            log_activity_py(f"Export failed for {sid}: {str(e)[:100]}")
        finally:
            if os.path.exists(export_lock_file):
                try:
                    os.remove(export_lock_file)
                except Exception:
                    pass
            if os.path.exists(export_tmp):
                try:
                    os.remove(export_tmp)
                except Exception:
                    pass

    return detail_cache

def apply_case_assignments(
    sessions: list, all_sessions: list, all_sessions_enriched: list
) -> tuple:
    """Apply case assignments and super staff enrichment to sessions."""
    case_assignments = {}
    if os.path.exists(assignments_file):
        try:
            with open(assignments_file) as f:
                case_assignments = json.load(f)
        except Exception:
            pass
    super_staff_map = {}
    if os.path.exists(staff_file_path):
        try:
            with open(staff_file_path) as f:
                for s in json.load(f):
                    super_staff_map[s['name']] = s
        except Exception:
            pass

    for s in sessions:
        sid = s.get('id', '')
        assigned_name = case_assignments.get(sid, '')
        if assigned_name:
            s['assigned_staff'] = assigned_name
            staff_info = super_staff_map.get(assigned_name, {})
            s['staff_gender'] = staff_info.get('gender', 'male')
            s['staff_mode'] = staff_info.get('mode', '')
            s['staff_model'] = staff_info.get('model', '')

    for s in all_sessions_enriched:
        sid = s.get('id', '')
        assigned_name = case_assignments.get(sid, '')
        if assigned_name:
            s['assigned_staff'] = assigned_name
            staff_info = super_staff_map.get(assigned_name, {})
            s['staff_gender'] = staff_info.get('gender', 'male')
            s['staff_mode'] = staff_info.get('mode', '')
            s['staff_model'] = staff_info.get('model', '')

    return sessions, all_sessions_enriched
