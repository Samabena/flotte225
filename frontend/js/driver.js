/* driver.js — Driver dashboard (US-022, US-023) */

const API = '/api/v1';
const token = () => localStorage.getItem('access_token');
const authHeader = () => ({ 'Authorization': `Bearer ${token()}` });

if (!token()) window.location.href = '/';

document.getElementById('btn-logout').addEventListener('click', () => {
  localStorage.clear();
  window.location.href = '/';
});

// ── Restore persisted state ───────────────────────────────────────────────────
// ── Greeting ──────────────────────────────────────────────────────────────────
function greetingWord() {
  const hour = new Date(
    new Date().toLocaleString('en-US', { timeZone: 'Africa/Abidjan' })
  ).getHours();
  return hour >= 18 ? 'Bonsoir' : 'Bonjour';
}

function setGreeting(name) {
  document.getElementById('greeting-word').textContent = greetingWord();
  if (name) document.getElementById('driver-name').textContent = name;
}

const savedName   = localStorage.getItem('driver_full_name');
const savedStatus = localStorage.getItem('driver_driving_status') === 'true';
const savedVehicle = localStorage.getItem('driver_active_vehicle_name') || '—';

setGreeting(savedName);
applyStatus(savedStatus, savedVehicle);

// ── Assigned vehicles ─────────────────────────────────────────────────────────
let assignedVehicles = [];

async function loadVehicles() {
  try {
    const res = await fetch(`${API}/driver/vehicles`, { headers: authHeader() });
    if (res.status === 401 || res.status === 403) {
      window.location.href = '/'; return;
    }
    const json = await res.json();
    assignedVehicles = json.data || [];
    renderVehicles(assignedVehicles);
    populateSelect(assignedVehicles);
  } catch (e) {
    console.error('Erreur véhicules', e);
  } finally {
    document.getElementById('vehicles-loading').classList.add('hidden');
  }
}

function renderVehicles(vehicles) {
  const tbody = document.getElementById('vehicles-tbody');
  const table = document.getElementById('vehicles-table');
  const empty = document.getElementById('empty-vehicles');
  const FUEL  = { essence: 'Essence', diesel: 'Diesel', electrique: 'Électrique', hybride: 'Hybride' };

  if (!vehicles.length) { empty.classList.remove('hidden'); return; }
  table.classList.remove('hidden');
  tbody.innerHTML = vehicles.map(v => `
    <tr class="border-b last:border-0">
      <td class="py-2 font-medium">${esc(v.name)}</td>
      <td class="py-2 text-gray-500">${esc(v.brand)} ${esc(v.model)}${v.year ? ` (${v.year})` : ''}</td>
      <td class="py-2">${esc(v.license_plate)}</td>
      <td class="py-2">${FUEL[v.fuel_type] || esc(v.fuel_type)}</td>
    </tr>`).join('');
}

function populateSelect(vehicles) {
  const sel = document.getElementById('vehicle-select');
  if (!vehicles.length) {
    sel.innerHTML = '<option value="">Aucun véhicule assigné</option>';
    return;
  }
  sel.innerHTML = '<option value="">— Sélectionner —</option>' + vehicles.map(v =>
    `<option value="${v.id}">${esc(v.name)} — ${esc(v.license_plate)}</option>`
  ).join('');
}

// ── Status UI (badge and card hidden from UI — state managed internally) ──────
function applyStatus(isDriving, vehicleName) {
  const actBlock   = document.getElementById('activate-block');
  const deactBlock = document.getElementById('deactivate-block');
  if (isDriving) {
    actBlock.classList.add('hidden');
    deactBlock.classList.remove('hidden');
    document.getElementById('active-vehicle-name').textContent = vehicleName || '—';
  } else {
    actBlock.classList.remove('hidden');
    deactBlock.classList.add('hidden');
  }
}

function persistStatus(summary, vehicleName) {
  localStorage.setItem('driver_full_name', summary.full_name || '');
  localStorage.setItem('driver_driving_status', summary.driving_status ? 'true' : 'false');
  localStorage.setItem('driver_active_vehicle_name', vehicleName || '');
  setGreeting(summary.full_name || 'Chauffeur');
}

// ── Activate (auto on vehicle select) ────────────────────────────────────────
document.getElementById('vehicle-select').addEventListener('change', async () => {
  const errEl    = document.getElementById('status-error');
  const sel      = document.getElementById('vehicle-select');
  const vehicleId = sel.value;
  errEl.classList.add('hidden');

  if (!vehicleId) return;

  sel.disabled = true;
  const selectedVehicle = assignedVehicles.find(v => v.id == vehicleId);
  const vehicleName = selectedVehicle ? `${selectedVehicle.name} (${selectedVehicle.license_plate})` : '';

  const res = await fetch(`${API}/driver/activate`, {
    method: 'POST',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ vehicle_id: parseInt(vehicleId) }),
  });

  sel.disabled = false;
  const json = await res.json().catch(() => ({}));
  if (res.ok) {
    persistStatus(json.data || {}, vehicleName);
    applyStatus(true, vehicleName);
  } else {
    errEl.textContent = json.detail || 'Erreur lors de l\'activation.';
    errEl.classList.remove('hidden');
  }
});

// ── Deactivate ────────────────────────────────────────────────────────────────
document.getElementById('btn-deactivate').addEventListener('click', async () => {
  const errEl = document.getElementById('status-error');
  errEl.classList.add('hidden');

  const res = await fetch(`${API}/driver/deactivate`, {
    method: 'POST',
    headers: authHeader(),
  });

  const json = await res.json().catch(() => ({}));
  if (res.ok) {
    persistStatus(json.data || {}, '');
    applyStatus(false, '');
  } else {
    errEl.textContent = json.detail || 'Erreur lors de la désactivation.';
    errEl.classList.remove('hidden');
  }
});

// ── Recent fuel entries (last 5 preview) ─────────────────────────────────────
async function loadRecentFuel() {
  try {
    const res = await fetch(`${API}/fuel`, { headers: authHeader() });
    if (!res.ok) return;
    const json = await res.json();
    renderFuelPreview((json.data || []).slice(0, 5));
  } catch (e) {
    console.error('Erreur saisies', e);
  } finally {
    document.getElementById('fuel-loading').classList.add('hidden');
  }
}

function renderFuelPreview(entries) {
  const tbody = document.getElementById('fuel-tbody');
  const table = document.getElementById('fuel-table');
  const empty = document.getElementById('empty-fuel');

  if (!entries.length) { empty.classList.remove('hidden'); return; }
  table.classList.remove('hidden');

  const vMap = {};
  assignedVehicles.forEach(v => { vMap[v.id] = v.name; });

  tbody.innerHTML = entries.map(e => `
    <tr class="border-b last:border-0">
      <td class="py-2">${new Date(e.date).toLocaleDateString('fr-FR')}</td>
      <td class="py-2 text-gray-500">${esc(vMap[e.vehicle_id] || `#${e.vehicle_id}`)}</td>
      <td class="py-2 text-right">${parseFloat(e.quantity_litres).toFixed(1)}</td>
      <td class="py-2 text-right font-medium">${parseFloat(e.amount_fcfa).toLocaleString('fr-FR')}</td>
    </tr>`).join('');
}

// ── Utility ───────────────────────────────────────────────────────────────────
function esc(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Boot ──────────────────────────────────────────────────────────────────────
loadVehicles().then(() => loadRecentFuel());
