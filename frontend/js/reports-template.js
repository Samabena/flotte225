/* reports-template.js — Deterministic PDF reports with in-app preview */

const API = '/api/v1';
const token = () => localStorage.getItem('access_token');
const authHeader = () => ({ 'Authorization': `Bearer ${token()}` });

if (!token()) window.location.href = '/';

document.getElementById('btn-logout').addEventListener('click', () => {
  localStorage.clear();
  window.location.href = '/';
});

// ── State ────────────────────────────────────────────────────────────────────
let currentTab     = 'fleet';
let preset         = 'last30';
let driversList    = [];
let currentBlob    = null;
let currentObjectUrl = null;
let pendingFilename  = null;

// ── Init ─────────────────────────────────────────────────────────────────────
async function init() {
  await loadPlan();
  applyPreset(preset);
}

// ── Plan banner ──────────────────────────────────────────────────────────────
async function loadPlan() {
  try {
    const res = await fetch(`${API}/subscription/my-plan`, { headers: authHeader() });
    if (res.status === 401 || res.status === 403) {
      localStorage.clear();
      window.location.href = '/';
      return;
    }
    const data = res.ok ? await res.json() : {};
    renderPlanBanner(data.plan_name || null);
  } catch {
    renderPlanBanner(null);
  }
}

function renderPlanBanner(plan) {
  const banner = document.getElementById('plan-banner');
  const palette = {
    starter:  'bg-gray-100 text-gray-600',
    pro:      'bg-blue-50 text-blue-700 border border-blue-200',
    business: 'bg-green-50 text-[#005F02] border border-green-200',
  };
  banner.className = `rounded-lg px-4 py-3 text-sm font-medium ${palette[plan] || 'bg-gray-100 text-gray-600'}`;
  banner.textContent = `Plan actuel : ${plan ? plan.charAt(0).toUpperCase() + plan.slice(1) : '—'}`;
  banner.classList.remove('hidden');
  document.getElementById('reports-panel').classList.remove('hidden');
}

// ── Tabs ─────────────────────────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tab);
  });
  document.getElementById('driver-picker').classList.toggle('hidden', tab !== 'driver');
  if (tab === 'driver' && driversList.length === 0) loadDrivers();
  closePreview();
}

async function loadDrivers() {
  const select = document.getElementById('driver-select');
  try {
    const res = await fetch(`${API}/drivers`, { headers: authHeader() });
    if (!res.ok) { select.innerHTML = '<option value="">Erreur de chargement</option>'; return; }
    driversList = await res.json();
    select.innerHTML = driversList.length
      ? driversList.map(d => `<option value="${d.id}">${d.full_name}${d.is_disabled ? ' (désactivé)' : ''}</option>`).join('')
      : '<option value="">Aucun conducteur</option>';
  } catch {
    select.innerHTML = '<option value="">Erreur réseau</option>';
  }
}

// ── Preset chips ─────────────────────────────────────────────────────────────
document.querySelectorAll('.preset-chip').forEach(chip => {
  chip.addEventListener('click', () => applyPreset(chip.dataset.preset));
});

function applyPreset(name) {
  preset = name;
  document.querySelectorAll('.preset-chip').forEach(c => {
    c.classList.toggle('active', c.dataset.preset === name);
  });
  document.getElementById('custom-range').classList.toggle('hidden', name !== 'custom');

  const today = new Date();
  const fmt = d => d.toISOString().slice(0, 10);
  let from = null, to = fmt(today);

  if      (name === 'last7')     { const d = new Date(today); d.setDate(d.getDate() - 7);  from = fmt(d); }
  else if (name === 'last30')    { const d = new Date(today); d.setDate(d.getDate() - 30); from = fmt(d); }
  else if (name === 'thisMonth') { from = fmt(new Date(today.getFullYear(), today.getMonth(), 1)); }
  else if (name === 'lastMonth') {
    from = fmt(new Date(today.getFullYear(), today.getMonth() - 1, 1));
    to   = fmt(new Date(today.getFullYear(), today.getMonth(), 0));
  }
  else if (name === 'thisYear')  { from = fmt(new Date(today.getFullYear(), 0, 1)); }

  if (from) document.getElementById('date-from').value = from;
  document.getElementById('date-to').value = to;
}

// ── Generate preview ─────────────────────────────────────────────────────────
document.getElementById('btn-preview').addEventListener('click', async () => {
  const btn = document.getElementById('btn-preview');
  const fb  = document.getElementById('feedback');

  const date_from = document.getElementById('date-from').value || null;
  const date_to   = document.getElementById('date-to').value || null;

  if (date_from && date_to && date_from > date_to) {
    showFeedback('La date de début doit être antérieure à la date de fin.', 'error');
    return;
  }

  let url, filename;
  if (currentTab === 'fleet') {
    url      = `${API}/reports/template/fleet`;
    filename = `rapport-flotte-${date_from || 'auto'}-${date_to || 'auto'}.pdf`;
  } else {
    const driverId = document.getElementById('driver-select').value;
    if (!driverId) { showFeedback('Veuillez sélectionner un conducteur.', 'error'); return; }
    url      = `${API}/reports/template/driver/${driverId}`;
    filename = `rapport-conducteur-${driverId}-${date_from || 'auto'}-${date_to || 'auto'}.pdf`;
  }

  btn.disabled = true;
  btn.textContent = 'Génération en cours…';
  fb.classList.add('hidden');
  closePreview();

  try {
    const res = await fetch(url, {
      method:  'POST',
      headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body:    JSON.stringify({ date_from, date_to }),
    });

    if (!res.ok) {
      let detail = `Erreur ${res.status}`;
      try { detail = (await res.json()).detail || detail; } catch { /* not JSON */ }
      showFeedback(detail, 'error');
    } else {
      currentBlob     = await res.blob();
      pendingFilename = parseFilename(res.headers.get('Content-Disposition')) || filename;
      openPreview(currentBlob);
      showFeedback('Rapport généré. Consultez l\'aperçu ci-dessous.', 'ok');
    }
  } catch {
    showFeedback('Erreur réseau. Veuillez réessayer.', 'error');
  }

  btn.textContent = 'Aperçu du rapport';
  btn.disabled = false;
});

// ── Download ─────────────────────────────────────────────────────────────────
document.getElementById('btn-download').addEventListener('click', () => {
  if (currentBlob && pendingFilename) triggerDownload(currentBlob, pendingFilename);
});

// ── Preview panel ─────────────────────────────────────────────────────────────
function openPreview(blob) {
  if (currentObjectUrl) URL.revokeObjectURL(currentObjectUrl);
  currentObjectUrl = URL.createObjectURL(blob);
  document.getElementById('pdf-frame').src = currentObjectUrl;
  const panel = document.getElementById('preview-panel');
  panel.classList.remove('hidden');
  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function closePreview() {
  document.getElementById('preview-panel').classList.add('hidden');
  document.getElementById('pdf-frame').src = '';
  if (currentObjectUrl) { URL.revokeObjectURL(currentObjectUrl); currentObjectUrl = null; }
}

document.getElementById('btn-close-preview').addEventListener('click', closePreview);

// ── Helpers ──────────────────────────────────────────────────────────────────
function showFeedback(msg, type) {
  const fb = document.getElementById('feedback');
  fb.textContent = msg;
  fb.className = `text-sm ${type === 'error' ? 'text-red-600' : 'text-green-700'}`;
  fb.classList.remove('hidden');
}

function parseFilename(disposition) {
  if (!disposition) return null;
  const match = /filename="?([^"]+)"?/.exec(disposition);
  return match ? match[1] : null;
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a   = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ── Boot ─────────────────────────────────────────────────────────────────────
init();
