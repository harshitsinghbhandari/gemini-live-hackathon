let allEvents = [];
let filteredEvents = [];
let activeCategories = new Set();
let currentView = 'table';
let selectedRow = null;

const CATEGORY_COLORS = [
  '#7c6af7', '#3ecf8e', '#f5a623', '#4a9eff', '#f06060',
  '#2dd4bf', '#e879f9', '#fb923c', '#a3e635', '#38bdf8'
];
const catColorMap = {};
let colorIdx = 0;

function getCatColor(cat) {
  if (!catColorMap[cat]) {
    catColorMap[cat] = CATEGORY_COLORS[colorIdx % CATEGORY_COLORS.length];
    colorIdx++;
  }
  return catColorMap[cat];
}

// PARSE
function parseLog(text) {
  const lines = text.split('\n');
  const events = [];
  let idx = 0;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    // Format A (new): [category][label] +Xms (allow optional emoji prefix or leading text)
    const matchA = trimmed.match(/(?:⏱\s+)?\[([^\]]+)\]\[([^\]]+)\]\s+\+(\d+)ms/);
    if (matchA) {
      events.push({
        idx: idx++,
        type: 'checkpoint',
        traceId: null,
        category: matchA[1],
        label: matchA[2],
        delta: parseInt(matchA[3]),
        total: null,
        raw: trimmed
      });
      continue;
    }

    // Format B (old): [traceId][name] label +Xms (total: Xms)
    const matchB = trimmed.match(/^\[(\d{3})\]\[([^\]]+)\]\s+(.+?)\s+\+(\d+)ms\s+\(total:\s+(\d+)ms\)$/);
    if (matchB) {
      events.push({
        idx: idx++,
        type: 'checkpoint',
        traceId: matchB[1],
        category: matchB[2],
        label: matchB[3],
        delta: parseInt(matchB[4]),
        total: parseInt(matchB[5]),
        raw: trimmed
      });
      continue;
    }

    // START/END lines
    const matchStart = trimmed.match(/^\[(\d{3})\]\[([^\]]+)\]\s+START$/);
    const matchEnd = trimmed.match(/^\[(\d{3})\]\[([^\]]+)\]\s+END\s+total:\s+(\d+)ms$/);

    if (matchStart) {
      events.push({
        idx: idx++,
        type: 'start',
        traceId: matchStart[1],
        category: matchStart[2],
        label: 'START',
        delta: 0,
        total: 0,
        raw: trimmed
      });
    } else if (matchEnd) {
      events.push({
        idx: idx++,
        type: 'end',
        traceId: matchEnd[1],
        category: matchEnd[2],
        label: 'END',
        delta: parseInt(matchEnd[3]),
        total: parseInt(matchEnd[3]),
        raw: trimmed
      });
    }
  }
  return events;
}

function loadEvents(events) {
  allEvents = events;
  activeCategories = new Set(events.map(e => e.category));
  colorIdx = 0;
  Object.keys(catColorMap).forEach(k => delete catColorMap[k]);
  events.forEach(e => getCatColor(e.category));
  buildCategoryList();
  applyFilters();
  updateStats();
}

// CATEGORY LIST & TOGGLES
function buildCategoryList() {
  const cats = {};
  allEvents.forEach(e => {
    cats[e.category] = (cats[e.category] || 0) + 1;
  });

  const list = document.getElementById('categoryList');
  if (!list) return;
  list.innerHTML = '';

  const allSelected = Object.keys(cats).every(c => activeCategories.has(c));

  // "Show All" Toggle
  const allBtn = document.createElement('div');
  allBtn.className = `category-item ${allSelected ? 'active' : ''}`;
  allBtn.innerHTML = `
    <span class="category-name" style="font-weight:600">Show All</span>
    <span class="category-count">${allEvents.length}</span>
  `;
  allBtn.onclick = () => {
    Object.keys(cats).forEach(c => activeCategories.add(c));
    buildCategoryList();
    applyFilters();
  };
  list.appendChild(allBtn);

  // Individual Categories
  Object.entries(cats).sort((a, b) => b[1] - a[1]).forEach(([cat, count]) => {
    const color = getCatColor(cat);
    const isActive = activeCategories.has(cat) && !allSelected;
    const item = document.createElement('div');
    item.className = `category-item ${isActive ? 'active' : ''} category-clickable`;
    item.innerHTML = `
      <span class="category-dot" style="background:${color}"></span>
      <span class="category-name">${cat}</span>
      <span class="category-count">${count}</span>
    `;
    item.onclick = (e) => {
      // Toggle selection: click selects only this one
      // If already active, maybe toggle back to "All"? 
      // Let's make it exclusive selection by default for a cleaner navigation feel
      activeCategories.clear();
      activeCategories.add(cat);
      buildCategoryList();
      applyFilters();
    };
    list.appendChild(item);
  });
}

// THE FILTER CORE
function applyFilters() {
  const sortSelect = document.getElementById('sortSelect');
  const sort = sortSelect ? sortSelect.value : 'index';

  // Perform filtering
  filteredEvents = allEvents.filter(e => {
    // 1. Category Filter
    if (!activeCategories.has(e.category)) return false;
    return true;
  });

  // Apply Sorting
  if (sort === 'delta_desc') {
    filteredEvents.sort((a, b) => b.delta - a.delta);
  } else if (sort === 'delta_asc') {
    filteredEvents.sort((a, b) => a.delta - b.delta);
  } else if (sort === 'category') {
    filteredEvents.sort((a, b) => a.category.localeCompare(b.category) || a.idx - b.idx);
  } else {
    // Original order
    filteredEvents.sort((a, b) => a.idx - b.idx);
  }

  updateStats();
  render();
}

// STATS & UTILS
function updateStats() {
  const deltas = allEvents.map(e => e.delta);
  const maxInLog = deltas.length ? Math.max(...deltas) : 0;

  // Auto-adjust sliders max if they are smaller than log data
  const minSlider = document.getElementById('minDelta');
  const maxSlider = document.getElementById('maxDelta');
  if (maxSlider && maxInLog > parseInt(maxSlider.max)) {
    const newMax = Math.ceil(maxInLog / 1000) * 1000;
    if (minSlider) minSlider.max = newMax;
    maxSlider.max = newMax;
  }

  const visibleDeltas = filteredEvents.map(e => e.delta).filter(d => d > 0);
  const statTotal = document.getElementById('statTotal');
  if (statTotal) statTotal.textContent = filteredEvents.length.toLocaleString();

  const sum = visibleDeltas.reduce((a, b) => a + b, 0);
  const avg = visibleDeltas.length ? Math.round(sum / visibleDeltas.length) : 0;
  const vMax = visibleDeltas.length ? Math.max(...visibleDeltas) : 0;

  const statAvg = document.getElementById('statAvg');
  if (statAvg) statAvg.innerHTML = (visibleDeltas.length ? avg : '—') + '<span class="stat-unit">ms</span>';
  const statMax = document.getElementById('statMax');
  if (statMax) statMax.innerHTML = (visibleDeltas.length ? vMax : '—') + '<span class="stat-unit">ms</span>';
  const statCats = document.getElementById('statCats');
  if (statCats) statCats.textContent = new Set(filteredEvents.map(e => e.category)).size;
}

function updateRangeLabel() {
  // Logic removed as UI elements were deleted
}

function deltaClass(ms) {
  if (ms <= 50) return 'delta-fast';
  if (ms <= 300) return 'delta-mid';
  return 'delta-slow';
}

function render() {
  const container = document.getElementById('logContainer');
  const empty = document.getElementById('emptyState');

  if (!allEvents || allEvents.length === 0) {
    if (container) {
      container.innerHTML = '';
      if (empty) {
        container.appendChild(empty);
        empty.style.display = 'flex';
      }
    }
    return;
  }

  if (empty) empty.style.display = 'none';

  try {
    if (currentView === 'table') {
      renderTable(container);
    } else if (currentView === 'timeline') {
      renderTimeline(container);
    } else {
      renderLogs(container);
    }
  } catch (err) {
    console.error('Render error:', err);
    if (container) container.innerHTML = `<div class="empty-state"><p><strong>Render Error</strong>${err.message}</p></div>`;
  }
}

function renderTable(container) {
  if (!container) return;
  if (filteredEvents.length === 0) {
    container.innerHTML = '<div class="empty-state"><strong>No matches</strong>Try adjusting your filters</div>';
    return;
  }

  const deltas = filteredEvents.map(e => e.delta);
  const maxDelta = deltas.length ? Math.max(...deltas, 1) : 1;

  const rows = filteredEvents.map((e, i) => {
    const color = getCatColor(e.category);
    const dc = deltaClass(e.delta);
    const barPct = Math.round((e.delta / maxDelta) * 100);
    const traceLabel = e.traceId || '—';
    const totalLabel = e.total !== null ? e.total + 'ms' : '—';

    return `
      <tr class="log-row" data-idx="${e.idx}" onclick="showDetail(${e.idx})">
        <td class="td-index">${i + 1}</td>
        <td class="td-trace"><span class="trace-badge">${traceLabel}</span></td>
        <td class="td-category">
          <span class="cat-badge" style="background:${color}18;color:${color}">
            <span class="cat-dot" style="background:${color}"></span>${e.category}
          </span>
        </td>
        <td class="td-label" title="${escHtml(e.label)}">${escHtml(e.label)}</td>
        <td class="td-delta"><span class="delta-value ${dc}">+${e.delta}ms</span></td>
        <td class="td-total">${totalLabel}</td>
        <td class="td-bar">
          <div class="bar-track">
            <div class="bar-fill" style="width:${barPct}%;background:${color}"></div>
          </div>
        </td>
      </tr>`;
  });

  container.innerHTML = `
    <table class="log-table">
      <thead>
        <tr>
          <th class="td-index">#</th>
          <th class="td-trace">trace</th>
          <th class="td-category">category</th>
          <th>label</th>
          <th class="td-delta">+delta</th>
          <th class="td-total">total</th>
          <th class="td-bar"></th>
        </tr>
      </thead>
      <tbody>
        ${rows.join('')}
      </tbody>
    </table>
  `;
}

function renderTimeline(container) {
  if (!container) return;
  if (filteredEvents.length === 0) {
    container.innerHTML = '<div class="empty-state"><strong>No matches</strong>Try adjusting your filters</div>';
    return;
  }

  const cats = {};
  filteredEvents.forEach(e => {
    if (!cats[e.category]) cats[e.category] = [];
    cats[e.category].push(e);
  });

  const deltas = filteredEvents.map(e => e.delta);
  const maxDelta = deltas.length ? Math.max(...deltas, 1) : 1;

  const catBlocks = Object.entries(cats).map(([cat, events]) => {
    const color = getCatColor(cat);
    const total = events.reduce((a, b) => a + b.delta, 0);
    const avg = Math.round(total / events.length);
    const max = Math.max(...events.map(e => e.delta));

    // aggregate repeated labels
    const labelMap = {};
    events.forEach(e => {
      if (!labelMap[e.label]) labelMap[e.label] = { deltas: [], raw: e.raw };
      labelMap[e.label].deltas.push(e.delta);
    });

    const eventRows = Object.entries(labelMap).map(([label, data]) => {
      const { deltas, raw } = data;
      const isMulti = deltas.length > 1;
      const avg2 = Math.round(deltas.reduce((a, b) => a + b, 0) / deltas.length);
      const max2 = Math.max(...deltas);
      const min2 = Math.min(...deltas);
      const barPct = Math.round((avg2 / maxDelta) * 100);
      const dc = deltaClass(avg2);

      const displayMs = isMulti
        ? `<span class="${dc}">avg ${avg2}ms</span> <span style="color:var(--text3)">min ${min2} max ${max2} ×${deltas.length}</span>`
        : `<span class="${dc}">+${deltas[0]}ms</span>`;

      return `
        <div class="tl-event">
          <div class="tl-label" title="${escHtml(label)}">${escHtml(label)}</div>
          <div class="tl-bar-outer">
            <div class="tl-bar-inner" style="width:${barPct}%;background:${color}88"></div>
          </div>
          <div class="tl-ms">${displayMs}</div>
          <div class="tl-total">${isMulti ? deltas.reduce((a, b) => a + b, 0) + 'ms total' : ''}</div>
        </div>`;
    });

    return `
      <div class="timeline-category">
        <div class="tl-cat-header">
          <span class="cat-dot" style="background:${color};width:8px;height:8px;border-radius:50%;display:inline-block"></span>
          <span class="tl-cat-name">${cat}</span>
          <span class="tl-cat-stats">${events.length} events · avg ${avg}ms · max ${max}ms · total ${total}ms</span>
        </div>
        <div class="tl-events">
          ${eventRows.join('')}
        </div>
      </div>`;
  });

  container.innerHTML = `<div class="timeline-container">${catBlocks.join('')}</div>`;
}

function renderLogs(container) {
  if (!container) return;
  if (filteredEvents.length === 0) {
    container.innerHTML = '<div class="empty-state"><strong>No matches</strong>Try adjusting your filters</div>';
    return;
  }

  const rows = filteredEvents.map((e, i) => {
    const color = getCatColor(e.category);
    return `
      <div class="raw-log-line" onclick="showDetail(${e.idx})">
        <span class="log-line-num">${i + 1}</span>
        <span class="log-line-cat" style="color:${color}">${e.category}</span>
        <span class="log-line-text">${escHtml(e.raw)}</span>
      </div>`;
  });

  container.innerHTML = `<div class="raw-logs-container">${rows.join('')}</div>`;
}

function showDetail(idx) {
  const e = allEvents.find(ev => ev.idx === idx);
  if (!e) return;

  document.querySelectorAll('.log-row').forEach(r => r.classList.remove('selected'));
  const row = document.querySelector(`[data-idx="${idx}"]`);
  if (row) row.classList.add('selected');

  const detailTitle = document.getElementById('detailTitle');
  if (detailTitle) detailTitle.textContent = e.category + ' / ' + e.label;
  const color = getCatColor(e.category);

  const rows = [
    ['category', e.category],
    ['label', e.label],
    ['delta', '+' + e.delta + 'ms'],
    ['total', e.total !== null ? e.total + 'ms' : '—'],
    ['trace id', e.traceId || '—'],
    ['type', e.type],
    ['event #', e.idx + 1],
  ];

  const detailBody = document.getElementById('detailBody');
  if (detailBody) {
    detailBody.innerHTML = rows.map(([k, v]) =>
      `<div class="detail-row"><span class="detail-key">${k}</span><span class="detail-val" style="color:${k === 'delta' ? color : 'var(--text)'}">${escHtml(String(v))}</span></div>`
    ).join('') + `<div style="margin-top:16px"><div class="detail-key" style="margin-bottom:6px;font-size:10px;letter-spacing:.08em;text-transform:uppercase">raw</div><pre style="font-family:var(--mono);font-size:10px;color:var(--text3);word-break:break-all;white-space:pre-wrap;line-height:1.6">${escHtml(e.raw)}</pre></div>`;
  }

  const detailPanel = document.getElementById('detailPanel');
  if (detailPanel) detailPanel.classList.add('open');
}

function closeDetail() {
  const detailPanel = document.getElementById('detailPanel');
  if (detailPanel) detailPanel.classList.remove('open');
  document.querySelectorAll('.log-row').forEach(r => r.classList.remove('selected'));
}

function switchView(view, btn) {
  currentView = view;
  document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
  if (btn) btn.classList.add('active');
  render();
}

function clearAll() {
  allEvents = [];
  filteredEvents = [];
  activeCategories = new Set();
  colorIdx = 0;
  Object.keys(catColorMap).forEach(k => delete catColorMap[k]);
  const categoryList = document.getElementById('categoryList');
  if (categoryList) categoryList.innerHTML = '';
  const statTotal = document.getElementById('statTotal');
  if (statTotal) statTotal.textContent = '—';
  const statAvg = document.getElementById('statAvg');
  if (statAvg) statAvg.innerHTML = '—';
  const statMax = document.getElementById('statMax');
  if (statMax) statMax.innerHTML = '—';
  const statCats = document.getElementById('statCats');
  if (statCats) statCats.textContent = '—';
  const searchInput = document.getElementById('searchInput');
  if (searchInput) searchInput.value = '';
  closeDetail();
  render();
}

function escHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// FILE HANDLING
const fileInput = document.getElementById('fileInput');
if (fileInput) {
  fileInput.addEventListener('change', e => {
    const files = Array.from(e.target.files);
    loadFiles(files);
    e.target.value = '';
  });
}

const drop = document.getElementById('fileDrop');
if (drop) {
  drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('drag-over'); });
  drop.addEventListener('dragleave', () => drop.classList.remove('drag-over'));
  drop.addEventListener('drop', e => {
    e.preventDefault();
    drop.classList.remove('drag-over');
    loadFiles(Array.from(e.dataTransfer.files));
  });
}

// Also allow dropping on whole page
document.addEventListener('dragover', e => e.preventDefault());
document.addEventListener('drop', e => {
  e.preventDefault();
  const files = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.log') || f.name.endsWith('.txt'));
  if (files.length) loadFiles(files);
});

function loadFiles(files) {
  let combined = '';
  let loaded = 0;
  files.forEach(file => {
    const reader = new FileReader();
    reader.onload = ev => {
      combined += ev.target.result + '\n';
      loaded++;
      if (loaded === files.length) {
        const events = parseLog(combined);
        loadEvents(events);
      }
    };
    reader.readAsText(file);
  });
}

// AUTO-FETCH
async function fetchLog() {
  try {
    const response = await fetch('../aegis.latency.log');
    if (!response.ok) throw new Error('File not found');
    const text = await response.text();
    const events = parseLog(text);
    loadEvents(events);
    const corsWarning = document.getElementById('corsWarning');
    if (corsWarning) corsWarning.style.display = 'none';
    console.log('Log loaded from ../aegis.latency.log');
  } catch (err) {
    console.warn('Could not auto-load aegis.latency.log:', err);
    if (window.location.protocol === 'file:') {
      const corsWarning = document.getElementById('corsWarning');
      if (corsWarning) corsWarning.style.display = 'block';
    }
  }
}

window.addEventListener('DOMContentLoaded', fetchLog);

// KEYBOARD
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeDetail();
});
