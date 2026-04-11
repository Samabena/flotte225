/* dashboard.js — Owner dashboard (Sprint 5 + 6) */

const API = '/api/v1';
const token = () => localStorage.getItem('access_token');
const authHeader = () => ({ 'Authorization': `Bearer ${token()}` });

// ── Redirect if not logged in ────────────────────────────────────────────────
if (!token()) {
  window.location.href = 'index.html';
}

document.getElementById('btn-logout').addEventListener('click', () => {
  localStorage.clear();
  window.location.href = 'index.html';
});

document.getElementById('upgrade-modal-close').addEventListener('click', () => {
  document.getElementById('modal-upgrade').classList.add('hidden');
});

// ── Fetch dashboard data ─────────────────────────────────────────────────────
async function loadDashboard() {
  let data;
  try {
    const res = await fetch(`${API}/dashboard/owner`, { headers: authHeader() });
    if (res.status === 401 || res.status === 403) {
      window.location.href = 'index.html';
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
}

// ── Fetch plan usage (US-046) ────────────────────────────────────────────────
async function loadPlanUsage() {
  try {
    const res = await fetch(`${API}/subscription/my-plan`, { headers: authHeader() });
    if (!res.ok) return;
    const json = await res.json();
    renderPlanUsage(json.data);
  } catch (e) {
    // Plan section stays hidden on error
  }
}

// ── KPI cards ────────────────────────────────────────────────────────────────
function renderKPIs(data) {
  const totalSpend = parseFloat(data.financial.total_spend_fcfa) || 0;
  document.getElementById('kpi-total-spend').textContent =
    totalSpend.toLocaleString('fr-FR') + ' FCFA';

  const activeVehicles = data.consumption.filter(v => v.entry_count >= 0).length;
  document.getElementById('kpi-active-vehicles').textContent = activeVehicles;

  const activeDrivers = data.drivers.filter(d => d.driving_status).length;
  document.getElementById('kpi-active-drivers').textContent = activeDrivers;
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

// ── US-034: WhatsApp config ────────────────────────────────────────────────────

document.getElementById('btn-whatsapp-config').addEventListener('click', () => {
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

// ── Boot ──────────────────────────────────────────────────────────────────────
loadDashboard();
loadPlanUsage();
