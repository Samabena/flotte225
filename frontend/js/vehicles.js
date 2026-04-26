const API = '/api/v1';
const token = () => localStorage.getItem('access_token');

let vehicles = [];
let editingId = null;
let selectedId = null;

// ── Auth guard ────────────────────────────────────────────────────────────────
if (!token()) window.location.href = '/';

function logout() {
  localStorage.clear();
  window.location.href = '/';
}

// ── Alert banner ──────────────────────────────────────────────────────────────
function showAlert(msg, type = 'success') {
  const el = document.getElementById('alert');
  el.textContent = msg;
  el.className = `mb-4 px-4 py-3 rounded-lg text-sm font-medium ${
    type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-700'
  }`;
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 4000);
}

// ── API helpers ───────────────────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token()}` },
    ...opts,
  });
  if (res.status === 401) { logout(); return null; }
  if (res.status === 204) return null;
  return res.json();
}

// ── Load vehicles ─────────────────────────────────────────────────────────────
async function loadVehicles() {
  const data = await apiFetch('/vehicles');
  if (!data) return;
  vehicles = Array.isArray(data) ? data : (data.data || []);
  renderList();
}

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
}

function statusBadge(status) {
  if (status === 'paused') return `<span class="badge-paused">En pause</span>`;
  if (status === 'archived') return `<span class="badge-archived">Archivé</span>`;
  return `<span class="badge-active">Actif</span>`;
}

function actionButtons(v) {
  const btns = [`<button onclick="openEditModal(${v.id})" class="text-xs text-blue-600 hover:underline font-medium">Modifier</button>`];
  if (v.status === 'active') {
    btns.push(`<button onclick="togglePause(${v.id}, 'pause')" class="text-xs text-amber-600 hover:underline font-medium">Pause</button>`);
  } else if (v.status === 'paused') {
    btns.push(`<button onclick="togglePause(${v.id}, 'resume')" class="text-xs text-green-700 hover:underline font-medium">Reprendre</button>`);
  }
  if (v.status !== 'archived') {
    btns.push(`<button onclick="openArchiveModal(${v.id}, '${esc(v.name)}')" class="text-xs text-red-600 hover:underline font-medium">Archiver</button>`);
  }
  return btns.join('');
}

function renderList() {
  const tbody = document.getElementById('vehicle-tbody');
  if (!vehicles.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="p-10 text-center text-gray-400">
      <p class="text-4xl mb-3">🚗</p>
      <p class="font-semibold text-gray-600">Aucun véhicule pour l'instant</p>
      <p class="text-sm mt-1">Cliquez sur <strong>+ Ajouter un véhicule</strong> pour commencer.</p>
    </td></tr>`;
    document.getElementById('plan-info').textContent = '';
    return;
  }

  tbody.innerHTML = vehicles.map(v => `
    <tr class="border-b border-gray-50 hover:bg-gray-50 transition">
      <td class="px-5 py-3 font-semibold text-gray-900">${esc(v.name)}</td>
      <td class="px-5 py-3 text-gray-600">${esc(v.brand)} ${esc(v.model)}${v.year ? ` (${v.year})` : ''}</td>
      <td class="px-5 py-3 text-gray-600 font-mono text-xs">${esc(v.license_plate)}</td>
      <td class="px-5 py-3 text-gray-600">${esc(v.fuel_type)}</td>
      <td class="px-5 py-3">${statusBadge(v.status)}</td>
      <td class="px-5 py-3 text-right">
        <div class="flex gap-3 justify-end">${actionButtons(v)}</div>
      </td>
    </tr>
  `).join('');

  document.getElementById('plan-info').textContent = `${vehicles.length} véhicule(s) enregistré(s)`;
}

// ── Add / Edit Modal ──────────────────────────────────────────────────────────
function openAddModal() {
  editingId = null;
  document.getElementById('form-modal-title').textContent = 'Nouveau véhicule';
  document.getElementById('form-submit-btn').textContent = 'Créer';
  ['v-name','v-plate','v-brand','v-model','v-year','v-vin'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('v-mileage').value = '0';
  document.getElementById('v-fuel').value = 'Diesel';
  document.getElementById('form-error').classList.add('hidden');
  document.getElementById('form-modal').classList.remove('hidden');
}

function openEditModal(id) {
  const v = vehicles.find(x => x.id === id);
  if (!v) return;
  editingId = id;
  document.getElementById('form-modal-title').textContent = 'Modifier le véhicule';
  document.getElementById('form-submit-btn').textContent = 'Enregistrer';
  document.getElementById('v-name').value = v.name || '';
  document.getElementById('v-plate').value = v.license_plate || '';
  document.getElementById('v-brand').value = v.brand || '';
  document.getElementById('v-model').value = v.model || '';
  document.getElementById('v-year').value = v.year || '';
  document.getElementById('v-fuel').value = v.fuel_type || 'Diesel';
  document.getElementById('v-mileage').value = v.initial_mileage || 0;
  document.getElementById('v-vin').value = v.vin || '';
  document.getElementById('form-error').classList.add('hidden');
  document.getElementById('form-modal').classList.remove('hidden');
}

function closeFormModal() {
  document.getElementById('form-modal').classList.add('hidden');
}

async function submitForm() {
  const errEl = document.getElementById('form-error');
  errEl.classList.add('hidden');

  const name = document.getElementById('v-name').value.trim();
  const license_plate = document.getElementById('v-plate').value.trim();
  const brand = document.getElementById('v-brand').value.trim();
  const model = document.getElementById('v-model').value.trim();
  const year = document.getElementById('v-year').value ? parseInt(document.getElementById('v-year').value) : null;
  const fuel_type = document.getElementById('v-fuel').value;
  const initial_mileage = parseInt(document.getElementById('v-mileage').value) || 0;
  const vin = document.getElementById('v-vin').value.trim() || null;

  if (!name || !license_plate || !brand || !model) {
    errEl.textContent = 'Nom, plaque, marque et modèle sont obligatoires.';
    errEl.classList.remove('hidden');
    return;
  }

  let res;
  if (editingId) {
    res = await apiFetch(`/vehicles/${editingId}`, {
      method: 'PATCH',
      body: JSON.stringify({ name, license_plate, brand, model, year, fuel_type, vin }),
    });
  } else {
    res = await apiFetch('/vehicles', {
      method: 'POST',
      body: JSON.stringify({ name, license_plate, brand, model, year, fuel_type, initial_mileage, vin }),
    });
  }

  if (!res) return;
  if (!res.success) {
    errEl.textContent = res.detail || res.message || 'Erreur lors de l\'enregistrement.';
    errEl.classList.remove('hidden');
    return;
  }

  closeFormModal();
  showAlert(editingId ? 'Véhicule mis à jour.' : 'Véhicule créé avec succès.');
  await loadVehicles();
}

// ── Pause / Resume ────────────────────────────────────────────────────────────
async function togglePause(id, action) {
  const res = await apiFetch(`/vehicles/${id}/${action}`, { method: 'POST' });
  if (!res) return;
  if (res.success !== false) {
    showAlert(action === 'pause' ? 'Véhicule mis en pause.' : 'Véhicule réactivé.');
    await loadVehicles();
  } else {
    showAlert(res.detail || 'Erreur.', 'error');
  }
}

// ── Archive ───────────────────────────────────────────────────────────────────
function openArchiveModal(id, name) {
  selectedId = id;
  document.getElementById('archive-vehicle-name').textContent = `Véhicule : ${name}`;
  document.getElementById('archive-modal').classList.remove('hidden');
}

function closeArchiveModal() {
  document.getElementById('archive-modal').classList.add('hidden');
}

async function submitArchive() {
  const res = await apiFetch(`/vehicles/${selectedId}/archive`, { method: 'POST' });
  closeArchiveModal();
  if (!res || res.success !== false) {
    showAlert('Véhicule archivé.');
    await loadVehicles();
  } else {
    showAlert(res.detail || 'Erreur.', 'error');
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────
loadVehicles();
