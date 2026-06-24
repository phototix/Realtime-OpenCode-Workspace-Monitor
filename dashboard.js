(function (global) {
'use strict';

// ── API KEY FETCH INTERCEPTOR ──
// Automatically attaches X-API-Key to every /api/ request so the web
// dashboard works the same way as the Android app without touching each
// individual fetch() call.
(function () {
  const _origFetch = global.fetch;
  global.fetch = function (input, init) {
    const url = typeof input === 'string' ? input
      : (input instanceof URL ? input.toString() : (input && input.url) || '');
    if (/\/api\//.test(url) && !url.startsWith('http')) {
      const key = localStorage.getItem('dashboard_api_key') || '';
      if (key) {
        init = init ? Object.assign({}, init) : {};
        const headers = new Headers(init.headers || {});
        headers.set('X-API-Key', key);
        init.headers = headers;
      }
    }
    return _origFetch.call(this, input, init);
  };
})();

const STATUS_URL = 'data/status.json';
global.POLL_INTERVAL = 2000;
global._pollTimer = null;

const TYPE_ICONS = {
  main: '\u2699',
  agent: '\u269B',
  engine: '\u26A1',
  helper: '\u2692'
};

let prevSessions = [];

const expandedTexts = new Set();

function toggleDisplay(id) {
  if (expandedTexts.has(id)) {
    expandedTexts.delete(id);
  } else {
    const el = document.getElementById(id);
    if (el && el.classList.contains('sc-text-expanded')) {
      expandedTexts.add(id);
    }
  }
}

function formatTime(isoStr) {
  if (!isoStr) return '—';
  const d = new Date(isoStr);
  return d.toLocaleTimeString();
}

function humanAgo(ts) {
  if (!ts) return '—';
  const ms = Date.now() - ts;
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return sec + 's ago';
  const min = Math.floor(sec / 60);
  if (min < 60) return min + 'm ago';
  const hr = Math.floor(min / 60);
  if (hr < 24) return hr + 'h ago';
  const day = Math.floor(hr / 24);
  if (day < 7) return day + 'd ago';
  const wk = Math.floor(day / 7);
  if (wk < 5) return wk + 'w ago';
  const mo = Math.floor(day / 30);
  if (mo < 12) return mo + 'mo ago';
  return Math.floor(day / 365) + 'y ago';
}

function formatUptime(raw) {
  if (!raw || raw === 'N/A') return '';
  const parts = raw.split('-');
  let days = 0, time = parts[parts.length - 1];
  if (parts.length > 1) days = parseInt(parts[0]);
  const timeParts = time.split(':');
  let h = 0, m = 0, s = 0;
  if (timeParts.length === 3) {
    h = parseInt(timeParts[0]); m = parseInt(timeParts[1]); s = parseInt(timeParts[2]);
  } else if (timeParts.length === 2) {
    m = parseInt(timeParts[0]); s = parseInt(timeParts[1]);
  }
  const segs = [];
  if (days > 0) segs.push(days + 'd');
  if (h > 0) segs.push(h + 'h');
  if (m > 0) segs.push(m + 'm');
  if (s > 0 && days === 0 && h === 0) segs.push(s + 's');
  return segs.join(' ') || raw;
}

// ── A-Z NAMES ──
const DEFAULT_NAMES = {
  A:{name:'Alice',gender:'F'}, B:{name:'Bob',gender:'M'}, C:{name:'Chloe',gender:'F'},
  D:{name:'David',gender:'M'}, E:{name:'Emma',gender:'F'}, F:{name:'Frank',gender:'M'},
  G:{name:'Grace',gender:'F'}, H:{name:'Henry',gender:'M'}, I:{name:'Ivy',gender:'F'},
  J:{name:'Jack',gender:'M'}, K:{name:'Kate',gender:'F'}, L:{name:'Liam',gender:'M'},
  M:{name:'Mia',gender:'F'}, N:{name:'Noah',gender:'M'}, O:{name:'Olivia',gender:'F'},
  P:{name:'Paul',gender:'M'}, Q:{name:'Quinn',gender:'F'}, R:{name:'Ryan',gender:'M'},
  S:{name:'Sarah',gender:'F'}, T:{name:'Tom',gender:'M'}, U:{name:'Uma',gender:'F'},
  V:{name:'Victor',gender:'M'}, W:{name:'Wendy',gender:'F'}, X:{name:'Xavier',gender:'M'},
  Y:{name:'Yara',gender:'F'}, Z:{name:'Zack',gender:'M'}
};
const NAMES_LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

function getNamesConfig() {
  try { return JSON.parse(localStorage.getItem('dashboard_names')) || DEFAULT_NAMES; } catch { return DEFAULT_NAMES; }
}

function saveNamesConfig(cfg) {
  localStorage.setItem('dashboard_names', JSON.stringify(cfg));
}

function getMappedName(pid, fallback) {
  const cfg = getNamesConfig();
  const idx = Math.abs((pid || 0) * 7 + 13) % 26;
  const entry = cfg[NAMES_LETTERS[idx]];
  return entry ? entry.name : fallback;
}

function getRandomName() {
  const cfg = getNamesConfig();
  const letters = Object.keys(cfg);
  if (letters.length === 0) return 'Staff';
  const entry = cfg[letters[Math.floor(Math.random() * letters.length)]];
  return entry ? entry.name : 'Staff';
}

function getWorkerGender(pid, sessionTitle) {
  // Check if this worker is a Super Staff agent
  if (sessionTitle) {
    const staff = global.superStaffCache.find(s => s.name === sessionTitle || sessionTitle.includes(s.name));
    if (staff) return staff.gender === 'female' ? 'F' : 'M';
  }
  // Fall back to name-based gender
  const cfg = getNamesConfig();
  const idx = Math.abs((pid || 0) * 7 + 13) % 26;
  const entry = cfg[NAMES_LETTERS[idx]];
  return entry ? entry.gender : 'M';
}

function switchContentTab(tab) {
  document.querySelectorAll('.content-tab').forEach(t => t.classList.toggle('active', t.dataset.panel === tab));
  document.querySelectorAll('.content-panel').forEach(p => p.classList.toggle('active', p.id === 'panel-' + tab));
}

var _lastMainPid = 0;
window._restSlotNames = window._restSlotNames || {};
window._discussNames = window._discussNames || {};

function renderDashboard(data) {
  if (!data) return;

  const _usedNames = new Set();

  function _claimName() {
    const cfg = getNamesConfig();
    const pool = Object.values(cfg).map(e => e.name).filter(n => n);
    const avail = pool.filter(n => !_usedNames.has(n));
    if (avail.length === 0) return pool[Math.floor(Math.random() * pool.length)] || 'Staff';
    const name = avail[Math.floor(Math.random() * avail.length)];
    _usedNames.add(name);
    return name;
  }

  const s = data.summary;

  // Detect engine restart — PID changed since last render
  if (_lastMainPid && s.main_pid && _lastMainPid !== s.main_pid) {
    console.log('Engine restart detected: PID', _lastMainPid, '->', s.main_pid);
    showToast('OpenCode engine restarted \u2014 refreshing...', 'info');
    _lastMainPid = s.main_pid;
    setTimeout(function() { location.reload(); }, 1500);
  }
  if (!_lastMainPid && s.main_pid) {
    _lastMainPid = s.main_pid;
  }

  if (s.boss_name) { global._serverBossName = s.boss_name; }
  document.getElementById('lastUpdated').textContent = formatTime(data.timestamp);
  document.getElementById('staffCount').textContent = s.cpu_core_count || '?';
  document.getElementById('sessionCount').textContent = (data.sessions || []).length;
  document.getElementById('cpuTotal').textContent = s.total_cpu_str || '0%';
  document.getElementById('memTotal').textContent = (s.total_mem_mb || 0) + 'MB';
  document.getElementById('activeTasks').textContent = s.active_task_count || 0;
  const loadPct = Math.min(s.cpu_load_pct || 0, 100);
  document.getElementById('cpuLoad').textContent = loadPct;
  document.getElementById('loadBar').style.width = loadPct + '%';
  document.getElementById('totalCost').textContent = '$' + (s.total_cost || 0).toFixed(4);

  const cpuCount = (navigator.hardwareConcurrency || 8);
  const cpuPct = Math.min(parseFloat(s.total_cpu || 0) / cpuCount * 100, 100);
  document.getElementById('cpuRow').textContent = s.total_cpu_str || '0%';
  document.getElementById('cpuBar').style.width = cpuPct + '%';

  const memTotalGb = parseFloat(s.mem_total_gb) || 0;
  const memUsedGb = parseFloat(s.total_mem_mb || 0) / 1024;
  const memPct = memTotalGb > 0 ? Math.round(memUsedGb / memTotalGb * 100) : 0;
  document.getElementById('memRow').textContent = (s.total_mem_mb || 0) + ' / ' + (memTotalGb * 1024).toFixed(0) + ' MB';
  document.getElementById('memBar').style.width = memPct + '%';

  document.getElementById('diskRow').textContent = s.disk_free + ' / ' + s.disk_total;
  function _parseSize(str) {
    const m = String(str).match(/^([\d.]+)\s*([KMGTP]?)/i);
    if (!m) return null;
    const units = {K: 1, M: 2, G: 3, T: 4, P: 5};
    return parseFloat(m[1]) * Math.pow(1024, units[m[2].toUpperCase()] || 0);
  }
  const _freeB = _parseSize(s.disk_free), _totalB = _parseSize(s.disk_total);
  const diskPct = (_freeB && _totalB && _totalB > 0) ? Math.round((1 - _freeB / _totalB) * 100) : 50;
  document.getElementById('diskBar').style.width = Math.min(diskPct, 100) + '%';

  const uptimeContainer = document.getElementById('uptimeRowContainer');
  const uptimeFmt = formatUptime(s.uptime);
  if (uptimeFmt) {
    document.getElementById('uptimeRow').textContent = uptimeFmt;
    uptimeContainer.style.display = '';
  } else {
    uptimeContainer.style.display = 'none';
  }

  const dot = document.getElementById('statusDot');
  dot.className = 'status-dot ' + (s.agent_count > 0 ? 'online' : 'offline');

  const currentSessions = data.sessions || [];
  function tryNotify(title, options) {
    if (!('Notification' in window) || Notification.permission !== 'granted') return;
    try { new Notification(title, options); } catch (_) {}
  }
  if (prevSessions.length > 0) {
    const prevMap = {};
    prevSessions.forEach(ps => { prevMap[ps.id] = ps; });
    currentSessions.forEach(cs => {
      const prev = prevMap[cs.id];
      if (prev && prev.state !== cs.state) {
        tryNotify('Case updated', {
          body: (cs.title || '?') + ' · ' + (prev.state || 'active') + ' → ' + (cs.state || 'active'),
          silent: true
        });
      } else if (!prev && cs.state === 'complete') {
        tryNotify('Case completed', { body: cs.title || '?', silent: true });
      } else if (!prev) {
        tryNotify('New case', { body: cs.title || '?', silent: true });
      }
    });
  }
  prevSessions = JSON.parse(JSON.stringify(currentSessions));

  const agents = data.agents || [];
  const agentMap = {};
  agents.forEach(a => { agentMap[a.pid] = a; });

  const SKIP_NAMES = ['find', 'sort', 'head', 'du', 'ps', 'sleep', 'cat', 'curl', 'wc', 'mkdir', 'touch', 'rm', 'mv', 'cp', 'zsh', 'bash', 'sh', 'rg', 'grep', 'awk', 'sed', 'echo', 'printf'];
  function isRealAgent(a) { return !SKIP_NAMES.includes((a.name||'').toLowerCase()); }

  const STATE_STYLE = {
    'thinking': { color: '#d29922', label: 'Thinking', dot: 'pulse', icon: '\u{1F4AD}' },
    'running-tools': { color: '#58a6ff', label: 'Running Tools', dot: 'pulse', icon: '\u26A1' },
    'complete': { color: '#3fb950', label: 'Complete', dot: 'static', icon: '\u2713' },
    'error': { color: '#f85149', label: 'Error', dot: 'static', icon: '\u2717' },
    'unknown': { color: '#8b949e', label: 'Unknown', dot: 'static', icon: '?' },
    '': { color: '#8b949e', label: 'In Progress', dot: 'pulse', icon: '\u25CF' },
  };

  // ── BRANDON SECTION ──
  const rootId = data.tree_root;
  const brandon = rootId ? agentMap[rootId] : null;
  const brandonSection = document.getElementById('brandonSection');

  if (brandon) {
    brandonSection.innerHTML = `
      <div class="node-card full-width">
        <div class="card-header">
          <div class="avatar engine">${TYPE_ICONS.engine || '?'}</div>
          <div class="info">
            <div class="name">${getBossName()}</div>
            <div class="meta">NodeService Engine · PID ${brandon.pid} · ${formatUptime(s.uptime) || 'N/A'}</div>
          </div>
          <div class="type-badge engine">boss</div>
          ${getAuth() ? '<button class="manage-btn" onclick="openNewSessionModal()">+ New Case</button>' : ''}
          <button class="manage-btn" onclick="openLoginModal()" ${getAuth() ? 'style="margin-left:6px"' : ''}>Manage</button>
        </div>
        <div class="card-body" style="display:flex;gap:12px;align-items:center">
          ${global.profilePhoto ? '<div class="boss-photo"><img src="' + global.profilePhoto + '" alt="Profile"></div>' : ''}
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;flex:1">
            <div class="item"><div class="v">${brandon.cpu || '0'}%</div><div class="l">CPU</div></div>
            <div class="item"><div class="v">${brandon.mem_mb || '0'} MB</div><div class="l">Memory</div></div>
            <div class="item"><div class="v">${s.cpu_core_count || '?'}</div><div class="l">Staff</div></div>
          </div>
        </div>
      </div>
    `;
  } else {
    brandonSection.innerHTML = '';
  }

  // ── OFFICE FLOOR ──
  function getDeskNumber(pid) {
    return ((pid * 7 + 13) % 1000 + 1000) % 1000; // 0-999
  }

  // Collect all workers (real + virtual)
  let allWorkers = [];
  (data.sessions || []).forEach(s => {
    // Real agents assigned to this session
    (s.agents || []).forEach(w => {
      allWorkers.push({
        name: w.name, pid: w.pid, cpu: w.cpu, mem_mb: w.mem_mb,
        ppid: w.ppid, command: w.command || '',
        sessionTitle: s.title, sessionState: s.state || '',
        sessionMode: s.last_mode || '', sessionUpdated: s.updated || 0
      });
    });
  });
  (data.standalone || []).forEach(w => {
    allWorkers.push({
      name: w.name, pid: w.pid, cpu: w.cpu, mem_mb: w.mem_mb,
      ppid: w.ppid || w.parent, command: '',
      sessionTitle: '(standalone)', sessionState: '', sessionMode: '',
      sessionUpdated: 0, standalone: true
    });
  });
  // Virtual workers: sessions with no real agents (conversations inside Brandon)
  const now = Date.now();
  (data.sessions || []).forEach(s => {
    if (!s.agents || s.agents.length === 0) {
      const isComplete = s.state === 'complete';
      const age = s.updated ? (now - s.updated) / 60000 : 0;
      if (isComplete && age > 1) return;

      const virtPid = -Math.abs(s.id ? s.id.split('').reduce((a,c)=>a*31+c.charCodeAt(0),0) % 99999 : Date.now());
      const wData = {
        name: '(virtual)', pid: virtPid, cpu: 0, mem_mb: 0,
        ppid: 14138, command: '',
        sessionTitle: s.title, sessionState: s.state || '',
        sessionMode: s.last_mode || '', sessionUpdated: s.updated || 0,
        virtual: true
      };
      if (s.assigned_staff) {
        wData.superStaff = s.assigned_staff;
        wData.name = s.assigned_staff;
        wData.staffGender = s.staff_gender || 'male';
        wData.staffMode = s.staff_mode || '';
        wData.staffModel = s.staff_model || '';
      }
      allWorkers.push(wData);
    }
  });

  // Collapse duplicate super-staff into one desk entry with a case count
  const staffCounts = {};
  allWorkers.forEach(w => { if (w.superStaff) staffCounts[w.superStaff] = (staffCounts[w.superStaff] || 0) + 1; });
  const seenStaff = new Set();
  allWorkers = allWorkers.filter(w => {
    if (!w.superStaff) return true;
    if (seenStaff.has(w.superStaff)) return false;
    seenStaff.add(w.superStaff);
    return true;
  });
  allWorkers.forEach(w => { if (w.superStaff) w.caseCount = staffCounts[w.superStaff]; });

  // Fill remaining staff slots with placeholder workers so count matches cpu cores
  const totalStaff = s.cpu_core_count || 10;
  const placeholderBase = -999999;
  while (allWorkers.length < totalStaff) {
    const pid = placeholderBase - allWorkers.length;
    allWorkers.push({
      name: '', pid: pid, cpu: 0, mem_mb: 0,
      ppid: 0, command: '',
      sessionTitle: '', sessionState: '', sessionMode: '',
      sessionUpdated: 0, placeholder: true
    });
  }

  // Pre-populate _usedNames with Super Staff names so _claimName() never uses them
  allWorkers.filter(w => w.superStaff).forEach(w => _usedNames.add(w.superStaff));

  // Assign real workers + super-staff virtuals to 6 office desks.
  const officeDeskCount = 6;
  const desks = new Array(officeDeskCount).fill(null);
  const deskTaken = new Set();
  allWorkers.filter(w => w.superStaff || (!w.virtual && !w.placeholder)).forEach(w => {
    let idx = getDeskNumber(w.pid);
    for (let attempt = 0; attempt < officeDeskCount; attempt++) {
      if (!deskTaken.has((idx + attempt) % officeDeskCount)) {
        idx = (idx + attempt) % officeDeskCount;
        break;
      }
    }
    if (!deskTaken.has(idx)) {
      desks[idx] = w;
      deskTaken.add(idx);
    }
  });

  const deskPids = new Set(desks.filter(d => d).map(d => d.pid));

  // Split virtual workers: discussing (thinking/running-tools) vs resting, deduplicated by session
  const virtuals = allWorkers.filter(w => w.virtual && !deskPids.has(w.pid));
  const seenDiscuss = new Set();
  const discussingPool = [];
  const restingVirtuals = [];
  const seenRest = new Set();
  virtuals.forEach(w => {
    const isDiscuss = w.sessionState === 'thinking' || w.sessionState === 'running-tools';
    const seen = isDiscuss ? seenDiscuss : seenRest;
    if (!w.sessionTitle || seen.has(w.sessionTitle)) return;
    seen.add(w.sessionTitle);
    if (isDiscuss) discussingPool.push(w);
    else restingVirtuals.push(w);
  });

  // Assign up to 3 discussing agents to discussion room slots
  const DISCUSS_SLOTS = 3;
  const discussSlots = new Array(DISCUSS_SLOTS).fill(null);
  const sortedDiscussing = [...discussingPool].sort((a, b) => a.pid - b.pid);
  sortedDiscussing.forEach((w, i) => {
    if (i < DISCUSS_SLOTS) discussSlots[i] = w;
  });
  const overflowDiscussing = sortedDiscussing.slice(DISCUSS_SLOTS);

  const restingPool = [...restingVirtuals, ...overflowDiscussing, ...allWorkers.filter(w => w.placeholder || (!w.virtual && !deskPids.has(w.pid)))];

  const officeFloor = document.getElementById('officeFloor');
  officeFloor.innerHTML = '';
  const occupied = deskTaken.size;
  const discussFilled = discussSlots.filter(Boolean).length;
  document.getElementById('staffLabel').textContent = `${occupied} working · ${discussFilled} discussing · ${restingPool.length} relaxing`;

  desks.forEach((worker, idx) => {
    const deskNum = idx + 1;
    const isOccupied = worker !== null;
    let isActive = false, stateStyle, agoStr = '', sessionLabel = '', isVirt = false;

    if (isOccupied) {
      isActive = worker.sessionState === 'thinking' || worker.sessionState === 'running-tools';
      stateStyle = STATE_STYLE[worker.sessionState] || STATE_STYLE[''];
      agoStr = humanAgo(worker.sessionUpdated);
      sessionLabel = worker.superStaff && worker.caseCount > 1
        ? 'Working on #' + worker.caseCount + ' cases.'
        : (worker.sessionTitle || '(standalone)');
      isVirt = worker.virtual;
      if (worker.superStaff) _usedNames.add(worker.superStaff);
      else _usedNames.add(getMappedName(worker.pid, worker.name));
    }

    let deskName = 'Vacant';
    let deskGif = 'assets/working-desk-empty.png';
    if (isOccupied) {
      if (worker.superStaff) deskName = worker.superStaff;
      else if (isVirt) deskName = _claimName();
      else deskName = getMappedName(worker.pid, worker.name);
      const deskGender = worker.superStaff ? (worker.staffGender === 'female' ? 'F' : 'M') : getWorkerGender(worker.pid, worker.sessionTitle);
      deskGif = deskGender === 'F' ? 'assets/working-staff-loop-female.gif' : 'assets/working-staff-loop.gif';
    }
    const card = document.createElement('div');
    card.className = 'desk-card' + (isOccupied ? ' occupied' : ' vacant');
    card.innerHTML = `
      <div class="desk-number">#${deskNum}</div>
      ${isOccupied ? `<div class="desk-active-dot ${isActive ? 'active' : 'idle'}"></div>` : ''}
      <div class="desk-avatar ${isOccupied ? 'occupied' : 'vacant'}"><img src="${deskGif}" class="desk-img" alt=""></div>
      <div class="desk-name">${deskName}</div>
      ${isOccupied ? `
        <div class="desk-session" style="background:${stateStyle.color}22;color:${stateStyle.color}">${worker.superStaff ? sessionLabel : (isVirt ? (isActive ? '\u{1F4AD}' : '\u2713') + ' ' + stateStyle.label : sessionLabel.length > 20 ? sessionLabel.slice(0,18)+'...' : sessionLabel)}</div>
        <div class="desk-stats">
          ${isVirt ? (worker.superStaff && worker.staffMode ? `<span style="font-size:9px;padding:1px 6px;border-radius:3px;background:${worker.staffMode === 'plan' ? '#bc8cff33' : '#58a6ff33'};color:${worker.staffMode === 'plan' ? '#bc8cff' : '#58a6ff'}">${worker.staffMode}</span>` : '<span>virtual</span>') : `<span>CPU ${worker.cpu || 0}%</span>`}
          <span>${isVirt ? 'conversation' : 'MEM ' + (worker.mem_mb || 0) + 'MB'}</span>
          <span>${agoStr}</span>
        </div>
      ` : '<div style="font-size:9px;color:var(--text-dim);margin-top:4px">Empty desk</div>'}
    `;
    officeFloor.appendChild(card);
  });

  // ── DISCUSSION ROOM ──
  const discussionDesk = document.getElementById('discussionDesk');
  const discussionLabel = document.getElementById('discussionLabel');
  discussionDesk.innerHTML = '';

  discussionLabel.innerHTML = discussFilled > 0
    ? '💬 Discussion Room <span class="count">(' + discussFilled + ' staff)</span>'
    : '💬 Discussion Room <span class="count">(vacant)</span>';

  discussSlots.forEach((worker, idx) => {
    const slotNum = idx + 1;
    const isOccupied = worker !== null;
    const card = document.createElement('div');
    card.className = 'discuss-slot' + (isOccupied ? ' occupied' : ' vacant');

    if (isOccupied) {
      let name = worker.superStaff || window._discussNames[worker.pid] || (window._discussNames[worker.pid] = _claimName());
      const stateStyle = STATE_STYLE[worker.sessionState] || STATE_STYLE[''];
      if (worker.superStaff) _usedNames.add(worker.superStaff);
      else _usedNames.add(getMappedName(worker.pid, worker.name));
      card.innerHTML = `
        <div class="slot-number">#${slotNum}</div>
        <div class="slot-active-dot"></div>
        <div class="slot-avatar occupied"><img src="assets/discuss-group-loop.gif" class="slot-img" alt="discussing"></div>
        <div class="slot-name">${name}</div>
        <div class="slot-session" style="background:${stateStyle.color}22;color:${stateStyle.color}">${escapeHtml(worker.sessionTitle || '')}</div>
        <div class="slot-stats">
          <span style="color:${stateStyle.color}">${stateStyle.label}</span>
          <span>${humanAgo(worker.sessionUpdated)}</span>
        </div>
      `;
    } else {
      card.innerHTML = `
        <div class="slot-number">#${slotNum}</div>
        <div class="slot-avatar vacant"><img src="assets/discuss-empty.png" class="slot-img vacant" alt="vacant"></div>
        <div class="slot-name" style="color:var(--text-dim)">Vacant</div>
      `;
    }
    discussionDesk.appendChild(card);
  });

  // ── REST ROOM ──
  const restRoomImages = {
    'power nap': {
      'power nap': 'sleeping-power-nap.png',
      'snoring softly': 'sleeping-snoring-softly.png',
      'dreaming big': 'sleeping-dreaming-big.png',
      'waking up': 'sleeping-waking-up.png',
    },
    gaming: {
      'gaming': 'gaming-gaming.png',
      'winning!': 'gaming-winning.png',
      'rage quitting': 'gaming-rage-quiting.png',
      'leveling up': 'gaming-leveling-up.png',
    },
    'sipping coffee': {
      'sipping coffee': 'coffee-sipping.png',
      'stirring sugar': 'coffee-stirring-sugar.png',
      'refilling cup': 'coffee-refilling-cup.png',
      'blowing on steam': 'coffee-blowing-on-steam.png',
    },
    'scrolling phone': {
      'scrolling': 'phone-scrolling.png',
      'laughing at memes': 'phone-laugh.png',
      'typing reply': 'phone-typing.png',
      'double-tapping': 'phone-tapping.png',
    },
    'reading news': {
      'reading news': 'news-reading.png',
      'shocking headline!': 'news-shocking.png',
      'scrolling feed': 'news-scrolling.png',
      'saving article': 'news-saving.png',
    },
    snacking: {
      'snacking': 'snacking-idle.png',
      'grabbing more': 'snacking-more.png',
      'crunching loudly': 'snacking-loudly.png',
      'sharing snacks': 'snacking-share.png',
    },
    'listening to music': {
      'listening': 'listening-music.png',
      'humming along': 'listening-humming.png',
      'air drumming': 'listening-air-drumming.png',
      'changing song': 'listening-changing-song.png',
    },
    meditating: {
      'meditating': 'meditating-idle.png',
      'deep breaths': 'meditating-deep-breath.png',
      'finding zen': 'meditating-finding-zen.png',
      'stretching': 'meditating-stretching.png',
    },
    'playing darts': {
      'playing darts': 'darts-playing.png',
      'bullseye!': 'darts-bull-eye.png',
      'close miss': 'darts-miss.png',
      'retrieving darts': 'darts-retrieving.png',
    },
    'watering plants': {
      'watering plants': 'plants-watering.png',
      'pruning leaves': 'plants-pruning.png',
      'repotting': 'plants-replotting.png',
      'admiring growth': 'plants-admiring-growth.png',
    },
    'reading a book': {
      'reading': 'reading-idle.png',
      'page turner!': 'reading-page-turner.png',
      'dog-earing page': 'reading-dog-earing.png',
      'checking chapter count': 'reading-chapter-count.png',
    },
    puzzling: {
      'solving': 'puzzle-solving.png',
      'almost there': 'puzzle-almost-there.png',
      'finding a piece': 'puzzle-finding-a-piece.png',
      'completing the picture': 'puzzle-completed.png',
    },
  };
  const restRoomLayout = [
    { emoji: '🛌', label: 'power nap', states: ['power nap', 'snoring softly', 'dreaming big', 'waking up'] },
    { emoji: '🎮', label: 'gaming', states: ['gaming', 'winning!', 'rage quitting', 'leveling up'] },
    { emoji: '☕', label: 'sipping coffee', states: ['sipping coffee', 'stirring sugar', 'refilling cup', 'blowing on steam'] },
    { emoji: '📱', label: 'scrolling phone', states: ['scrolling', 'laughing at memes', 'typing reply', 'double-tapping'] },
    { emoji: '📰', label: 'reading news', states: ['reading news', 'shocking headline!', 'scrolling feed', 'saving article'] },
    { emoji: '🍿', label: 'snacking', states: ['snacking', 'grabbing more', 'crunching loudly', 'sharing snacks'] },
    { emoji: '🎵', label: 'listening to music', states: ['listening', 'humming along', 'air drumming', 'changing song'] },
    { emoji: '🧘', label: 'meditating', states: ['meditating', 'deep breaths', 'finding zen', 'stretching'] },
    { emoji: '🎯', label: 'playing darts', states: ['playing darts', 'bullseye!', 'close miss', 'retrieving darts'] },
    { emoji: '🌿', label: 'watering plants', states: ['watering plants', 'pruning leaves', 'repotting', 'admiring growth'] },
    { emoji: '🧩', label: 'puzzling', states: ['solving', 'almost there', 'finding a piece', 'completing the picture'] },
    { emoji: '📖', label: 'reading a book', states: ['reading', 'page turner!', 'dog-earing page', 'checking chapter count'] },
  ];

  const restGrid = document.getElementById('restRoomGrid');
  const restLabel = document.getElementById('restRoomLabel');
  restGrid.innerHTML = '';

  // Chaotic rest room assignment with epoch-shuffled slots
  const restEpoch = Math.floor(Date.now() / 30000);
  function _restHash(pid, mod) {
    let h = Math.abs(pid) + restEpoch * 48271;
    h = ((h >> 16) ^ h) * 0x45d9f3b;
    h = ((h >> 16) ^ h) * 0x45d9f3b;
    h = (h >> 16) ^ h;
    return Math.abs(h) % mod;
  }
  const shuffled = [...restingPool];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  const assigned = {};
  shuffled.forEach(w => {
    const slotIdx = _restHash(w.pid, restRoomLayout.length);
    // Linear probe if slot taken
    for (let attempt = 0; attempt < restRoomLayout.length; attempt++) {
      const candidate = (slotIdx + attempt) % restRoomLayout.length;
      if (!assigned[candidate]) {
        assigned[candidate] = w;
        break;
      }
    }
  });

  const occupiedRestCount = Object.keys(assigned).length;
  restLabel.style.display = 'block';
  restLabel.innerHTML = '☕ Rest Room <span class="count">(' + occupiedRestCount + ' resting)</span>';

  const stateCycleMs = 2000;
  restRoomLayout.forEach((layout, idx) => {
    const worker = assigned[idx] || null;
    const stateLen = (layout.states || [layout.label]).length;
    const stateIdx = Math.floor(Date.now() / stateCycleMs) % stateLen;
    const currentLabel = (layout.states || [layout.label])[stateIdx];
    const card = document.createElement('div');
    card.className = 'rest-card';
    const imgFile = restRoomImages[layout.label] ? restRoomImages[layout.label][currentLabel] : null;
    if (worker) {
      // Use Super Staff name if assigned, otherwise claim a unique name
      if (worker.superStaff) {
        window._restSlotNames[idx] = worker.superStaff;
      } else {
        if (stateIdx === 0) delete window._restSlotNames[idx];
        if (!window._restSlotNames[idx]) window._restSlotNames[idx] = _claimName();
      }
      card.innerHTML = `
        ${imgFile ? `<img src="assets/rest-room/${imgFile}" class="rc-img" alt="${currentLabel}">` : `<div class="rc-emoji">${layout.emoji}</div>`}
        <div class="rc-desk">${window._restSlotNames[idx]}</div>
        <div class="rc-label">${currentLabel}${worker.virtual ? ' (virtual)' : ''}</div>
      `;
    } else {
      card.style.opacity = '0.4';
      card.innerHTML = `
        ${imgFile ? `<img src="assets/rest-room/${imgFile}" class="rc-img" alt="${currentLabel}" style="opacity:0.4">` : `<div class="rc-emoji">${layout.emoji}</div>`}
        <div class="rc-label" style="color:var(--text-dim)">${currentLabel}</div>
      `;
    }
    restGrid.appendChild(card);
  });

  // ── SESSIONS GRID ──
  const sessions = data.sessions || [];
  const grid = document.getElementById('sessionsGrid');
  grid.innerHTML = '';

  document.getElementById('sessionsLabel').style.display = sessions.length > 0 ? 'block' : 'none';
  document.getElementById('sessionsCount').textContent = sessions.length > 0 ? '(' + sessions.length + ')' : '';

  if (sessions.length === 0) {
    grid.innerHTML = '<div class="empty-state"><div class="icon">📋</div><div class="text">No Cases working on at the moment</div></div>';
  }

  // Build staff assignment lookup from all_sessions
  const staffMap = {};
  (data.all_sessions || []).forEach(s => {
    if (s.assigned_staff) staffMap[s.id] = s.assigned_staff;
  });

  const loggedIn = !!getAuth();

  sessions.forEach(ss => {
    const state = STATE_STYLE[ss.state] || STATE_STYLE[''];
    const agoStr = humanAgo(ss.updated);
    const scId = 'sc-' + ss.id.replace(/[^a-zA-Z0-9]/g, '');
    const previewId = 'prev-' + ss.id.replace(/[^a-zA-Z0-9]/g, '');
    const agents = ss.agents || [];

    let agentChips = '';
    agents.forEach(a => {
      agentChips += `<span class="sc-agent-chip">${getMappedName(a.pid, a.name)} (PID ${a.pid}) · ${a.cpu}% · ${a.mem_mb}MB</span>`;
    });

    let toolInfo = ss.tool_name ? `<span style="font-size:9px;color:var(--blue);margin-top:2px">\u2699 ${ss.tool_name}</span>` : '';
    let costInfo = (ss.cost || ss.tokens) ? `$${(ss.cost||0).toFixed(4)} · ${(ss.tokens||0).toLocaleString()} tokens` : '';
    let fileInfo = ss.files_changed ? `${ss.files_changed} files changed` : '';
    let dirInfo = ss.directory || '';

    const card = document.createElement('div');
    card.className = 'session-card state-' + (ss.state || '');
    card.dataset.sid = ss.id;
    card.innerHTML = `
      <div class="sc-header">
        <div class="sc-icon ${ss.state || ''}">${state.icon}</div>
        <div style="flex:1;min-width:0">
          <div class="sc-title">${escapeHtml(ss.title || '?')}</div>
          <div class="sc-meta">${ss.slug ? escapeHtml(ss.slug) + ' · ' : ''}${ss.last_mode ? `<span style="font-size:9px;padding:1px 5px;border-radius:3px;font-weight:500;background:${ss.last_mode === 'plan' ? '#bc8cff33' : '#58a6ff33'};color:${ss.last_mode === 'plan' ? '#bc8cff' : '#58a6ff'}">${ss.last_mode}</span> ` : ''}${staffMap[ss.id] ? `<span style="font-size:9px;padding:1px 5px;border-radius:3px;font-weight:500;background:#2ea04322;color:#3fb950">${escapeHtml(staffMap[ss.id])}</span> ` : ''}${escapeHtml(ss.agent_type || '')} ${ss.model_id ? '· ' + escapeHtml(ss.model_id) : ''}</div>
        </div>
      </div>
      ${ss.last_user_prompt ? `<div style="margin-top:4px;padding:4px 6px;background:#58a6ff11;border-left:2px solid var(--blue);border-radius:4px;font-size:10px;color:var(--blue);white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="${escapeHtml(ss.last_user_prompt).replace(/"/g,'&quot;')}">${escapeHtml(ss.last_user_prompt.slice(0,60))}${ss.last_user_prompt.length > 60 ? '...' : ''}</div>` : ''}
      ${ss.last_text ? `
        <div class="sc-text-preview" onclick="toggleDisplay('${previewId}')">${escapeHtml(ss.last_text.slice(0,80))}${ss.last_text.length > 80 ? '...' : ''}</div>
        <div class="sc-text-expanded" id="${previewId}">${renderMarkdown(ss.last_text)}</div>
      ` : ''}
      ${toolInfo}
      <div style="display:flex;gap:6px;margin-top:4px;font-size:10px;color:var(--text-dim)">
        <span>${agoStr} ago</span>
        ${dirInfo ? `<span>${escapeHtml(dirInfo.split('/').pop() || dirInfo)}</span>` : ''}
      </div>
      ${agentChips ? `<div class="sc-agent-bar">${agentChips}</div>` : ''}
      <div style="margin-top:4px;padding-top:4px;border-top:1px solid var(--border)">
        <div style="font-size:9px;color:var(--text-dim);display:flex;gap:6px;flex-wrap:wrap">
          ${costInfo ? `<span>${costInfo}</span>` : ''}
          ${fileInfo ? `<span>${fileInfo}</span>` : ''}
          ${ss.agent_type ? `<span>${ss.agent_type}</span>` : ''}
          ${ss.model_id ? `<span>${ss.model_id}</span>` : ''}
        </div>
      </div>
      <div style="display:flex;gap:6px;align-items:center;margin-top:6px;padding-top:4px;border-top:1px solid var(--border)">
        <div class="sc-state-badge ${ss.state || '\\30'}" style="margin-right:auto">${state.label}</div>
        ${loggedIn && ss.state !== 'thinking' && ss.state !== 'running-tools' ? `<button class="comment-btn" onclick="event.stopPropagation();continueSession('${ss.id}')" title="Quick instruction">\u{1F4AC}</button>` : ''}
        <button class="sc-copy-id" onclick="event.stopPropagation();navigator.clipboard.writeText('${ss.id}').then(function(){showToast('Session ID copied','success')}).catch(function(){})" title="Copy Session ID" style="background:none;border:none;cursor:pointer;font-size:11px;padding:0 2px;color:var(--text-dim);line-height:1">📋</button>
        ${(ss.todos || []).filter(function(t){ return t.status !== 'completed'; }).length > 0 ? `<span style="color:var(--yellow);font-size:11px">\uD83D\uDCCB ${(ss.todos || []).filter(function(t){ return t.status !== 'completed'; }).length}</span>` : ''}
        ${(ss.pending_permissions || []).length > 0 ? `<span style="color:var(--yellow);cursor:pointer;font-size:11px" onclick="showQuestions('${ss.id}')" title="Permission required">\u{1F512} ${(ss.pending_permissions || []).length}</span>` : ''}
        ${(ss.pending_questions || []).length > 0 ? ((ss.pending_questions || []).filter(function(q){ return !q.answered; }).length > 0 ? `<span style="color:var(--yellow);cursor:pointer;font-size:11px" onclick="showQuestions('${ss.id}')">\u2753 ${(ss.pending_questions || []).filter(function(q){ return !q.answered; }).length}</span>` : `<span style="color:var(--green);cursor:pointer;font-size:11px" onclick="showQuestions('${ss.id}')">\u2713</span>`) : ''}
        <div class="sc-status-dot ${ss.state || '\\30'}"></div>
      </div>
    `;
    // Restore expanded text preview after render
    if (expandedTexts.has(previewId)) {
      const prevEl = document.getElementById(previewId);
      if (prevEl) prevEl.style.display = 'block';
    }
    grid.appendChild(card);
  });

  // Cases list (only active sessions)
  const sl = document.getElementById('sessionList');
  sl.innerHTML = '';
  const allCases = data.sessions || [];
  const activeCases = allCases.filter(s => s.active);
  if (activeCases.length === 0) {
    sl.innerHTML = '<div style="font-size:11px;color:var(--text-dim)">No active cases</div>';
  } else {
    // State badge styling
    const STATE_STYLE = {
      'thinking': { color: '#d29922', label: 'Thinking', dot: 'pulse' },
      'running-tools': { color: '#58a6ff', label: 'Running Tools', dot: 'pulse' },
      'complete': { color: '#3fb950', label: 'Complete', dot: 'static' },
      'error': { color: '#f85149', label: 'Error', dot: 'static' },
      'unknown': { color: '#8b949e', label: 'Unknown', dot: 'static' },
      '': { color: '#8b949e', label: 'In Progress', dot: 'pulse' },
    };

    activeCases.slice(0, 8).forEach(ss => {
      const div = document.createElement('div');
      div.style.cssText = 'font-size:11px;padding:6px 0;border-bottom:1px solid rgba(48,54,61,0.3)';

      const agoStr = humanAgo(ss.updated);

      const state = STATE_STYLE[ss.state] || STATE_STYLE[''];
      const slug = ss.slug ? ` · ${ss.slug}` : '';
      const cost = ss.cost ? ` · $${(ss.cost).toFixed(4)}` : '';
      const tokens = ss.tokens ? ` · ${ss.tokens.toLocaleString()} tokens` : '';

      const previewId = 'preview-' + ss.id.replace(/[^a-zA-Z0-9]/g, '');

      div.innerHTML = `
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:2px">
          <span class="status-dot" style="width:6px;height:6px;background:${state.color};animation:${state.dot === 'pulse' ? 'pulse 2s infinite' : 'none'};flex-shrink:0"></span>
          <span style="font-weight:500;font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(ss.title || '?')}</span>
        </div>
        <div style="display:flex;gap:4px;margin:2px 0 2px 12px;flex-wrap:wrap">
          <span style="font-size:9px;color:${state.color};background:${state.color}22;padding:1px 5px;border-radius:3px;font-weight:500">${state.label}</span>
          <span style="font-size:9px;color:var(--text-dim)">${agoStr} ago${slug}</span>
        </div>
        ${ss.last_text ? `<div style="font-size:9px;color:var(--text-dim);margin:2px 0 0 12px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" onclick="toggleDisplay('${previewId}')">${escapeHtml(ss.last_text.slice(0,60))}${ss.last_text.length > 60 ? '...' : ''}</div><div id="${previewId}" style="display:none;font-size:9px;color:var(--text-dim);margin:2px 0 0 12px;padding:4px;background:var(--surface2);border-radius:4px">${renderMarkdown(ss.last_text)}</div>` : ''}
        ${ss.tool_name ? `<div style="font-size:8px;color:var(--blue);margin:1px 0 0 12px">\u2699 ${escapeHtml(ss.tool_name)}</div>` : ''}
        ${cost || tokens ? `<div style="font-size:8px;color:var(--text-dim);margin:1px 0 0 12px">${cost}${tokens}</div>` : ''}
        <div style="display:flex;gap:4px;margin:2px 0 0 12px;flex-wrap:wrap;font-size:9px">
          ${(ss.pending_permissions || []).length > 0 ? `<span style="color:var(--yellow);cursor:pointer" onclick="showQuestions('${ss.id}')">🔒</span>` : ''}
          ${(ss.pending_questions || []).length > 0 ? ((ss.pending_questions || []).filter(function(q){ return !q.answered; }).length > 0 ? `<span style="color:var(--yellow);cursor:pointer" onclick="showQuestions('${ss.id}')">❓ ${(ss.pending_questions || []).filter(function(q){ return !q.answered; }).length}</span>` : `<span style="color:var(--green);cursor:pointer" onclick="showQuestions('${ss.id}')">✓</span>`) : ''}
        </div>
      `;
      sl.appendChild(div);
    });
  }

  // Activity log
  const log = document.getElementById('activityLog');
  log.innerHTML = '';
  const entries = data.activity_log || [];
  if (entries.length === 0) {
    log.innerHTML = '<div class="entry" style="color:var(--text-dim)">No activity yet</div>';
  } else {
    entries.slice().reverse().slice(0, 40).forEach(line => {
      const div = document.createElement('div');
      div.className = 'entry';

      const match = line.match(/^\[(\d{2}:\d{2}:\d{2})\]\s*(.*)/);
      if (match) {
        div.innerHTML = `<span class="time">${match[1]}</span>${match[2]}`;
      } else {
        div.textContent = line;
      }
      log.appendChild(div);
    });
  }

  // ── STANDALONE (Others panel) ──
  const standaloneGrid = document.getElementById('standaloneGrid');
  const standaloneCount = document.getElementById('standaloneCount');
  const emptyState = document.getElementById('emptyState');
  const standaloneList = data.standalone || [];
  standaloneGrid.innerHTML = '';
  if (standaloneList.length > 0) {
    emptyState.style.display = 'none';
    standaloneCount.textContent = '(' + standaloneList.length + ')';
    standaloneList.slice(0, 12).forEach(w => {
      const card = document.createElement('div');
      card.className = 'proc-card';
      card.innerHTML = `
        <div class="pc-icon">\u269B</div>
        <div class="pc-info">
          <div class="pc-name">${escapeHtml(getMappedName(w.pid, w.name || '?'))}</div>
          <div class="pc-meta">PID ${w.pid} · CPU ${w.cpu || 0}% · ${w.mem_mb || 0}MB · ${escapeHtml(w.elapsed || '?')}</div>
        </div>
      `;
      standaloneGrid.appendChild(card);
    });
  } else {
    emptyState.style.display = 'flex';
    standaloneCount.textContent = '(0)';
  }
}

global._polling = false;
async function poll() {
  if (global._polling) return;
  global._polling = true;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const resp = await fetch(STATUS_URL + '?_=' + Date.now());
      if (!resp.ok) throw new Error('Status ' + resp.status);
      const data = await resp.json();
      renderDashboard(data);
      global._polling = false;
      return;
    } catch (e) {
      if (attempt === 0) {
        await new Promise(r => setTimeout(r, 1000));
      } else {
        console.log('Poll failed:', e.message);
        showToast('Poll failed: ' + e.message, 'error');
      }
    }
  }
  global._polling = false;
}

function schedulePoll() {
  global._pollTimer = setTimeout(() => {
    poll().then(() => schedulePoll());
  }, global.POLL_INTERVAL);
}

// Request notification permission
if ('Notification' in window && Notification.permission === 'default') {
  Notification.requestPermission();
}

poll();
schedulePoll();

// Export functions used by onclick handlers
global.toggleDisplay = toggleDisplay;
global.switchContentTab = switchContentTab;

// Export functions/constants for second IIFE
global.humanAgo = humanAgo;
global.formatUptime = formatUptime;
global.getNamesConfig = getNamesConfig;
global.saveNamesConfig = saveNamesConfig;
global.DEFAULT_NAMES = DEFAULT_NAMES;
global.poll = poll;
global.schedulePoll = schedulePoll;
})(window);
