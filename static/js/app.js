// ── GLOBALS ───────────────────────────────────────────────────────────────────
let META = {};

async function loadMeta() {
  const r = await fetch('/api/meta');
  META = await r.json();
}

// ── HTTP HELPERS ──────────────────────────────────────────────────────────────
async function api(url, method='GET', body=null) {
  const opts = { method, headers: {'Content-Type':'application/json'} };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(url, opts);
  return r.json();
}

// ── TOAST ─────────────────────────────────────────────────────────────────────
function toast(msg, type='success') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast ${type} show`;
  setTimeout(() => el.classList.remove('show'), 3500);
}

// ── MODAL ─────────────────────────────────────────────────────────────────────
function openModal(title, html, wide=false) {
  document.getElementById('modalTitle').textContent = title;
  document.getElementById('modalBody').innerHTML = html;
  const m = document.getElementById('mainModal');
  m.className = wide ? 'modal open modal-wide' : 'modal open';
  document.getElementById('modalOverlay').classList.add('open');
}
function closeModal() {
  document.getElementById('mainModal').classList.remove('open');
  document.getElementById('modalOverlay').classList.remove('open');
}

// ── TABS ──────────────────────────────────────────────────────────────────────
function initTabs(containerId) {
  const c = document.getElementById(containerId);
  if (!c) return;
  c.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      c.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      c.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = c.querySelector('#' + btn.dataset.tab);
      if (panel) panel.classList.add('active');
    });
  });
}

// ── NUMBER FORMATTING ─────────────────────────────────────────────────────────
function fmt(v, dec=2) {
  if (v == null || v === '') return '—';
  const n = parseFloat(v);
  if (isNaN(n)) return v;
  return n.toLocaleString('en-PK', {minimumFractionDigits:dec, maximumFractionDigits:dec});
}
function fmtM(v) {
  const n = parseFloat(v) || 0;
  return (n/1e6).toFixed(2);
}
function cr(v) { return 'Rs. ' + fmt(v); }
function crM(v) { return 'Rs. ' + fmtM(v) + ' M'; }

// ── DATE HELPERS ──────────────────────────────────────────────────────────────
const MONTHS = ["January","February","March","April","May","June",
                "July","August","September","October","November","December"];
const MONTHS_S = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function todayStr() {
  return new Date().toISOString().split('T')[0];
}
function currentFY() {
  const d = new Date();
  const y = d.getFullYear(); const m = d.getMonth()+1;
  if (m >= 7) return `${y}-${String(y+1).slice(-2)}`;
  return `${y-1}-${String(y).slice(-2)}`;
}

// ── MONTH/YEAR SELECTS ────────────────────────────────────────────────────────
function buildMonthSelectAppend(id) {
  const sel = document.getElementById(id);
  if (!sel) return;
  MONTHS.forEach((m, i) => {
    const opt = document.createElement('option');
    opt.value = i+1; opt.textContent = m;
    sel.appendChild(opt);
  });
}

function buildMonthSelect(id, selectedMonth) {
  const sel = document.getElementById(id);
  if (!sel) return;
  MONTHS.forEach((m, i) => {
    const opt = document.createElement('option');
    opt.value = i+1; opt.textContent = m;
    if (selectedMonth != null && i+1 === selectedMonth) opt.selected = true;
    sel.appendChild(opt);
  });
}
function buildYearSelect(id, selectedYear, from=2018, to=2036) {
  const sel = document.getElementById(id);
  if (!sel) return;
  for (let y = to; y >= from; y--) {
    const opt = document.createElement('option');
    opt.value = y; opt.textContent = y;
    if (y === selectedYear) opt.selected = true;
    sel.appendChild(opt);
  }
}
function buildPMSelect(id, selected='') {
  const sel = document.getElementById(id);
  if (!sel) return;
  sel.innerHTML = '<option value="">All PMs</option>';
  (META.project_managers || []).forEach(pm => {
    const opt = document.createElement('option');
    opt.value = pm; opt.textContent = pm;
    if (pm === selected) opt.selected = true;
    sel.appendChild(opt);
  });
}
function buildGroupSelect(id, selected='') {
  const sel = document.getElementById(id);
  if (!sel) return;
  sel.innerHTML = '<option value="">All Groups</option>';
  (META.project_groups || []).forEach(g => {
    const opt = document.createElement('option');
    opt.value = g; opt.textContent = g;
    if (g === selected) opt.selected = true;
    sel.appendChild(opt);
  });
}

function buildFYSelect(id, selected) {
  const sel = document.getElementById(id);
  if (!sel) return;
  sel.innerHTML = '<option value="">All (Since Start)</option>';
  (META.available_fys || []).forEach(fy => {
    const opt = document.createElement('option');
    opt.value = fy.value; opt.textContent = fy.label;
    if (selected != null && String(fy.value) === String(selected)) opt.selected = true;
    sel.appendChild(opt);
  });
}

/**
 * Builds the standard Period Filter bar (FY + Month-within-that-FY + Cumulative checkbox)
 * used identically across Dashboard, Projects, Reports, and all list pages.
 *
 * Behavior:
 *  - FY dropdown: "All (Since Start)" or a specific FY (e.g. 2025-26)
 *  - Month dropdown: ONLY enabled once a specific FY is picked. Shows the 12 months
 *    belonging to THAT FY (Jul..Jun with correct years attached internally), e.g.
 *    picking FY 2025-26 shows Jul 2025, Aug 2025, ... Jun 2026.
 *  - Cumulative checkbox: only meaningful once a Month is also picked.
 *      checked   -> Jul (of that FY) through the selected month
 *      unchecked -> that single month only
 *    If no month is picked (FY only, or "All"), checkbox has no effect —
 *    FY-only always means the full FY cumulative; "All" always means since start.
 *
 * Inserts into the element with id=containerId. Calls onChange() whenever any control changes.
 * Returns an object with .getParams() -> {fy_start, month, year, cumulative} query-string-ready values.
 */
function buildPeriodFilter(containerId, onChange, opts={}) {
  const c = document.getElementById(containerId);
  if (!c) return null;
  c.innerHTML = `
    <div class="filter-group">
      <span class="filter-label">Financial Year</span>
      <select id="${containerId}_fy" class="form-control"></select>
    </div>
    <div class="filter-group">
      <span class="filter-label">Month</span>
      <select id="${containerId}_month" class="form-control"><option value="">Whole FY</option></select>
    </div>
    <div class="filter-group" style="flex-direction:row;align-items:center;gap:6px;padding-top:14px">
      <input type="checkbox" id="${containerId}_cum" checked style="width:16px;height:16px;cursor:pointer">
      <label for="${containerId}_cum" style="font-size:11px;font-weight:600;color:#374151;cursor:pointer">Cumulative</label>
    </div>
  `;
  const fySel = document.getElementById(`${containerId}_fy`);
  const mSel  = document.getElementById(`${containerId}_month`);
  const cumCb = document.getElementById(`${containerId}_cum`);

  buildFYSelect(`${containerId}_fy`, opts.defaultFy !== undefined ? opts.defaultFy : (META.current_fy_start ?? ''));

  const FY_MONTH_NAMES = ["July","August","September","October","November","December",
                          "January","February","March","April","May","June"];

  function rebuildMonthOptions() {
    const fyVal = fySel.value;
    mSel.innerHTML = '<option value="">Whole FY</option>';
    if (!fyVal) { mSel.disabled = true; cumCb.disabled = true; return; }
    mSel.disabled = false; cumCb.disabled = false;
    const fy1 = parseInt(fyVal);
    FY_MONTH_NAMES.forEach((name, idx) => {
      const monthNum = idx < 6 ? idx + 7 : idx - 5;       // Jul=7..Dec=12, Jan=1..Jun=6
      const yearNum  = idx < 6 ? fy1 : fy1 + 1;
      const opt = document.createElement('option');
      opt.value = `${monthNum}-${yearNum}`;
      opt.textContent = `${name} ${yearNum}`;
      mSel.appendChild(opt);
    });
  }
  rebuildMonthOptions();

  fySel.addEventListener('change', () => { rebuildMonthOptions(); onChange && onChange(); });
  mSel.addEventListener('change', () => onChange && onChange());
  cumCb.addEventListener('change', () => onChange && onChange());

  return {
    getParams() {
      const fy = fySel.value || '';
      let month = '', year = '';
      if (mSel.value) { const [m,y] = mSel.value.split('-'); month = m; year = y; }
      return {
        fy_start: fy,
        month, year,
        cumulative: cumCb.checked ? '1' : '0',
      };
    },
    asQueryString() {
      const p = this.getParams();
      return `fy_start=${encodeURIComponent(p.fy_start)}&month=${encodeURIComponent(p.month)}&year=${encodeURIComponent(p.year)}&cumulative=${p.cumulative}`;
    },
    setFy(v) { fySel.value = v; rebuildMonthOptions(); },
    setMonthYear(m, y) {
      const fy1 = m >= 7 ? y : y - 1;
      fySel.value = fy1; rebuildMonthOptions();
      mSel.value = `${m}-${y}`;
    },
  };
}

// ── PROJECT SEARCH COMBO ──────────────────────────────────────────────────────
let _allProjects = [];
async function loadProjectList() {
  const r = await fetch('/api/projects/list');
  _allProjects = await r.json();
}

function setupProjectSearch(inputId, hiddenId, infoId) {
  const inp = document.getElementById(inputId);
  const hid = document.getElementById(hiddenId);
  const inf = document.getElementById(infoId);
  if (!inp) return;

  let dropdown = null;

  inp.addEventListener('input', () => {
    const q = inp.value.toLowerCase();
    const matches = _allProjects.filter(p =>
      p.job_no?.toLowerCase().includes(q) ||
      p.project_name?.toLowerCase().includes(q) ||
      p.sheet_ref?.toLowerCase().includes(q)
    ).slice(0, 15);
    showDropdown(matches);
  });

  inp.addEventListener('focus', () => {
    if (!inp.value) showDropdown(_allProjects.slice(0,15));
  });

  function showDropdown(items) {
    removeDropdown();
    if (!items.length) return;
    dropdown = document.createElement('div');
    dropdown.className = 'proj-dropdown';
    dropdown.style.cssText = `position:absolute;z-index:999;background:#fff;border:1.5px solid #BFDBFE;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.12);max-height:240px;overflow-y:auto;width:${inp.offsetWidth}px;`;
    items.forEach(p => {
      const item = document.createElement('div');
      item.style.cssText = 'padding:9px 14px;cursor:pointer;font-size:12px;border-bottom:1px solid #F1F5F9;';
      item.innerHTML = `<strong style="color:#1565C0">${p.job_no || '—'}</strong> &nbsp;${p.project_name}<br><span style="color:#64748B;font-size:10px">${p.project_manager} · ${p.project_group}</span>`;
      item.addEventListener('mousedown', e => {
        e.preventDefault();
        inp.value = `${p.job_no} — ${p.project_name}`;
        if (hid) hid.value = p.id;
        if (inf) inf.textContent = `PM: ${p.project_manager}  |  Fee: Rs.${p.nespak_fee_mil} M  |  ${p.project_group}`;
        inp.dispatchEvent(new Event('projectSelected', {bubbles:true}));
        inp.dataset.projectId = p.id;
        removeDropdown();
      });
      dropdown.appendChild(item);
    });
    const rect = inp.getBoundingClientRect();
    dropdown.style.top = (rect.bottom + window.scrollY) + 'px';
    dropdown.style.left = (rect.left + window.scrollX) + 'px';
    document.body.appendChild(dropdown);
  }

  function removeDropdown() {
    if (dropdown) { dropdown.remove(); dropdown = null; }
  }
  document.addEventListener('click', e => {
    if (e.target !== inp) removeDropdown();
  });
}

// ── CONFIRM DIALOG ────────────────────────────────────────────────────────────
function confirmDialog(msg) {
  return new Promise(resolve => {
    if (confirm(msg)) resolve(true); else resolve(false);
  });
}

// ── SHOW DIALOG WITH CUSTOM CONTENT ──────────────────────────────────────────
async function showDialog(title, contentHtml, buttons = ['Cancel', 'OK']) {
  return new Promise(resolve => {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:9999;';
    
    const modalContent = document.createElement('div');
    modalContent.style.cssText = 'background:white;padding:24px;border-radius:8px;max-width:500px;width:90%;box-shadow:0 4px 6px rgba(0,0,0,0.1);';
    
    const modalTitle = document.createElement('h3');
    modalTitle.textContent = title;
    modalTitle.style.cssText = 'margin:0 0 16px 0;color:#1e293b;font-size:18px;';
    
    const modalBody = document.createElement('div');
    modalBody.innerHTML = contentHtml;
    modalBody.style.cssText = 'margin-bottom:20px;';
    
    const modalButtons = document.createElement('div');
    modalButtons.style.cssText = 'display:flex;gap:8px;justify-content:flex-end;';
    
    buttons.forEach((btnText, idx) => {
      const btn = document.createElement('button');
      btn.textContent = btnText;
      btn.style.cssText = idx === buttons.length - 1 
        ? 'padding:8px 16px;background:#1565C0;color:white;border:none;border-radius:4px;cursor:pointer;'
        : 'padding:8px 16px;background:#e2e8f0;color:#334155;border:none;border-radius:4px;cursor:pointer;';
      btn.onclick = () => {
        document.body.removeChild(modal);
        resolve(idx === buttons.length - 1); // Resolve true only for last button (OK/Add/Save)
      };
      modalButtons.appendChild(btn);
    });
    
    modalContent.appendChild(modalTitle);
    modalContent.appendChild(modalBody);
    modalContent.appendChild(modalButtons);
    modal.appendChild(modalContent);
    document.body.appendChild(modal);
  });
}

// ── INIT ──────────────────────────────────────────────────────────────────────
// appReady resolves once META and project list are loaded. Every page's own
// DOMContentLoaded handler should `await appReady` before calling
// buildPMSelect/buildGroupSelect/etc, otherwise those dropdowns may render
// empty due to a race between this script's init and the page's init.
window.appReady = new Promise((resolve) => {
  document.addEventListener('DOMContentLoaded', async () => {
    await loadMeta();
    await loadProjectList();

    const d = new Date();
    const dateEl = document.getElementById('todayDate');
    if (dateEl) dateEl.textContent = d.toLocaleDateString('en-PK', {weekday:'short',day:'numeric',month:'short',year:'numeric'});
    const fyEl = document.getElementById('fyBadge');
    if (fyEl) fyEl.textContent = 'FY ' + currentFY();

    resolve();
  });
});
