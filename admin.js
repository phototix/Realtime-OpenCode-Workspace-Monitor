(function (global) {
'use strict';

// ── API FETCH HELPER ──
async function apiFetch(url, options) {
  try {
    const resp = await fetch(url, { ...options, signal: AbortSignal.timeout(10000) });
    return await resp.json();
  } catch (e) {
    showToast('Network error: ' + e.message, 'error');
    return null;
  }
}

// ── MODAL HELPER ──
function getModal(id) {
  return document.getElementById(id);
}

// ── SHA-256 ──
async function sha256(str) {
  const buf = new TextEncoder().encode(str);
  const hash = await crypto.subtle.digest('SHA-256', buf);
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2,'0')).join('');
}

// ── USER MANAGEMENT ──
const USERS_KEY = 'dashboard_users';
const AUTH_KEY = 'dashboard_auth';
const ADMIN_PORT = '';

function getUsers() {
  try { return JSON.parse(localStorage.getItem(USERS_KEY)) || []; } catch { return []; }
}
function saveUsers(users) {
  localStorage.setItem(USERS_KEY, JSON.stringify(users));
}
function getAuth() {
  try { return JSON.parse(sessionStorage.getItem(AUTH_KEY)); } catch { return null; }
}

global._serverBossName = '';
function getBossName() {
  return global._serverBossName || 'Brandon';
}
function setAuth(auth) {
  sessionStorage.setItem(AUTH_KEY, JSON.stringify(auth));
}
function clearAuth() {
  sessionStorage.removeItem(AUTH_KEY);
}

async function initDefaultUsers() {
  let users = getUsers();
  if (users.length === 0) {
    const hash = await sha256('#Quidents64#');
    users = [{ email: 'brandon@kkbuddy.com', passwordHash: hash, role: 'admin', created: Date.now() }];
    saveUsers(users);
  }
}
initDefaultUsers();

// ── AUTH UI ──
function openLoginModal() {
  const auth = getAuth();
  if (auth) {
    openAdminModal();
    return;
  }
  document.getElementById('loginModal').style.display = 'flex';
  document.getElementById('loginError').style.display = 'none';
  document.getElementById('loginEmail').value = '';
  document.getElementById('loginPassword').value = '';
  setTimeout(() => document.getElementById('loginEmail').focus(), 100);
}
function closeLoginModal() {
  document.getElementById('loginModal').style.display = 'none';
}
function closeAdminModal() {
  document.getElementById('adminModal').style.display = 'none';
  if (_cronRefreshTimer) { clearInterval(_cronRefreshTimer); _cronRefreshTimer = null; }
}

async function handleLogin() {
  const email = document.getElementById('loginEmail').value.trim().toLowerCase();
  const pw = document.getElementById('loginPassword').value;
  const err = document.getElementById('loginError');
  const btn = document.getElementById('loginBtn');

  if (!email || !pw) { err.textContent = 'Please enter email and password'; err.style.display = 'block'; return; }

  btn.disabled = true; btn.textContent = 'Signing in...';
  const hash = await sha256(pw);
  const users = getUsers();
  const user = users.find(u => u.email === email && u.passwordHash === hash);

  if (user) {
    setAuth({ email: user.email, role: user.role });
    closeLoginModal();
    openAdminModal();
    // Auto-fetch API key on login so remote clients can use it without manual setup
    loadApiKey();
  } else {
    err.textContent = 'Invalid email or password';
    err.style.display = 'block';
  }
  btn.disabled = false; btn.textContent = 'Sign In';
}

function handleLogout() {
  clearAuth();
  closeAdminModal();
  updateLoginIndicator();
  showToast('Logged out', 'success');
}

function updateLoginIndicator() {
  const auth = getAuth();
  const ind = document.getElementById('loginIndicator');
  if (auth) {
    ind.style.display = 'inline';
  } else {
    ind.style.display = 'none';
  }
}
updateLoginIndicator();

// Enter key to submit login
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && document.getElementById('loginModal').style.display === 'flex') {
    handleLogin();
  }
});

// ── ADMIN MODAL ──
function openAdminModal() {
  const auth = getAuth();
  if (!auth) { openLoginModal(); return; }
  const modal = document.getElementById('adminModal');
  document.getElementById('adminUserName').textContent = auth.email;
  const roleBadge = document.getElementById('adminUserRole');
  roleBadge.textContent = auth.role;
  roleBadge.className = 'role-badge ' + auth.role;

  // Show/hide admin-only tabs
  document.querySelectorAll('.admin-tab.admin-only').forEach(t => {
    t.style.display = auth.role === 'admin' ? '' : 'none';
  });

  // If user (not admin) is on a restricted tab, switch to sessions
  if (auth.role !== 'admin') {
    const activeTab = document.querySelector('.tab-content.active');
    if (activeTab && activeTab.id === 'tab-users') {
      switchTab('sessions');
    }
  }

  // Load super staff cache
  fetch('/api/super-staff').then(r => r.json()).then(d => { if (d.ok) global.superStaffCache = d.staff || []; }).catch(() => {});

  modal.style.display = 'flex';
  renderCasesTab();
  renderSystemTab();
  renderUsersTab();
  renderLogsTab();
  renderInAppAlertsTab();
}

// ── TABS ──
let currentTab = 'sessions';

function switchTab(tabId) {
  currentTab = tabId;
  document.querySelectorAll('.admin-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tabId));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.toggle('active', t.id === 'tab-' + tabId));

  if (_cronRefreshTimer) { clearInterval(_cronRefreshTimer); _cronRefreshTimer = null; }

  // Lazy render
  if (tabId === 'sessions') renderCasesTab();
  if (tabId === 'system') renderSystemTab();
  if (tabId === 'users') renderUsersTab();
  if (tabId === 'names') renderNamesTab();
  if (tabId === 'logs') renderLogsTab();
  if (tabId === 'inapp-alerts') renderInAppAlertsTab();
  if (tabId === 'notifications') renderNotificationsTab();
  if (tabId === 'providers') renderProvidersTab();
  if (tabId === 'super-staff') renderSuperStaffTab();
  if (tabId === 'cron') { renderCronTab(); _cronRefreshTimer = setInterval(updateCronCountdowns, 1000); }
  if (tabId === 'workflows') renderWorkflowsTab();
}

// ── SESSIONS TAB ──
async function renderCasesTab() {
  const el = document.getElementById('sessionsTabContent');
  const query = (document.getElementById('sessionSearch').value || '').toLowerCase();
  const workspaceFilter = document.getElementById('workspaceFilter').value;
  try {
    const resp = await fetch('data/status.json?_=' + Date.now());
    const data = await resp.json();
    const sessions = data.all_sessions || data.sessions || [];
    // Sync case assignments from fresh data
    sessions.forEach(s => { if (s.assigned_staff) _caseAssignments[s.id] = s.assigned_staff; });
    document.getElementById('sessionsTabCount').textContent = '(' + sessions.length + ' total)';

    // Build workspace filter options
    const workspaces = [...new Set((sessions.map(s => s.directory || '(default)')))].
      filter(Boolean).sort();
    const filterEl = document.getElementById('workspaceFilter');
    const curVal = filterEl.value;
    filterEl.innerHTML = '<option value="">All Workspaces</option>' +
      workspaces.map(w => '<option value="' + w.replace(/"/g,'&quot;') + '">' + w.split('/').pop() || w + '</option>').join('');
    if (curVal) filterEl.value = curVal;

    if (sessions.length === 0) {
      el.innerHTML = '<div class="empty-state"><div class="icon">📋</div><div class="text">No Cases working on at the moment</div></div>';
      return;
    }

    // Group by workspace
    const grouped = {};
    sessions.filter(s => {
      if (query && !(s.title||'').toLowerCase().includes(query) && !(s.slug||'').toLowerCase().includes(query)) return false;
      if (workspaceFilter) {
        const dir = s.directory || '(default)';
        if (dir !== workspaceFilter) return false;
      }
      return true;
    }).forEach(s => {
      const key = s.directory || '(default)';
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(s);
    });

    if (Object.keys(grouped).length === 0) {
      el.innerHTML = '<div class="empty-state"><div class="icon">📋</div><div class="text">No Cases working on at the moment</div></div>';
      return;
    }

    let html = '';
    for (const [dir, group] of Object.entries(grouped)) {
      const shortDir = dir === '(default)' ? 'Default' : dir.split('/').pop() || dir;
      html += '<div style="margin-bottom:16px">';
      html += '<div style="font-size:11px;color:var(--yellow);margin-bottom:6px;display:flex;align-items:center;gap:6px">' +
        '<span>📁</span><span>' + shortDir + '</span>' +
        '<span style="font-size:10px;color:var(--text-dim)">(' + group.length + ' cases)</span>' +
        '<span style="font-size:9px;color:var(--text-dim);margin-left:4px;opacity:0.6">' + dir + '</span>' +
      '</div>';

      html += '<table class="admin-table"><colgroup><col style="width:22%"><col style="width:8%"><col style="width:8%"><col style="width:15%"><col style="width:8%"><col style="width:8%"><col style="width:8%"><col style="width:23%"></colgroup><thead><tr><th>Title</th><th>State</th><th>Mode</th><th>Model</th><th>Cost</th><th>Tokens</th><th>Updated</th><th>Actions</th></tr></thead><tbody>';
      group.forEach(s => {
        const agoStr = global.humanAgo(s.updated);
        const stateColor = s.state === 'thinking' ? 'var(--yellow)' : s.state === 'running-tools' ? 'var(--blue)' : s.state === 'complete' ? 'var(--green)' : 'var(--text-dim)';
        const isActive = s.state === 'thinking' || s.state === 'running-tools';
        const jsonDir = (s.directory || '').replace(/'/g,"\\'");
        const escId = s.id.replace(/[^a-zA-Z0-9]/g,'_');
        var sTitle = escapeHtml(s.title || '?');
        var sState = escapeHtml(s.state || 'active');
        var sModel = escapeHtml(s.model_id || '—');
        var sAssigned = escapeHtml(s.assigned_staff || '');
        html += '<tr>' +
          '<td style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + sTitle.replace(/"/g,'&quot;') + '">' + sTitle + '</td>' +
          '<td><span style="color:' + stateColor + '">' + sState + '</span></td>' +
          '<td>' + (s.last_mode ? '<span style="font-size:10px;padding:1px 6px;border-radius:3px;font-weight:500;background:' + (s.last_mode === 'plan' ? '#bc8cff33' : '#58a6ff33') + ';color:' + (s.last_mode === 'plan' ? '#bc8cff' : '#58a6ff') + '">' + s.last_mode + '</span>' : '—') + '</td>' +
          '<td style="font-size:10px;color:var(--text-dim)">' + sModel + '</td>' +
          '<td>$' + (s.cost||0).toFixed(4) + '</td>' +
          '<td>' + ((s.tokens||0).toLocaleString()) + '</td>' +
          '<td style="font-size:10px;color:var(--text-dim)">' + agoStr + '</td>' +
          '<td style="white-space:nowrap">' +
            '<select onchange="assignStaff(\'' + s.id + '\',this.value)" style="font-size:9px;padding:1px 4px;background:var(--surface2);border:1px solid var(--border);border-radius:4px;color:var(--text);outline:none;vertical-align:middle;max-width:80px" title="Assign super staff">' +
              '<option value="">' + (sAssigned || '\u{1F464}') + '</option>' +
              global.superStaffCache.map(function(st) { return '<option value="' + st.name.replace(/"/g,'&quot;') + '"' + (s.assigned_staff === st.name ? ' selected' : '') + '>' + escapeHtml(st.name) + '</option>'; }).join('') +
              (s.assigned_staff ? '<option value="__unassign__" style="color:var(--red)">\u2715 Unassign</option>' : '') +
            '</select> ' +
            todoBadge(s) +
            questionBadge(s) +
            '<button class="view-btn" onclick="viewSession(\'' + s.id + '\')">View</button> ' +
            '<button class="rename-btn" onclick="renameSession(\'' + s.id + '\',\'' + (s.title||'?').replace(/'/g,"\\'") + '\')">Rename</button> ' +
            (isActive ? '<button class="stop-btn" onclick="stopSession(\'' + s.id + '\',\'' + jsonDir + '\', event)">Stop</button>' : '') +
             (s.state !== 'thinking' && s.state !== 'running-tools' ? ' <button class="send-btn" data-sid="' + s.id + '" onclick="continueSession(\'' + s.id + '\')">Continue</button>' : '') +
          '</td>' +
        '</tr>';
      });
      html += '</tbody></table></div>';
    }
    el.innerHTML = html;
  } catch (e) {
    el.innerHTML = '<div style="font-size:12px;color:var(--red)">Error loading cases: ' + e.message + '</div>';
  }
}

let _caseAssignments = {};

async function assignStaff(sessionId, staffName) {
  if (!staffName) return;
  const isUnassign = staffName === '__unassign__';
  const name = isUnassign ? '' : staffName;
  try {
    const data = await sendQueued('super-staff-assign', { sessionId: sessionId, staffName: name });
    if (data.ok) {
      if (isUnassign) delete _caseAssignments[sessionId];
      else _caseAssignments[sessionId] = staffName;
      showToast(isUnassign ? 'Assignment removed' : 'Assigned: ' + staffName, 'success');
      renderCasesTab();
    } else {
      showToast('Error: ' + data.message, 'error');
    }
  } catch (e) {
    showToast('Error: ' + e.message, 'error');
  }
}

async function stopSession(id, dir, event) {
  const btn = (event || window.event).target; btn.disabled = true; btn.textContent = 'Stopping...';
  try {
    try {
      const data = await sendQueued('stop-session', { id, directory: dir || '' });
      if (data.ok) {
        showToast('Case stopped (deleted)', 'success');
        renderCasesTab();
      } else {
        showToast('Error: ' + data.message, 'error');
        btn.disabled = false; btn.textContent = 'Stop';
      }
    } catch (e) {
      showToast('Error: ' + e.message, 'error');
      btn.disabled = false; btn.textContent = 'Stop';
    }
  } catch (e) {
    showToast('Failed to connect to admin API', 'error');
    btn.disabled = false; btn.textContent = 'Stop';
  }
}

function viewSession(id) {
  const modal = document.getElementById('sessionViewModal');
  const body = document.getElementById('sessionViewBody');
  fetch('data/status.json?_=' + Date.now()).then(r => r.json()).then(data => {
    const s = (data.all_sessions || data.sessions || []).find(x => x.id === id);
    if (!s) {
      body.innerHTML = '<div style="font-size:12px;color:var(--red)">Case not found</div>';
      modal.style.display = 'flex';
      return;
    }
    const stateColor = s.state === 'thinking' ? 'var(--yellow)' : s.state === 'running-tools' ? 'var(--blue)' : s.state === 'complete' ? 'var(--green)' : 'var(--text-dim)';
    body.innerHTML = `
      <div class="admin-card">
        <div class="row"><span class="label">State</span><span class="value" style="color:${stateColor}">${escapeHtml(s.state || 'active')}</span></div>
        <div class="row"><span class="label">Slug</span><span class="value">${escapeHtml(s.slug || '—')}</span></div>
        <div class="row"><span class="label">Session ID</span><span class="value" style="display:flex;align-items:center;gap:6px"><span style="font-family:monospace;font-size:11px">${escapeHtml(id)}</span><button onclick="navigator.clipboard.writeText('${id.replace(/'/g,"\\'")}')" style="font-size:10px;padding:1px 6px;border-radius:3px;border:1px solid var(--border);background:var(--surface2);color:var(--text-dim);cursor:pointer">Copy</button></span></div>
        <div class="row"><span class="label">Model</span><span class="value">${escapeHtml(s.model_id || '—')}</span></div>
        <div class="row"><span class="label">Cost</span><span class="value">$${(s.cost||0).toFixed(4)}</span></div>
        <div class="row"><span class="label">Tokens</span><span class="value">${(s.tokens||0).toLocaleString()}</span></div>
        <div class="row"><span class="label">Updated</span><span class="value">${global.humanAgo(s.updated)}</span></div>
        <div class="row"><span class="label">Directory</span><span class="value" style="font-size:10px">${escapeHtml(s.directory || '—')}</span></div>
        ${s.last_mode ? `<div class="row"><span class="label">Last Mode</span><span class="value">${escapeHtml(s.last_mode)}</span></div>` : ''}
      </div>
    `;
    modal.style.display = 'flex';
  }).catch(() => {
    body.innerHTML = '<div style="font-size:12px;color:var(--red)">Failed to load case data</div>';
    modal.style.display = 'flex';
  });
}

function continueSession(id) {
  let modal = document.getElementById('sessionContinueModal');
  let body = document.getElementById('continueModalBody');
  let titleEl = document.getElementById('continueModalTitle');
  if (!modal || !body) {
    modal = document.querySelector('#sessionContinueModal');
    body = document.querySelector('#continueModalBody');
    titleEl = document.querySelector('#continueModalTitle');
  }
  if (!modal || !body) { showToast('Continue modal not available', 'error'); return; }
  fetch('data/status.json?_=' + Date.now()).then(r => r.json()).then(data => {
    if (data.summary && data.summary.engine_restarted_at) {
      showToast('Cannot continue \u2014 OpenCode engine restarted. All prior cases are invalid.', 'error');
      return;
    }
    const s = (data.all_sessions || data.sessions || []).find(x => x.id === id);
    if (!s) {
      body.innerHTML = '<div style="font-size:12px;color:var(--red)">Case not found</div>';
      modal.style.display = 'flex';
      return;
    }
    if (s.state === 'thinking' || s.state === 'running-tools') {
      showToast('This case is already active — wait for it to complete before continuing.', 'error');
      return;
    }
    titleEl.textContent = 'Continue Case \u2014 ' + (s.title || '?');
    const escId = s.id.replace(/[^a-zA-Z0-9]/g,'_');
    const dirEsc = (s.directory || '').replace(/'/g,"\\'");
    body.innerHTML = `
      ${s.last_user_prompt ? `<div class="admin-card"><h4>Last User Prompt</h4><div style="font-size:11px;color:var(--text);line-height:1.5;white-space:pre-wrap;word-break:break-word">${escapeHtml(s.last_user_prompt)}</div></div>` : ''}
      <div class="admin-card">
        ${s.last_text ? `<h4 style="display:flex;align-items:center;gap:8px">Last Response${s.last_mode ? `<span style="font-size:9px;padding:1px 6px;border-radius:3px;font-weight:500;background:${s.last_mode === 'plan' ? '#bc8cff33' : '#58a6ff33'};color:${s.last_mode === 'plan' ? '#bc8cff' : '#58a6ff'}">${s.last_mode}</span>` : ''}</h4><div style="font-size:11px;color:var(--text-dim);line-height:1.5;white-space:pre-wrap;word-break:break-word;margin-bottom:16px">${escapeHtml(s.last_text)}</div><hr style="border:none;border-top:1px solid var(--border);margin:12px 0">` : ''}
        <h4>New Instruction</h4>
        <textarea id="instruct-${escId}" placeholder="Enter your instruction to continue this case..." style="width:100%;padding:10px 12px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:13px;outline:none;resize:vertical;min-height:80px;font-family:inherit" onkeydown="if(event.key==='Enter'&&event.shiftKey)event.preventDefault()"></textarea>
        <div style="display:flex;gap:8px;align-items:center;margin-top:12px;flex-wrap:wrap">
          <select id="model-${escId}" style="flex:1;min-width:180px;padding:10px 12px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:12px;outline:none">
            <option value="">Loading models...</option>
          </select>
          <select id="mode-${escId}" style="width:150px;padding:10px 12px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:12px;outline:none" onchange="onModeChange(this,'${escId}')">
            ${(() => {
              const agents = getCustomAgents();
              const lastMode = s.last_mode || '';
              let opts = '<option value="build"' + (lastMode !== 'plan' ? ' selected' : '') + '>Build</option>';
              opts += '<option value="plan"' + (lastMode === 'plan' ? ' selected' : '') + '>Plan</option>';
              if (agents.length > 0) {
                opts += '<option disabled style="font-size:9px;color:var(--text-dim)">── Agents ──</option>';
                agents.forEach(a => {
                  opts += '<option value="' + escapeHtml(a.name) + '"' + (a.name === lastMode ? ' selected' : '') + '>' + escapeHtml(a.name) + '</option>';
                });
              }
              return opts;
            })()}
          </select>
          <button class="btn btn-primary btn-sm" onclick="sessionInstructView('${s.id}','${dirEsc}')">Send</button>
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-top:8px">
          <input type="checkbox" id="branch-${escId}" style="accent-color:var(--blue)">
          <label for="branch-${escId}" style="font-size:11px;color:var(--text-dim);cursor:pointer">Start as a new case instead</label>
        </div>
        <div style="font-size:10px;color:var(--text-dim);margin-top:6px">Press Send to continue this case with the instruction above</div>
      </div>
    `;
    modal.style.display = 'flex';
    loadModels('model-' + escId, s.model_id || '');
  }).catch(() => {
    body.innerHTML = '<div style="font-size:12px;color:var(--red)">Failed to load case data</div>';
    modal.style.display = 'flex';
  });
}

function openNewSessionModal() {
  const modal = document.getElementById('newSessionModal');
  document.getElementById('newSessionTitle').value = '';
  document.getElementById('newSessionMessage').value = '';
  document.getElementById('newSessionError').style.display = 'none';
  renderModeOptions('newSessionMode', 'build');
  modal.style.display = 'flex';
  // Populate models
  const modelSel = document.getElementById('newSessionModel');
  modelSel.innerHTML = '<option value="">Loading models...</option>';
  loadModels('newSessionModel', '');
  // Populate workflows
  const wfSel = document.getElementById('newSessionWorkflow');
  wfSel.innerHTML = '<option value="">— None —</option>';
  fetch('/api/workflows').then(r => r.json()).then(d => {
    (d.workflows || []).forEach(wf => {
      const opt = document.createElement('option');
      opt.value = wf.id;
      opt.textContent = wf.name + ' (' + (wf.nodes || []).length + ' stages)';
      wfSel.appendChild(opt);
    });
  }).catch(() => {});
  // Populate workspaces
  const wsSel = document.getElementById('newSessionWorkspace');
  wsSel.innerHTML = '<option value="">Default (home)</option>';
  fetch('data/status.json?_=' + Date.now()).then(r => r.json()).then(data => {
    const dirs = [...new Set((data.all_sessions || []).map(s => s.directory).filter(Boolean))].sort();
    dirs.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d;
      opt.textContent = d.split('/').pop() || d;
      opt.title = d;
      wsSel.appendChild(opt);
    });
  }).catch(() => {});
}

function onNewCaseWorkflowChange() {
  const wfId = document.getElementById('newSessionWorkflow').value;
  if (!wfId) return;
  fetch('/api/workflows').then(r => r.json()).then(d => {
    const wf = (d.workflows || []).find(w => w.id === wfId);
    if (!wf || !wf.nodes || !wf.nodes.length) return;
    // Find first node (no incoming edges)
    const edges = wf.edges || [];
    const hasIncoming = new Set(edges.map(e => e.to));
    const first = wf.nodes.find(n => !hasIncoming.has(n.id)) || wf.nodes[0];
    if (first.staff_ic) {
      // Find the matching mode option (staff name)
      const modeSel = document.getElementById('newSessionMode');
      for (const opt of modeSel.options) {
        if (opt.value === first.staff_ic) {
          opt.selected = true;
          // Trigger onchange to auto-select model
          if (typeof onNewCaseModeChange === 'function') onNewCaseModeChange();
          break;
        }
      }
    }
    if (first.instructions) {
      document.getElementById('newSessionMessage').value = first.instructions;
    }
  }).catch(() => {});
}

async function startNewSession() {
  const title = document.getElementById('newSessionTitle').value.trim();
  let message = document.getElementById('newSessionMessage').value.trim();
  const mode = document.getElementById('newSessionMode').value;
  const model = document.getElementById('newSessionModel').value;
  const directory = document.getElementById('newSessionWorkspace').value;
  const workflowId = document.getElementById('newSessionWorkflow').value;
  const err = document.getElementById('newSessionError');
  err.style.display = 'none';

  if (!title) { err.textContent = 'Please enter a title'; err.style.display = 'block'; return; }
  if (!message) { err.textContent = 'Please enter instructions'; err.style.display = 'block'; return; }

  // Prepend Roles & Scope if a Super Staff agent is selected
  const staff = getStaffForMode(mode);
  const finalMode = staff ? staff.mode : mode;
  const finalMessage = staff ? (staff.description + '\n\n' + message) : message;
  const finalModel = staff && staff.model ? staff.model : model;

  // Close modal immediately
  closeNewSessionModal();
  showToast('Starting new case...', 'success');
  var _nsStart = Date.now();

  try {
    try {
      const data = await sendQueued('new-session', { title, message: finalMessage, mode: finalMode, model: finalModel, directory, fresh: true, workflow_id: workflowId }, function(d) {
        if (d.status === 'processing' || d.status === 'queued') {
          var elapsed = Math.round((Date.now() - _nsStart) / 1000) + 's';
          var tMsg = document.getElementById('toastMessage');
          if (tMsg) tMsg.textContent = 'Starting new case... (' + elapsed + ')';
        }
      });
      if (!data.ok) {
        showToast('Error: ' + data.message, 'error');
      } else if (data.workflow === 'attached') {
        showToast('Workflow attached and first stage started', 'success');
      } else if (data.workflow_error) {
        showToast('Case started but workflow attach failed: ' + data.workflow_error, 'error');
      }
    } catch (e) {
      showToast('Error: ' + e.message, 'error');
    }
  } catch (e) {
    showToast('Error: ' + e.message, 'error');
  }
}

async function loadModels(selectId, selected) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  sel.innerHTML = '<option value="">Loading models...</option>';
  try {
    const resp = await fetch('data/status.json?_=' + Date.now());
    const data = await resp.json();
    const models = data.available_models || [];
    if (models.length === 0) { sel.innerHTML = '<option value="">No models available</option>'; return; }
    const grouped = {};
    models.forEach(m => {
      if (!grouped[m.provider]) grouped[m.provider] = [];
      grouped[m.provider].push(m.id);
    });
    let html = '<option value="">Default model</option>';
    for (const [provider, ids] of Object.entries(grouped)) {
      html += '<optgroup label="' + provider + '">';
      ids.forEach(id => {
        const selAttr = id === selected ? ' selected' : '';
        html += '<option value="' + id.replace(/"/g,'&quot;') + '"' + selAttr + '>' + id + '</option>';
      });
      html += '</optgroup>';
    }
    sel.innerHTML = html;
  } catch (e) {
    sel.innerHTML = '<option value="">Failed to load models</option>';
  }
}

async function sessionInstructView(id, dir) {
  const escId = id.replace(/[^a-zA-Z0-9]/g,'_');
  const branch = document.getElementById('branch-' + escId) ? document.getElementById('branch-' + escId).checked : false;

  // Pre-check: fetch latest status.json to verify session still exists
  try {
    const checkResp = await fetch('data/status.json?_=' + Date.now());
    const checkData = await checkResp.json();
    if (checkData.summary && checkData.summary.engine_restarted_at) {
      showToast('Cannot continue \u2014 OpenCode engine restarted. Please refresh and create a new case.', 'error');
      renderCasesTab();
      return;
    }
    if (!branch) {
      const stillExists = (checkData.all_sessions || []).some(function(s) { return s.id === id; });
      if (!stillExists) {
        showToast('This case no longer exists \u2014 the engine was restarted. Create a new case.', 'error');
        renderCasesTab();
        return;
      }
      const updated = (checkData.all_sessions || []).find(function(s) { return s.id === id; });
      if (updated && (updated.state === 'thinking' || updated.state === 'running-tools')) {
        showToast('This case is already active — wait for it to complete, then try again.', 'error');
        renderCasesTab();
        return;
      }
    }
  } catch (e) {
    // Silent fail on pre-check, let the main request handle it
  }

  const input = document.getElementById('instruct-' + escId);
  const modelSel = document.getElementById('model-' + escId);
  const modeSel = document.getElementById('mode-' + escId);
  const mode = modeSel ? modeSel.value : '';
  const staff = getStaffForMode(mode);
  const message = input ? input.value.trim() : '';
  if (!message) { showToast('Please enter an instruction', 'error'); return; }
  const finalMode = staff ? staff.mode : mode;
  const finalMessage = staff ? (staff.description + '\n\n' + message) : message;

  // Close modal immediately
  closeContinueModal();

  // Update session card in main dashboard to "Sending..."
  const card = document.querySelector('.session-card[data-sid="' + CSS.escape(id) + '"]');
  if (card) {
    const badge = card.querySelector('.sc-state-badge');
    if (badge) { badge.textContent = 'Sending...'; badge.style.color = 'var(--yellow)'; badge.style.background = '#d2992233'; }
    const dot = card.querySelector('.sc-status-dot');
    if (dot) { dot.style.background = 'var(--yellow)'; }
  }

  // Revert UI helper function
  function _revertUI() {
    if (card) {
      const badge = card.querySelector('.sc-state-badge');
      if (badge) { badge.textContent = 'Complete'; badge.style.color = 'var(--green)'; badge.style.background = '#3fb95033'; }
      const dot = card.querySelector('.sc-status-dot');
      if (dot) { dot.style.background = 'var(--green)'; }
    }
    if (adminBtn) { adminBtn.textContent = 'Continue'; adminBtn.disabled = false; }
  }

  // Update admin table Continue button to "Sending..."
  const adminBtn = document.querySelector('.send-btn[data-sid="' + CSS.escape(id) + '"]');
  if (adminBtn) { adminBtn.textContent = 'Sending...'; adminBtn.disabled = true; }
  const _instructStart = Date.now();

  try {
    const data = await sendQueued('session-instruct', {
      id, message: finalMessage,
      model: staff && staff.model ? staff.model : (modelSel ? modelSel.value : ''),
      mode: finalMode,
      directory: dir || '',
      fork: branch
    }, function(d) {
      if (d.status === 'processing' || d.status === 'queued') {
        var elapsed = Math.round((Date.now() - _instructStart) / 1000) + 's';
        if (card) {
          var badge = card.querySelector('.sc-state-badge');
          if (badge) badge.textContent = 'Sending... (' + elapsed + ')';
        }
        if (adminBtn) adminBtn.textContent = 'Sending... (' + elapsed + ')';
      }
    });
    if (data.ok) {
      showToast(data.message, 'success');
      if (input) input.value = '';
    } else {
      _revertUI();
      if (data.code === 'engine_restarted') {
        showToast('Engine restarted \u2014 refresh the page to see active cases.', 'error');
      } else {
        showToast('Error: ' + data.message, 'error');
      }
    }
  } catch (e) {
    _revertUI();
    showToast('Error: ' + e.message, 'error');
  }
  renderCasesTab();
}

// ── QUESTION RESPONSE ──
function questionBadge(s) {
  const pq = s.pending_questions || [];
  if (pq.length === 0) return '';
  const unanswered = pq.filter(function(q){ return !q.answered; });
  if (unanswered.length > 0) {
    return '<button class="question-btn" onclick="showQuestions(\'' + s.id + '\')">\u2753 ' + unanswered.length + '</button> ';
  }
  return '<span style="font-size:10px;color:var(--green);cursor:pointer;margin-left:4px" onclick="showQuestions(\'' + s.id + '\')" title="Questions answered">\u2713</span> ';
}

function todoBadge(s) {
  const todos = s.todos || [];
  const completed = todos.filter(function(t){ return t.status === 'completed'; }).length;
  const total = todos.length;
  if (total === 0) return '';
  return '<span style="font-size:10px;color:var(--yellow);margin-left:4px;cursor:pointer" onclick="showTasks(\'' + s.id + '\')" title="View tasks">\uD83D\uDCCB Tasks (' + completed + '/' + total + ')</span> ';
}

function showTasks(id) {
  fetch('data/status.json?_=' + Date.now()).then(function(r){ return r.json(); }).then(function(data) {
    var s = (data.all_sessions || data.sessions || []).find(function(x){ return x.id === id; });
    var body = document.getElementById('tasksModalBody');
    var modal = document.getElementById('tasksModal');
    if (!s || !s.todos || s.todos.length === 0) {
      body.innerHTML = '<div style="font-size:12px;color:var(--text-dim)">No tasks</div>';
      modal.style.display = 'flex';
      return;
    }
    var done = s.todos.filter(function(t){ return t.status === 'completed'; }).length;
    var html = '<div style="font-size:12px;color:var(--text-dim);margin-bottom:16px">' + escapeHtml(s.title || '?') + '</div>';
    html += '<div style="font-size:11px;color:var(--text-dim);margin-bottom:12px">Tasks (' + done + '/' + s.todos.length + ')</div>';
    s.todos.forEach(function(t) {
      var isDone = t.status === 'completed';
      var pri = t.priority === 'high' ? ' 🔥' : '';
      html += '<div style="display:flex;align-items:center;gap:8px;padding:4px 0;font-size:11px;border-bottom:1px solid var(--border)">' +
        '<span style="color:' + (isDone ? 'var(--green)' : 'var(--text-dim)') + '">' + (isDone ? '✓' : '○') + '</span>' +
        '<span style="' + (isDone ? 'text-decoration:line-through;color:var(--text-dim)' : '') + '">' + escapeHtml(t.content) + '</span>' +
        '<span style="font-size:9px;color:var(--text-dim);margin-left:auto">' + pri + '</span>' +
        '</div>';
    });
    html += '<div style="margin-top:16px"><button class="btn btn-sm" style="background:var(--surface2);color:var(--text-dim)" onclick="closeTasksModal()">Close</button></div>';
    body.innerHTML = html;
    modal.style.display = 'flex';
  }).catch(function() {
    document.getElementById('tasksModalBody').innerHTML = '<div style="font-size:12px;color:var(--red)">Failed to load tasks</div>';
    document.getElementById('tasksModal').style.display = 'flex';
  });
}

function closeTasksModal() {
  document.getElementById('tasksModal').style.display = 'none';
}

function showQuestions(id) {
  fetch('data/status.json?_=' + Date.now()).then(function(r){ return r.json(); }).then(function(data) {
    var s = (data.all_sessions || data.sessions || []).find(function(x){ return x.id === id; });
    var body = document.getElementById('questionModalBody');
    var modal = document.getElementById('questionModal');
    if (!s || !s.pending_questions || s.pending_questions.length === 0) {
      body.innerHTML = '<div style="font-size:12px;color:var(--text-dim)">No questions</div>';
      modal.style.display = 'flex';
      return;
    }
    var hasUnanswered = s.pending_questions.some(function(q){ return !q.answered; });
    var html = '<div style="font-size:12px;color:var(--text-dim);margin-bottom:16px">' + (s.title || '?') + '</div>';
    var selected = {};
    s.pending_questions.forEach(function(q, qi) {
      if (q.answered) {
        var selText = '';
        if (q.selected_indices && q.options) {
          selText = q.selected_indices.map(function(idx){ return q.options[idx] ? escapeHtml(q.options[idx].label) : ''; }).join(', ');
        }
        html += '<div style="margin-bottom:10px;opacity:0.7;padding:10px;background:var(--surface2);border-radius:8px;border-left:3px solid var(--green)">';
        if (s.pending_questions.length > 1) html += '<div style="font-size:10px;color:var(--text-dim);margin-bottom:4px">Question ' + (qi+1) + ' of ' + s.pending_questions.length + '</div>';
        if (q.header) html += '<div style="font-size:11px;color:var(--green);font-weight:600;margin-bottom:2px"><span style="color:var(--green)">\u2713</span> ' + escapeHtml(q.header) + '</div>';
        html += '<div style="font-size:12px;color:var(--text-dim);margin-bottom:4px">' + escapeHtml(q.question) + '</div>';
        if (selText) html += '<div style="font-size:11px;color:var(--green);padding:3px 8px;background:#3fb95022;border-radius:4px;display:inline-block">Selected: ' + selText + '</div>';
        html += '</div>';
        return;
      }
      html += '<div class="admin-card" style="margin-bottom:12px">';
      if (s.pending_questions.length > 1) html += '<div style="font-size:10px;color:var(--text-dim);margin-bottom:6px">Question ' + (qi+1) + ' of ' + s.pending_questions.length + '</div>';
      if (q.header) html += '<div style="font-size:11px;color:var(--yellow);font-weight:600;margin-bottom:4px">' + escapeHtml(q.header) + '</div>';
      html += '<div style="font-size:13px;color:var(--text);margin-bottom:12px">' + escapeHtml(q.question) + '</div>';
      q.options.forEach(function(o, oi) {
        var optId = 'qopt-' + id.replace(/[^a-zA-Z0-9]/g,'_') + '-' + qi + '-' + oi;
        html += '<div style="display:flex;align-items:flex-start;gap:10px;padding:8px 10px;margin-bottom:6px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;cursor:pointer" onclick="selectQuestionOption(\'' + id + '\',' + qi + ',' + oi + ')">' +
          '<input type="radio" name="q-' + qi + '" id="' + optId + '" style="margin-top:2px;accent-color:var(--blue)">' +
          '<div><div style="font-size:12px;font-weight:500;color:var(--text)">' + escapeHtml(o.label) + '</div>' +
          (o.description ? '<div style="font-size:10px;color:var(--text-dim);margin-top:2px">' + escapeHtml(o.description) + '</div>' : '') + '</div></div>';
      });
      html += '</div>';
    });
    if (hasUnanswered) {
      html += '<div style="display:flex;gap:8px;margin-top:8px">' +
        '<button class="btn btn-primary btn-sm" onclick="sendAnswers(\'' + id + '\')" id="sendAnswersBtn">Send Answers</button>' +
        '<button class="btn btn-sm" style="background:var(--surface2);color:var(--text-dim)" onclick="closeQuestionModal()">Cancel</button>' +
      '</div>';
    } else {
      html += '<div style="display:flex;gap:8px;margin-top:8px">' +
        '<button class="btn btn-sm" style="background:var(--surface2);color:var(--text-dim)" onclick="closeQuestionModal()">Close</button>' +
      '</div>';
    }
    body.innerHTML = html;
    modal.style.display = 'flex';
  });
}

function selectQuestionOption(id, qi, oi) {
  var prefix = 'qopt-' + id.replace(/[^a-zA-Z0-9]/g,'_') + '-' + qi + '-';
  var radio = document.getElementById(prefix + oi);
  if (radio) radio.checked = true;
}

function sendAnswers(id) {
  fetch('data/status.json?_=' + Date.now()).then(function(r){ return r.json(); }).then(function(data) {
    var s = (data.all_sessions || data.sessions || []).find(function(x){ return x.id === id; });
    if (!s || !s.pending_questions) return;
    // Check if still unanswered
    var hasUnanswered = s.pending_questions.some(function(q){ return !q.answered; });
    if (!hasUnanswered) { closeQuestionModal(); renderCasesTab(); showToast('Already answered', 'success'); return; }
    var answers = [];
    s.pending_questions.forEach(function(q, qi) {
      if (q.answered) return;
      var radios = document.querySelectorAll('input[name="q-' + qi + '"]:checked');
      radios.forEach(function(r) {
        var idx = parseInt(r.id.split('-').pop());
        if (q.options[idx]) answers.push(q.options[idx].label);
      });
    });
    if (answers.length === 0) { showToast('Please select an option for each question', 'error'); return; }

    var btn = document.getElementById('sendAnswersBtn');
    if (btn) { btn.disabled = true; btn.textContent = 'Sending...'; }
    var _answerStart = Date.now();
    sendQueued('session-answer', { id: id, answers: answers, directory: s.directory || '' }, function(d) {
      if ((d.status === 'processing' || d.status === 'queued') && btn) {
        var elapsed = Math.round((Date.now() - _answerStart) / 1000) + 's';
        btn.textContent = 'Sending... (' + elapsed + ')';
      }
    }).then(function(data) {
      if (data.ok) {
        showToast('Answers sent', 'success');
        closeQuestionModal();
        renderCasesTab();
      } else {
        showToast('Error: ' + data.message, 'error');
        if (btn) { btn.disabled = false; btn.textContent = 'Send Answers'; }
      }
    }).catch(function(e) {
      showToast('Error: ' + e.message, 'error');
      if (btn) { btn.disabled = false; btn.textContent = 'Send Answers'; }
    });
  });
}

function closeQuestionModal() {
  document.getElementById('questionModal').style.display = 'none';
}

// ── SYSTEM TAB ──
async function renderSystemTab() {
  try {
    const resp = await fetch('data/status.json?_=' + Date.now());
    const data = await resp.json();
    const s = data.summary || {};
    document.getElementById('sysUptime').textContent = global.formatUptime(s.uptime) || '—';
    document.getElementById('sysCpuCores').textContent = s.cpu_core_count || '—';
    document.getElementById('sysMemory').textContent = (s.total_mem_mb || 0) + ' MB / ' + (s.mem_total_gb || '?') + ' GB';
    document.getElementById('sysDisk').textContent = s.disk_free + ' free / ' + s.disk_total + ' total';
  } catch {}

  try {
    const resp = await fetch('/api/ping');
    const data = await resp.json();
    document.getElementById('sysDaemonStatus').innerHTML = data.daemon_alive
      ? '<span style="color:var(--green)">● Running</span>'
      : '<span style="color:var(--red)">● Stopped</span>';
  } catch {
    document.getElementById('sysDaemonStatus').innerHTML = '<span style="color:var(--yellow)">● Unknown</span>';
  }
}

async function restartDaemon() {
  const msg = document.getElementById('sysMsg');
  const err = document.getElementById('sysErr');
  msg.style.display = 'none'; err.style.display = 'none';
  try {
    const data = await sendQueued('restart-daemon', {});
    if (data.ok) {
      msg.textContent = 'Daemon restarted successfully'; msg.style.display = 'block';
      setTimeout(() => renderSystemTab(), 2000);
    } else {
      err.textContent = data.message; err.style.display = 'block';
    }
  } catch (e) {
    err.textContent = 'Failed to connect: ' + e.message; err.style.display = 'block';
  }
}

async function killDaemon() {
  const msg = document.getElementById('sysMsg');
  const err = document.getElementById('sysErr');
  msg.style.display = 'none'; err.style.display = 'none';
  if (!confirm('Kill the dashboard daemon? It will stop updating.')) return;
  try {
    const data = await sendQueued('kill-daemon', {});
    if (data.ok) {
      msg.textContent = 'Daemon killed'; msg.style.display = 'block';
      renderSystemTab();
    } else {
      err.textContent = data.message; err.style.display = 'block';
    }
  } catch (e) {
    err.textContent = 'Failed to connect: ' + e.message; err.style.display = 'block';
  }
}

// ── USERS TAB ──
function renderUsersTab() {
  const el = document.getElementById('usersTabContent');
  const auth = getAuth();
  if (!auth || auth.role !== 'admin') {
    el.innerHTML = '<div style="font-size:12px;color:var(--red)">Admin access required</div>';
    return;
  }

  const users = getUsers();
  let html = '<table class="admin-table"><thead><tr><th>Email</th><th>Role</th><th>Created</th><th></th></tr></thead><tbody>';
  users.forEach(u => {
    const created = u.created ? new Date(u.created).toLocaleDateString() : '—';
    html += '<tr>' +
      '<td>' + u.email + '</td>' +
      '<td><span style="color:' + (u.role === 'admin' ? 'var(--purple)' : 'var(--blue)') + '">' + u.role + '</span></td>' +
      '<td style="font-size:10px;color:var(--text-dim)">' + created + '</td>' +
      '<td>' +
        (users.length > 1 ? '<button class="stop-btn" onclick="deleteUser(\'' + u.email.replace(/'/g,"\\'") + '\')">Delete</button>' : '') +
      '</td>' +
    '</tr>';
  });
  html += '</tbody></table>';

  html += '<div class="admin-card" style="margin-top:16px"><h4>Add User</h4>';
  html += '<div class="inline-form">' +
    '<input type="email" id="newUserEmail" placeholder="Email">' +
    '<input type="password" id="newUserPw" placeholder="Password">' +
    '<select id="newUserRole" style="padding:8px 10px;background:var(--surface2);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:12px">' +
      '<option value="user">User</option><option value="admin">Admin</option>' +
    '</select>' +
    '<button class="btn btn-sm btn-primary" onclick="addUser()">Add</button>' +
  '</div>';
  html += '<div class="form-error" id="usersErr" style="margin-top:8px"></div>';
  html += '<div class="form-success" id="usersMsg" style="margin-top:8px"></div></div>';

  el.innerHTML = html;
}

async function addUser() {
  const email = document.getElementById('newUserEmail').value.trim().toLowerCase();
  const pw = document.getElementById('newUserPw').value;
  const role = document.getElementById('newUserRole').value;
  const err = document.getElementById('usersErr');
  const msg = document.getElementById('usersMsg');
  err.style.display = 'none'; msg.style.display = 'none';

  if (!email || !pw) { err.textContent = 'Email and password required'; err.style.display = 'block'; return; }
  if (pw.length < 6) { err.textContent = 'Password must be at least 6 characters'; err.style.display = 'block'; return; }

  const users = getUsers();
  if (users.find(u => u.email === email)) {
    err.textContent = 'User already exists'; err.style.display = 'block'; return;
  }

  const hash = await sha256(pw);
  users.push({ email, passwordHash: hash, role, created: Date.now() });
  saveUsers(users);
  msg.textContent = 'User added successfully'; msg.style.display = 'block';
  document.getElementById('newUserEmail').value = '';
  document.getElementById('newUserPw').value = '';
  renderUsersTab();
}

function deleteUser(email) {
  if (!confirm('Delete user ' + email + '?')) return;
  let users = getUsers();
  if (users.length <= 1) { showToast('Cannot delete last admin', 'error'); return; }
  users = users.filter(u => u.email !== email);
  saveUsers(users);
  showToast('User deleted', 'success');
  renderUsersTab();
}

// ── NAMES TAB ──
function renderNamesTab() {
  const el = document.getElementById('namesTabContent');
  const cfg = global.getNamesConfig();
  const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  document.getElementById('namesTabCount').textContent = '(' + letters.length + ' names)';

  let html = '<table class="admin-table"><thead><tr><th style="width:50px">Letter</th><th>Name</th><th style="width:60px">Gender</th><th style="width:80px"></th></tr></thead><tbody>';
  letters.split('').forEach(l => {
    const entry = cfg[l] || global.DEFAULT_NAMES[l] || { name: '?', gender: '?' };
    const genderColor = entry.gender === 'F' ? 'var(--pink)' : 'var(--blue)';
    html += '<tr>' +
      '<td style="font-weight:700;font-size:14px">' + l + '</td>' +
      '<td><input type="text" id="name-input-' + l + '" value="' + entry.name.replace(/"/g,'&quot;') + '" style="width:160px;padding:5px 8px;background:var(--surface2);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:12px;outline:none" onchange="saveName(\'' + l + '\')"></td>' +
      '<td><span style="color:' + genderColor + '">' + (entry.gender === 'F' ? '♀ Female' : '♂ Male') + '</span></td>' +
      '<td><button class="view-btn" onclick="resetName(\'' + l + '\')" style="font-size:9px">Reset</button></td>' +
    '</tr>';
  });
  html += '</tbody></table>';
  html += '<div style="margin-top:12px"><button class="btn btn-sm" style="background:var(--surface2);color:var(--text-dim)" onclick="resetAllNames()">Reset All to Default</button></div>';
  html += '<div class="form-success" id="namesMsg" style="margin-top:8px"></div>';
  el.innerHTML = html;
}

function saveName(letter) {
  const input = document.getElementById('name-input-' + letter);
  const name = input ? input.value.trim() : '';
  if (!name) return;
  const cfg = global.getNamesConfig();
  cfg[letter] = cfg[letter] || {};
  cfg[letter].name = name;
  if (!cfg[letter].gender) cfg[letter].gender = global.DEFAULT_NAMES[letter]?.gender || 'M';
  global.saveNamesConfig(cfg);
  const msg = document.getElementById('namesMsg');
  msg.textContent = 'Saved ' + letter + ' → ' + name;
  msg.style.display = 'block';
  setTimeout(() => msg.style.display = 'none', 2000);
}

function resetName(letter) {
  const cfg = global.getNamesConfig();
  const def = global.DEFAULT_NAMES[letter];
  if (def) {
    cfg[letter] = { name: def.name, gender: def.gender };
    global.saveNamesConfig(cfg);
    renderNamesTab();
  }
}

function resetAllNames() {
  if (!confirm('Reset all names to defaults?')) return;
  global.saveNamesConfig(global.DEFAULT_NAMES);
  renderNamesTab();
}

// ── SETTINGS TAB ──
function updateSettingPreview(id) {
  if (id === 'pollInterval') document.getElementById('pollIntervalVal').textContent = document.getElementById('pollIntervalRange').value;
  if (id === 'retention') document.getElementById('retentionVal').textContent = document.getElementById('retentionRange').value;
  if (id === 'cronInterval') document.getElementById('cronIntervalVal').textContent = document.getElementById('cronIntervalRange').value;
  if (id === 'logLines') document.getElementById('logLinesVal').textContent = document.getElementById('logLinesRange').value;
}

function restartPollTimer() {
  if (global._pollTimer) clearTimeout(global._pollTimer);
  global._polling = false;
  global.poll().then(() => global.schedulePoll());
}

function saveSettings() {
  const bossName = document.getElementById('bossNameInput').value.trim();
  if (bossName) {
    global._serverBossName = bossName;
    sendQueued('save-boss-name', { name: bossName }).catch(() => {});
  }
  const apiKey = document.getElementById('apiKeyInput').value.trim();
  if (apiKey) {
    localStorage.setItem('dashboard_api_key', apiKey);
  } else {
    localStorage.removeItem('dashboard_api_key');
  }
  const newPoll = parseInt(document.getElementById('pollIntervalRange').value);
  const retention = parseInt(document.getElementById('retentionRange').value);
  const cronInterval = parseInt(document.getElementById('cronIntervalRange').value);
  const logLines = parseInt(document.getElementById('logLinesRange').value);
  const settings = { pollInterval: newPoll, retention, cronInterval, logLines };
  localStorage.setItem('dashboard_settings', JSON.stringify(settings));
  if (newPoll !== global.POLL_INTERVAL) {
    global.POLL_INTERVAL = newPoll;
    restartPollTimer();
  }
  const msg = document.getElementById('settingsMsg');
  msg.textContent = 'Settings saved';
  msg.style.display = 'block';
  setTimeout(() => msg.style.display = 'none', 3000);
}

function loadSettings() {
  try {
    const s = JSON.parse(localStorage.getItem('dashboard_settings'));
    if (s) {
      if (s.pollInterval) { document.getElementById('pollIntervalRange').value = s.pollInterval; document.getElementById('pollIntervalVal').textContent = s.pollInterval; global.POLL_INTERVAL = s.pollInterval; }
      if (s.retention) { document.getElementById('retentionRange').value = s.retention; document.getElementById('retentionVal').textContent = s.retention; }
      if (s.cronInterval) { document.getElementById('cronIntervalRange').value = s.cronInterval; document.getElementById('cronIntervalVal').textContent = s.cronInterval; }
      if (s.logLines) { document.getElementById('logLinesRange').value = s.logLines; document.getElementById('logLinesVal').textContent = s.logLines; }
    }
    document.getElementById('bossNameInput').value = getBossName();
    const savedKey = localStorage.getItem('dashboard_api_key') || '';
    document.getElementById('apiKeyInput').value = savedKey;
  } catch {}
  updatePhotoPreview();
}

function toggleApiKeyVisibility() {
  const input = document.getElementById('apiKeyInput');
  const btn = document.getElementById('apiKeyToggleBtn');
  if (input.type === 'password') {
    input.type = 'text';
    btn.textContent = 'Hide';
  } else {
    input.type = 'password';
    btn.textContent = 'Show';
  }
}

// ── PROFILE PHOTO ──
global.profilePhoto = localStorage.getItem('dashboard_boss_photo') || '';
let cropper = null;

async function checkProfilePhoto() {
  if (global.profilePhoto) return; // already cached in localStorage
  try {
    const r = await fetch('/assets/profile_photo.png', { method: 'HEAD' });
    if (r.ok) {
      global.profilePhoto = '/assets/profile_photo.png?t=' + Date.now();
      localStorage.setItem('dashboard_boss_photo', global.profilePhoto);
    }
  } catch(e) {}
}

loadSettings();
checkProfilePhoto();

function openCropModal(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(e) {
    const img = document.getElementById('cropImage');
    img.src = e.target.result;
    document.getElementById('cropModal').style.display = 'flex';
    if (cropper) cropper.destroy();
    cropper = new Cropper(img, { aspectRatio: 1 / 1, viewMode: 1 });
  };
  reader.readAsDataURL(file);
  event.target.value = '';
}

function closeCropModal() {
  document.getElementById('cropModal').style.display = 'none';
  if (cropper) { cropper.destroy(); cropper = null; }
}

async function cropAndSave() {
  if (!cropper) return;
  const canvas = cropper.getCroppedCanvas({ width: 256, height: 256 });
  const dataUrl = canvas.toDataURL();
  try {
    const d = await sendQueued('upload-photo', { dataUrl });
    if (d.ok) {
      global.profilePhoto = d.url;
      localStorage.setItem('dashboard_boss_photo', d.url);
      closeCropModal();
      updatePhotoPreview();
    }
  } catch(e) {
    showToast('Failed to upload photo', 'error');
  }
}

async function removeProfilePhoto() {
  try {
    await sendQueued('remove-photo', {}).catch(() => {});
  } catch(e) {}
  global.profilePhoto = '';
  localStorage.removeItem('dashboard_boss_photo');
  updatePhotoPreview();
}

function updatePhotoPreview() {
  const preview = document.getElementById('settingsPhotoPreview');
  const removeBtn = document.getElementById('removePhotoBtn');
  if (global.profilePhoto) {
    preview.src = global.profilePhoto;
    preview.style.display = 'block';
    removeBtn.style.display = 'inline-block';
  } else {
    preview.style.display = 'none';
    removeBtn.style.display = 'none';
  }
}

// ── SECURITY TAB ──
// ── API KEY MANAGEMENT ──
let _apiKeyFull = ''; // holds the full key after Reveal or Regenerate

async function loadApiKey() {
  const input = document.getElementById('apiKeyDisplay');
  const msg = document.getElementById('apiKeyMsg');
  const err = document.getElementById('apiKeyErr');
  msg.style.display = 'none'; err.style.display = 'none';
  try {
    const r = await fetch('/api/api-key');
    const d = await r.json();
    if (d.ok) {
      // Server returns the full key (already authenticated via X-API-Key header)
      _apiKeyFull = d.key || '';
      input.value = _apiKeyFull || d.masked || '—';
      // Also update localStorage so the interceptor picks it up automatically
      if (_apiKeyFull) localStorage.setItem('dashboard_api_key', _apiKeyFull);
    } else {
      err.textContent = d.message || 'Failed to load key'; err.style.display = 'block';
    }
  } catch (e) {
    err.textContent = 'Request failed — check the API key in Settings first'; err.style.display = 'block';
  }
}

async function regenerateApiKey() {
  const input = document.getElementById('apiKeyDisplay');
  const msg = document.getElementById('apiKeyMsg');
  const err = document.getElementById('apiKeyErr');
  msg.style.display = 'none'; err.style.display = 'none';
  if (!confirm('Generate a new API key? The current key will stop working immediately.')) return;
  try {
    const d = await sendQueued('api-key/regenerate', {});
    if (d.ok && d.key) {
      _apiKeyFull = d.key;
      input.value = _apiKeyFull;
      localStorage.setItem('dashboard_api_key', _apiKeyFull);
      msg.textContent = '✓ New key generated — copy it to your Android app Settings now.';
      msg.style.display = 'block';
    } else {
      err.textContent = d.message || 'Regeneration failed'; err.style.display = 'block';
    }
  } catch (e) {
    err.textContent = 'Request failed'; err.style.display = 'block';
  }
}

async function copyApiKey() {
  const val = document.getElementById('apiKeyDisplay').value;
  if (!val || val === 'Loading…' || val === '—') return;
  try {
    await navigator.clipboard.writeText(val);
    const btn = document.getElementById('apiKeyCopyBtn');
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
  } catch {
    document.getElementById('apiKeyErr').textContent = 'Clipboard access denied — copy manually.';
    document.getElementById('apiKeyErr').style.display = 'block';
  }
}

async function changePassword() {
  const current = document.getElementById('secCurrentPw').value;
  const newPw = document.getElementById('secNewPw').value;
  const confirm = document.getElementById('secConfirmPw').value;
  const msg = document.getElementById('secMsg');
  const err = document.getElementById('secErr');
  msg.style.display = 'none'; err.style.display = 'none';

  const auth = getAuth();
  if (!auth) { err.textContent = 'Not logged in'; err.style.display = 'block'; return; }

  const users = getUsers();
  const user = users.find(u => u.email === auth.email);
  if (!user) { err.textContent = 'User not found'; err.style.display = 'block'; return; }

  const curHash = await sha256(current);
  if (curHash !== user.passwordHash) {
    err.textContent = 'Current password is incorrect'; err.style.display = 'block'; return;
  }
  if (newPw.length < 6) { err.textContent = 'New password must be at least 6 characters'; err.style.display = 'block'; return; }
  if (newPw !== confirm) { err.textContent = 'Passwords do not match'; err.style.display = 'block'; return; }

  user.passwordHash = await sha256(newPw);
  saveUsers(users);
  msg.textContent = 'Password updated successfully'; msg.style.display = 'block';
  document.getElementById('secCurrentPw').value = '';
  document.getElementById('secNewPw').value = '';
  document.getElementById('secConfirmPw').value = '';
}

// ── NOTIFICATIONS TAB ──
async function renderInAppAlertsTab() {
  const el = document.getElementById('ntfHistory');
  try {
    const resp = await fetch('/api/notifications/messages');
    const data = await resp.json();
    if (!data.ok || !data.notifications || data.notifications.length === 0) {
      el.innerHTML = '<div style="color:var(--text-dim);padding:8px 0">No notifications sent yet</div>';
      return;
    }
    let html = '';
    data.notifications.forEach(function(n) {
      const ts = n.created_at ? new Date(n.created_at * 1000).toLocaleString() : '';
      const color = n.type === 'error' ? 'var(--red)' : n.type === 'warning' ? 'var(--yellow)' : n.type === 'success' ? 'var(--green)' : 'var(--blue)';
      html += '<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border)">' +
        '<span style="color:' + color + ';font-weight:bold">\u25CF</span>' +
        '<span style="flex:1">' + escapeHtml(n.message) + '</span>' +
        '<span style="color:var(--text-dim);font-size:10px">' + ts + '</span>' +
        '<button class="stop-btn" style="font-size:10px;padding:2px 8px" onclick="dismissNotification(\'' + n.id + '\')">Dismiss</button>' +
        '</div>';
    });
    el.innerHTML = html;
  } catch (e) {
    el.innerHTML = '<div style="color:var(--red)">Error loading notifications</div>';
  }
}

function sendNotification() {
  const message = document.getElementById('ntfMessage').value.trim();
  if (!message) { showToast('Enter a message', 'error'); return; }
  const type = document.getElementById('ntfType').value;
  sendQueued('notifications-send', { message: message, type: type }).then(function() {
    showToast('Notification sent', 'success');
    document.getElementById('ntfMessage').value = '';
    renderInAppAlertsTab();
  }).catch(function(e) {
    showToast('Failed: ' + e.message, 'error');
  });
}

function dismissNotification(id) {
  sendQueued('notifications-dismiss', { id: id }).then(function() {
    renderInAppAlertsTab();
  }).catch(function(e) {
    showToast('Failed: ' + e.message, 'error');
  });
}

// ── EXTERNAL NOTIFICATIONS TAB ──
async function renderNotificationsTab() {
  const el = document.getElementById('notificationProvidersList');
  try {
    const resp = await fetch('/api/notification-providers');
    const data = await resp.json();
    if (!data.ok || !data.providers || data.providers.length === 0) {
      el.innerHTML = '<div style="color:var(--text-dim);padding:8px 0">No providers configured. Add one below.</div>';
      return;
    }
    let html = '';
    data.providers.forEach(function(p) {
      const typeIcon = p.type === 'slack' ? '💬' : p.type === 'discord' ? '🎮' : '🔗';
      const statusColor = p.enabled ? 'var(--green)' : 'var(--text-dim)';
      html +=       '<div class="admin-card" style="display:flex;align-items:center;gap:12px;margin-bottom:8px">' +
        '<span>' + typeIcon + '</span>' +
        '<div style="flex:1;min-width:0">' +
          '<div style="font-size:13px;font-weight:500">' + escapeHtml(p.name) + '</div>' +
          '<div style="font-size:10px;color:var(--text-dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + escapeHtml(p.type) + ' — ' + escapeHtml(p.webhook_url) + '</div>' +
        '</div>' +
        '<button class="btn btn-sm" style="background:' + (p.enabled ? 'var(--green)' : 'var(--surface2)') + ';color:' + (p.enabled ? '#fff' : 'var(--text-dim)') + ';padding:2px 10px;font-size:10px;cursor:pointer;border:none;border-radius:4px" onclick="toggleNotificationProvider(\'' + p.id + '\',' + (p.enabled ? 'false' : 'true') + ')">' + (p.enabled ? 'Enabled' : 'Disabled') + '</button>' +
        (p.failure_count > 0 ? '<span style="font-size:9px;color:var(--red);margin-left:4px" title="' + escapeHtml(p.last_error || '') + '">&#9888; ' + p.failure_count + '</span>' : '') +
        (p.last_success_at ? '<span style="font-size:9px;color:var(--text-dim);margin-left:4px">&#10003; ' + humanAgo(p.last_success_at) + '</span>' : '') +
        '<button class="btn btn-sm" style="background:none;color:var(--text-dim);font-size:14px;cursor:pointer;padding:2px 6px" onclick="openNotificationSettings(\'' + p.id + '\')" title="Settings">&#9881;</button>' +
        '<button class="btn btn-sm" style="background:var(--surface2);color:var(--blue)" onclick="testNotificationProvider(\'' + p.id + '\')">Test</button>' +
        '<button class="stop-btn" onclick="deleteNotificationProvider(\'' + p.id + '\')">Delete</button>' +
        '</div>';
    });
    el.innerHTML = html;
  } catch (e) {
    el.innerHTML = '<div style="color:var(--red)">Error loading providers</div>';
  }
}

function addNotificationProvider() {
  const name = document.getElementById('npName').value.trim();
  const type = document.getElementById('npType').value;
  const webhook_url = document.getElementById('npUrl').value.trim();
  const msg = document.getElementById('npMsg');
  if (!name) { msg.innerHTML = '<span style="color:var(--red)">Enter a provider name</span>'; return; }
  if (!webhook_url) { msg.innerHTML = '<span style="color:var(--red)">Enter a webhook URL</span>'; return; }
  msg.innerHTML = '';
  sendQueued('notification-providers/create', { name, type, webhook_url }).then(function() {
    document.getElementById('npName').value = '';
    document.getElementById('npUrl').value = '';
    msg.innerHTML = '<span style="color:var(--green)">Provider added</span>';
    renderNotificationsTab();
  }).catch(function(e) {
    msg.innerHTML = '<span style="color:var(--red)">' + e.message + '</span>';
  });
}

function testNotificationProvider(id) {
  sendQueued('notification-providers/test', { id: id }).then(function(data) {
    showToast(data.message || 'Test sent', data.ok ? 'success' : 'error');
  }).catch(function(e) {
    showToast('Test failed: ' + e.message, 'error');
  });
}

function toggleNotificationProvider(id, enabled) {
  sendQueued('notification-providers/update', { id: id, enabled: enabled }).then(function() {
    renderNotificationsTab();
  }).catch(function(e) {
    showToast('Failed: ' + e.message, 'error');
  });
}

function deleteNotificationProvider(id) {
  if (!confirm('Delete this notification provider?')) return;
  sendQueued('notification-providers/delete', { id: id }).then(function() {
    showToast('Provider deleted', 'success');
    renderNotificationsTab();
  }).catch(function(e) {
    showToast('Failed: ' + e.message, 'error');
  });
}

// ── NOTIFICATION SETTINGS ──
let _nsProviderId = '';

function openNotificationSettings(id) {
  _nsProviderId = id;
  fetch('/api/notification-providers').then(function(r) { return r.json(); }).then(function(data) {
    if (!data.ok || !data.providers) return;
    var p = data.providers.find(function(x) { return x.id === id; });
    if (!p) return;
    var scopes = p.scopes || {};
    document.getElementById('nsProviderName').textContent = p.name + ' (' + p.type + ')';
    document.getElementById('nsStateChange').checked = scopes.state_change !== false;
    document.getElementById('nsUserInteraction').checked = scopes.user_interaction !== false;
    document.getElementById('nsDesksFull').checked = scopes.desks_full === true;
    document.getElementById('nsNoActiveCases').checked = scopes.no_active_cases === true;
    document.getElementById('nsNoActiveTimeout').value = p.no_active_timeout || 300;
    document.getElementById('nsGapSec').value = p.gap_sec || 300;
    document.getElementById('nsErr').style.display = 'none';
    document.getElementById('notificationSettingsModal').style.display = 'flex';
  });
}

function saveNotificationSettings() {
  var data = {
    id: _nsProviderId,
    scopes: {
      state_change: document.getElementById('nsStateChange').checked,
      user_interaction: document.getElementById('nsUserInteraction').checked,
      desks_full: document.getElementById('nsDesksFull').checked,
      no_active_cases: document.getElementById('nsNoActiveCases').checked,
    },
    no_active_timeout: parseInt(document.getElementById('nsNoActiveTimeout').value) || 300,
    gap_sec: parseInt(document.getElementById('nsGapSec').value) || 300,
  };
  var err = document.getElementById('nsErr');
  sendQueued('notification-providers/update', data).then(function() {
    closeNotificationSettings();
    renderNotificationsTab();
    showToast('Settings saved', 'success');
  }).catch(function(e) {
    err.textContent = e.message;
    err.style.display = 'block';
  });
}

function closeNotificationSettings() {
  document.getElementById('notificationSettingsModal').style.display = 'none';
}

// ── LOGS TAB ──
async function renderLogsTab() {
  const el = document.getElementById('logsTabContent');
  const query = (document.getElementById('logSearch').value || '').toLowerCase();
  try {
    const resp = await fetch('data/activity.log?_=' + Date.now());
    const text = await resp.text();
    const lines = text.split('\n').filter(l => l.trim()).reverse().slice(0, 200);

    if (lines.length === 0) {
      el.innerHTML = '<div style="color:var(--text-dim)">No log entries</div>';
      return;
    }

    const filtered = query ? lines.filter(l => l.toLowerCase().includes(query)) : lines;
    el.innerHTML = filtered.map(l => {
      const match = l.match(/^\[(\d{2}:\d{2}:\d{2})\]\s*(.*)/);
      if (match) {
        return '<div><span style="color:var(--text-dim)">[' + match[1] + ']</span> ' + escapeHtml(match[2]) + '</div>';
      }
      return '<div>' + escapeHtml(l) + '</div>';
    }).join('');
  } catch {
    el.innerHTML = '<div style="color:var(--red)">Error loading logs</div>';
  }
}

function refreshLogs() {
  document.getElementById('logSearch').value = '';
  renderLogsTab();
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ── QUEUE MIDDLEMAN ──
let _queuePollTimers = {};

function sendQueued(type, payload, onProgress) {
  return fetch('/api/queue', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, payload })
  }).then(function(r) { return r.json(); }).then(function(data) {
    if (!data.queueId) {
      var qMsg = data.message || 'Queue rejected';
      if (data.error_id) qMsg += ' [' + data.error_id + ']';
      throw new Error(qMsg);
    }
    return new Promise(function(resolve, reject) {
      const timeout = setTimeout(function() {
        clearInterval(poll);
        delete _queuePollTimers[data.queueId];
        resolve({ok: true, message: 'Request sent! Wait dashboard to reflect the updates.', timeout: true});
      }, 180000);
      const poll = setInterval(function() {
        fetch('/api/queue/' + data.queueId).then(function(r) { return r.json(); }).then(function(d) {
          if (onProgress) onProgress(d);
          if (d.status === 'done') {
            clearInterval(poll);
            clearTimeout(timeout);
            delete _queuePollTimers[data.queueId];
            resolve(d.result);
          } else if (d.status === 'failed') {
            clearInterval(poll);
            clearTimeout(timeout);
            delete _queuePollTimers[data.queueId];
            reject(new Error(d.error || 'Queue failed'));
          }
        }).catch(function() {});
      }, 2000);
      _queuePollTimers[data.queueId] = { poll: poll, timeout: timeout };
    });
  });
}

// ── PROVIDER TAB ──
async function renderProvidersTab() {
  const el = document.getElementById('providersTabContent');
  try {
    const resp = await fetch('/api/providers');
    const data = await resp.json();
    if (!data.ok) { el.innerHTML = '<div style="font-size:12px;color:var(--red)">Failed to load providers</div>'; return; }

    let html = '';

    // AI Providers section
    html += '<div class="admin-card"><h4>AI Providers</h4>';
    if (data.providers && data.providers.length > 0) {
      html += '<table class="admin-table"><thead><tr><th>Provider</th><th>Auth</th><th>Status</th><th></th></tr></thead><tbody>';
      data.providers.forEach(p => {
        html += '<tr><td>' + escapeHtml(p.name) + '</td><td style="font-size:10px;color:var(--text-dim)">' + escapeHtml(p.type) + '</td>' +
          '<td><span style="color:var(--green)">● Active</span></td>' +
          '<td><button class="stop-btn" onclick="providerLogout(\'' + escapeHtml(p.name) + '\', event)">Logout</button></td></tr>';
      });
      html += '</tbody></table>';
    } else {
      html += '<div style="font-size:12px;color:var(--text-dim)">No providers configured</div>';
    }
    // Login form
    html += '<div style="margin-top:12px"><h4>Add Provider</h4>';
    html += '<div class="inline-form"><input type="text" id="providerLoginUrl" placeholder="Provider URL (optional)" style="flex:1">';
    html += '<button class="btn btn-sm btn-primary" onclick="providerLogin()">Login</button></div>';
    html += '<div id="providerLoginResult" style="font-size:11px;color:var(--text-dim);margin-top:6px"></div></div>';
    html += '</div>';

    // Ollama section
    html += '<div class="admin-card" style="margin-top:16px"><h4>Ollama Connections</h4>';
    if (data.ollama && data.ollama.length > 0) {
      html += '<table class="admin-table"><thead><tr><th>URL</th><th>Status</th><th>Models</th><th></th></tr></thead><tbody>';
      data.ollama.forEach(o => {
        const statusColor = o.status === 'online' ? 'var(--green)' : 'var(--red)';
        const statusLabel = o.status === 'online' ? '● Online' : '● Offline';
        html += '<tr><td style="font-size:11px">' + escapeHtml(o.url) + '</td>' +
          '<td><span style="color:' + statusColor + '">' + statusLabel + '</span></td>' +
          '<td>' + (o.models || 0) + '</td>' +
          '<td><button class="stop-btn" onclick="ollamaRemove(\'' + escapeHtml(o.url) + '\', event)">Remove</button></td></tr>';
      });
      html += '</tbody></table>';
    } else {
      html += '<div style="font-size:12px;color:var(--text-dim)">No Ollama connections</div>';
    }
    // Add Ollama form
    html += '<div style="margin-top:12px"><h4>Add Server</h4>';
    html += '<div class="inline-form"><input type="text" id="ollamaAddUrl" placeholder="https://ollama.example.com" style="flex:1">';
    html += '<button class="btn btn-sm btn-primary" onclick="ollamaAdd()">Add</button></div>';
    html += '<div id="ollamaAddResult" style="font-size:11px;color:var(--text-dim);margin-top:6px"></div></div>';
    html += '</div>';

    el.innerHTML = html;
  } catch (e) {
    el.innerHTML = '<div style="font-size:12px;color:var(--red)">Error: ' + e.message + '</div>';
  }
}

async function providerLogout(name, event) {
  const btn = (event || window.event).target; btn.disabled = true;
  try {
    const data = await sendQueued('provider-logout', { provider: name });
    showToast(data.ok ? 'Logged out: ' + name : 'Error: ' + data.message, data.ok ? 'success' : 'error');
    renderProvidersTab();
  } catch (e) {
    showToast('Error: ' + e.message, 'error');
    btn.disabled = false;
  }
}

async function providerLogin() {
  const url = document.getElementById('providerLoginUrl').value.trim();
  const result = document.getElementById('providerLoginResult');
  const btn = document.querySelector('#tab-providers .btn-primary');
  if (btn) btn.disabled = true;
  try {
    const data = await sendQueued('provider-login', { url });
    if (data.ok) {
      result.innerHTML = data.instruction || 'Login initiated. Check your browser if a window opened.';
      setTimeout(() => { result.innerHTML = ''; renderProvidersTab(); }, 3000);
    } else {
      result.innerHTML = '<span style="color:var(--red)">' + escapeHtml(data.message) + '</span>';
    }
  } catch (e) {
    result.innerHTML = '<span style="color:var(--red)">' + escapeHtml(e.message) + '</span>';
  }
  if (btn) btn.disabled = false;
}

async function ollamaAdd() {
  const url = document.getElementById('ollamaAddUrl').value.trim();
  const result = document.getElementById('ollamaAddResult');
  if (!url) { result.innerHTML = '<span style="color:var(--red)">Please enter a URL</span>'; return; }
  try {
    const data = await sendQueued('ollama-add', { url });
    if (data.ok) {
      document.getElementById('ollamaAddUrl').value = '';
      result.innerHTML = '<span style="color:var(--green)">URL added</span>';
      setTimeout(() => { result.innerHTML = ''; renderProvidersTab(); }, 2000);
    } else {
      result.innerHTML = '<span style="color:var(--red)">' + escapeHtml(data.message) + '</span>';
    }
  } catch (e) {
    result.innerHTML = '<span style="color:var(--red)">' + escapeHtml(e.message) + '</span>';
  }
}

async function ollamaRemove(url, event) {
  const btn = (event || window.event).target; btn.disabled = true;
  try {
    const data = await sendQueued('ollama-remove', { url });
    showToast(data.ok ? 'Ollama URL removed' : 'Error: ' + data.message, data.ok ? 'success' : 'error');
    renderProvidersTab();
  } catch (e) {
    showToast('Error: ' + e.message, 'error');
    btn.disabled = false;
  }
}

// ── SUPER STAFF TAB ──
global.superStaffCache = [];

let editingStaffName = null;

async function renderSuperStaffTab() {
  const el = document.getElementById('superStaffTabContent');
  try {
    const resp = await fetch('/api/super-staff');
    const data = await resp.json();
    if (!data.ok) { el.innerHTML = '<div style="font-size:12px;color:var(--red)">Failed to load staff</div>'; return; }
    global.superStaffCache = data.staff || [];

    let html = '';

    // Staff list
    html += '<div class="admin-card"><h4>Staff Members <button class="btn btn-sm btn-primary" onclick="openStaffModal(null)" style="float:right;margin-top:-4px">+ New Staff</button></h4>';
    if (global.superStaffCache.length > 0) {
      html += '<table class="admin-table"><thead><tr><th>Name</th><th>Mode</th><th>Model</th><th>Description</th><th>Path</th><th></th></tr></thead><tbody>';
      global.superStaffCache.forEach(s => {
        const escName = escapeHtml(s.name);
        html += '<tr><td>' + escName + '</td>' +
          '<td><span style="color:' + (s.mode === 'plan' ? 'var(--purple)' : 'var(--blue)') + '">' + escapeHtml(s.mode) + '</span></td>' +
          '<td style="font-size:10px;color:var(--text-dim)">' + escapeHtml(s.model || 'default') + '</td>' +
          '<td style="font-size:10px;color:var(--text-dim);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + escapeHtml(s.description) + '">' + (s.description ? s.description.slice(0,40) + (s.description.length > 40 ? '...' : '') : '—') + '</td>' +
          '<td style="font-size:10px;color:var(--text-dim)">' + escapeHtml((s.path || '~').split('/').pop()) + '</td>' +
          '<td><button class="view-btn" onclick="openStaffModal(\'' + escName.replace(/'/g,"\\'") + '\')" style="margin-right:4px">Edit</button><button class="stop-btn" onclick="deleteSuperStaff(\'' + escName.replace(/'/g,"\\'") + '\')">Delete</button></td></tr>';
      });
      html += '</tbody></table>';
    } else {
      html += '<div style="font-size:12px;color:var(--text-dim)">No staff members created yet</div>';
    }
    html += '</div>';

    el.innerHTML = html;
  } catch (e) {
    el.innerHTML = '<div style="font-size:12px;color:var(--red)">Error: ' + e.message + '</div>';
  }
}

function openStaffModal(originalName) {
  editingStaffName = originalName;
  const modal = document.getElementById('staffModal');
  const titleEl = document.getElementById('staffModalTitle');
  const nameInput = document.getElementById('staffName');
  const descInput = document.getElementById('staffDescription');
  const genderSel = document.getElementById('staffGender');
  const modeSel = document.getElementById('staffMode');
  const modelSel = document.getElementById('staffModel');
  const pathSel = document.getElementById('staffPath');
  const err = document.getElementById('staffModalErr');
  err.style.display = 'none';

  if (originalName) {
    titleEl.textContent = 'Edit Staff Member';
    const staff = global.superStaffCache.find(s => s.name === originalName);
    if (staff) {
      nameInput.value = staff.name;
      descInput.value = staff.description || '';
      genderSel.value = staff.gender || 'male';
      modeSel.value = staff.mode || 'build';
      loadModels('staffModel', staff.model || '');
    }
  } else {
    titleEl.textContent = 'Create Staff Member';
    nameInput.value = '';
    descInput.value = '';
    genderSel.value = 'male';
    modeSel.value = 'build';
    loadModels('staffModel', '');
  }

  // Populate workspace paths
  pathSel.innerHTML = '<option value="' + window.location.origin.replace('http://localhost:5500','').replace('http://127.0.0.1:5500','') + '">~ (home)</option>';
  fetch('data/status.json?_=' + Date.now()).then(r => r.json()).then(sd => {
    const dirs = [...new Set((sd.all_sessions || []).map(s => s.directory).filter(Boolean))].sort();
    dirs.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d;
      opt.textContent = d.split('/').pop() || d;
      opt.title = d;
      if (originalName) {
        const staff = global.superStaffCache.find(s => s.name === originalName);
        if (staff && staff.path === d) opt.selected = true;
      }
      pathSel.appendChild(opt);
    });
  }).catch(() => {});

  if (originalName) {
    const staff = global.superStaffCache.find(s => s.name === originalName);
    if (staff && staff.path) pathSel.value = staff.path;
  }

  modal.style.display = 'flex';
}

function closeStaffModal() {
  document.getElementById('staffModal').style.display = 'none';
}

async function saveStaff() {
  const name = document.getElementById('staffName').value.trim();
  const description = document.getElementById('staffDescription').value.trim();
  const gender = document.getElementById('staffGender').value;
  const mode = document.getElementById('staffMode').value;
  const model = document.getElementById('staffModel').value;
  const path = document.getElementById('staffPath').value;
  const err = document.getElementById('staffModalErr');
  err.style.display = 'none';

  if (!name) { err.textContent = 'Name is required'; err.style.display = 'block'; return; }

  const isEdit = !!editingStaffName;
  const type = isEdit ? 'super-staff-update' : 'super-staff-create';
  const body = isEdit
    ? { originalName: editingStaffName, name, description, gender, mode, model, path }
    : { name, description, gender, mode, model, path };

  try {
    const data = await sendQueued(type, body);
    if (data.ok) {
      closeStaffModal();
      showToast(isEdit ? 'Staff member updated' : 'Staff member created', 'success');
      // Refresh cache first
      await renderSuperStaffTab();
      // Update case assignments cache if name changed
      if (isEdit && editingStaffName !== name) {
        for (const sid in _caseAssignments) {
          if (_caseAssignments[sid] === editingStaffName) {
            _caseAssignments[sid] = name;
          }
        }
        // Re-render admin cases tab with fresh cache
        if (currentTab === 'sessions') renderCasesTab();
      }
    } else {
      err.textContent = data.message; err.style.display = 'block';
    }
  } catch (e) {
    err.textContent = e.message; err.style.display = 'block';
  }
}

async function deleteSuperStaff(name) {
  if (!confirm('Delete staff member "' + name + '"?')) return;
  try {
    const data = await sendQueued('super-staff-delete', { name });
    showToast(data.ok ? 'Deleted: ' + name : 'Error: ' + data.message, data.ok ? 'success' : 'error');
    renderSuperStaffTab();
  } catch (e) {
    showToast('Error: ' + e.message, 'error');
  }
}

function getCustomAgents() {
  return global.superStaffCache || [];
}

function onModeChange(modeSel, escId) {
  const modelSel = document.getElementById('model-' + escId);
  if (!modelSel) return;
  const staff = global.superStaffCache.find(s => s.name === modeSel.value);
  if (staff && staff.model) {
    modelSel.value = staff.model;
    modelSel.disabled = true;
  } else {
    modelSel.disabled = false;
  }
}

function onNewCaseModeChange() {
  const mode = document.getElementById('newSessionMode').value;
  const modelSel = document.getElementById('newSessionModel');
  if (!modelSel) return;
  const staff = global.superStaffCache.find(s => s.name === mode);
  if (staff && staff.model) {
    modelSel.value = staff.model;
    modelSel.disabled = true;
  } else {
    modelSel.disabled = false;
  }
}

function getStaffForMode(mode) {
  return global.superStaffCache.find(s => s.name === mode);
}

function renderModeOptions(selectId, selected) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  let html = '<option value="build"' + (selected === 'build' ? ' selected' : '') + '>Build</option>' +
    '<option value="plan"' + (selected === 'plan' ? ' selected' : '') + '>Plan</option>';
  const agents = getCustomAgents();
  if (agents.length > 0) {
    html += '<option disabled style="font-size:9px;color:var(--text-dim)">── Custom Agents ──</option>';
    agents.forEach(a => {
      const selAttr = a.name === selected ? ' selected' : '';
      html += '<option value="' + escapeHtml(a.name) + '"' + selAttr + '>' + escapeHtml(a.name) + '</option>';
    });
  }
  sel.innerHTML = html;
}

// ── TOAST ──
function showToast(message, type) {
  const t = document.getElementById('toast');
  document.getElementById('toastMessage').textContent = message;
  t.className = 'toast ' + type;
  t.style.display = 'flex';
}

function copyToastMessage() {
  const msg = document.getElementById('toastMessage').textContent;
  const btn = document.querySelector('.toast-copy');
  const orig = btn.textContent;
  navigator.clipboard.writeText(msg).then(() => {
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = orig; btn.classList.remove('copied'); }, 1500);
  }).catch(() => {
    const ta = document.createElement('textarea');
    ta.value = msg;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = orig; btn.classList.remove('copied'); }, 1500);
  });
}

function dismissToast() {
  document.getElementById('toast').style.display = 'none';
}

function closeViewModal() {
  const el = document.getElementById('sessionViewModal') || document.querySelector('#sessionViewModal');
  if (el) el.style.display = 'none';
}

function closeContinueModal() {
  const el = document.getElementById('sessionContinueModal') || document.querySelector('#sessionContinueModal');
  if (el) el.style.display = 'none';
}

function closeNewSessionModal() {
  const el = document.getElementById('newSessionModal') || document.querySelector('#newSessionModal');
  if (el) el.style.display = 'none';
}

// ── Rename Case ──
let _renameSessionId = '';

function renameSession(id, currentTitle) {
  _renameSessionId = id;
  const input = document.getElementById('renameInput');
  if (input) input.value = currentTitle;
  document.getElementById('renameError').style.display = 'none';
  document.getElementById('renameModal').style.display = 'flex';
  setTimeout(() => { if (input) input.focus(); }, 100);
}

function closeRenameModal() {
  document.getElementById('renameModal').style.display = 'none';
  _renameSessionId = '';
}

async function saveRename() {
  const input = document.getElementById('renameInput');
  const newTitle = input ? input.value.trim() : '';
  const errEl = document.getElementById('renameError');
  if (!newTitle) {
    errEl.textContent = 'Title cannot be empty';
    errEl.style.display = 'block';
    return;
  }
  if (!_renameSessionId) return;
  errEl.style.display = 'none';
  try {
    const data = await sendQueued('rename-session', { id: _renameSessionId, title: newTitle });
    if (data.ok) {
      closeRenameModal();
      showToast('Case renamed', 'success');
      renderCasesTab();
    } else {
      errEl.textContent = data.message;
      errEl.style.display = 'block';
    }
  } catch (e) {
    errEl.textContent = 'Network error: ' + e.message;
    errEl.style.display = 'block';
  }
}

// Enter key support for rename modal
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && document.getElementById('renameModal').style.display === 'flex') {
    saveRename();
  }
});

// ── Cron Jobs ──
let _cronJobsCache = [];
let _cronRefreshTimer = null;

function formatDuration(sec) {
  sec = Math.round(sec);
  if (sec < 60) return sec + 's';
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  if (m < 60) return m + 'm ' + s + 's';
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return h + 'h ' + rm + 'm';
}

function formatExactTime(tsSec) {
  if (!tsSec) return 'Never';
  const d = new Date(tsSec * 1000);
  const pad = n => String(n).padStart(2, '0');
  const dateStr = d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate());
  const timeStr = pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  const isToday = d.toDateString() === new Date().toDateString();
  return isToday ? timeStr : dateStr + ' ' + timeStr;
}

function getCronCountdown(job) {
  if (job.enabled === false) return { text: 'Disabled', badgeClass: 'badge-disabled', value: -1 };
  const lastTime = job.last_run || job.created || 0;
  const nextRunTime = lastTime + (job.interval_sec || 300);
  const diff = nextRunTime - (Date.now() / 1000);
  if (diff <= 0) return { text: 'Due now', badgeClass: 'badge-due', value: 0 };
  return { text: 'in ' + formatDuration(diff), badgeClass: 'badge-next', value: diff };
}

function updateCronCountdowns() {
  if (currentTab !== 'cron' || !_cronJobsCache.length) return;
  _cronJobsCache.forEach(job => {
    const badge = document.getElementById('cron-badge-' + job.id);
    const lastEl = document.getElementById('cron-last-' + job.id);
    if (badge) {
      const c = getCronCountdown(job);
      badge.textContent = c.text;
      badge.className = 'badge ' + c.badgeClass;
    }
    if (lastEl && job.last_run) {
      lastEl.textContent = formatExactTime(job.last_run) + ' (' + global.humanAgo(job.last_run * 1000) + ')';
    }
  });
}

async function renderCronTab() {
  const el = document.getElementById('cronTabContent');
  el.innerHTML = '<div style="font-size:12px;color:var(--text-dim)">Loading cron jobs...</div>';
  try {
    const r = await fetch('/api/cron-jobs');
    const d = await r.json();
    if (!d.ok) { el.innerHTML = '<div style="color:var(--danger)">Failed to load cron jobs</div>'; return; }
    _cronJobsCache = d.jobs || [];
  } catch(e) {
    el.innerHTML = '<div style="color:var(--danger)">Error loading cron jobs</div>';
    return;
  }
  if (!_cronJobsCache.length) {
    el.innerHTML = '<div style="text-align:center;padding:40px 20px;color:var(--text-dim)"><div style="font-size:40px;margin-bottom:12px">⏰</div><div>No cron jobs scheduled</div></div>';
    return;
  }
  let html = '';
  for (const job of _cronJobsCache) {
    const enabled = job.enabled !== false;
    const lastTime = job.last_run ? formatExactTime(job.last_run) + ' (' + global.humanAgo(job.last_run * 1000) + ')' : 'Never';
    const lastStatus = job.last_status || '—';
    const intervalMin = Math.round((job.interval_sec || 300) / 60);
    const action = job.action || {};
    const typeLabel = action.type === 'session' ? 'Continue Case' : 'New Case';
    const msg = (action.message || '').substring(0, 80);
    const countdown = getCronCountdown(job);
    html += `<div class="admin-card" style="opacity:${enabled ? 1 : 0.5}" data-cron-id="${job.id}">
      <div style="display:flex;justify-content:space-between;align-items:start;gap:12px">
        <div style="flex:1;min-width:0">
          <div style="font-weight:600;margin-bottom:4px;display:flex;align-items:center;gap:8px">
            <span>${escapeHtml(job.name)}</span>
            <span class="badge ${countdown.badgeClass}" id="cron-badge-${job.id}">${countdown.text}</span>
          </div>
          <div style="font-size:11px;color:var(--text-dim);margin-bottom:6px">
            <span class="badge" style="background:var(--surface2)">${typeLabel}</span>
            <span class="badge" style="background:var(--surface2)">every ${intervalMin}m</span>
            ${action.staff ? `<span class="badge badge-staff">${escapeHtml(action.staff)}</span>` : ''}
          </div>
          <div style="font-size:12px;color:var(--text-dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:8px">“${escapeHtml(msg)}${(action.message||'').length > 80 ? '…' : ''}”</div>
          <div style="display:flex;gap:16px;font-size:11px;color:var(--text-dim);border-top:1px solid rgba(48,54,61,0.2);padding-top:6px">
            <div><strong style="color:var(--text)">Last:</strong> <span id="cron-last-${job.id}">${escapeHtml(lastTime)}</span></div>
            <div><strong style="color:var(--text)">Status:</strong> <span style="color:${lastStatus.startsWith('fail') ? 'var(--red)' : 'var(--green)'}">${escapeHtml(lastStatus)}</span></div>
          </div>
        </div>
        <div style="display:flex;gap:4px;flex-shrink:0;align-items:center;margin-top:2px">
          <label class="toggle-switch" style="margin:0">
            <input type="checkbox" ${enabled ? 'checked' : ''} onchange="toggleCronJob('${job.id}')">
            <span class="toggle-slider"></span>
          </label>
          <button class="view-btn" onclick="openCronModal('${job.id}')">Edit</button>
          <button class="send-btn" onclick="runCronJob('${job.id}')" ${job._running ? 'disabled' : ''}>Run</button>
          <button class="stop-btn" onclick="deleteCronJob('${job.id}')">Delete</button>
        </div>
      </div>
    </div>`;
  }
  el.innerHTML = html;
}

async function openCronModal(jobId) {
  const overlay = document.getElementById('cronModal');
  const body = document.getElementById('cronModalBody');
  const title = document.getElementById('cronModalTitle');
  let job = null;
  if (jobId) {
    job = _cronJobsCache.find(j => j.id === jobId) || null;
    title.textContent = 'Edit Cron Job';
  } else {
    title.textContent = 'New Cron Job';
  }
  const name = job ? escapeHtml(job.name) : '';
  const intervalMin = job ? Math.round((job.interval_sec || 300) / 60) : 5;
  const action = job ? (job.action || {}) : {};
  const typeVal = action.type || 'workspace';
  const model = escapeHtml(action.model || '');
  const modeVal = escapeHtml(action.mode || '');
  const staffName = escapeHtml(action.staff || '');
  const dirVal = escapeHtml(action.directory || '');
  const sidVal = escapeHtml(action.session_id || '');
  const forkCheck = action.fork ? 'checked' : '';
  const msgVal = escapeHtml(action.message || '');
  // Determine initial mode value (staff name takes priority over mode)
  const initialMode = staffName || modeVal || 'build';
  body.innerHTML = `
    <div class="form-group">
      <label>Job Name</label>
      <input type="text" id="cronName" value="${name}" placeholder="e.g. Daily Standup Summary">
    </div>
    <div class="form-group">
      <label>Interval (minutes)</label>
      <input type="number" id="cronInterval" value="${intervalMin}" min="1" style="width:100px">
    </div>
    <div class="form-group">
      <label>Type</label>
      <select id="cronType" onchange="toggleCronType()" style="width:100%;padding:10px 12px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:12px;outline:none">
        <option value="workspace" ${typeVal === 'workspace' ? 'selected' : ''}>New Case (workspace)</option>
        <option value="session" ${typeVal === 'session' ? 'selected' : ''}>Continue Existing Case</option>
      </select>
    </div>
    <div id="cronSessionFields" style="display:${typeVal === 'session' ? 'block' : 'none'}">
      <div class="form-group">
        <label>Case</label>
        <select id="cronSessionId" style="width:100%;padding:10px 12px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:12px;outline:none">
          <option value="">Loading cases...</option>
        </select>
      </div>
      <div class="form-group">
        <label style="display:flex;align-items:center;gap:8px">
          <input type="checkbox" id="cronFork" ${forkCheck}>
          Fork as new case instead
        </label>
      </div>
    </div>
    <div id="cronWorkspaceFields" style="display:${typeVal === 'session' ? 'none' : 'block'}">
      <div class="form-group">
        <label>Workspace Directory (optional)</label>
        <select id="cronDirectory" style="width:100%;padding:10px 12px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:12px;outline:none">
          <option value="">~ (home)</option>
        </select>
      </div>
    </div>
    <div class="form-group">
      <label>Message / Instruction</label>
      <textarea id="cronMessage" rows="3" style="width:100%;resize:vertical;padding:10px 12px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:12px;outline:none;font-family:inherit">${msgVal}</textarea>
    </div>
    <div class="form-group">
      <label>Mode</label>
      <select id="cronMode" onchange="onCronModeChange()" style="width:100%;padding:10px 12px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:12px;outline:none">
        <option value="build">Build</option>
        <option value="plan">Plan</option>
      </select>
    </div>
    <div class="form-group">
      <label>Model</label>
      <select id="cronModel" style="width:100%;padding:10px 12px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:12px;outline:none">
        <option value="">Loading models...</option>
      </select>
    </div>
    <div class="form-error" id="cronModalErr" style="display:none"></div>
    <button class="btn btn-primary" onclick="saveCronJob('${jobId || ''}')" style="width:100%;margin-top:8px">${jobId ? 'Update' : 'Create'} Cron Job</button>
  `;
  overlay.style.display = 'flex';
  // Load sessions + directories + populate mode dropdown with staff
  try {
    const [sr, sdResp] = await Promise.all([
      fetch('/api/super-staff'),
      fetch('data/status.json?_=' + Date.now())
    ]);
    const sd = await sr.json();
    const statusData = await sdResp.json();
    const allSessions = statusData.all_sessions || statusData.sessions || [];
    // Populate mode dropdown with super staff options
    const modeSel = document.getElementById('cronMode');
    if (sd.ok && sd.staff && sd.staff.length) {
      modeSel.innerHTML = '<option value="build">Build</option><option value="plan">Plan</option>';
      for (const s of sd.staff) {
        const opt = document.createElement('option');
        opt.value = s.name;
        opt.textContent = s.name + (s.model ? ' (' + s.model + ')' : '');
        if (s.name === initialMode || s.name === staffName) opt.selected = true;
        modeSel.appendChild(opt);
      }
    }
    // Populate model dropdown and apply mode selection effects
    loadModels('cronModel', model || '');
    onCronModeChange();
    // Populate sessions dropdown (case title + workspace)
    const sidSel = document.getElementById('cronSessionId');
    sidSel.innerHTML = '<option value="">Select a case...</option>';
    for (const s of allSessions) {
      const opt = document.createElement('option');
      opt.value = s.id || '';
      const label = s.title || s.slug || s.id || '';
      const sub = s.directory ? ' (' + s.directory.split('/').pop() + ')' : '';
      opt.textContent = label + sub;
      opt.title = s.id || '';
      if (s.id === sidVal) opt.selected = true;
      sidSel.appendChild(opt);
    }
    // Populate directories dropdown
    const dirSel = document.getElementById('cronDirectory');
    dirSel.innerHTML = '<option value="">~ (home)</option>';
    const dirs = [...new Set(allSessions.map(s => s.directory).filter(Boolean))].sort();
    dirs.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d;
      opt.textContent = d.split('/').pop() || d;
      opt.title = d;
      if (d === dirVal) opt.selected = true;
      dirSel.appendChild(opt);
    });
  } catch(e) {}
}

function onCronModeChange() {
  const modeSel = document.getElementById('cronMode');
  const modelInput = document.getElementById('cronModel');
  if (!modeSel || !modelInput) return;
  const staff = getStaffForMode(modeSel.value);
  if (staff && staff.model) {
    modelInput.value = staff.model;
    modelInput.disabled = true;
  } else {
    modelInput.disabled = false;
  }
}

function closeCronModal() {
  document.getElementById('cronModal').style.display = 'none';
}

function toggleCronType() {
  const t = document.getElementById('cronType').value;
  document.getElementById('cronSessionFields').style.display = t === 'session' ? 'block' : 'none';
  document.getElementById('cronWorkspaceFields').style.display = t === 'session' ? 'none' : 'block';
}

async function saveCronJob(jobId) {
  const name = document.getElementById('cronName').value.trim();
  const intervalMin = parseInt(document.getElementById('cronInterval').value) || 5;
  const type = document.getElementById('cronType').value;
  const message = document.getElementById('cronMessage').value.trim();
  const errEl = document.getElementById('cronModalErr');
  if (!name || !message) {
    errEl.textContent = 'Name and message are required';
    errEl.style.display = 'block';
    return;
  }
  errEl.style.display = 'none';
  const modeVal = document.getElementById('cronMode').value;
  const staff = getStaffForMode(modeVal);
  const action = {
    type: type,
    message: message,
    staff: staff ? staff.name : '',
    mode: staff ? staff.mode : (modeVal || ''),
    model: document.getElementById('cronModel').value.trim() || (staff ? staff.model : ''),
  };
  if (type === 'session') {
    action.session_id = document.getElementById('cronSessionId').value.trim();
    action.fork = document.getElementById('cronFork').checked;
    if (!action.session_id) {
      errEl.textContent = 'Case ID is required for Continue Case type';
      errEl.style.display = 'block';
      return;
    }
  } else {
    action.directory = document.getElementById('cronDirectory').value.trim() || '';
  }
  const jobType = jobId ? 'cron-jobs/update' : 'cron-jobs/create';
  const payload = jobId ? { id: jobId, name, interval_sec: intervalMin * 60, action } : { name, interval_sec: intervalMin * 60, action };
  try {
    const d = await sendQueued(jobType, payload);
    if (!d.ok) {
      errEl.textContent = d.message || 'Failed to save';
      errEl.style.display = 'block';
      return;
    }
    closeCronModal();
    renderCronTab();
    showToast('Cron job saved', 'success');
  } catch(e) {
    errEl.textContent = 'Network error';
    errEl.style.display = 'block';
  }
}

async function deleteCronJob(jobId) {
  if (!confirm('Delete this cron job?')) return;
  try {
    const d = await sendQueued('cron-jobs/delete', { id: jobId });
    if (d.ok) {
      renderCronTab();
      showToast('Cron job deleted', 'success');
    }
  } catch(e) {}
}

async function toggleCronJob(jobId) {
  try {
    const d = await sendQueued('cron-jobs/toggle', { id: jobId });
    if (d.ok) renderCronTab();
  } catch(e) {}
}

async function runCronJob(jobId) {
  try {
    const d = await sendQueued('cron-jobs/run', { id: jobId });
    if (d.ok) {
      showToast('Job triggered — refresh to see result', 'success');
      renderCronTab();
    } else {
      showToast('Failed: ' + (d.message || 'unknown'), 'error');
    }
  } catch(e) {
    showToast('Error triggering job', 'error');
  }
}

// Initial auth check on page load
document.addEventListener('DOMContentLoaded', () => {
  updateLoginIndicator();
});

// ── WORKFLOW EDITOR ──
global.wfEditor = null;
let _wfStaffCache = [];

async function loadWorkflowStaff() {
  try {
    const r = await fetch('/api/super-staff');
    const d = await r.json();
    _wfStaffCache = d.staff || [];
  } catch(e) { _wfStaffCache = []; }
}

async function renderWorkflowsTab() {
  const el = document.getElementById('wfListContent');
  el.innerHTML = '<div style="font-size:12px;color:var(--text-dim)">Loading workflows...</div>';
  try {
    const r = await fetch('/api/workflows');
    const d = await r.json();
    if (!d.ok) { el.innerHTML = '<div style="color:var(--danger)">Failed to load workflows</div>'; return; }
    const workflows = d.workflows || [];
    if (!workflows.length) {
      el.innerHTML = '<div style="text-align:center;padding:40px 20px;color:var(--text-dim)"><div style="font-size:40px;margin-bottom:12px">🔁</div><div>No workflows defined yet</div></div>';
      return;
    }
    let html = '<table class="admin-table"><thead><tr><th>Name</th><th>Stages</th><th>Created</th><th></th></tr></thead><tbody>';
    for (const wf of workflows) {
      const stageCount = (wf.nodes || []).length;
      const created = wf.created ? new Date(wf.created * 1000).toLocaleDateString() : '—';
      html += `<tr>
        <td><strong>${escapeHtml(wf.name)}</strong></td>
        <td>${stageCount}</td>
        <td>${created}</td>
        <td style="text-align:right">
          <button class="view-btn" onclick="viewWorkflow('${wf.id}')">View</button>
          <button class="view-btn" onclick="openWorkflowEditor('${wf.id}')">Edit</button>
          <button class="stop-btn" onclick="deleteWorkflow('${wf.id}')">Delete</button>
        </td>
      </tr>`;
    }
    html += '</tbody></table>';
    el.innerHTML = html;
  } catch(e) {
    el.innerHTML = '<div style="color:var(--danger)">Error loading workflows</div>';
  }
}

async function openWorkflowEditor(wfId) {
  document.getElementById('wfListView').style.display = 'none';
  document.getElementById('wfEditorView').style.display = 'block';
  await loadWorkflowStaff();
  if (!global.wfEditor) {
    global.wfEditor = new WfEditor();
  }
  if (wfId) {
    try {
      const r = await fetch('/api/workflows');
      const d = await r.json();
      const wf = (d.workflows || []).find(w => w.id === wfId);
      if (wf) global.wfEditor.loadWorkflow(wf);
    } catch(e) { global.wfEditor.loadWorkflow(null); }
  } else {
    global.wfEditor.loadWorkflow(null);
  }
}

function closeWorkflowEditor() {
  if (global.wfEditor) global.wfEditor.destroy();
  global.wfEditor = null;
  document.getElementById('wfEditorView').style.display = 'none';
  document.getElementById('wfListView').style.display = 'block';
  renderWorkflowsTab();
}

async function deleteWorkflow(wfId) {
  if (!confirm('Delete this workflow?')) return;
  try {
    const resp = await sendQueued('workflow-delete', { id: wfId });
    showToast('Workflow deleted', 'success');
    renderWorkflowsTab();
  } catch(e) { showToast('Error: ' + e.message, 'error'); }
}

function renderMarkdown(text) {
  if (!text) return '';
  var src = escapeHtml(String(text).replace(/\r\n/g, '\n'));
  var lines = src.split('\n');

  function inlineMd(s) {
    var codeTokens = [];
    s = s.replace(/`([^`]+)`/g, function(_, code) {
      var key = '%%CODE' + codeTokens.length + '%%';
      codeTokens.push('<code>' + code + '</code>');
      return key;
    });
    s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/(^|[^*])\*([^*]+)\*(?=[^*]|$)/g, '$1<em>$2</em>');
    codeTokens.forEach(function(token, idx) {
      s = s.replace('%%CODE' + idx + '%%', token);
    });
    return s;
  }

  function splitTableRow(line) {
    var row = line.trim().replace(/^\|/, '').replace(/\|$/, '');
    return row.split('|').map(function(cell) { return inlineMd(cell.trim()); });
  }

  function isBlockStart(line) {
    var t = line.trim();
    return /^```/.test(t)
      || /^#{1,4}\s+/.test(t)
      || /^\s*[-*]\s+/.test(t)
      || /^\s*\d+\.\s+/.test(t)
      || /^\s*>\s?/.test(t)
      || (t.includes('|'));
  }

  var out = [];
  var i = 0;
  while (i < lines.length) {
    var line = lines[i];
    var t = line.trim();

    if (!t) {
      i++;
      continue;
    }

    if (/^```/.test(t)) {
      var lang = (t.match(/^```(\w+)?/) || [])[1] || '';
      var codeLines = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i].trim())) {
        codeLines.push(lines[i]);
        i++;
      }
      if (i < lines.length) i++;
      out.push('<pre><code' + (lang ? ' class="lang-' + lang + '"' : '') + '>' + codeLines.join('\n') + '</code></pre>');
      continue;
    }

    var h = t.match(/^(#{1,4})\s+(.+)$/);
    if (h) {
      var level = Math.min(4, h[1].length);
      out.push('<h' + level + '>' + inlineMd(h[2]) + '</h' + level + '>');
      i++;
      continue;
    }

    if (t.includes('|') && i + 1 < lines.length && /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[i + 1])) {
      var headCells = splitTableRow(lines[i]);
      i += 2;
      var bodyRows = [];
      while (i < lines.length && lines[i].trim() && lines[i].includes('|')) {
        bodyRows.push(splitTableRow(lines[i]));
        i++;
      }
      var table = '<table><thead><tr>' + headCells.map(function(c) { return '<th>' + c + '</th>'; }).join('') + '</tr></thead><tbody>';
      bodyRows.forEach(function(r) {
        table += '<tr>' + r.map(function(c) { return '<td>' + c + '</td>'; }).join('') + '</tr>';
      });
      table += '</tbody></table>';
      out.push(table);
      continue;
    }

    if (/^\s*[-*]\s+/.test(line)) {
      var ul = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        ul.push('<li>' + inlineMd(lines[i].replace(/^\s*[-*]\s+/, '')) + '</li>');
        i++;
      }
      out.push('<ul>' + ul.join('') + '</ul>');
      continue;
    }

    if (/^\s*\d+\.\s+/.test(line)) {
      var ol = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        ol.push('<li>' + inlineMd(lines[i].replace(/^\s*\d+\.\s+/, '')) + '</li>');
        i++;
      }
      out.push('<ol>' + ol.join('') + '</ol>');
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      var q = [];
      while (i < lines.length && /^\s*>\s?/.test(lines[i])) {
        q.push(inlineMd(lines[i].replace(/^\s*>\s?/, '')));
        i++;
      }
      out.push('<blockquote>' + q.join('<br>') + '</blockquote>');
      continue;
    }

    var para = [inlineMd(t)];
    i++;
    while (i < lines.length && lines[i].trim() && !isBlockStart(lines[i])) {
      para.push(inlineMd(lines[i].trim()));
      i++;
    }
    out.push('<p>' + para.join(' ') + '</p>');
  }

  return out.join('');
}

async function viewWorkflow(wfId) {
  document.getElementById('wfViewModal').style.display = 'flex';
  document.getElementById('wfViewTitle').textContent = 'Loading...';
  document.getElementById('wfViewBody').innerHTML = '<div style="font-size:12px;color:var(--text-dim)">Loading...</div>';
  try {
    const r = await fetch('/api/workflows');
    const d = await r.json();
    const wf = (d.workflows || []).find(w => w.id === wfId);
    if (!wf) { document.getElementById('wfViewBody').innerHTML = '<div style="color:var(--red)">Workflow not found</div>'; return; }
    document.getElementById('wfViewTitle').textContent = wf.name || 'Untitled';

    // Fetch workflow instances for this workflow
    const ir = await fetch('/api/workflow-instances');
    const id = await ir.json();
    const instances = (id.instances || []).filter(i => i.workflow_id === wfId);

    var nodeNames = (wf.nodes || []).reduce(function(acc, n) { acc[n.id] = n.name || n.id; return acc; }, {});
    var sortedRuns = (instances || []).slice().sort(function(a, b) {
      return (b.started_at || 0) - (a.started_at || 0);
    });

    // Workflow metadata
    var nodeCount = (wf.nodes || []).length;
    var edgeCount = (wf.edges || []).length;
    var created = wf.created ? new Date(wf.created * 1000).toLocaleString() : '—';
    var updated = wf.updated ? new Date(wf.updated * 1000).toLocaleString() : '—';

    var detailsHtml = '<div class="admin-card"><h4>Details</h4>' +
      '<div class="row"><span class="label">Nodes</span><span class="value">' + nodeCount + '</span></div>' +
      '<div class="row"><span class="label">Edges</span><span class="value">' + edgeCount + '</span></div>' +
      '<div class="row"><span class="label">Runs</span><span class="value">' + sortedRuns.length + '</span></div>' +
      '<div class="row"><span class="label">Created</span><span class="value">' + created + '</span></div>' +
      '<div class="row"><span class="label">Updated</span><span class="value">' + updated + '</span></div>' +
      '</div>';

    // Last Responses tab (latest completed summaries)
    var responsesWithSummary = sortedRuns.filter(function(inst) { return !!inst.summary; });
    var responsesHtml = '';
    if (responsesWithSummary.length === 0) {
      responsesHtml = '<div class="admin-card"><div style="font-size:12px;color:var(--text-dim)">No workflow summaries yet.</div></div>';
    } else {
      responsesWithSummary.slice(0, 8).forEach(function(inst, idx) {
        var startedText = inst.started_at ? new Date(inst.started_at * 1000).toLocaleString() : '—';
        responsesHtml += '<div class="admin-card">' +
          '<div style="display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:8px">' +
          '<strong style="font-size:12px">Response #' + (idx + 1) + '</strong>' +
          '<span style="font-size:10px;color:var(--text-dim)">' + startedText + '</span>' +
          '</div>' +
          '<div style="font-size:11px;color:var(--text-dim);margin-bottom:8px">Session: ' + escapeHtml((inst.session_id || '').slice(0, 24)) + ((inst.session_id || '').length > 24 ? '…' : '') + '</div>' +
          '<div class="wf-doc">' + renderMarkdown(inst.summary) + '</div>' +
          '</div>';
      });
    }

    // Runs tab (table)
    var runsHtml = '';
    if (sortedRuns.length === 0) {
      runsHtml = '<div class="admin-card"><div style="font-size:12px;color:var(--text-dim)">No runs found for this workflow.</div></div>';
    } else {
      var runRows = '';
      sortedRuns.forEach(function(inst) {
        var ns = inst.node_states || {};
        var total = Object.keys(ns).length;
        var done = Object.values(ns).filter(function(s) { return s.status === 'completed' || s.status === 'failed'; }).length;
        var pct = total > 0 ? Math.round(done / total * 100) : 0;
        var statusColor = inst.status === 'completed' ? 'var(--green)' : (inst.status === 'failed' ? 'var(--red)' : 'var(--yellow)');
        var statusBg = inst.status === 'completed' ? '#3fb95022' : (inst.status === 'failed' ? '#f8514922' : '#d2992222');
        var startedText = inst.started_at ? new Date(inst.started_at * 1000).toLocaleString() : '—';
        var currentNode = inst.current_node ? (nodeNames[inst.current_node] || inst.current_node) : '—';
        runRows += '<tr>' +
          '<td style="font-family:monospace;font-size:10px">' + escapeHtml((inst.session_id || '').slice(0, 24)) + ((inst.session_id || '').length > 24 ? '…' : '') + '</td>' +
          '<td><span class="wf-view-pill" style="color:' + statusColor + ';background:' + statusBg + '">' + escapeHtml(inst.status || 'unknown') + '</span></td>' +
          '<td>' + escapeHtml(currentNode) + '</td>' +
          '<td>' + pct + '%</td>' +
          '<td style="white-space:nowrap">' + startedText + '</td>' +
          '</tr>';
      });
      runsHtml = '<div class="admin-card">' +
        '<table class="wf-view-run-table">' +
        '<thead><tr><th>Session</th><th>Status</th><th>Current Stage</th><th>Progress</th><th>Started</th></tr></thead>' +
        '<tbody>' + runRows + '</tbody>' +
        '</table>' +
        '</div>';
    }

    // Nodes list
    var stagesHtml = '';
    if (wf.nodes && wf.nodes.length > 0) {
      stagesHtml += '<div class="admin-card"><h4>Stages</h4>';
      wf.nodes.forEach(function(n) {
        var nodeType = String(n.node_type || n.type || 'io').toLowerCase();
        if (nodeType !== 'starter' && nodeType !== 'end') nodeType = 'io';
        var typeBg = nodeType === 'starter' ? '#2ea04333' : (nodeType === 'end' ? '#f8514933' : '#1f6feb33');
        var typeColor = nodeType === 'starter' ? '#3fb950' : (nodeType === 'end' ? '#ff7b72' : '#58a6ff');
        var typeLabel = nodeType === 'starter' ? 'Starter' : (nodeType === 'end' ? 'End' : 'I/O');
        var staff = n.staff_ic || '';
        var mode = n.mode || '';
        var model = n.model || '';
        stagesHtml += '<div style="padding:10px;margin-bottom:8px;background:var(--surface2);border-radius:8px;font-size:12px">' +
          '<div style="font-weight:500;margin-bottom:4px;display:flex;align-items:center;gap:8px">' + escapeHtml(n.name || n.id) +
          '<span style="font-size:9px;padding:2px 6px;border-radius:999px;background:' + typeBg + ';color:' + typeColor + ';font-weight:600;text-transform:uppercase">' + typeLabel + '</span></div>' +
          (n.instructions ? '<div style="color:var(--text-dim);margin-bottom:4px;white-space:pre-wrap">' + escapeHtml(n.instructions.slice(0, 200)) + (n.instructions.length > 200 ? '…' : '') + '</div>' : '') +
          (staff || mode || model ? '<div style="display:flex;gap:6px;flex-wrap:wrap">' : '') +
          (staff ? '<span style="font-size:10px;padding:1px 5px;border-radius:3px;background:var(--accent)22;color:var(--accent)">' + escapeHtml(staff) + '</span>' : '') +
          (mode ? '<span style="font-size:10px;padding:1px 5px;border-radius:3px;background:' + (mode === 'plan' ? '#bc8cff33' : '#58a6ff33') + ';color:' + (mode === 'plan' ? '#bc8cff' : '#58a6ff') + '">' + escapeHtml(mode) + '</span>' : '') +
          (model ? '<span style="font-size:10px;color:var(--text-dim)">' + escapeHtml(model) + '</span>' : '') +
          (staff || mode || model ? '</div>' : '') +
          '</div>';
      });
      stagesHtml += '</div>';
    } else {
      stagesHtml = '<div class="admin-card"><div style="font-size:12px;color:var(--text-dim)">No stages defined.</div></div>';
    }

    // Edges
    var connectionsHtml = '';
    if (wf.edges && wf.edges.length > 0) {
      connectionsHtml += '<div class="admin-card"><h4>Connections</h4><table class="wf-view-run-table"><thead><tr><th>From</th><th>To</th></tr></thead><tbody>';
      wf.edges.forEach(function(e) {
        connectionsHtml += '<tr><td>' + escapeHtml(nodeNames[e.from] || e.from) + '</td><td>' + escapeHtml(nodeNames[e.to] || e.to) + '</td></tr>';
      });
      connectionsHtml += '</tbody></table></div>';
    } else {
      connectionsHtml = '<div class="admin-card"><div style="font-size:12px;color:var(--text-dim)">No connections defined.</div></div>';
    }

    var tabHtml = '' +
      '<div class="wf-view-tabs" id="wfViewTabs">' +
      '<button class="wf-view-tab" data-tab="responses" onclick="switchWorkflowViewTab(\'responses\')">Last Responses</button>' +
      '<button class="wf-view-tab" data-tab="details" onclick="switchWorkflowViewTab(\'details\')">Details</button>' +
      '<button class="wf-view-tab" data-tab="runs" onclick="switchWorkflowViewTab(\'runs\')">Runs</button>' +
      '<button class="wf-view-tab" data-tab="stages" onclick="switchWorkflowViewTab(\'stages\')">Stages</button>' +
      '<button class="wf-view-tab" data-tab="connections" onclick="switchWorkflowViewTab(\'connections\')">Connections</button>' +
      '</div>' +
      '<div class="wf-view-panel" data-panel="responses">' + responsesHtml + '</div>' +
      '<div class="wf-view-panel" data-panel="details">' + detailsHtml + '</div>' +
      '<div class="wf-view-panel" data-panel="runs">' + runsHtml + '</div>' +
      '<div class="wf-view-panel" data-panel="stages">' + stagesHtml + '</div>' +
      '<div class="wf-view-panel" data-panel="connections">' + connectionsHtml + '</div>';

    document.getElementById('wfViewBody').innerHTML = tabHtml;
    switchWorkflowViewTab('responses');
  } catch(e) {
    document.getElementById('wfViewBody').innerHTML = '<div style="color:var(--red)">Error: ' + e.message + '</div>';
  }
}

function switchWorkflowViewTab(tabId) {
  const tabRoot = document.getElementById('wfViewTabs');
  const body = document.getElementById('wfViewBody');
  if (!tabRoot || !body) return;
  tabRoot.querySelectorAll('.wf-view-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  body.querySelectorAll('.wf-view-panel').forEach(panel => {
    panel.classList.toggle('active', panel.dataset.panel === tabId);
  });
}

function closeWorkflowViewModal() {
  document.getElementById('wfViewModal').style.display = 'none';
}

class WfEditor {
  constructor() {
    console.log('[WfEditor] Constructor called');
    this.workflowId = null;
    this.nodes = [];
    this.edges = [];
    this.selectedNodeId = null;
    this.selectedNodeIds = new Set();
    this.dragging = null;
    this.connecting = null;
    this.selectBox = null;
    this.spacePressed = false;
    this.panning = null;
    this.overlayDragging = null;
    this.overlayPos = { x: 12, y: 12 };
    this.overlayReady = false;
    this.zoom = 1;
    this.minZoom = 0.5;
    this.maxZoom = 2;
    this.baseCanvasWidth = 2400;
    this.baseCanvasHeight = 1600;
    this._nodeIdCounter = 1;
    this._cbs = {};
    this._setupCanvas();
  }

  _screenToCanvas(clientX, clientY) {
    const wrap = document.getElementById('wfCanvasWrap');
    const rect = wrap.getBoundingClientRect();
    const x = (clientX - rect.left + wrap.scrollLeft) / this.zoom;
    const y = (clientY - rect.top + wrap.scrollTop) / this.zoom;
    return { x, y };
  }

  _isTypingElement(el) {
    if (!el) return false;
    const tag = (el.tagName || '').toLowerCase();
    return tag === 'input' || tag === 'textarea' || tag === 'select' || el.isContentEditable;
  }

  _syncOverlayPosition() {
    const wrap = document.getElementById('wfCanvasWrap');
    const overlay = document.getElementById('wfEdgeOverlay');
    if (!wrap || !overlay) return;

    if (!this.overlayReady) {
      const defaultY = Math.max(12, wrap.clientHeight - overlay.offsetHeight - 12);
      this.overlayPos.x = 12;
      this.overlayPos.y = defaultY;
      this.overlayReady = true;
    }

    const maxX = Math.max(12, wrap.clientWidth - overlay.offsetWidth - 12);
    const maxY = Math.max(12, wrap.clientHeight - overlay.offsetHeight - 12);
    this.overlayPos.x = Math.max(12, Math.min(maxX, this.overlayPos.x));
    this.overlayPos.y = Math.max(12, Math.min(maxY, this.overlayPos.y));

    overlay.style.left = (wrap.scrollLeft + this.overlayPos.x) + 'px';
    overlay.style.top = (wrap.scrollTop + this.overlayPos.y) + 'px';
    overlay.style.bottom = 'auto';
  }

  _updateCanvasSize() {
    const wrap = document.getElementById('wfCanvasWrap');
    const content = document.getElementById('wfCanvasContent');
    const sizer = document.getElementById('wfCanvasSizer');
    if (!wrap || !content || !sizer) return;

    let maxX = this.baseCanvasWidth;
    let maxY = this.baseCanvasHeight;
    this.nodes.forEach(n => {
      maxX = Math.max(maxX, n.x + 320);
      maxY = Math.max(maxY, n.y + 220);
    });

    content.style.width = maxX + 'px';
    content.style.height = maxY + 'px';
    content.style.transform = 'scale(' + this.zoom + ')';
    sizer.style.width = (maxX * this.zoom) + 'px';
    sizer.style.height = (maxY * this.zoom) + 'px';
    this._syncOverlayPosition();

    const label = document.getElementById('wfZoomLabel');
    if (label) label.textContent = Math.round(this.zoom * 100) + '%';
  }

  _setZoom(nextZoom, pivotClientX = null, pivotClientY = null) {
    const wrap = document.getElementById('wfCanvasWrap');
    if (!wrap) return;
    const oldZoom = this.zoom;
    const clamped = Math.max(this.minZoom, Math.min(this.maxZoom, nextZoom));
    if (Math.abs(clamped - oldZoom) < 0.0001) return;

    const rect = wrap.getBoundingClientRect();
    const px = pivotClientX == null ? rect.left + rect.width / 2 : pivotClientX;
    const py = pivotClientY == null ? rect.top + rect.height / 2 : pivotClientY;
    const worldX = (px - rect.left + wrap.scrollLeft) / oldZoom;
    const worldY = (py - rect.top + wrap.scrollTop) / oldZoom;

    this.zoom = clamped;
    this._updateCanvasSize();

    wrap.scrollLeft = worldX * this.zoom - (px - rect.left);
    wrap.scrollTop = worldY * this.zoom - (py - rect.top);

    this.renderEdges();
  }

  zoomIn() { this._setZoom(this.zoom + 0.1); }
  zoomOut() { this._setZoom(this.zoom - 0.1); }
  resetZoom() { this._setZoom(1); }

  _normalizeNodeType(rawType) {
    const t = String(rawType || '').toLowerCase();
    if (t === 'starter' || t === 'start') return 'starter';
    if (t === 'end' || t === 'finish') return 'end';
    return 'io';
  }

  _enforceNodeTypeRules() {
    if (!this.nodes.length) return;
    this.nodes.forEach(n => {
      n.node_type = this._normalizeNodeType(n.node_type || n.type);
    });
    let starter = this.nodes.find(n => n.node_type === 'starter');
    let end = this.nodes.find(n => n.node_type === 'end');
    if (!starter) starter = this.nodes[0];
    if (!end) end = this.nodes[this.nodes.length - 1];
    this.nodes.forEach(n => {
      if (n.id === starter.id) n.node_type = 'starter';
      else if (n.id === end.id) n.node_type = 'end';
      else n.node_type = 'io';
    });
  }

  loadWorkflow(wf) {
    if (wf) {
      this.workflowId = wf.id;
      this.nodes = JSON.parse(JSON.stringify(wf.nodes || []));
      this.edges = JSON.parse(JSON.stringify(wf.edges || []));
      this._enforceNodeTypeRules();
      this._nodeIdCounter = Math.max(...this.nodes.map(n => parseInt(n.id.replace('n','')) || 0), 0) + 1;
      document.getElementById('wfEditorTitle').value = wf.name || '';
    } else {
      this.workflowId = null;
      this.nodes = [];
      this.edges = [];
      this._nodeIdCounter = 1;
      document.getElementById('wfEditorTitle').value = '';
    }
    this.selectedNodeId = null;
    this.selectedNodeIds = new Set();
    this.dragging = null;
    this.connecting = null;
    this.selectBox = null;
    this.spacePressed = false;
    this.panning = null;
    this.overlayDragging = null;
    this.overlayPos = { x: 12, y: 12 };
    this.overlayReady = false;
    this.zoom = 1;
    this.render();
  }

  _setupCanvas() {
    const wrap = document.getElementById('wfCanvasWrap');
    const overlay = document.getElementById('wfEdgeOverlay');
    const overlayHeader = document.getElementById('wfEdgeOverlayHeader');

    if (overlayHeader) {
      this._cbs.overlayMouseDown = (e) => {
        if (e.button !== 0) return;
        this.overlayDragging = {
          startX: e.clientX,
          startY: e.clientY,
          x: this.overlayPos.x,
          y: this.overlayPos.y,
        };
        if (overlay) overlay.classList.add('dragging');
        e.preventDefault();
        e.stopPropagation();
      };
      overlayHeader.addEventListener('mousedown', this._cbs.overlayMouseDown);
    }

    // Canvas mousedown: start marquee selection when clicking blank area.
    this._cbs.canvasMouseDown = (e) => {
      if (e.button !== 0) return;

      if (this.spacePressed) {
        this.panning = {
          startX: e.clientX,
          startY: e.clientY,
          scrollLeft: wrap.scrollLeft,
          scrollTop: wrap.scrollTop,
        };
        wrap.classList.add('wf-panning');
        e.preventDefault();
        return;
      }

      if (!(e.target === wrap || e.target.classList.contains('wf-grid') || e.target.id === 'wfNodesLayer' || e.target.id === 'wfSvg')) return;

      const pt = this._screenToCanvas(e.clientX, e.clientY);
      const additive = e.shiftKey;
      if (!additive) this.selectedNodeIds.clear();
      this.selectedNodeId = null;
      this.selectBox = { startX: pt.x, startY: pt.y, x: pt.x, y: pt.y, additive: additive };
      this._renderSelectionBox();
      this.render();
      e.preventDefault();
    };
    wrap.addEventListener('mousedown', this._cbs.canvasMouseDown);

    this._cbs.canvasScroll = () => {
      this._syncOverlayPosition();
    };
    wrap.addEventListener('scroll', this._cbs.canvasScroll);

    this._cbs.keyDown = (e) => {
      if (e.code !== 'Space') return;
      if (this._isTypingElement(e.target)) return;
      this.spacePressed = true;
      wrap.classList.add('wf-pan-mode');
      e.preventDefault();
    };
    this._cbs.keyUp = (e) => {
      if (e.code !== 'Space') return;
      this.spacePressed = false;
      wrap.classList.remove('wf-pan-mode');
      if (!this.panning) wrap.classList.remove('wf-panning');
      e.preventDefault();
    };
    document.addEventListener('keydown', this._cbs.keyDown);
    document.addEventListener('keyup', this._cbs.keyUp);

    this._cbs.windowResize = () => {
      this._syncOverlayPosition();
    };
    window.addEventListener('resize', this._cbs.windowResize);

    this._cbs.canvasWheel = (e) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      e.preventDefault();
      const dir = e.deltaY > 0 ? -0.1 : 0.1;
      this._setZoom(this.zoom + dir, e.clientX, e.clientY);
    };
    wrap.addEventListener('wheel', this._cbs.canvasWheel, { passive: false });

    // Mouse move (drag nodes / draw connections)
    this._cbs.mouseMove = (e) => {
      if (this.overlayDragging) {
        const dx = e.clientX - this.overlayDragging.startX;
        const dy = e.clientY - this.overlayDragging.startY;
        this.overlayPos.x = this.overlayDragging.x + dx;
        this.overlayPos.y = this.overlayDragging.y + dy;
        this._syncOverlayPosition();
        return;
      }

      if (this.panning) {
        wrap.scrollLeft = this.panning.scrollLeft - (e.clientX - this.panning.startX);
        wrap.scrollTop = this.panning.scrollTop - (e.clientY - this.panning.startY);
        this._syncOverlayPosition();
        return;
      }

      if (this.dragging) {
        const pt = this._screenToCanvas(e.clientX, e.clientY);
        const dx = pt.x - this.dragging.startX;
        const dy = pt.y - this.dragging.startY;
        const moved = this.dragging.items || [];
        moved.forEach(item => {
          const node = this.nodes.find(n => n.id === item.id);
          if (!node) return;
          node.x = Math.max(0, item.origX + dx);
          node.y = Math.max(0, item.origY + dy);
        });
        this.renderNodes();
        this.renderEdges();
      }
      if (this.connecting) {
        this.connecting.mouseX = e.clientX;
        this.connecting.mouseY = e.clientY;
        this._renderTempEdge();
      }
      if (this.selectBox) {
        const pt = this._screenToCanvas(e.clientX, e.clientY);
        this.selectBox.x = pt.x;
        this.selectBox.y = pt.y;
        this._renderSelectionBox();
        this._applySelectionBox();
      }
    };
    document.addEventListener('mousemove', this._cbs.mouseMove);

    // Mouse up (stop drag / finish connection)
    this._cbs.mouseUp = (e) => {
      if (this.overlayDragging) {
        this.overlayDragging = null;
        if (overlay) overlay.classList.remove('dragging');
      }
      if (this.panning) {
        this.panning = null;
        wrap.classList.remove('wf-panning');
      }
      if (this.dragging) {
        this.dragging = null;
      }
      if (this.connecting) {
        this._finishConnection(e);
      }
      if (this.selectBox) {
        this._clearSelectionBox();
      }
    };
    document.addEventListener('mouseup', this._cbs.mouseUp);
  }

  _renderSelectionBox() {
    const wrap = document.getElementById('wfCanvasWrap');
    if (!this.selectBox) return;
    if (!this._selectBoxEl) {
      this._selectBoxEl = document.createElement('div');
      this._selectBoxEl.className = 'wf-select-box';
      wrap.appendChild(this._selectBoxEl);
    }
    const minX = Math.min(this.selectBox.startX, this.selectBox.x);
    const minY = Math.min(this.selectBox.startY, this.selectBox.y);
    const w = Math.abs(this.selectBox.x - this.selectBox.startX);
    const h = Math.abs(this.selectBox.y - this.selectBox.startY);
    this._selectBoxEl.style.left = minX + 'px';
    this._selectBoxEl.style.top = minY + 'px';
    this._selectBoxEl.style.width = w + 'px';
    this._selectBoxEl.style.height = h + 'px';
    this._selectBoxEl.style.transform = 'scale(' + this.zoom + ')';
    this._selectBoxEl.style.transformOrigin = '0 0';
  }

  _applySelectionBox() {
    if (!this.selectBox) return;
    const minX = Math.min(this.selectBox.startX, this.selectBox.x);
    const minY = Math.min(this.selectBox.startY, this.selectBox.y);
    const maxX = Math.max(this.selectBox.startX, this.selectBox.x);
    const maxY = Math.max(this.selectBox.startY, this.selectBox.y);
    const selected = new Set(this.selectBox.additive ? Array.from(this.selectedNodeIds) : []);
    this.nodes.forEach(n => {
      const nx1 = n.x;
      const ny1 = n.y;
      const nx2 = n.x + 200;
      const ny2 = n.y + 74;
      const intersects = nx1 <= maxX && nx2 >= minX && ny1 <= maxY && ny2 >= minY;
      if (intersects) selected.add(n.id);
    });
    this.selectedNodeIds = selected;
    this.selectedNodeId = this.selectedNodeIds.size === 1 ? Array.from(this.selectedNodeIds)[0] : null;
    this.render();
  }

  _clearSelectionBox() {
    this.selectBox = null;
    if (this._selectBoxEl && this._selectBoxEl.parentNode) {
      this._selectBoxEl.parentNode.removeChild(this._selectBoxEl);
    }
    this._selectBoxEl = null;
  }

  destroy() {
    document.removeEventListener('mousemove', this._cbs.mouseMove);
    document.removeEventListener('mouseup', this._cbs.mouseUp);
    const wrap = document.getElementById('wfCanvasWrap');
    if (wrap) wrap.removeEventListener('mousedown', this._cbs.canvasMouseDown);
    if (wrap) wrap.removeEventListener('wheel', this._cbs.canvasWheel);
    if (wrap) wrap.removeEventListener('scroll', this._cbs.canvasScroll);
    const overlayHeader = document.getElementById('wfEdgeOverlayHeader');
    if (overlayHeader) overlayHeader.removeEventListener('mousedown', this._cbs.overlayMouseDown);
    document.removeEventListener('keydown', this._cbs.keyDown);
    document.removeEventListener('keyup', this._cbs.keyUp);
    window.removeEventListener('resize', this._cbs.windowResize);
    this._clearSelectionBox();
  }

  addNode(nodeType = 'io') {
    const centerX = 50 + (this.nodes.length * 30) % 400;
    const centerY = 80 + Math.floor(this.nodes.length / 5) * 140;
    const id = 'n' + (this._nodeIdCounter++);
    const desiredType = this._normalizeNodeType(nodeType);
    this.nodes.push({ id, name: 'Stage ' + (this.nodes.length + 1), node_type: desiredType, instructions: '', staff_ic: '', mode: 'build', model: '', x: centerX, y: centerY });
    if (desiredType === 'starter' || desiredType === 'end') {
      this.nodes.forEach(n => {
        if (n.id !== id && n.node_type === desiredType) n.node_type = 'io';
      });
    }
    this._enforceNodeTypeRules();
    this.selectNode(id);
    this.render();
  }

  deleteSelected() {
    const ids = this.selectedNodeIds.size ? new Set(this.selectedNodeIds) : (this.selectedNodeId ? new Set([this.selectedNodeId]) : new Set());
    if (!ids.size) return;
    this.nodes = this.nodes.filter(n => !ids.has(n.id));
    this.edges = this.edges.filter(e => !ids.has(e.from) && !ids.has(e.to));
    this.selectedNodeId = null;
    this.selectedNodeIds.clear();
    this.render();
  }

  selectNode(nodeId, additive = false) {
    if (!additive) this.selectedNodeIds.clear();
    if (additive && this.selectedNodeIds.has(nodeId)) {
      this.selectedNodeIds.delete(nodeId);
    } else {
      this.selectedNodeIds.add(nodeId);
    }
    this.selectedNodeId = this.selectedNodeIds.size === 1 ? Array.from(this.selectedNodeIds)[0] : null;
    this.render();
  }

  deselectAll() {
    this.selectedNodeId = null;
    this.selectedNodeIds.clear();
    document.getElementById('wfInspector').classList.remove('open');
    document.getElementById('wfDeleteBtn').disabled = true;
    this.renderNodes();
    this.renderEdgesList();
  }

  render() {
    this._updateCanvasSize();
    this.renderNodes();
    this.renderEdges();
    this.updateInspector();
    this.renderEdgesList();
    document.getElementById('wfDeleteBtn').disabled = !(this.selectedNodeId || this.selectedNodeIds.size);
  }

  renderEdgesList() {
    const el = document.getElementById('wfEdgeList');
    const count = document.getElementById('wfEdgeCount');
    if (!this.edges.length) {
      el.innerHTML = '<div style="font-size:10px;color:var(--text-dim)">No connections</div>';
      count.textContent = '';
      return;
    }
    count.textContent = '(' + this.edges.length + ')';
    let rows = '';
    for (const e of this.edges) {
      const fromNode = this.nodes.find(n => n.id === e.from);
      const toNode = this.nodes.find(n => n.id === e.to);
      const fromName = fromNode ? fromNode.name || fromNode.id : e.from;
      const toName = toNode ? toNode.name || toNode.id : e.to;
      rows += '<tr>' +
        '<td>' + escapeHtml(fromName) + ' → ' + escapeHtml(toName) + '</td>' +
        '<td class="action"><button class="wf-edge-del-btn" title="Delete edge" data-edge-from="' + e.from + '" data-edge-to="' + e.to + '">×</button></td>' +
        '</tr>';
    }
    el.innerHTML =
      '<table class="wf-edge-table">' +
      '<thead><tr><th>Connection</th><th class="action">Action</th></tr></thead>' +
      '<tbody>' + rows + '</tbody>' +
      '</table>';
    // Attach click handlers to delete buttons
    el.querySelectorAll('.wf-edge-del-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const from = btn.dataset.edgeFrom;
        const to = btn.dataset.edgeTo;
        this.edges = this.edges.filter(e2 => !(e2.from === from && e2.to === to));
        this.render();
        e.stopPropagation();
      });
    });
  }

  renderNodes() {
    const layer = document.getElementById('wfNodesLayer');
    layer.innerHTML = '';
    for (const node of this.nodes) {
      const nodeType = this._normalizeNodeType(node.node_type || node.type);
      const isStarter = nodeType === 'starter';
      const isEnd = nodeType === 'end';
      const div = document.createElement('div');
      const isSelected = this.selectedNodeIds.has(node.id) || node.id === this.selectedNodeId;
      div.className = 'wf-node type-' + nodeType + (isSelected ? ' selected' : '');
      div.style.left = node.x + 'px';
      div.style.top = node.y + 'px';
      div.dataset.nodeId = node.id;

      // Find staff name
      const staff = _wfStaffCache.find(s => s.name === node.staff_ic);
      const staffLabel = staff ? staff.name : (node.staff_ic || 'No staff');

      div.innerHTML = `
        <div class="wf-node-header">
          <span class="wf-node-drag">⠿</span>
          <span class="wf-node-dot" style="background:${staff ? '#3fb950' : '#484f58'}"></span>
          <span class="wf-node-name">${escapeHtml(node.name || 'Untitled')}</span>
          <span class="wf-node-type-chip ${nodeType}">${nodeType === 'starter' ? 'Starter' : nodeType === 'end' ? 'End' : 'I/O'}</span>
        </div>
        <div class="wf-node-body">
          <div style="font-size:10px;color:var(--text-dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml((node.instructions || '').substring(0, 40))}</div>
          <div class="wf-node-staff">
            <span style="font-size:10px;color:var(--accent)">${escapeHtml(staffLabel)}</span>
            ${node.mode ? '<span style="font-size:9px;padding:1px 5px;border-radius:3px;font-weight:500;background:' + (node.mode === 'plan' ? '#bc8cff33' : '#58a6ff33') + ';color:' + (node.mode === 'plan' ? '#bc8cff' : '#58a6ff') + '">' + escapeHtml(node.mode) + '</span>' : ''}
            ${node.model ? '<span style="font-size:9px;color:var(--text-dim)">' + escapeHtml(node.model.split('/').pop() || node.model) + '</span>' : ''}
          </div>
        </div>
        ${isStarter ? '' : '<div class="wf-node-port wf-node-port-in" data-port="in" data-node="' + node.id + '"></div>'}
        ${isEnd ? '' : '<div class="wf-node-port wf-node-port-out" data-port="out" data-node="' + node.id + '"></div>'}
      `;

      // Node click -> select
      div.querySelector('.wf-node-header').addEventListener('click', (e) => {
        if (this.spacePressed || this.panning) return;
        e.stopPropagation();
        this.selectNode(node.id, e.shiftKey);
      });

      // Node drag
      div.querySelector('.wf-node-header').addEventListener('mousedown', (e) => {
        if (this.spacePressed) return;
        e.preventDefault();
        const additive = e.shiftKey;
        if (!this.selectedNodeIds.has(node.id)) {
          if (!additive) this.selectedNodeIds.clear();
          this.selectedNodeIds.add(node.id);
        }
        const selectedIds = this.selectedNodeIds.size ? Array.from(this.selectedNodeIds) : [node.id];
        const items = selectedIds.map(id => {
          const n = this.nodes.find(x => x.id === id);
          return n ? { id: id, origX: n.x, origY: n.y } : null;
        }).filter(Boolean);
        this.selectedNodeId = this.selectedNodeIds.size === 1 ? selectedIds[0] : null;
        const canvasPt = this._screenToCanvas(e.clientX, e.clientY);
        this.dragging = { startX: canvasPt.x, startY: canvasPt.y, items: items };
        this.render();
      });

      // Output port -> start connection
      const outPort = div.querySelector('.wf-node-port-out');
      if (outPort) {
        outPort.addEventListener('mousedown', (e) => {
          if (this.spacePressed) return;
          e.stopPropagation();
          e.preventDefault();
          const rect = e.target.getBoundingClientRect();
          const centerX = rect.left + (rect.width / 2);
          const centerY = rect.top + (rect.height / 2);
          const startPt = this._screenToCanvas(centerX, centerY);
          this.connecting = { fromId: node.id, fromX: startPt.x, fromY: startPt.y, mouseX: e.clientX, mouseY: e.clientY };
        });
      }

      // Input port -> drop connection here is handled in mouseup
      layer.appendChild(div);
    }
  }

  renderEdges() {
    const svg = document.getElementById('wfSvg');
    const svgRect = svg.getBoundingClientRect();
    console.log('[WfEditor] renderEdges. SVG rect:', svgRect.left, svgRect.top, svgRect.width, svgRect.height);
    console.log('[WfEditor] SVG scroll:', svg.parentElement?.scrollLeft, svg.parentElement?.scrollTop);
    svg.querySelectorAll('.wf-edge-group, .wf-edge-temp').forEach(el => el.remove());

    console.log('[WfEditor] renderEdges called. Edges to render:', this.edges.length);
    if (this.edges.length > 0) console.log('[WfEditor] First edge from/to:', this.edges[0]);

    for (const edge of this.edges) {
      const fromNode = this.nodes.find(n => n.id === edge.from);
      const toNode = this.nodes.find(n => n.id === edge.to);
      if (!fromNode || !toNode) {
        console.log('[WfEditor] Skipping edge — node not found:', edge.from, edge.to);
        continue;
      }
      const wrap = document.getElementById('wfCanvasWrap');
      const d = this._edgePath(fromNode, toNode);

      console.log('[WfEditor] Edge path d:', d.slice(0, 80));

      const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      g.setAttribute('class', 'wf-edge-group');
      g.addEventListener('mouseenter', () => console.log('[WfEditor] Edge group mouseenter'));
      g.addEventListener('mouseleave', () => console.log('[WfEditor] Edge group mouseleave'));

      const delEdge = () => {
        console.log('[WfEditor] Edge clicked — deleting:', edge.from, '->', edge.to);
        this.edges = this.edges.filter(e2 => !(e2.from === edge.from && e2.to === edge.to));
        this.renderEdges();
      };

      // Wider invisible hit area for easy clicking
      const hit = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      hit.setAttribute('d', d);
      hit.setAttribute('stroke', 'transparent');
      hit.setAttribute('stroke-width', '20');
      hit.setAttribute('fill', 'none');
      hit.addEventListener('click', (e) => { console.log('[WfEditor] hit path click'); e.stopPropagation(); delEdge(); });
      g.appendChild(hit);

      const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      p.setAttribute('d', d);
      p.setAttribute('stroke', '#58a6ff');
      p.setAttribute('stroke-width', '2');
      p.setAttribute('fill', 'none');
      p.setAttribute('marker-end', 'url(#wfArrow)');
      p.addEventListener('click', (e) => { console.log('[WfEditor] visible path click'); e.stopPropagation(); delEdge(); });
      g.appendChild(p);

      svg.appendChild(g);
    }
  }

  _edgePath(fromNode, toNode) {
    const NODE_WIDTH = 200;
    const NODE_HEIGHT = 74;
    const x1 = fromNode.x + NODE_WIDTH;
    const y1 = fromNode.y + NODE_HEIGHT / 2;
    const x2 = toNode.x;
    const y2 = toNode.y + NODE_HEIGHT / 2;
    const dx = Math.max(50, Math.abs(x2 - x1) * 0.45);
    return `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
  }

  _renderTempEdge() {
    const svg = document.getElementById('wfSvg');
    const old = svg.querySelector('.wf-edge-temp');
    if (old) old.remove();
    if (!this.connecting) return;
    const mousePt = this._screenToCanvas(this.connecting.mouseX, this.connecting.mouseY);
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', this.connecting.fromX);
    line.setAttribute('y1', this.connecting.fromY);
    line.setAttribute('x2', mousePt.x);
    line.setAttribute('y2', mousePt.y);
    line.setAttribute('stroke', '#58a6ff');
    line.setAttribute('stroke-width', '2');
    line.setAttribute('stroke-dasharray', '5,3');
    line.setAttribute('class', 'wf-edge-temp');
    svg.appendChild(line);
  }

  _finishConnection(e) {
    if (!this.connecting) return;
    const el = document.elementFromPoint(e.clientX, e.clientY);
    if (el && el.classList.contains('wf-node-port-in')) {
      const toId = el.dataset.node;
      if (toId && toId !== this.connecting.fromId) {
        const fromNode = this.nodes.find(n => n.id === this.connecting.fromId);
        const toNode = this.nodes.find(n => n.id === toId);
        if (fromNode && this._normalizeNodeType(fromNode.node_type) === 'end') {
          this.connecting = null;
          return;
        }
        if (toNode && this._normalizeNodeType(toNode.node_type) === 'starter') {
          this.connecting = null;
          return;
        }
        // Check no duplicate
        const exists = this.edges.some(e2 => e2.from === this.connecting.fromId && e2.to === toId);
        if (!exists) {
          this.edges.push({ from: this.connecting.fromId, to: toId });
          this.render();
        }
      }
    }
    this.connecting = null;
    const svg = document.getElementById('wfSvg');
    const old = svg.querySelector('.wf-edge-temp');
    if (old) old.remove();
  }

  updateInspector() {
    const insp = document.getElementById('wfInspector');
    const singleSelectedId = this.selectedNodeIds.size === 1 ? Array.from(this.selectedNodeIds)[0] : this.selectedNodeId;
    const node = this.nodes.find(n => n.id === singleSelectedId);
    if (!node) {
      insp.classList.remove('open');
      return;
    }
    insp.classList.add('open');
    document.getElementById('wfInspType').value = this._normalizeNodeType(node.node_type || node.type);
    document.getElementById('wfInspName').value = node.name || '';
    document.getElementById('wfInspInstructions').value = node.instructions || '';

    // Populate staff dropdown
    const staffSel = document.getElementById('wfInspStaff');
    staffSel.innerHTML = '<option value="">— None —</option>';
    for (const s of _wfStaffCache) {
      const opt = document.createElement('option');
      opt.value = s.name;
      opt.textContent = s.name + ' (' + (s.mode || 'build') + ')';
      if (s.name === node.staff_ic) opt.selected = true;
      staffSel.appendChild(opt);
    }

    // Populate mode dropdown
    const modeSel = document.getElementById('wfInspMode');
    modeSel.innerHTML = '<option value="build">Build</option><option value="plan">Plan</option>';
    const agents = getCustomAgents();
    if (agents.length > 0) {
      modeSel.innerHTML += '<option disabled style="font-size:9px;color:var(--text-dim)">── Custom Agents ──</option>';
      agents.forEach(a => {
        modeSel.innerHTML += '<option value="' + escapeHtml(a.name) + '">' + escapeHtml(a.name) + '</option>';
      });
    }
    modeSel.value = node.mode || 'build';

    // Populate model dropdown
    const modelSel = document.getElementById('wfInspModel');
    if (modelSel.options.length <= 1) {
      // Load models from status.json
      fetch('data/status.json?_=' + Date.now()).then(r => r.json()).then(data => {
        const models = data.available_models || [];
        if (!models.length) return;
        const grouped = {};
        models.forEach(m => {
          if (!grouped[m.provider]) grouped[m.provider] = [];
          grouped[m.provider].push(m.id);
        });
        let html = '<option value="">Default model</option>';
        for (const [provider, ids] of Object.entries(grouped)) {
          html += '<optgroup label="' + provider + '">';
          ids.forEach(id => {
            const selAttr = id === node.model ? ' selected' : '';
            html += '<option value="' + id.replace(/"/g,'&quot;') + '"' + selAttr + '>' + id + '</option>';
          });
          html += '</optgroup>';
        }
        modelSel.innerHTML = html;
        modelSel.value = node.model || '';
      }).catch(() => {});
    }
    modelSel.value = node.model || '';

    // Auto-fill mode/model when a staff is selected
    const selectedStaff = node.staff_ic;
    if (selectedStaff) {
      const found = _wfStaffCache.find(s => s.name === selectedStaff);
      if (found) {
        if (found.mode) {
          modeSel.value = found.mode;
          modeSel.disabled = true;
        }
        if (found.model) {
          modelSel.value = found.model;
          modelSel.disabled = true;
        }
      }
    } else {
      modeSel.disabled = false;
      modelSel.disabled = false;
    }
  }

  onInspectorChange() {
    const node = this.nodes.find(n => n.id === this.selectedNodeId);
    if (!node) return;
    node.node_type = this._normalizeNodeType(document.getElementById('wfInspType').value);
    if (node.node_type === 'starter' || node.node_type === 'end') {
      this.nodes.forEach(n => {
        if (n.id !== node.id && this._normalizeNodeType(n.node_type) === node.node_type) n.node_type = 'io';
      });
    }
    node.name = document.getElementById('wfInspName').value || 'Untitled';
    node.instructions = document.getElementById('wfInspInstructions').value;
    node.staff_ic = document.getElementById('wfInspStaff').value;
    node.mode = document.getElementById('wfInspMode').value;
    node.model = document.getElementById('wfInspModel').value;
    // If staff selected, re-populate mode/model from staff config (disables manual edit)
    if (node.staff_ic) {
      const found = _wfStaffCache.find(s => s.name === node.staff_ic);
      if (found) {
        if (found.mode) node.mode = found.mode;
        if (found.model) node.model = found.model;
      }
    }
    this._enforceNodeTypeRules();
    this.renderNodes();
    this.updateInspector();
  }

  _validateFlowStructure() {
    const starters = this.nodes.filter(n => this._normalizeNodeType(n.node_type) === 'starter');
    const ends = this.nodes.filter(n => this._normalizeNodeType(n.node_type) === 'end');
    if (!starters.length) return 'Workflow requires a Starter node.';
    if (!ends.length) return 'Workflow requires an End node.';

    const outgoing = new Map();
    const incoming = new Map();
    this.nodes.forEach(n => {
      outgoing.set(n.id, []);
      incoming.set(n.id, []);
    });
    this.edges.forEach(e => {
      if (outgoing.has(e.from) && incoming.has(e.to)) {
        outgoing.get(e.from).push(e.to);
        incoming.get(e.to).push(e.from);
      }
    });

    const hasStarterWithOutput = starters.some(n => (outgoing.get(n.id) || []).length > 0);
    if (!hasStarterWithOutput) return 'Starter node must connect to at least one next node.';

    const hasEndWithInput = ends.some(n => (incoming.get(n.id) || []).length > 0);
    if (!hasEndWithInput) return 'End node must have at least one incoming connection.';

    const queue = starters.map(n => n.id);
    const seen = new Set(queue);
    while (queue.length) {
      const current = queue.shift();
      if (ends.some(n => n.id === current)) return null;
      (outgoing.get(current) || []).forEach(nextId => {
        if (!seen.has(nextId)) {
          seen.add(nextId);
          queue.push(nextId);
        }
      });
    }
    return 'No valid path from Starter node to End node.';
  }

  async save() {
    const name = document.getElementById('wfEditorTitle').value.trim();
    if (!name) { showToast('Please enter a workflow name', 'error'); return; }
    if (!this.nodes.length) { showToast('Add at least one stage', 'error'); return; }
    const flowError = this._validateFlowStructure();
    if (flowError) { showToast(flowError, 'error'); return; }
    const status = document.getElementById('wfEditorStatus');
    status.textContent = 'Saving...';
    const wf = {
      id: this.workflowId || 'wf_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 6),
      name: name,
      nodes: this.nodes.map(n => ({ ...n, node_type: this._normalizeNodeType(n.node_type) })),
      edges: this.edges.map(e => ({ ...e })),
    };
    try {
      const resp = await sendQueued('workflow-save', { workflow: wf });
      this.workflowId = wf.id;
      status.textContent = 'Saved ✓';
      showToast('Workflow saved', 'success');
      setTimeout(() => { status.textContent = ''; }, 2000);
    } catch(e) {
      status.textContent = 'Save failed';
      showToast('Error: ' + e.message, 'error');
    }
  }
}

const _exports = {
  sha256, getUsers, saveUsers, getAuth, setAuth, clearAuth,
  initDefaultUsers, openLoginModal, closeLoginModal, closeAdminModal,
  handleLogin, handleLogout, updateLoginIndicator, openAdminModal,
  switchTab, renderCasesTab, assignStaff, stopSession, viewSession,
  continueSession, openNewSessionModal, startNewSession, loadModels,
  sessionInstructView, showQuestions, selectQuestionOption, sendAnswers,
  closeQuestionModal, closeTasksModal, showTasks, renderSystemTab, restartDaemon, killDaemon,
  renderUsersTab, addUser, deleteUser, renderNamesTab, saveName,
  resetName, resetAllNames, updateSettingPreview, saveSettings,
  loadSettings, toggleApiKeyVisibility, openCropModal, closeCropModal,
  cropAndSave, removeProfilePhoto, updatePhotoPreview, loadApiKey,
  regenerateApiKey, copyApiKey, changePassword,
  renderNotificationsTab, addNotificationProvider, testNotificationProvider,
  deleteNotificationProvider, renderInAppAlertsTab,
  openNotificationSettings, saveNotificationSettings, closeNotificationSettings,
  toggleNotificationProvider,
  sendNotification, dismissNotification, renderLogsTab, refreshLogs,
  escapeHtml, sendQueued, renderProvidersTab, providerLogout,
  providerLogin, ollamaAdd, ollamaRemove, renderSuperStaffTab,
  openStaffModal, closeStaffModal, saveStaff, deleteSuperStaff,
  getCustomAgents, onModeChange, onNewCaseModeChange, getStaffForMode,
  getBossName,
  renderModeOptions, showToast, copyToastMessage, dismissToast,
  closeViewModal, closeContinueModal, closeNewSessionModal,
  renameSession, closeRenameModal, saveRename,
  onNewCaseWorkflowChange,
  formatDuration, formatExactTime, getCronCountdown, updateCronCountdowns,
  renderCronTab, openCronModal, onCronModeChange, closeCronModal,
  toggleCronType, saveCronJob, deleteCronJob, toggleCronJob, runCronJob,
  apiFetch, getModal,
  renderWorkflowsTab, openWorkflowEditor, closeWorkflowEditor, deleteWorkflow,
  viewWorkflow, closeWorkflowViewModal, switchWorkflowViewTab, renderMarkdown,
  loadWorkflowStaff, WfEditor
};
for (const key in _exports) {
  global[key] = _exports[key];
}
console.log('admin.js exports check:', {
  openAdminModal: typeof global.openAdminModal,
  renderWorkflowsTab: typeof global.renderWorkflowsTab
});
})(window);
