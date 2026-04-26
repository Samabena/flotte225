/* maintenance.js — Fleet maintenance management (US-015, US-016) */

const API = '/api/v1';
const token = () => localStorage.getItem('access_token');
const authHeader = () => ({ 'Authorization': `Bearer ${token()}` });

if (!token()) window.location.href = '/';

document.getElementById('btn-logout').addEventListener('click', () => {
  localStorage.clear();
  window.location.href = '/';
});

// ── State ─────────────────────────────────────────────────────────────────────
let allVehicles = [];
let selectedVehicleId = null;

// ── Load vehicles ─────────────────────────────────────────────────────────────
async function loadVehicles() {
  try {
    const res = await fetch(`${API}/vehicles`, { headers: authHeader() });
    if (res.status === 401 || res.status === 403) {
      window.location.href = '/'; return;
    }
    const json = await res.json();
    allVehicles = json.data || [];
    populateSelect(allVehicles);
    loadOverview(allVehicles);
  } catch (e) {
    console.error('Erreur chargement véhicules', e);
  }
}

function populateSelect(vehicles) {
  const sel  = document.getElementById('vehicle-select');
  const hint = document.getElementById('no-vehicles-hint');
  if (!vehicles.length) {
    sel.innerHTML = '<option value="">Aucun véhicule actif</option>';
    hint.classList.remove('hidden');
    return;
  }
  hint.classList.add('hidden');
  sel.innerHTML = '<option value="">— Choisir un véhicule —</option>' +
    vehicles.map(v => `<option value="${v.id}">${esc(v.name)} — ${esc(v.license_plate)}</option>`).join('');
}

document.getElementById('vehicle-select').addEventListener('change', async (e) => {
  const id = e.target.value;
  if (!id) {
    document.getElementById('maintenance-panel').classList.add('hidden');
    selectedVehicleId = null;
    return;
  }
  selectedVehicleId = parseInt(id);
  await loadMaintenance(selectedVehicleId);
  document.getElementById('maintenance-panel').classList.remove('hidden');
});

// ── Load maintenance record for one vehicle ───────────────────────────────────
async function loadMaintenance(vehicleId) {
  document.getElementById('maint-error').classList.add('hidden');
  document.getElementById('maint-success').classList.add('hidden');

  try {
    const res = await fetch(`${API}/vehicles/${vehicleId}/maintenance`, { headers: authHeader() });
    if (!res.ok) return;
    const json = await res.json();
    const m = json.data || {};
    fillForm(m);
    renderStatusBadges(m);
  } catch (e) {
    console.error('Erreur maintenance', e);
  }
}

function fillForm(m) {
  document.getElementById('m-oil-km').value     = m.last_oil_change_km  ?? '';
  document.getElementById('m-insurance').value  = m.insurance_expiry    ?? '';
  document.getElementById('m-inspection').value = m.inspection_expiry   ?? '';
}

function renderStatusBadges(m) {
  const today = new Date();

  const oilEl = document.getElementById('oil-status');
  if (m.last_oil_change_km != null) {
    oilEl.textContent = `${parseInt(m.last_oil_change_km).toLocaleString('fr-FR')} km`;
    oilEl.className = 'text-sm font-semibold text-gray-700';
  } else {
    oilEl.textContent = 'Non renseigné';
    oilEl.className = 'text-sm font-semibold text-gray-400';
  }

  setExpiryBadge(document.getElementById('insurance-status'),  m.insurance_expiry,  today);
  setExpiryBadge(document.getElementById('inspection-status'), m.inspection_expiry, today);
}

function setExpiryBadge(el, dateStr, today) {
  if (!dateStr) {
    el.innerHTML = '<span class="badge-warning text-xs px-2 py-0.5 rounded-full font-medium">Non renseigné</span>';
    return;
  }
  const expiry = new Date(dateStr);
  const diffDays = Math.ceil((expiry - today) / (1000 * 3600 * 24));
  const formatted = expiry.toLocaleDateString('fr-FR');

  if (diffDays < 0) {
    el.innerHTML = `<span class="badge-critical text-xs px-2 py-0.5 rounded-full font-medium">Expiré (${formatted})</span>`;
  } else if (diffDays <= 30) {
    el.innerHTML = `<span class="badge-warning text-xs px-2 py-0.5 rounded-full font-medium">Expire dans ${diffDays}j (${formatted})</span>`;
  } else {
    el.innerHTML = `<span class="badge-ok text-xs px-2 py-0.5 rounded-full font-medium">Valide jusqu'au ${formatted}</span>`;
  }
}

// ── Save maintenance ──────────────────────────────────────────────────────────
document.getElementById('btn-save-maint').addEventListener('click', async () => {
  const errEl = document.getElementById('maint-error');
  const okEl  = document.getElementById('maint-success');
  errEl.classList.add('hidden');
  okEl.classList.add('hidden');

  if (!selectedVehicleId) return;

  const oilKm      = document.getElementById('m-oil-km').value;
  const insurance  = document.getElementById('m-insurance').value;
  const inspection = document.getElementById('m-inspection').value;

  const body = {};
  if (oilKm)      body.last_oil_change_km = parseInt(oilKm);
  if (insurance)  body.insurance_expiry   = insurance;
  if (inspection) body.inspection_expiry  = inspection;

  const res = await fetch(`${API}/vehicles/${selectedVehicleId}/maintenance`, {
    method:  'PUT',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body:    JSON.stringify(body),
  });

  const json = await res.json().catch(() => ({}));
  if (res.ok) {
    okEl.textContent = 'Informations mises à jour avec succès.';
    okEl.classList.remove('hidden');
    renderStatusBadges(json.data || {});
    loadOverview(allVehicles);
    setTimeout(() => okEl.classList.add('hidden'), 3000);
  } else {
    errEl.textContent = json.detail || 'Erreur lors de la sauvegarde.';
    errEl.classList.remove('hidden');
  }
});

// ── Overview table — all vehicles ─────────────────────────────────────────────
async function loadOverview(vehicles) {
  document.getElementById('overview-loading').classList.remove('hidden');
  document.getElementById('overview-table').classList.add('hidden');
  document.getElementById('empty-overview').classList.add('hidden');

  if (!vehicles.length) {
    document.getElementById('overview-loading').classList.add('hidden');
    document.getElementById('empty-overview').classList.remove('hidden');
    return;
  }

  try {
    const results = await Promise.all(
      vehicles.map(v =>
        fetch(`${API}/vehicles/${v.id}/maintenance`, { headers: authHeader() })
          .then(r => r.ok ? r.json() : { data: {} })
          .then(j => ({ vehicle: v, maint: j.data || {} }))
      )
    );
    renderOverview(results);
  } catch (e) {
    console.error("Erreur vue d'ensemble", e);
  } finally {
    document.getElementById('overview-loading').classList.add('hidden');
  }
}

function renderOverview(rows) {
  const tbody = document.getElementById('overview-tbody');
  const table = document.getElementById('overview-table');
  const today = new Date();

  if (!rows.length) {
    document.getElementById('empty-overview').classList.remove('hidden');
    return;
  }
  table.classList.remove('hidden');

  tbody.innerHTML = rows.map(({ vehicle, maint }) => {
    const oil = maint.last_oil_change_km != null
      ? `${parseInt(maint.last_oil_change_km).toLocaleString('fr-FR')} km`
      : '<span class="text-gray-400">—</span>';
    return `
      <tr class="border-b last:border-0">
        <td class="py-2 font-medium">${esc(vehicle.name)}<span class="text-gray-400 ml-1 text-xs">${esc(vehicle.license_plate)}</span></td>
        <td class="py-2">${oil}</td>
        <td class="py-2">${expiryCell(maint.insurance_expiry, today)}</td>
        <td class="py-2">${expiryCell(maint.inspection_expiry, today)}</td>
        <td class="py-2 text-right">
          <button class="text-xs text-[#005F02] hover:underline"
            onclick="selectVehicle(${vehicle.id})">Modifier</button>
        </td>
      </tr>`;
  }).join('');
}

function expiryCell(dateStr, today) {
  if (!dateStr) return '<span class="text-gray-400">—</span>';
  const expiry   = new Date(dateStr);
  const diffDays = Math.ceil((expiry - today) / (1000 * 3600 * 24));
  const formatted = expiry.toLocaleDateString('fr-FR');
  if (diffDays < 0)   return `<span class="badge-critical text-xs px-2 py-0.5 rounded-full font-medium">Expiré</span>`;
  if (diffDays <= 30) return `<span class="badge-warning  text-xs px-2 py-0.5 rounded-full font-medium">${formatted}</span>`;
  return `<span class="text-gray-600 text-xs">${formatted}</span>`;
}

function selectVehicle(id) {
  const sel = document.getElementById('vehicle-select');
  sel.value = id;
  sel.dispatchEvent(new Event('change'));
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Add vehicle modal ─────────────────────────────────────────────────────────

function openModal() {
  // Clear previous values and errors
  ['v-name', 'v-brand', 'v-model', 'v-plate', 'v-year'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('v-fuel').value    = 'Diesel';
  document.getElementById('v-mileage').value = '0';
  document.getElementById('add-vehicle-error').classList.add('hidden');
  document.getElementById('modal-add-vehicle').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('modal-add-vehicle').classList.add('hidden');
}

document.getElementById('btn-open-add-vehicle').addEventListener('click', openModal);
document.getElementById('btn-close-modal').addEventListener('click', closeModal);
document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);

// Close when clicking the overlay backdrop
document.getElementById('modal-add-vehicle').addEventListener('click', (e) => {
  if (e.target === document.getElementById('modal-add-vehicle')) closeModal();
});

document.getElementById('btn-save-vehicle').addEventListener('click', async () => {
  const errEl = document.getElementById('add-vehicle-error');
  errEl.classList.add('hidden');

  const name    = document.getElementById('v-name').value.trim();
  const brand   = document.getElementById('v-brand').value.trim();
  const model   = document.getElementById('v-model').value.trim();
  const plate   = document.getElementById('v-plate').value.trim();
  const fuel    = document.getElementById('v-fuel').value;
  const mileage = parseInt(document.getElementById('v-mileage').value) || 0;
  const yearVal = document.getElementById('v-year').value;
  const year    = yearVal ? parseInt(yearVal) : null;

  if (!name || !brand || !model || !plate) {
    errEl.textContent = 'Veuillez remplir tous les champs obligatoires.';
    errEl.classList.remove('hidden');
    return;
  }

  const btn = document.getElementById('btn-save-vehicle');
  btn.disabled = true;
  btn.textContent = 'Enregistrement…';

  try {
    const res = await fetch(`${API}/vehicles`, {
      method:  'POST',
      headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        name,
        brand,
        model,
        license_plate: plate,
        fuel_type: fuel,
        initial_mileage: mileage,
        ...(year ? { year } : {}),
      }),
    });

    const json = await res.json().catch(() => ({}));
    if (res.ok) {
      const newVehicle = json.data;
      closeModal();
      // Reload vehicle list and auto-select the newly created vehicle
      await loadVehicles();
      selectVehicle(newVehicle.id);
    } else {
      const detail = json.detail;
      errEl.textContent = Array.isArray(detail)
        ? detail.map(e => e.msg).join(' · ')
        : (detail || 'Erreur lors de la création.');
      errEl.classList.remove('hidden');
    }
  } catch {
    errEl.textContent = 'Erreur réseau. Veuillez réessayer.';
    errEl.classList.remove('hidden');
  }

  btn.disabled = false;
  btn.textContent = 'Enregistrer le véhicule';
});

// ── Utility ───────────────────────────────────────────────────────────────────
function esc(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Boot ──────────────────────────────────────────────────────────────────────
loadVehicles();
