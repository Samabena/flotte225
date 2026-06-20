/* driver.js — Driver dashboard (US-022, US-023) */

const API = '/api/v1';
const token = () => localStorage.getItem('access_token');
const authHeader = () => ({ 'Authorization': `Bearer ${token()}` });

if (!token()) window.location.href = '/login';

document.getElementById('btn-logout').addEventListener('click', () => {
  localStorage.clear();
  window.location.href = '/login';
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

const savedName    = localStorage.getItem('driver_full_name');
const savedStatus  = localStorage.getItem('driver_driving_status') === 'true';
const savedVehicle = localStorage.getItem('driver_active_vehicle_name') || '—';
const savedStartKm = localStorage.getItem('driver_active_start_km') || '—';

setGreeting(savedName);
applyStatus(savedStatus, savedVehicle, savedStartKm);

// ── Assigned vehicles ─────────────────────────────────────────────────────────
let assignedVehicles = [];

async function loadVehicles() {
  try {
    const res = await fetch(`${API}/driver/vehicles`, { headers: authHeader() });
    if (res.status === 401 || res.status === 403) {
      window.location.href = '/login'; return;
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
  const opts = vehicles.length
    ? '<option value="">— Sélectionner —</option>' + vehicles.map(v =>
        `<option value="${v.id}">${esc(v.name)} — ${esc(v.license_plate)}</option>`).join('')
    : '<option value="">Aucun véhicule assigné</option>';

  const sel = document.getElementById('vehicle-select');
  if (sel) sel.innerHTML = opts;

  // Same vehicle list feeds the maintenance-expense form
  const meSel = document.getElementById('me-vehicle');
  if (meSel) meSel.innerHTML = opts;
}

// ── Status UI (badge and card hidden from UI — state managed internally) ──────
function applyStatus(isDriving, vehicleName, startKm) {
  const actBlock   = document.getElementById('activate-block');
  const deactBlock = document.getElementById('deactivate-block');
  if (isDriving) {
    actBlock.classList.add('hidden');
    deactBlock.classList.remove('hidden');
    document.getElementById('active-vehicle-name').textContent = vehicleName || '—';
    if (startKm !== undefined) {
      document.getElementById('active-start-km').textContent = startKm || '—';
    }
  } else {
    actBlock.classList.remove('hidden');
    deactBlock.classList.add('hidden');
  }
}

function persistStatus(summary, vehicleName, startKm) {
  localStorage.setItem('driver_full_name', summary.full_name || '');
  localStorage.setItem('driver_driving_status', summary.driving_status ? 'true' : 'false');
  localStorage.setItem('driver_active_vehicle_name', vehicleName || '');
  if (startKm !== undefined) {
    localStorage.setItem('driver_active_start_km', startKm == null ? '' : String(startKm));
  }
  setGreeting(summary.full_name || 'Chauffeur');
}

function showStatusError(msg) {
  const el = document.getElementById('status-error');
  el.textContent = msg;
  el.className = 'mt-3 text-sm bg-red-50 border border-red-100 text-red-700 rounded-lg px-3 py-2';
}

function showStatusOk(msg) {
  const el = document.getElementById('status-error');
  el.textContent = msg;
  el.className = 'mt-3 text-sm bg-green-50 border border-green-100 text-green-700 rounded-lg px-3 py-2';
  setTimeout(() => el.classList.add('hidden'), 6000);
}

// ── Prendre le véhicule (démarrer un trajet) ─────────────────────────────────
document.getElementById('btn-activate').addEventListener('click', async () => {
  const errEl     = document.getElementById('status-error');
  const sel       = document.getElementById('vehicle-select');
  const kmInput   = document.getElementById('start-odometer');
  const vehicleId = sel.value;
  const startKm   = kmInput.value;
  errEl.classList.add('hidden');

  if (!vehicleId) { showStatusError('Veuillez sélectionner un véhicule.'); return; }
  if (startKm === '' || isNaN(parseInt(startKm))) {
    showStatusError('Veuillez saisir le kilométrage au départ.'); return;
  }

  const btn = document.getElementById('btn-activate');
  btn.disabled = true;
  const selectedVehicle = assignedVehicles.find(v => v.id == vehicleId);
  const vehicleName = selectedVehicle ? `${selectedVehicle.name} (${selectedVehicle.license_plate})` : '';

  // Offline-first: send now, or queue and sync on reconnect (idempotent via client_uuid).
  const result = await Flotte.queueOrSend({
    type: 'trip-start',
    url: `${API}/driver/activate`,
    body: { vehicle_id: parseInt(vehicleId), start_odometer: parseInt(startKm) },
  });

  btn.disabled = false;
  if (result.ok) {
    // Optimistic UI for both online and queued (offline) cases.
    persistStatus(result.data || { driving_status: true }, vehicleName, parseInt(startKm));
    applyStatus(true, vehicleName, parseInt(startKm));
    kmInput.value = '';
    if (result.queued) {
      showStatusOk('Pas de réseau — trajet démarré, sera synchronisé automatiquement.');
    }
  } else {
    const detail = result.json && result.json.detail;
    showStatusError((Array.isArray(detail) ? detail.map(d => d.msg).join(' · ') : detail)
      || 'Erreur lors de la prise du véhicule.');
  }
});

// ── Rendre le véhicule (terminer le trajet) ──────────────────────────────────
document.getElementById('btn-deactivate').addEventListener('click', async () => {
  const errEl   = document.getElementById('status-error');
  const kmInput = document.getElementById('end-odometer');
  const endKm   = kmInput.value;
  errEl.classList.add('hidden');

  if (endKm === '' || isNaN(parseInt(endKm))) {
    showStatusError('Veuillez saisir le kilométrage au retour.'); return;
  }

  const btn = document.getElementById('btn-deactivate');
  btn.disabled = true;
  const result = await Flotte.queueOrSend({
    type: 'trip-end',
    url: `${API}/driver/deactivate`,
    body: { end_odometer: parseInt(endKm) },
  });

  btn.disabled = false;
  if (result.ok) {
    persistStatus(result.data || { driving_status: false }, '', '');
    applyStatus(false, '', '');
    kmInput.value = '';
    if (result.queued) {
      showStatusOk('Pas de réseau — fin de trajet enregistrée, sera synchronisée automatiquement.');
    }
  } else {
    const detail = result.json && result.json.detail;
    showStatusError((Array.isArray(detail) ? detail.map(d => d.msg).join(' · ') : detail)
      || 'Erreur lors de la remise du véhicule.');
  }
});

// ── Maintenance expense (logged by the driver, for an assigned vehicle) ───────
(function initExpenseDate() {
  const d = document.getElementById('me-date');
  if (d && !d.value) d.value = new Date().toISOString().slice(0, 10);
})();

document.getElementById('btn-add-expense')?.addEventListener('click', async () => {
  const errEl = document.getElementById('me-error');
  const okEl  = document.getElementById('me-success');
  errEl.classList.add('hidden');
  okEl.classList.add('hidden');

  const vehicleId = document.getElementById('me-vehicle').value;
  const date      = document.getElementById('me-date').value;
  const type      = document.getElementById('me-type').value;
  const km        = document.getElementById('me-km').value;
  const cost      = document.getElementById('me-cost').value;
  const location  = document.getElementById('me-location').value.trim();

  const fail = (m) => { errEl.textContent = m; errEl.classList.remove('hidden'); };
  if (!vehicleId) return fail('Veuillez sélectionner un véhicule.');
  if (!date)      return fail('Veuillez indiquer la date.');
  if (cost === '' || parseFloat(cost) <= 0) return fail('Le coût doit être supérieur à 0.');

  const body = { date, type, cost_fcfa: parseFloat(cost) };
  if (km) body.odometer_km = parseInt(km);
  if (location) body.location = location;

  const clearForm = () => {
    document.getElementById('me-km').value = '';
    document.getElementById('me-cost').value = '';
    document.getElementById('me-location').value = '';
  };

  const btn = document.getElementById('btn-add-expense');
  btn.disabled = true;

  // Offline-first: send now, or queue locally and sync on reconnect (idempotent).
  const result = await Flotte.queueOrSend({
    type: 'expense',
    url: `${API}/driver/vehicles/${vehicleId}/maintenance-expenses`,
    body,
  });

  btn.disabled = false;
  if (result.ok && result.queued) {
    okEl.textContent = 'Pas de réseau — dépense enregistrée et sera synchronisée automatiquement.';
    okEl.classList.remove('hidden');
    clearForm();
    setTimeout(() => okEl.classList.add('hidden'), 6000);
  } else if (result.ok) {
    okEl.textContent = 'Dépense enregistrée. Votre responsable la verra dans le tableau de bord.';
    okEl.classList.remove('hidden');
    clearForm();
    setTimeout(() => okEl.classList.add('hidden'), 5000);
  } else {
    const detail = result.json && result.json.detail;
    fail(Array.isArray(detail) ? detail.map(d => d.msg).join(' · ') : (detail || "Erreur lors de l'enregistrement."));
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
