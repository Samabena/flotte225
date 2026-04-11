/* admin.js — Super Admin panel (Sprint 6) */

const API = '/api/v1';
const token = () => localStorage.getItem('access_token');
const authHeader = () => ({ 'Authorization': `Bearer ${token()}`, 'Content-Type': 'application/json' });

if (!token()) window.location.href = 'index.html';

document.getElementById('btn-logout').addEventListener('click', () => {
  localStorage.clear();
  window.location.href = 'index.html';
});

// ── State ─────────────────────────────────────────────────────────────────────

let pendingDeleteId = null;
let pendingPlanOwnerId = null;

// ── Fetch & render users ──────────────────────────────────────────────────────

async function loadUsers(q = '', role = '') {
  const tbody = document.getElementById('users-tbody');
  tbody.innerHTML = '<tr><td colspan="6" class="px-4 py-8 text-center text-gray-400">Chargement…</td></tr>';

  const params = new URLSearchParams();
  if (q)    params.set('q', q);
  if (role) params.set('role', role);

  let users;
  try {
    const res = await fetch(`${API}/admin/users?${params}`, { headers: authHeader() });
    if (res.status === 401 || res.status === 403) {
      window.location.href = 'index.html';
      return;
    }
    users = (await res.json()).data;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" class="px-4 py-8 text-center text-red-400">Erreur de chargement</td></tr>';
    return;
  }

  document.getElementById('user-count').textContent = `${users.length} utilisateur${users.length !== 1 ? 's' : ''}`;

  if (users.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="px-4 py-8 text-center text-gray-400">Aucun résultat</td></tr>';
    return;
  }

  tbody.innerHTML = users.map(u => {
    const roleBadge = roleLabel(u.role);
    const statusBadge = u.is_active
      ? '<span class="badge-active text-xs px-2 py-0.5 rounded-full">Actif</span>'
      : '<span class="badge-inactive text-xs px-2 py-0.5 rounded-full">Suspendu</span>';
    const date = new Date(u.created_at).toLocaleDateString('fr-FR');
    const isAdmin = u.role === 'SUPER_ADMIN';

    const suspendBtn = u.is_active
      ? `<button onclick="suspendUser(${u.id})" class="text-amber-600 hover:underline text-xs" ${isAdmin ? 'disabled title="Non autorisé"' : ''}>Suspendre</button>`
      : `<button onclick="reactivateUser(${u.id})" class="text-green-700 hover:underline text-xs">Réactiver</button>`;

    const fleetBtn = u.role === 'OWNER'
      ? `<button onclick="viewFleet(${u.id}, '${esc(u.full_name)}')" class="text-[#005F02] hover:underline text-xs">Flotte</button>`
      : '';

    const planBtn = u.role === 'OWNER'
      ? `<button onclick="openPlanModal(${u.id}, '${esc(u.full_name)}')" class="text-purple-700 hover:underline text-xs">Plan</button>`
      : '';

    const deleteBtn = !isAdmin
      ? `<button onclick="confirmDelete(${u.id}, '${esc(u.full_name)}')" class="text-red-600 hover:underline text-xs">Supprimer</button>`
      : '';

    const actions = [fleetBtn, planBtn, suspendBtn, deleteBtn].filter(Boolean).join('<span class="text-gray-300 mx-1">|</span>');

    return `
      <tr class="border-b last:border-0 hover:bg-gray-50" id="user-row-${u.id}">
        <td class="px-4 py-3 font-medium">${esc(u.full_name)}</td>
        <td class="px-4 py-3 text-gray-500">${esc(u.email)}</td>
        <td class="px-4 py-3">${roleBadge}</td>
        <td class="px-4 py-3">${statusBadge}</td>
        <td class="px-4 py-3 text-gray-400">${date}</td>
        <td class="px-4 py-3 text-right whitespace-nowrap">${actions}</td>
      </tr>`;
  }).join('');
}

function roleLabel(role) {
  const map = {
    OWNER: '<span class="badge-owner text-xs px-2 py-0.5 rounded-full">Propriétaire</span>',
    DRIVER: '<span class="badge-driver text-xs px-2 py-0.5 rounded-full">Chauffeur</span>',
    SUPER_ADMIN: '<span class="badge-admin text-xs px-2 py-0.5 rounded-full">Admin</span>',
  };
  return map[role] || role;
}

// ── US-037: Suspend / reactivate ──────────────────────────────────────────────

async function suspendUser(userId) {
  const res = await fetch(`${API}/admin/users/${userId}/suspend`, {
    method: 'PATCH',
    headers: authHeader(),
  });
  if (res.ok) loadUsers(currentQ(), currentRole());
}

async function reactivateUser(userId) {
  const res = await fetch(`${API}/admin/users/${userId}/reactivate`, {
    method: 'PATCH',
    headers: authHeader(),
  });
  if (res.ok) loadUsers(currentQ(), currentRole());
}

// ── US-038: Delete ────────────────────────────────────────────────────────────

function confirmDelete(userId, name) {
  pendingDeleteId = userId;
  document.getElementById('modal-delete-msg').textContent =
    `Supprimer définitivement le compte de "${name}" ? Cette action est irréversible.`;
  document.getElementById('modal-delete').classList.remove('hidden');
}

document.getElementById('modal-delete-close').addEventListener('click', () => {
  document.getElementById('modal-delete').classList.add('hidden');
});

document.getElementById('btn-confirm-delete').addEventListener('click', async () => {
  if (!pendingDeleteId) return;
  const res = await fetch(`${API}/admin/users/${pendingDeleteId}`, {
    method: 'DELETE',
    headers: authHeader(),
  });
  document.getElementById('modal-delete').classList.add('hidden');
  if (res.ok || res.status === 204) {
    loadUsers(currentQ(), currentRole());
  }
  pendingDeleteId = null;
});

// ── US-039: View fleet ────────────────────────────────────────────────────────

async function viewFleet(ownerId, ownerName) {
  document.getElementById('modal-fleet-title').textContent = `Flotte — ${ownerName}`;
  document.getElementById('modal-fleet-body').innerHTML = '<p class="text-gray-400">Chargement…</p>';
  document.getElementById('modal-fleet').classList.remove('hidden');

  const res = await fetch(`${API}/admin/users/${ownerId}/fleet`, { headers: authHeader() });
  const json = await res.json();
  const vehicles = json.data?.vehicles ?? [];

  if (vehicles.length === 0) {
    document.getElementById('modal-fleet-body').innerHTML = '<p class="text-gray-400">Aucun véhicule enregistré.</p>';
    return;
  }

  document.getElementById('modal-fleet-body').innerHTML = `
    <table class="w-full text-sm">
      <thead><tr class="text-left text-gray-500 border-b">
        <th class="pb-2 font-medium">Nom</th>
        <th class="pb-2 font-medium">Marque / Modèle</th>
        <th class="pb-2 font-medium">Plaque</th>
        <th class="pb-2 font-medium">Statut</th>
      </tr></thead>
      <tbody>
        ${vehicles.map(v => `
          <tr class="border-b last:border-0">
            <td class="py-2 font-medium">${esc(v.name)}</td>
            <td class="py-2 text-gray-500">${esc(v.brand)} ${esc(v.model)}</td>
            <td class="py-2">${esc(v.license_plate)}</td>
            <td class="py-2"><span class="text-xs px-2 py-0.5 rounded-full ${statusClass(v.status)}">${esc(v.status)}</span></td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

function statusClass(s) {
  return s === 'active' ? 'badge-active' : s === 'paused' ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-500';
}

document.getElementById('modal-fleet-close').addEventListener('click', () => {
  document.getElementById('modal-fleet').classList.add('hidden');
});

// ── US-040: Assign plan ────────────────────────────────────────────────────────

function openPlanModal(ownerId, ownerName) {
  pendingPlanOwnerId = ownerId;
  document.getElementById('modal-plan-owner').textContent = `Propriétaire : ${ownerName}`;
  document.getElementById('modal-plan-error').classList.add('hidden');
  document.getElementById('modal-plan').classList.remove('hidden');
}

document.getElementById('modal-plan-close').addEventListener('click', () => {
  document.getElementById('modal-plan').classList.add('hidden');
});
document.getElementById('modal-plan-close2').addEventListener('click', () => {
  document.getElementById('modal-plan').classList.add('hidden');
});

document.getElementById('btn-assign-plan').addEventListener('click', async () => {
  const planName = document.getElementById('plan-select').value;
  const errorEl = document.getElementById('modal-plan-error');
  errorEl.classList.add('hidden');

  const res = await fetch(`${API}/admin/users/${pendingPlanOwnerId}/plan`, {
    method: 'PUT',
    headers: authHeader(),
    body: JSON.stringify({ plan_name: planName }),
  });

  if (res.ok) {
    document.getElementById('modal-plan').classList.add('hidden');
    pendingPlanOwnerId = null;
  } else {
    const json = await res.json();
    errorEl.textContent = json.detail || 'Erreur lors de la mise à jour du plan.';
    errorEl.classList.remove('hidden');
  }
});

// ── US-041: Analytics tab ─────────────────────────────────────────────────────

async function loadAnalytics() {
  const res = await fetch(`${API}/admin/analytics`, { headers: authHeader() });
  if (!res.ok) return;
  const data = (await res.json()).data;

  document.getElementById('an-owners').textContent = data.total_owners;
  document.getElementById('an-drivers').textContent = data.total_drivers;
  document.getElementById('an-vehicles').textContent = data.total_vehicles;
  document.getElementById('an-spend').textContent =
    data.total_spend_fcfa.toLocaleString('fr-FR') + ' FCFA';

  const newEl = document.getElementById('an-new-owners');
  if (data.new_owners_this_month > 0) {
    newEl.textContent = `+${data.new_owners_this_month} ce mois-ci`;
  }

  const plansEl = document.getElementById('an-plans');
  const plansEmpty = document.getElementById('an-plans-empty');
  if (!data.plan_distribution || data.plan_distribution.length === 0) {
    plansEmpty.classList.remove('hidden');
    return;
  }

  const total = data.plan_distribution.reduce((s, p) => s + p.owner_count, 0);
  const planColors = { starter: '#6B7280', pro: '#005F02', business: '#C0B87A' };

  plansEl.innerHTML = data.plan_distribution.map(p => {
    const pct = total ? Math.round((p.owner_count / total) * 100) : 0;
    const color = planColors[p.plan_name] || '#005F02';
    return `
      <div>
        <div class="flex justify-between mb-1">
          <span class="font-medium capitalize">${esc(p.plan_name)}</span>
          <span class="text-gray-500">${p.owner_count} owner${p.owner_count !== 1 ? 's' : ''} (${pct}%)</span>
        </div>
        <div class="w-full bg-gray-100 rounded-full h-2">
          <div class="h-2 rounded-full" style="width:${pct}%;background:${color}"></div>
        </div>
      </div>`;
  }).join('');
}

// ── Tab switching ─────────────────────────────────────────────────────────────

document.querySelectorAll('.admin-tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.admin-tab').forEach(b => {
      b.classList.remove('active', 'border-[#005F02]', 'text-[#005F02]');
      b.classList.add('border-transparent', 'text-gray-500');
    });
    btn.classList.add('active', 'border-[#005F02]', 'text-[#005F02]');
    btn.classList.remove('border-transparent', 'text-gray-500');

    document.getElementById('tab-users').classList.add('hidden');
    document.getElementById('tab-analytics').classList.add('hidden');
    const target = document.getElementById(`tab-${btn.dataset.tab}`);
    target.classList.remove('hidden');

    if (btn.dataset.tab === 'analytics') loadAnalytics();
  });
});

// ── Search / filter controls ──────────────────────────────────────────────────

const currentQ = () => document.getElementById('search-input').value.trim();
const currentRole = () => document.getElementById('role-filter').value;

document.getElementById('btn-search').addEventListener('click', () => {
  loadUsers(currentQ(), currentRole());
});

document.getElementById('search-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') loadUsers(currentQ(), currentRole());
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
loadUsers();
