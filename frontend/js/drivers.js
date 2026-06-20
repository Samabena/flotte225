const API = '/api/v1';
const token = () => localStorage.getItem('access_token');

let drivers = [];
let vehicles = [];                  // active vehicles for this owner
let driverVehicles = new Map();     // driver_id → [{id, name, license_plate}]
let selectedDriverId = null;

// ── Auth guard ────────────────────────────────────────────────────────────────
if (!token()) window.location.href = '/login';

function logout() {
  localStorage.clear();
  window.location.href = '/login';
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

// ── Load drivers + vehicles + assignments ─────────────────────────────────────
async function loadDrivers() {
  const data = await apiFetch('/drivers');
  if (!data) return;
  drivers = Array.isArray(data) ? data : (data.data || []);

  // Load active vehicles + per-vehicle drivers, then build driver→vehicles map
  const vData = await apiFetch('/vehicles');
  vehicles = vData ? (vData.data || []) : [];

  driverVehicles = new Map();
  await Promise.all(vehicles.map(async (v) => {
    const r = await apiFetch(`/vehicles/${v.id}/drivers`);
    const list = r ? (r.data || []) : [];
    list.forEach(d => {
      if (!driverVehicles.has(d.id)) driverVehicles.set(d.id, []);
      driverVehicles.get(d.id).push({ id: v.id, name: v.name, license_plate: v.license_plate });
    });
  }));

  renderList();
}

function renderList() {
  const el = document.getElementById('driver-list');
  if (!drivers.length) {
    el.innerHTML = `
      <div class="p-10 text-center text-gray-400">
        <p class="text-4xl mb-3">👤</p>
        <p class="font-semibold text-gray-600">Aucun chauffeur pour l'instant</p>
        <p class="text-sm mt-1">Cliquez sur <strong>+ Nouveau chauffeur</strong> pour commencer.</p>
      </div>`;
    return;
  }

  el.innerHTML = drivers.map(d => {
    const assigned = driverVehicles.get(d.id) || [];
    const vehicleBadges = assigned.length
      ? assigned.map(v => `
          <span class="badge-vehicle">
            ${esc(v.name)} · ${esc(v.license_plate)}
            <button title="Retirer ce véhicule"
              onclick="unassignVehicle(${v.id}, ${d.id}, '${esc(d.full_name)}')">×</button>
          </span>`).join(' ')
      : `<span class="text-xs text-gray-400 italic">Aucun véhicule assigné</span>`;

    return `
    <div class="px-5 py-4 hover:bg-gray-50 transition">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-full bg-green-100 flex items-center justify-center text-green-800 font-bold text-sm">
            ${d.full_name.charAt(0).toUpperCase()}
          </div>
          <div>
            <p class="font-semibold text-gray-900 text-sm">${esc(d.full_name)}</p>
            <p class="text-xs text-gray-400">@${esc(d.username)}</p>
          </div>
        </div>
        <div class="flex items-center gap-3">
          ${statusBadge(d)}
          <div class="flex gap-2 flex-wrap justify-end">
            <button onclick="shareDriverAccess('${esc(d.username)}')"
              class="text-xs text-[#128C7E] hover:underline font-medium">Partager l'accès</button>
            <button onclick="openAssignModal(${d.id}, '${esc(d.full_name)}')"
              class="text-xs text-[#005F02] hover:underline font-medium">+ Véhicule</button>
            <button onclick="openRenameModal(${d.id}, '${esc(d.full_name)}')"
              class="text-xs text-gray-600 hover:underline font-medium">Renommer</button>
            <button onclick="openResetModal(${d.id}, '${esc(d.full_name)}')"
              class="text-xs text-blue-600 hover:underline font-medium">Mot de passe</button>
            ${d.is_disabled
              ? `<button onclick="toggleStatus(${d.id}, false)" class="text-xs text-green-700 hover:underline font-medium">Réactiver</button>`
              : `<button onclick="toggleStatus(${d.id}, true)" class="text-xs text-orange-600 hover:underline font-medium">Désactiver</button>`
            }
            <button onclick="openRemoveModal(${d.id}, '${esc(d.full_name)}')"
              class="text-xs text-red-600 hover:underline font-medium">Supprimer</button>
          </div>
        </div>
      </div>
      <div class="mt-2 ml-12 flex flex-wrap gap-1.5">${vehicleBadges}</div>
    </div>
  `;}).join('');

  document.getElementById('plan-info').textContent = `${drivers.length} chauffeur(s) enregistré(s)`;
}

function statusBadge(d) {
  if (d.is_disabled) return `<span class="badge-disabled">Désactivé</span>`;
  if (d.driving_status) return `<span class="badge-driving">En mission</span>`;
  return `<span class="badge-active">Actif</span>`;
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
}

// ── Create ────────────────────────────────────────────────────────────────────
function openCreateModal() {
  document.getElementById('c-fullname').value = '';
  document.getElementById('c-username').value = '';
  document.getElementById('c-password').value = '';
  document.getElementById('create-error').classList.add('hidden');
  document.getElementById('create-modal').classList.remove('hidden');
}

function closeCreateModal() {
  document.getElementById('create-modal').classList.add('hidden');
}

async function submitCreate() {
  const full_name = document.getElementById('c-fullname').value.trim();
  const username = document.getElementById('c-username').value.trim();
  const password = document.getElementById('c-password').value;
  const errEl = document.getElementById('create-error');

  errEl.classList.add('hidden');

  if (!full_name || !username || !password) {
    errEl.textContent = 'Tous les champs sont obligatoires.';
    errEl.classList.remove('hidden');
    return;
  }

  const res = await apiFetch('/drivers', {
    method: 'POST',
    body: JSON.stringify({ full_name, username, password }),
  });

  if (!res) return;
  if (!res.success) {
    errEl.textContent = res.detail || res.message || 'Erreur lors de la création.';
    errEl.classList.remove('hidden');
    return;
  }

  closeCreateModal();
  showAlert('Chauffeur créé avec succès.');
  await loadDrivers();
}

// ── Toggle status ─────────────────────────────────────────────────────────────
async function toggleStatus(driverId, disable) {
  const res = await apiFetch(`/drivers/${driverId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ is_disabled: disable }),
  });
  if (!res) return;
  if (res.success !== false) {
    showAlert(disable ? 'Chauffeur désactivé.' : 'Chauffeur réactivé.');
    await loadDrivers();
  } else {
    showAlert(res.detail || 'Erreur.', 'error');
  }
}

// ── Rename ────────────────────────────────────────────────────────────────────
function openRenameModal(id, name) {
  selectedDriverId = id;
  document.getElementById('rename-current-name').textContent = `Chauffeur : ${name}`;
  const input = document.getElementById('r-fullname');
  input.value = name;
  document.getElementById('rename-error').classList.add('hidden');
  document.getElementById('rename-modal').classList.remove('hidden');
  input.focus();
  input.select();
}

function closeRenameModal() {
  document.getElementById('rename-modal').classList.add('hidden');
}

async function submitRename() {
  const full_name = document.getElementById('r-fullname').value.trim();
  const errEl = document.getElementById('rename-error');
  errEl.classList.add('hidden');

  if (!full_name) {
    errEl.textContent = 'Le nom complet est requis.';
    errEl.classList.remove('hidden');
    return;
  }

  const res = await apiFetch(`/drivers/${selectedDriverId}/name`, {
    method: 'PATCH',
    body: JSON.stringify({ full_name }),
  });

  if (!res) return;
  if (res.success !== false) {
    closeRenameModal();
    showAlert('Nom du chauffeur modifié.');
    await loadDrivers();
  } else {
    errEl.textContent = res.detail || 'Erreur.';
    errEl.classList.remove('hidden');
  }
}

// ── Reset password ────────────────────────────────────────────────────────────
function openResetModal(id, name) {
  selectedDriverId = id;
  document.getElementById('reset-driver-name').textContent = `Chauffeur : ${name}`;
  document.getElementById('r-password').value = '';
  document.getElementById('reset-error').classList.add('hidden');
  document.getElementById('reset-modal').classList.remove('hidden');
}

function closeResetModal() {
  document.getElementById('reset-modal').classList.add('hidden');
}

async function submitReset() {
  const new_password = document.getElementById('r-password').value;
  const errEl = document.getElementById('reset-error');
  errEl.classList.add('hidden');

  if (new_password.length < 6) {
    errEl.textContent = 'Le mot de passe doit contenir au moins 6 caractères.';
    errEl.classList.remove('hidden');
    return;
  }

  const res = await apiFetch(`/drivers/${selectedDriverId}/password`, {
    method: 'PATCH',
    body: JSON.stringify({ new_password }),
  });

  if (!res) return;
  if (res.success !== false) {
    closeResetModal();
    showAlert('Mot de passe réinitialisé.');
  } else {
    errEl.textContent = res.detail || 'Erreur.';
    errEl.classList.remove('hidden');
  }
}

// ── Remove ────────────────────────────────────────────────────────────────────
function openRemoveModal(id, name) {
  selectedDriverId = id;
  document.getElementById('remove-driver-name').textContent = `Chauffeur : ${name}`;
  document.getElementById('remove-modal').classList.remove('hidden');
}

function closeRemoveModal() {
  document.getElementById('remove-modal').classList.add('hidden');
}

async function submitRemove() {
  const res = await fetch(`${API}/drivers/${selectedDriverId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token()}` },
  });
  closeRemoveModal();
  if (res.ok || res.status === 204) {
    showAlert('Chauffeur supprimé.');
    await loadDrivers();
  } else {
    const json = await res.json().catch(() => ({}));
    showAlert(json.detail || 'Erreur lors de la suppression.', 'error');
  }
}

// ── Assign vehicle ────────────────────────────────────────────────────────────
function openAssignModal(driverId, driverName) {
  selectedDriverId = driverId;
  document.getElementById('assign-driver-name').textContent = `Chauffeur : ${driverName}`;
  document.getElementById('assign-error').classList.add('hidden');

  const alreadyAssigned = new Set((driverVehicles.get(driverId) || []).map(v => v.id));
  const available = vehicles.filter(v => !alreadyAssigned.has(v.id));
  const select = document.getElementById('a-vehicle-id');
  select.innerHTML = available.length
    ? available.map(v => `<option value="${v.id}">${esc(v.name)} — ${esc(v.license_plate)}</option>`).join('')
    : '<option value="">Aucun véhicule disponible</option>';

  document.getElementById('assign-modal').classList.remove('hidden');
}

function closeAssignModal() {
  document.getElementById('assign-modal').classList.add('hidden');
}

async function submitAssign() {
  const errEl = document.getElementById('assign-error');
  errEl.classList.add('hidden');
  const vehicleId = document.getElementById('a-vehicle-id').value;
  if (!vehicleId) {
    errEl.textContent = 'Aucun véhicule sélectionné.';
    errEl.classList.remove('hidden');
    return;
  }

  const res = await apiFetch(`/vehicles/${vehicleId}/drivers`, {
    method: 'POST',
    body: JSON.stringify({ driver_id: selectedDriverId }),
  });
  if (!res) return;
  if (res.success === false || res.detail) {
    errEl.textContent = res.detail || 'Erreur lors de l\'assignation.';
    errEl.classList.remove('hidden');
    return;
  }

  closeAssignModal();
  showAlert('Véhicule assigné.');
  await loadDrivers();
}

async function unassignVehicle(vehicleId, driverId, driverName) {
  if (!confirm(`Retirer ce véhicule de ${driverName} ?`)) return;
  await apiFetch(`/vehicles/${vehicleId}/drivers/${driverId}`, { method: 'DELETE' });
  showAlert('Véhicule retiré.');
  await loadDrivers();
}

// ── Share driver login link ─────────────────────────────────────────────────
const driverLoginUrl = () => `${window.location.origin}/login-chauffeur`;

function whatsappMessage(username) {
  const lines = [
    'Bonjour 👋',
    `Connectez-vous à votre espace chauffeur Flotte225 : ${driverLoginUrl()}`,
  ];
  if (username) lines.push(`Votre identifiant : ${username}`);
  return lines.join('\n');
}

function openWhatsApp(message) {
  window.open(`https://wa.me/?text=${encodeURIComponent(message)}`, '_blank', 'noopener');
}

async function copyDriverLink(btn) {
  const url = driverLoginUrl();
  try {
    await navigator.clipboard.writeText(url);
  } catch {
    // Fallback for browsers without clipboard API (or non-HTTPS contexts)
    const ta = document.createElement('textarea');
    ta.value = url;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
  }
  if (btn) {
    const original = btn.textContent;
    btn.textContent = '✓ Copié';
    setTimeout(() => { btn.textContent = original; }, 1500);
  }
}

function shareDriverLinkWhatsApp() {
  openWhatsApp(whatsappMessage());
}

function shareDriverAccess(username) {
  openWhatsApp(whatsappMessage(username));
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.getElementById('driver-login-url').textContent = driverLoginUrl();
loadDrivers();
