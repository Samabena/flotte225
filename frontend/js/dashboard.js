/* dashboard.js — Owner dashboard (Sprint 5 + 6) */

const API = '/api/v1';
const token = () => localStorage.getItem('access_token');
const authHeader = () => ({ 'Authorization': `Bearer ${token()}` });

function isTokenValid(t) {
  try {
    const payload = JSON.parse(atob(t.split('.')[1]));
    return payload.exp * 1000 > Date.now();
  } catch { return false; }
}

// ── Redirect if not logged in, expired, or wrong role ───────────────────────
function getRoleFromToken(t) {
  try { return JSON.parse(atob(t.split('.')[1])).role || null; } catch { return null; }
}

const _dashTok = token();
if (!_dashTok || !isTokenValid(_dashTok) || getRoleFromToken(_dashTok) !== 'OWNER') {
  localStorage.clear();
  window.location.href = '/login';
}

document.getElementById('btn-logout').addEventListener('click', () => {
  localStorage.clear();
  window.location.href = '/login';
});

document.getElementById('upgrade-modal-close').addEventListener('click', () => {
  document.getElementById('modal-upgrade').classList.add('hidden');
});

// ── Greeting (by name) ───────────────────────────────────────────────────────
function greetingWord() {
  const hour = new Date(
    new Date().toLocaleString('en-US', { timeZone: 'Africa/Abidjan' })
  ).getHours();
  return hour >= 18 ? 'Bonsoir' : 'Bonjour';
}

async function loadMe() {
  const wordEl = document.getElementById('greeting-word');
  const nameEl = document.getElementById('owner-name');
  if (wordEl) wordEl.textContent = greetingWord();
  // Show a cached name immediately, then refresh from the server.
  const cached = localStorage.getItem('owner_full_name');
  if (cached && nameEl) nameEl.textContent = cached;
  try {
    const res = await fetch(`${API}/auth/me`, { headers: authHeader() });
    if (!res.ok) return;
    const me = await res.json();
    const name = (me.full_name || '').trim();
    if (name) {
      localStorage.setItem('owner_full_name', name);
      if (nameEl) nameEl.textContent = name;
    }
  } catch (e) {
    /* keep cached / placeholder name */
  }
}

// ── Fetch dashboard data ─────────────────────────────────────────────────────
async function loadDashboard() {
  let data;
  try {
    const res = await fetch(`${API}/dashboard/owner`, { headers: authHeader() });
    if (res.status === 401 || res.status === 403) {
      localStorage.clear();
      window.location.href = '/login';
      return;
    }
    const json = await res.json();
    data = json.data;
  } catch (e) {
    console.error('Erreur chargement tableau de bord', e);
    return;
  }

  renderKPIs(data);
  renderSpendByVehicle(data.financial.spend_per_vehicle);
  renderMonthlyTrend(data.financial.monthly_trend);
  renderSpendDonut(data.financial.spend_per_vehicle);
  renderConsumption(data.consumption);
  renderDrivers(data.drivers);
  renderAlerts(data.alerts);
  populateRevenueVehicles(data.consumption);
}

// ── Quick revenue entry (owner) ───────────────────────────────────────────────
function populateRevenueVehicles(consumption) {
  const sel = document.getElementById('rev-vehicle');
  if (!sel) return;
  const list = consumption || [];
  sel.innerHTML = '<option value="">— Sélectionner —</option>' +
    list.map(v => `<option value="${v.vehicle_id}">${v.vehicle_name}</option>`).join('');
  const d = document.getElementById('rev-date');
  if (d && !d.value) d.value = new Date().toISOString().slice(0, 10);
}

document.getElementById('btn-add-revenue')?.addEventListener('click', async () => {
  const errEl = document.getElementById('rev-error');
  const okEl  = document.getElementById('rev-success');
  errEl.classList.add('hidden'); okEl.classList.add('hidden');

  const vehicleId = document.getElementById('rev-vehicle').value;
  const date      = document.getElementById('rev-date').value;
  const amount    = document.getElementById('rev-amount').value;
  const note      = document.getElementById('rev-note').value.trim();

  const fail = (m) => { errEl.textContent = m; errEl.classList.remove('hidden'); };
  if (!vehicleId) return fail('Veuillez sélectionner un véhicule.');
  if (!date) return fail('Veuillez indiquer la date.');
  if (amount === '' || parseFloat(amount) <= 0) return fail('Le montant doit être supérieur à 0.');

  const body = { date, amount_fcfa: parseFloat(amount) };
  if (note) body.note = note;

  const btn = document.getElementById('btn-add-revenue');
  btn.disabled = true;
  try {
    const res = await fetch(`${API}/vehicles/${vehicleId}/revenues`, {
      method: 'POST',
      headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const json = await res.json().catch(() => ({}));
    if (res.ok) {
      okEl.textContent = 'Recette enregistrée.';
      okEl.classList.remove('hidden');
      document.getElementById('rev-amount').value = '';
      document.getElementById('rev-note').value = '';
      loadDashboard();  // refresh KPIs (recettes + bénéfice net)
      setTimeout(() => okEl.classList.add('hidden'), 4000);
    } else {
      const detail = json.detail;
      fail(Array.isArray(detail) ? detail.map(d => d.msg).join(' · ') : (detail || "Erreur lors de l'enregistrement."));
    }
  } catch {
    fail('Erreur réseau. Réessayez.');
  }
  btn.disabled = false;
});

// ── Fetch plan usage (US-046) ────────────────────────────────────────────────
async function loadPlanUsage() {
  try {
    const res = await fetch(`${API}/subscription/my-plan`, { headers: authHeader() });
    if (res.status === 401 || res.status === 403) {
      localStorage.clear();
      window.location.href = '/login';
      return;
    }
    if (!res.ok) return;
    const json = await res.json();
    renderPlanUsage(json.data);
  } catch (e) {
    // Plan section stays hidden on error
  }
}

// ── KPI cards ────────────────────────────────────────────────────────────────
function renderKPIs(data) {
  const fin = data.financial;
  const fcfa = n => (parseFloat(n) || 0).toLocaleString('fr-FR') + ' FCFA';

  document.getElementById('kpi-total-spend').textContent = fcfa(fin.total_spend_fcfa);
  document.getElementById('kpi-spend-breakdown').textContent =
    `Carburant ${fcfa(fin.fuel_total_fcfa)} · Maintenance ${fcfa(fin.maintenance_total_fcfa)}`;

  document.getElementById('kpi-revenue').textContent = fcfa(fin.total_revenue_fcfa);

  const net = parseFloat(fin.net_profit_fcfa) || 0;
  const netEl = document.getElementById('kpi-net-profit');
  netEl.textContent = fcfa(net);
  netEl.classList.toggle('text-red-600', net < 0);
  netEl.classList.toggle('text-[#005F02]', net >= 0);

  const distance = parseInt(fin.total_distance_km) || 0;
  const costPerKm = parseFloat(fin.cost_per_km_fcfa) || 0;
  document.getElementById('kpi-cost-per-km').textContent =
    distance > 0 ? costPerKm.toLocaleString('fr-FR', { maximumFractionDigits: 1 }) + ' FCFA' : '—';
  document.getElementById('kpi-distance').textContent =
    distance > 0 ? `sur ${distance.toLocaleString('fr-FR')} km` : 'distance non renseignée';

  const activeVehicles = data.consumption.filter(v => v.entry_count >= 0).length;
  document.getElementById('kpi-active-vehicles').textContent = activeVehicles;

  document.getElementById('kpi-active-drivers').textContent = (data.drivers || []).length;
}

// ── Spend by vehicle — bar chart ─────────────────────────────────────────────
function renderSpendByVehicle(spendData) {
  if (!spendData || spendData.length === 0) {
    document.getElementById('chart-spend-vehicle').classList.add('hidden');
    document.getElementById('empty-spend-vehicle').classList.remove('hidden');
    return;
  }

  const labels = spendData.map(v => v.vehicle_name);
  const values = spendData.map(v => parseFloat(v.spend_fcfa));
  const colors = labels.map((_, i) => i % 2 === 0 ? '#005F02' : '#C0B87A');

  new Chart(document.getElementById('chart-spend-vehicle'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Dépense (FCFA)',
        data: values,
        backgroundColor: colors,
        borderRadius: 4,
      }]
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          ticks: { callback: v => v.toLocaleString('fr-FR') },
          grid: { color: '#f3f4f6' },
        },
        x: { grid: { display: false } }
      }
    }
  });
}

// ── Monthly trend — line chart ───────────────────────────────────────────────
function renderMonthlyTrend(monthlyData) {
  if (!monthlyData || monthlyData.length === 0) {
    document.getElementById('chart-monthly').classList.add('hidden');
    document.getElementById('empty-monthly').classList.remove('hidden');
    return;
  }

  const labels = monthlyData.map(m => m.month);
  const values = monthlyData.map(m => parseFloat(m.spend_fcfa));

  const canvas = document.getElementById('chart-monthly');
  const ctx = canvas.getContext('2d');
  const gradient = ctx.createLinearGradient(0, 0, 0, 200);
  gradient.addColorStop(0, 'rgba(192,184,122,0.35)');
  gradient.addColorStop(1, 'rgba(192,184,122,0)');

  new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Dépense (FCFA)',
        data: values,
        borderColor: '#C0B87A',
        backgroundColor: gradient,
        fill: true,
        tension: 0.35,
        pointBackgroundColor: '#005F02',
        pointRadius: 4,
      }]
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          ticks: { callback: v => v.toLocaleString('fr-FR') },
          grid: { color: '#f3f4f6' },
        },
        x: { grid: { display: false } }
      }
    }
  });
}

// ── Consumption table ────────────────────────────────────────────────────────
function renderConsumption(data) {
  const tbody = document.getElementById('consumption-tbody');
  const empty = document.getElementById('empty-consumption');

  if (!data || data.length === 0) {
    tbody.parentElement.classList.add('hidden');
    empty.classList.remove('hidden');
    return;
  }

  tbody.innerHTML = data.map(v => {
    const conso = v.avg_consumption_per_100km !== null
      ? parseFloat(v.avg_consumption_per_100km).toFixed(2) + ' L/100'
      : '<span class="text-gray-400">Insuffisant</span>';
    return `
      <tr class="border-b last:border-0">
        <td class="py-2 font-medium">${esc(v.vehicle_name)}</td>
        <td class="py-2 text-gray-500">${esc(v.brand)} ${esc(v.model)}</td>
        <td class="py-2 text-right">${conso}</td>
      </tr>`;
  }).join('');
}

// ── Drivers panel ────────────────────────────────────────────────────────────
function renderDrivers(drivers) {
  const list = document.getElementById('drivers-list');
  const empty = document.getElementById('empty-drivers');

  if (!drivers || drivers.length === 0) {
    list.classList.add('hidden');
    empty.classList.remove('hidden');
    return;
  }

  list.innerHTML = drivers.map(d => {
    const badge = d.driving_status
      ? '<span class="badge-active text-xs px-2 py-0.5 rounded-full font-medium">Actif</span>'
      : '<span class="badge-inactive text-xs px-2 py-0.5 rounded-full font-medium">Inactif</span>';
    const vehicle = d.active_vehicle_name
      ? `<span class="text-xs text-gray-400 ml-2">${esc(d.active_vehicle_name)}</span>`
      : '';
    return `
      <li class="flex items-center justify-between py-2 border-b last:border-0">
        <span class="font-medium text-sm">${esc(d.full_name)}</span>
        <span class="flex items-center gap-1">${badge}${vehicle}</span>
      </li>`;
  }).join('');
}

// ── Alerts & anomalies ────────────────────────────────────────────────────────
const COMPLIANCE_TYPES = ['insurance_expiry', 'inspection_expiry', 'oil_change'];
const ANOMALY_TYPES = ['consumption_anomaly', 'cost_spike'];

function renderAlerts(alerts) {
  const compliance = alerts.filter(a => COMPLIANCE_TYPES.includes(a.type));
  const anomalies  = alerts.filter(a => ANOMALY_TYPES.includes(a.type));

  // Alertes tab
  const alertsList = document.getElementById('alerts-list');
  const emptyAlerts = document.getElementById('empty-alerts');
  if (compliance.length === 0) {
    alertsList.classList.add('hidden');
    emptyAlerts.classList.remove('hidden');
  } else {
    alertsList.innerHTML = compliance.map(a => {
      const cls = a.severity === 'critical' ? 'badge-critical' : 'badge-warning';
      const label = a.severity === 'critical' ? 'CRITIQUE' : 'ATTENTION';
      return `
        <li class="flex items-start gap-3 p-3 rounded-lg bg-gray-50 text-sm">
          <span class="${cls} text-xs px-2 py-0.5 rounded-full font-bold shrink-0 mt-0.5">${label}</span>
          <div>
            <span class="font-semibold">${esc(a.vehicle_name)}</span>
            <span class="text-gray-500 mx-1">·</span>
            <span>${esc(a.message)}</span>
            <span class="text-gray-400 text-xs block mt-0.5">${esc(a.detail)}</span>
          </div>
        </li>`;
    }).join('');
  }

  // Anomalies tab
  const anomaliesList = document.getElementById('anomalies-list');
  const emptyAnomalies = document.getElementById('empty-anomalies');
  if (anomalies.length === 0) {
    anomaliesList.classList.add('hidden');
    emptyAnomalies.classList.remove('hidden');
  } else {
    anomaliesList.innerHTML = anomalies.map(a => `
      <li class="flex items-start gap-3 p-3 rounded-lg bg-amber-50 text-sm">
        <span class="badge-warning text-xs px-2 py-0.5 rounded-full font-bold shrink-0 mt-0.5">ANOMALIE</span>
        <div>
          <span class="font-semibold">${esc(a.vehicle_name)}</span>
          <span class="text-gray-500 mx-1">·</span>
          <span>${esc(a.message)}</span>
          <span class="text-gray-400 text-xs block mt-0.5">${esc(a.detail)}</span>
        </div>
      </li>`).join('');
  }
}

// ── Donut: spend distribution (US-021) ───────────────────────────────────────
function renderSpendDonut(spendData) {
  const canvas = document.getElementById('chart-donut');
  const empty  = document.getElementById('empty-donut');

  if (!spendData || spendData.length === 0) {
    canvas.classList.add('hidden');
    empty.classList.remove('hidden');
    return;
  }

  const labels = spendData.map(v => v.vehicle_name);
  const values = spendData.map(v => parseFloat(v.spend_fcfa));
  const palette = [
    '#005F02', '#C0B87A', '#4CAF50', '#8BC34A', '#CDDC39',
    '#FFC107', '#FF9800', '#795548', '#607D8B', '#9E9E9E',
  ];
  const colors = labels.map((_, i) => palette[i % palette.length]);

  new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: '#fff',
      }]
    },
    options: {
      maintainAspectRatio: false,
      cutout: '62%',
      plugins: {
        legend: {
          position: 'right',
          labels: { boxWidth: 12, font: { size: 11 }, padding: 10 },
        },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.label}: ${parseFloat(ctx.raw).toLocaleString('fr-FR')} FCFA`,
          }
        }
      }
    }
  });
}

// ── Plan usage gauges (US-046) ───────────────────────────────────────────────
function renderPlanUsage(data) {
  const { plan, active_vehicles, active_drivers, expires_at } = data;

  document.getElementById('plan-badge').textContent = plan.name;

  // Vehicles gauge
  const maxV = plan.max_vehicles;
  const vPct = maxV ? Math.min((active_vehicles / maxV) * 100, 100) : 0;
  document.getElementById('plan-vehicles-label').textContent =
    maxV ? `${active_vehicles} / ${maxV}` : `${active_vehicles} (illimité)`;
  document.getElementById('plan-vehicles-bar').style.width = maxV ? `${vPct}%` : '0%';

  // Drivers gauge
  const maxD = plan.max_drivers;
  const dPct = maxD ? Math.min((active_drivers / maxD) * 100, 100) : 0;
  document.getElementById('plan-drivers-label').textContent =
    maxD ? `${active_drivers} / ${maxD}` : `${active_drivers} (illimité)`;
  document.getElementById('plan-drivers-bar').style.width = maxD ? `${dPct}%` : '0%';

  // Expiry
  if (expires_at) {
    const expEl = document.getElementById('plan-expire');
    expEl.textContent = `Expire le ${new Date(expires_at).toLocaleDateString('fr-FR')}`;
    expEl.classList.remove('hidden');
  }

  // Show upgrade CTA for starter plan
  if (plan.name === 'starter') {
    document.getElementById('btn-upgrade').classList.remove('hidden');
  }

  // Wire upgrade button to upgrade modal
  document.getElementById('btn-upgrade').addEventListener('click', showUpgradePrompt);
}

// ── Upgrade prompt (US-045) ──────────────────────────────────────────────────
function showUpgradePrompt(msg) {
  if (typeof msg === 'string') {
    document.getElementById('upgrade-modal-msg').textContent = msg;
  }
  document.getElementById('modal-upgrade').classList.remove('hidden');
}

// Intercept plan-gated 403s and show upgrade modal
async function apiFetch(url, options = {}) {
  const res = await fetch(url, { ...options, headers: { ...authHeader(), ...(options.headers || {}) } });
  if (res.status === 403) {
    const json = await res.json().catch(() => ({}));
    const detail = json.detail || '';
    if (detail.toLowerCase().includes('abonnement') || detail.toLowerCase().includes('plan') || detail.toLowerCase().includes('limit')) {
      showUpgradePrompt(detail);
      return null;
    }
  }
  return res;
}

// ── Tab switching ─────────────────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-alertes').classList.add('hidden');
    document.getElementById('tab-anomalies').classList.add('hidden');
    document.getElementById(`tab-${btn.dataset.tab}`).classList.remove('hidden');
  });
});

// ── Utility ───────────────────────────────────────────────────────────────────
function esc(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── US-031: Export ────────────────────────────────────────────────────────────

async function triggerExport(format, type, filename) {
  const res = await apiFetch(`${API}/export?format=${format}&type=${type}`, { method: 'POST' });
  if (!res) return; // plan-gated 403 already showed upgrade modal
  if (!res.ok) {
    const json = await res.json().catch(() => ({}));
    alert(json.detail || 'Erreur lors de l\'export.');
    return;
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

document.getElementById('btn-export-fuel-excel').addEventListener('click', () => {
  triggerExport('excel', 'fuel', 'carburant.xlsx');
});
document.getElementById('btn-export-maint-pdf').addEventListener('click', () => {
  triggerExport('pdf', 'maintenance', 'maintenance.pdf');
});

// ── US-034: WhatsApp config ──────────────────────────────────────────────────

const _btnWA = document.getElementById('btn-whatsapp-config');
if (_btnWA) _btnWA.addEventListener('click', () => {
  document.getElementById('wa-error').classList.add('hidden');
  document.getElementById('wa-success').classList.add('hidden');
  document.getElementById('modal-whatsapp').classList.remove('hidden');
});

['modal-wa-close', 'modal-wa-close2'].forEach(id => {
  document.getElementById(id).addEventListener('click', () => {
    document.getElementById('modal-whatsapp').classList.add('hidden');
  });
});

document.getElementById('btn-save-whatsapp').addEventListener('click', async () => {
  const number = document.getElementById('wa-number-input').value.trim();
  const errEl = document.getElementById('wa-error');
  const okEl = document.getElementById('wa-success');
  errEl.classList.add('hidden');
  okEl.classList.add('hidden');

  const res = await fetch(`${API}/owner/whatsapp`, {
    method: 'PATCH',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ whatsapp_number: number }),
  });

  if (res.ok) {
    okEl.classList.remove('hidden');
    setTimeout(() => document.getElementById('modal-whatsapp').classList.add('hidden'), 1200);
  } else {
    const json = await res.json().catch(() => ({}));
    errEl.textContent = json.detail || 'Erreur lors de la mise à jour.';
    errEl.classList.remove('hidden');
  }
});

// ── Section navigation ────────────────────────────────────────────────────────
const SECTIONS = ['dashboard', 'vehicles', 'drivers', 'fuel'];

function showSection(name) {
  SECTIONS.forEach(s => {
    const el = document.getElementById(`section-${s}`);
    if (el) el.classList.toggle('hidden', s !== name);
  });
  document.querySelectorAll('.nav-link').forEach(link => {
    const isActive = link.dataset.section === name;
    link.classList.toggle('bg-white/10', isActive);
  });
  if (name === 'vehicles') loadVehicles();
  if (name === 'drivers') loadDriverAssignments();
  if (name === 'fuel') loadOwnerFuelEntries();
}

document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', () => showSection(link.dataset.section));
});

// ── Vehicles management ───────────────────────────────────────────────────────
let allVehicles = [];
let currentVehicleTab = 'active';
let editingVehicleId = null;

const FUEL_LABELS = { essence: 'Essence', diesel: 'Diesel', electrique: 'Électrique', hybride: 'Hybride' };
const STATUS_BADGE = {
  active:   '<span class="badge-active   text-xs px-2 py-0.5 rounded-full font-medium">Actif</span>',
  paused:   '<span class="badge-warning  text-xs px-2 py-0.5 rounded-full font-medium">En pause</span>',
  archived: '<span class="badge-inactive text-xs px-2 py-0.5 rounded-full font-medium">Archivé</span>',
};

async function loadVehicles() {
  document.getElementById('vehicles-loading').classList.remove('hidden');
  document.getElementById('vehicles-table').classList.add('hidden');
  document.getElementById('empty-vehicles').classList.add('hidden');
  try {
    const [activeRes, archivedRes] = await Promise.all([
      apiFetch(`${API}/vehicles`),
      apiFetch(`${API}/vehicles/archived`),
    ]);
    const activeData   = activeRes   && activeRes.ok   ? await activeRes.json()   : { data: [] };
    const archivedData = archivedRes && archivedRes.ok ? await archivedRes.json() : { data: [] };
    allVehicles = [...(activeData.data || []), ...(archivedData.data || [])];
    renderVehiclesTab(currentVehicleTab);
  } catch (e) {
    console.error('Erreur chargement véhicules', e);
  } finally {
    document.getElementById('vehicles-loading').classList.add('hidden');
  }
}

function renderVehiclesTab(tab) {
  currentVehicleTab = tab;
  const filtered = allVehicles.filter(v => v.status === tab);
  const tbody = document.getElementById('vehicles-tbody');
  const table = document.getElementById('vehicles-table');
  const empty = document.getElementById('empty-vehicles');

  if (filtered.length === 0) {
    table.classList.add('hidden');
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');
  table.classList.remove('hidden');

  tbody.innerHTML = filtered.map(v => {
    let actions = '';
    if (v.status === 'active') {
      actions = `
        <button class="text-xs text-[#005F02] hover:underline mr-2" onclick="openEditVehicle(${v.id})">Modifier</button>
        <button class="text-xs text-amber-600 hover:underline mr-2" onclick="confirmAction('Mettre ce véhicule en pause ?', () => pauseVehicle(${v.id}))">Pause</button>
        <button class="text-xs text-gray-500 hover:underline" onclick="confirmAction('Archiver ce véhicule ?', () => archiveVehicle(${v.id}))">Archiver</button>`;
    } else if (v.status === 'paused') {
      actions = `
        <button class="text-xs text-[#005F02] hover:underline mr-2" onclick="openEditVehicle(${v.id})">Modifier</button>
        <button class="text-xs text-blue-600 hover:underline mr-2" onclick="confirmAction('Réactiver ce véhicule ?', () => resumeVehicle(${v.id}))">Réactiver</button>
        <button class="text-xs text-gray-500 hover:underline" onclick="confirmAction('Archiver ce véhicule ?', () => archiveVehicle(${v.id}))">Archiver</button>`;
    } else if (v.status === 'archived') {
      actions = `
        <button class="text-xs text-[#005F02] hover:underline" onclick="confirmAction('Restaurer ce véhicule ?', () => restoreVehicle(${v.id}))">Restaurer</button>`;
    }
    return `
      <tr class="border-b last:border-0">
        <td class="py-2 font-medium">${esc(v.name)}</td>
        <td class="py-2 text-gray-500">${esc(v.brand)} ${esc(v.model)}${v.year ? ` (${v.year})` : ''}</td>
        <td class="py-2">${esc(v.license_plate)}</td>
        <td class="py-2">${FUEL_LABELS[v.fuel_type] || esc(v.fuel_type)}</td>
        <td class="py-2">${STATUS_BADGE[v.status] || esc(v.status)}</td>
        <td class="py-2 text-right whitespace-nowrap">${actions}</td>
      </tr>`;
  }).join('');
}

document.querySelectorAll('.vehicle-tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.vehicle-tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderVehiclesTab(btn.dataset.vtab);
  });
});

document.getElementById('btn-add-vehicle').addEventListener('click', () => openVehicleModal());

function openVehicleModal(vehicle = null) {
  editingVehicleId = vehicle ? vehicle.id : null;
  document.getElementById('modal-vehicle-title').textContent =
    vehicle ? 'Modifier le véhicule' : 'Ajouter un véhicule';
  document.getElementById('v-name').value    = vehicle?.name          || '';
  document.getElementById('v-brand').value   = vehicle?.brand         || '';
  document.getElementById('v-model').value   = vehicle?.model         || '';
  document.getElementById('v-plate').value   = vehicle?.license_plate || '';
  document.getElementById('v-fuel').value    = vehicle?.fuel_type     || '';
  document.getElementById('v-mileage').value = vehicle?.initial_mileage ?? '';
  document.getElementById('v-year').value    = vehicle?.year          || '';
  document.getElementById('vehicle-form-error').classList.add('hidden');
  document.getElementById('modal-vehicle').classList.remove('hidden');
}

function openEditVehicle(id) {
  const v = allVehicles.find(v => v.id === id);
  if (v) openVehicleModal(v);
}

['modal-vehicle-close', 'modal-vehicle-cancel'].forEach(id => {
  document.getElementById(id).addEventListener('click', () => {
    document.getElementById('modal-vehicle').classList.add('hidden');
  });
});

document.getElementById('btn-save-vehicle').addEventListener('click', async () => {
  const errEl = document.getElementById('vehicle-form-error');
  errEl.classList.add('hidden');

  const name          = document.getElementById('v-name').value.trim();
  const brand         = document.getElementById('v-brand').value.trim();
  const model         = document.getElementById('v-model').value.trim();
  const license_plate = document.getElementById('v-plate').value.trim();
  const fuel_type     = document.getElementById('v-fuel').value;
  const mileageRaw    = document.getElementById('v-mileage').value;
  const yearRaw       = document.getElementById('v-year').value;

  if (!name || !brand || !model || !license_plate || !fuel_type) {
    errEl.textContent = 'Veuillez remplir tous les champs obligatoires (*).';
    errEl.classList.remove('hidden');
    return;
  }
  if (!editingVehicleId && mileageRaw === '') {
    errEl.textContent = 'Le kilométrage initial est obligatoire.';
    errEl.classList.remove('hidden');
    return;
  }

  const body = { name, brand, model, license_plate, fuel_type };
  if (mileageRaw !== '') body.initial_mileage = parseFloat(mileageRaw);
  if (yearRaw)           body.year = parseInt(yearRaw);

  const isEdit = editingVehicleId !== null;
  const res = await apiFetch(
    isEdit ? `${API}/vehicles/${editingVehicleId}` : `${API}/vehicles`,
    { method: isEdit ? 'PATCH' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
  );
  if (!res) return;
  if (res.ok) {
    document.getElementById('modal-vehicle').classList.add('hidden');
    loadVehicles();
  } else {
    const json = await res.json().catch(() => ({}));
    errEl.textContent = json.detail || 'Erreur lors de l\'enregistrement.';
    errEl.classList.remove('hidden');
  }
});

async function vehicleAction(path) {
  const res = await apiFetch(`${API}/vehicles/${path}`, { method: 'POST' });
  if (res && res.ok) loadVehicles();
  else if (res) { const j = await res.json().catch(() => ({})); alert(j.detail || 'Erreur.'); }
}

function pauseVehicle(id)   { vehicleAction(`${id}/pause`); }
function resumeVehicle(id)  { vehicleAction(`${id}/resume`); }
function archiveVehicle(id) { vehicleAction(`${id}/archive`); }
function restoreVehicle(id) { vehicleAction(`${id}/restore`); }

// ── Drivers management ────────────────────────────────────────────────────────
let activeVehiclesList = [];

async function loadDriverAssignments() {
  document.getElementById('drivers-mgmt-loading').classList.remove('hidden');
  document.getElementById('drivers-mgmt-table').classList.add('hidden');
  document.getElementById('empty-drivers-mgmt').classList.add('hidden');
  try {
    const res = await apiFetch(`${API}/vehicles`);
    if (!res || !res.ok) return;
    const json = await res.json();
    activeVehiclesList = json.data || [];

    const results = await Promise.all(
      activeVehiclesList.map(v =>
        apiFetch(`${API}/vehicles/${v.id}/drivers`)
          .then(r => r && r.ok ? r.json() : { data: [] })
          .then(d => ({ vehicle: v, drivers: d.data || [] }))
      )
    );
    renderDriverAssignments(results);
    updateAssignVehicleSelect(activeVehiclesList);
  } catch (e) {
    console.error('Erreur chargement chauffeurs', e);
  } finally {
    document.getElementById('drivers-mgmt-loading').classList.add('hidden');
  }
}

function renderDriverAssignments(vehiclesWithDrivers) {
  const tbody = document.getElementById('drivers-mgmt-tbody');
  const table = document.getElementById('drivers-mgmt-table');
  const empty = document.getElementById('empty-drivers-mgmt');

  const rows = [];
  vehiclesWithDrivers.forEach(({ vehicle, drivers }) => {
    drivers.forEach(d => {
      const badge = d.driving_status
        ? '<span class="badge-active   text-xs px-2 py-0.5 rounded-full font-medium">En conduite</span>'
        : '<span class="badge-inactive text-xs px-2 py-0.5 rounded-full font-medium">Inactif</span>';
      rows.push(`
        <tr class="border-b last:border-0">
          <td class="py-2 font-medium">${esc(d.full_name)}</td>
          <td class="py-2 text-gray-500">${esc(vehicle.name)}</td>
          <td class="py-2">${badge}</td>
          <td class="py-2 text-right">
            <button class="text-xs text-red-600 hover:underline"
              onclick="confirmAction('Retirer ce chauffeur du véhicule ?', () => removeDriver(${vehicle.id}, ${d.id}))">
              Retirer
            </button>
          </td>
        </tr>`);
    });
  });

  if (rows.length === 0) {
    table.classList.add('hidden');
    empty.classList.remove('hidden');
  } else {
    empty.classList.add('hidden');
    table.classList.remove('hidden');
    tbody.innerHTML = rows.join('');
  }
}

function updateAssignVehicleSelect(vehicles) {
  const select = document.getElementById('assign-vehicle-id');
  select.innerHTML = vehicles.length
    ? vehicles.map(v => `<option value="${v.id}">${esc(v.name)} — ${esc(v.license_plate)}</option>`).join('')
    : '<option value="">Aucun véhicule actif</option>';
}

document.getElementById('btn-assign-driver').addEventListener('click', () => {
  document.getElementById('assign-error').classList.add('hidden');
  document.getElementById('assign-success').classList.add('hidden');
  document.getElementById('assign-driver-id').value = '';
  updateAssignVehicleSelect(activeVehiclesList);
  document.getElementById('modal-assign-driver').classList.remove('hidden');
});

['modal-assign-close', 'modal-assign-cancel'].forEach(id => {
  document.getElementById(id).addEventListener('click', () => {
    document.getElementById('modal-assign-driver').classList.add('hidden');
  });
});

document.getElementById('btn-do-assign').addEventListener('click', async () => {
  const errEl = document.getElementById('assign-error');
  const okEl  = document.getElementById('assign-success');
  errEl.classList.add('hidden');
  okEl.classList.add('hidden');

  const vehicleId = document.getElementById('assign-vehicle-id').value;
  const driverIdRaw = document.getElementById('assign-driver-id').value.trim();

  if (!vehicleId || !driverIdRaw) {
    errEl.textContent = 'Veuillez sélectionner un véhicule et entrer l\'ID du chauffeur.';
    errEl.classList.remove('hidden');
    return;
  }

  const res = await apiFetch(`${API}/vehicles/${vehicleId}/drivers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ driver_id: parseInt(driverIdRaw) }),
  });
  if (!res) return;
  if (res.ok) {
    okEl.textContent = 'Chauffeur assigné avec succès.';
    okEl.classList.remove('hidden');
    setTimeout(() => {
      document.getElementById('modal-assign-driver').classList.add('hidden');
      loadDriverAssignments();
    }, 1200);
  } else {
    const json = await res.json().catch(() => ({}));
    errEl.textContent = json.detail || 'Erreur lors de l\'assignation.';
    errEl.classList.remove('hidden');
  }
});

async function removeDriver(vehicleId, driverId) {
  const res = await apiFetch(`${API}/vehicles/${vehicleId}/drivers/${driverId}`, { method: 'DELETE' });
  if (res && res.ok) loadDriverAssignments();
  else if (res) { const j = await res.json().catch(() => ({})); alert(j.detail || 'Erreur.'); }
}

// ── Confirm modal ─────────────────────────────────────────────────────────────
let confirmCallback = null;

function confirmAction(msg, callback) {
  document.getElementById('confirm-msg').textContent = msg;
  confirmCallback = callback;
  document.getElementById('modal-confirm').classList.remove('hidden');
}

document.getElementById('confirm-cancel').addEventListener('click', () => {
  document.getElementById('modal-confirm').classList.add('hidden');
  confirmCallback = null;
});

document.getElementById('confirm-ok').addEventListener('click', () => {
  document.getElementById('modal-confirm').classList.add('hidden');
  if (confirmCallback) confirmCallback();
  confirmCallback = null;
});

// ── Owner fuel entries (Sprint 10 — route tracking) ───────────────────────────
async function loadOwnerFuelEntries() {
  const loading = document.getElementById('fuel-loading');
  const table   = document.getElementById('fuel-table');
  const empty   = document.getElementById('empty-fuel');
  if (!loading) return;
  loading.classList.remove('hidden');
  table.classList.add('hidden');
  empty.classList.add('hidden');

  try {
    const [entriesRes, driversRes] = await Promise.all([
      fetch(`${API}/owner/fuel-entries`, { headers: authHeader() }),
      fetch(`${API}/drivers`, { headers: authHeader() }),
    ]);
    if (!entriesRes.ok) { loading.classList.add('hidden'); return; }

    const entries = (await entriesRes.json()).data || [];
    const driverList = driversRes.ok ? ((await driversRes.json()).data || []) : [];
    const driverMap = {};
    driverList.forEach(d => { driverMap[d.id] = d.username || d.full_name || `#${d.id}`; });

    loading.classList.add('hidden');
    if (!entries.length) { empty.classList.remove('hidden'); return; }

    table.classList.remove('hidden');
    document.getElementById('fuel-tbody').innerHTML = entries.map(e => {
      const conso = e.consumption_per_100km
        ? parseFloat(e.consumption_per_100km).toFixed(2) + ' L'
        : '<span class="text-gray-300">—</span>';

      const hasRoute = e.departure_place && e.destination_place;
      const trajet = hasRoute
        ? `<span class="text-xs text-gray-700">${esc(e.departure_place)} → ${esc(e.destination_place)}</span>`
        : '<span class="text-gray-300">—</span>';

      let distanceCell = '<span class="text-gray-300">—</span>';
      if (hasRoute && e.route_distance_km) {
        const routeKm  = parseFloat(e.route_distance_km);
        const odoKm    = e.distance_km ? parseInt(e.distance_km) : null;
        const hasGap   = odoKm !== null && Math.abs(routeKm - odoKm) / Math.max(routeKm, 1) > 0.20;
        distanceCell = `<span class="font-medium ${hasGap ? 'text-amber-600' : 'text-[#005F02]'}">
          ${routeKm.toLocaleString('fr-FR')} km
          ${hasGap ? '<span title="Écart > 20% entre la distance Google et le relevé kilométrique" class="ml-1 cursor-help">⚠️</span>' : ''}
        </span>`;
      }

      return `<tr class="border-b last:border-0">
        <td class="py-2 whitespace-nowrap">${new Date(e.date).toLocaleDateString('fr-FR')}</td>
        <td class="py-2 text-gray-600">${esc(driverMap[e.driver_id] || `#${e.driver_id}`)}</td>
        <td class="py-2 text-gray-600">${esc(allVehicles.find(v => v.id === e.vehicle_id)?.name || `#${e.vehicle_id}`)}</td>
        <td class="py-2 text-right">${parseInt(e.odometer_km).toLocaleString('fr-FR')}</td>
        <td class="py-2 text-right">${parseFloat(e.quantity_litres).toFixed(1)}</td>
        <td class="py-2 text-right font-medium">${parseFloat(e.amount_fcfa).toLocaleString('fr-FR')}</td>
        <td class="py-2 text-right">${conso}</td>
        <td class="py-2 max-w-xs">${trajet}</td>
        <td class="py-2 text-right whitespace-nowrap">${distanceCell}</td>
      </tr>`;
    }).join('');
  } catch (err) {
    console.error('Erreur saisies carburant', err);
    loading.classList.add('hidden');
  }
}

// ── Boot ──────────────────────────────────────────────────────────────────────
loadMe();
loadDashboard();
loadPlanUsage();
