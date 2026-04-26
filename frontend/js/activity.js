/* activity.js — Filterable activity log (Sprint 5 / US-025) */

const API = '/api/v1';
const token = () => localStorage.getItem('access_token');
const authHeader = () => ({ 'Authorization': `Bearer ${token()}` });

const LIMIT = 50;
let currentOffset = 0;
let currentDriverId = '';
let currentVehicleId = '';
let currentTotal = 0;

if (!token()) {
  window.location.href = '/';
}

document.getElementById('btn-logout').addEventListener('click', () => {
  localStorage.clear();
  window.location.href = '/';
});

// ── Populate filter dropdowns ─────────────────────────────────────────────────
async function loadFilters() {
  try {
    // Load vehicles
    const vRes = await fetch(`${API}/vehicles`, { headers: authHeader() });
    if (vRes.status === 401 || vRes.status === 403) {
      localStorage.clear();
      window.location.href = '/';
      return;
    }
    const vData = await vRes.json();
    const vehicleSelect = document.getElementById('filter-vehicle');
    (vData.data || []).forEach(v => {
      const opt = document.createElement('option');
      opt.value = v.id;
      opt.textContent = v.name;
      vehicleSelect.appendChild(opt);
    });

    // Load drivers from dashboard
    const dRes = await fetch(`${API}/dashboard/owner`, { headers: authHeader() });
    if (dRes.status === 401 || dRes.status === 403) {
      localStorage.clear();
      window.location.href = '/';
      return;
    }
    const dData = await dRes.json();
    const driverSelect = document.getElementById('filter-driver');
    (dData.data?.drivers || []).forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.driver_id;
      opt.textContent = d.full_name;
      driverSelect.appendChild(opt);
    });
  } catch (e) {
    console.error('Erreur chargement filtres', e);
  }
}

// ── Fetch and render logs ─────────────────────────────────────────────────────
async function loadLogs(offset = 0) {
  const params = new URLSearchParams({ limit: LIMIT, offset });
  if (currentDriverId) params.set('driver_id', currentDriverId);
  if (currentVehicleId) params.set('vehicle_id', currentVehicleId);

  try {
    const res = await fetch(`${API}/owner/activity-logs?${params}`, { headers: authHeader() });
    if (res.status === 401 || res.status === 403) {
      localStorage.clear();
      window.location.href = '/';
      return;
    }
    const json = await res.json();
    const logs = json.data || [];
    renderTable(logs);
    updatePagination(logs.length, offset);
  } catch (e) {
    console.error('Erreur chargement journal', e);
  }
}

function renderTable(logs) {
  const tbody = document.getElementById('activity-tbody');
  const empty = document.getElementById('empty-activity');

  if (logs.length === 0) {
    tbody.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  tbody.innerHTML = logs.map(log => {
    const date = new Date(log.created_at).toLocaleString('fr-FR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
    const actionClass = {
      CREATE: 'badge-create',
      UPDATE: 'badge-update',
      DELETE: 'badge-delete',
    }[log.action] || '';
    const actionLabel = {
      CREATE: 'Création',
      UPDATE: 'Modification',
      DELETE: 'Suppression',
    }[log.action] || log.action;

    return `
      <tr class="border-b last:border-0 hover:bg-gray-50">
        <td class="px-4 py-3 text-gray-500">${esc(date)}</td>
        <td class="px-4 py-3 font-medium">${esc(log.driver_name || '—')}</td>
        <td class="px-4 py-3">${esc(log.vehicle_name || '—')}</td>
        <td class="px-4 py-3">
          <span class="${actionClass} text-xs px-2 py-0.5 rounded-full font-medium">${esc(actionLabel)}</span>
        </td>
      </tr>`;
  }).join('');
}

function updatePagination(count, offset) {
  const hasMore = count === LIMIT;
  const hasPrev = offset > 0;
  const page = Math.floor(offset / LIMIT) + 1;

  document.getElementById('btn-prev').disabled = !hasPrev;
  document.getElementById('btn-next').disabled = !hasMore;
  document.getElementById('pagination-info').textContent =
    count > 0 ? `Page ${page}` : '';

  currentOffset = offset;
}

// ── Filter controls ───────────────────────────────────────────────────────────
document.getElementById('btn-filter').addEventListener('click', () => {
  currentDriverId = document.getElementById('filter-driver').value;
  currentVehicleId = document.getElementById('filter-vehicle').value;
  loadLogs(0);
});

document.getElementById('btn-clear').addEventListener('click', () => {
  currentDriverId = '';
  currentVehicleId = '';
  document.getElementById('filter-driver').value = '';
  document.getElementById('filter-vehicle').value = '';
  loadLogs(0);
});

document.getElementById('btn-prev').addEventListener('click', () => {
  if (currentOffset >= LIMIT) loadLogs(currentOffset - LIMIT);
});

document.getElementById('btn-next').addEventListener('click', () => {
  loadLogs(currentOffset + LIMIT);
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
loadFilters();
loadLogs(0);
