/* fuel.js — Driver fuel entry + history (US-010 – US-014) */

const API = '/api/v1';
const token = () => localStorage.getItem('access_token');
const authHeader = () => ({ 'Authorization': `Bearer ${token()}` });

if (!token()) window.location.href = '/';

document.getElementById('btn-logout').addEventListener('click', () => {
  localStorage.clear();
  window.location.href = '/';
});

// ── Set today as default date ─────────────────────────────────────────────────
document.getElementById('f-date').value = new Date().toISOString().split('T')[0];

// ── Load assigned vehicles for the form select ────────────────────────────────
let vehicleMap = {};

async function loadVehicles() {
  try {
    const res = await fetch(`${API}/driver/vehicles`, { headers: authHeader() });
    if (res.status === 401 || res.status === 403) {
      window.location.href = '/'; return;
    }
    const json = await res.json();
    const vehicles = json.data || [];
    vehicles.forEach(v => { vehicleMap[v.id] = v.name; });

    const sel = document.getElementById('f-vehicle');
    if (!vehicles.length) {
      sel.innerHTML = '<option value="">Aucun véhicule assigné</option>';
      document.getElementById('btn-submit').disabled = true;
      return;
    }
    sel.innerHTML = vehicles.map(v =>
      `<option value="${v.id}">${esc(v.name)} — ${esc(v.license_plate)}</option>`
    ).join('');
  } catch (e) {
    console.error('Erreur chargement véhicules', e);
  }
}

// ── Submit new fuel entry ─────────────────────────────────────────────────────
document.getElementById('btn-submit').addEventListener('click', async () => {
  const errEl = document.getElementById('form-error');
  const okEl  = document.getElementById('form-success');
  errEl.classList.add('hidden');
  okEl.classList.add('hidden');

  const vehicle_id      = document.getElementById('f-vehicle').value;
  const date            = document.getElementById('f-date').value;
  const odometer_km     = document.getElementById('f-odometer').value;
  const quantity_litres = document.getElementById('f-quantity').value;
  const amount_fcfa     = document.getElementById('f-amount').value;

  if (!vehicle_id || !date || !odometer_km || !quantity_litres || !amount_fcfa) {
    errEl.textContent = 'Veuillez remplir tous les champs obligatoires.';
    errEl.classList.remove('hidden');
    return;
  }

  const res = await fetch(`${API}/fuel`, {
    method: 'POST',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({
      vehicle_id:      parseInt(vehicle_id),
      date,
      odometer_km:     parseInt(odometer_km),
      quantity_litres: parseFloat(quantity_litres),
      amount_fcfa:     parseFloat(amount_fcfa),
    }),
  });

  const json = await res.json().catch(() => ({}));
  if (res.ok) {
    okEl.textContent = 'Saisie enregistrée avec succès !';
    okEl.classList.remove('hidden');
    // Reset form
    document.getElementById('f-odometer').value = '';
    document.getElementById('f-quantity').value  = '';
    document.getElementById('f-amount').value    = '';
    document.getElementById('f-date').value = new Date().toISOString().split('T')[0];
    loadHistory();
    setTimeout(() => okEl.classList.add('hidden'), 3000);
  } else {
    errEl.textContent = json.detail || 'Erreur lors de l\'enregistrement.';
    errEl.classList.remove('hidden');
  }
});

// ── Load history ──────────────────────────────────────────────────────────────
async function loadHistory() {
  document.getElementById('history-loading').classList.remove('hidden');
  document.getElementById('history-table').classList.add('hidden');
  document.getElementById('empty-history').classList.add('hidden');

  try {
    const res = await fetch(`${API}/fuel`, { headers: authHeader() });
    if (!res.ok) return;
    const json = await res.json();
    renderHistory(json.data || []);
  } catch (e) {
    console.error('Erreur historique', e);
  } finally {
    document.getElementById('history-loading').classList.add('hidden');
  }
}

function renderHistory(entries) {
  const tbody = document.getElementById('history-tbody');
  const table = document.getElementById('history-table');
  const empty = document.getElementById('empty-history');

  if (!entries.length) {
    empty.classList.remove('hidden');
    return;
  }
  table.classList.remove('hidden');

  const now = Date.now();
  const TWENTY_FOUR_H = 24 * 3600 * 1000;

  tbody.innerHTML = entries.map(e => {
    const canEdit = (now - new Date(e.created_at).getTime()) < TWENTY_FOUR_H;
    const conso = e.consumption_per_100km !== null && e.consumption_per_100km !== undefined
      ? parseFloat(e.consumption_per_100km).toFixed(2) + ' L'
      : '<span class="text-gray-300">—</span>';

    const actions = canEdit
      ? `<button class="text-xs text-[#005F02] hover:underline mr-2" onclick="openEditModal(${e.id}, '${e.date}', ${e.odometer_km}, ${e.quantity_litres}, ${e.amount_fcfa})">Modifier</button>
         <button class="text-xs text-red-600 hover:underline" onclick="confirmDelete(${e.id})">Supprimer</button>`
      : '<span class="text-gray-300 text-xs">—</span>';

    return `
      <tr class="border-b last:border-0">
        <td class="py-2">${new Date(e.date).toLocaleDateString('fr-FR')}</td>
        <td class="py-2 text-gray-500">${esc(vehicleMap[e.vehicle_id] || `#${e.vehicle_id}`)}</td>
        <td class="py-2 text-right">${parseInt(e.odometer_km).toLocaleString('fr-FR')}</td>
        <td class="py-2 text-right">${parseFloat(e.quantity_litres).toFixed(1)}</td>
        <td class="py-2 text-right font-medium">${parseFloat(e.amount_fcfa).toLocaleString('fr-FR')}</td>
        <td class="py-2 text-right">${conso}</td>
        <td class="py-2 text-right whitespace-nowrap">${actions}</td>
      </tr>`;
  }).join('');
}

// ── Edit modal ────────────────────────────────────────────────────────────────
let editingEntryId = null;

function openEditModal(id, date, odometer, quantity, amount) {
  editingEntryId = id;
  document.getElementById('e-date').value     = date;
  document.getElementById('e-odometer').value = odometer;
  document.getElementById('e-quantity').value = quantity;
  document.getElementById('e-amount').value   = amount;
  document.getElementById('edit-error').classList.add('hidden');
  document.getElementById('modal-edit').classList.remove('hidden');
}

['modal-edit-close', 'modal-edit-cancel'].forEach(id => {
  document.getElementById(id).addEventListener('click', () => {
    document.getElementById('modal-edit').classList.add('hidden');
  });
});

document.getElementById('btn-save-edit').addEventListener('click', async () => {
  const errEl = document.getElementById('edit-error');
  errEl.classList.add('hidden');

  const body = {};
  const date     = document.getElementById('e-date').value;
  const odometer = document.getElementById('e-odometer').value;
  const quantity = document.getElementById('e-quantity').value;
  const amount   = document.getElementById('e-amount').value;

  if (date)     body.date            = date;
  if (odometer) body.odometer_km     = parseInt(odometer);
  if (quantity) body.quantity_litres = parseFloat(quantity);
  if (amount)   body.amount_fcfa     = parseFloat(amount);

  const res = await fetch(`${API}/fuel/${editingEntryId}`, {
    method: 'PATCH',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const json = await res.json().catch(() => ({}));
  if (res.ok) {
    document.getElementById('modal-edit').classList.add('hidden');
    loadHistory();
  } else {
    errEl.textContent = json.detail || 'Erreur lors de la modification.';
    errEl.classList.remove('hidden');
  }
});

// ── Delete confirm ────────────────────────────────────────────────────────────
let deletingEntryId = null;

function confirmDelete(id) {
  deletingEntryId = id;
  document.getElementById('modal-confirm').classList.remove('hidden');
}

document.getElementById('confirm-cancel').addEventListener('click', () => {
  document.getElementById('modal-confirm').classList.add('hidden');
  deletingEntryId = null;
});

document.getElementById('confirm-ok').addEventListener('click', async () => {
  document.getElementById('modal-confirm').classList.add('hidden');
  if (!deletingEntryId) return;

  const res = await fetch(`${API}/fuel/${deletingEntryId}`, {
    method: 'DELETE',
    headers: authHeader(),
  });

  deletingEntryId = null;
  if (res.ok) {
    loadHistory();
  } else {
    const json = await res.json().catch(() => ({}));
    alert(json.detail || 'Erreur lors de la suppression.');
  }
});

// ── Utility ───────────────────────────────────────────────────────────────────
function esc(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Boot ──────────────────────────────────────────────────────────────────────
loadVehicles().then(() => loadHistory());
