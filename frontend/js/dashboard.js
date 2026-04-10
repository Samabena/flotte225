/* dashboard.js — Owner dashboard (Sprint 5) */

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
  renderConsumption(data.consumption);
  renderDrivers(data.drivers);
  renderAlerts(data.alerts);
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

// ── Boot ──────────────────────────────────────────────────────────────────────
loadDashboard();
