const API = '/api/v1';
const token     = () => localStorage.getItem('access_token');
const authHeader = () => ({ 'Authorization': `Bearer ${token()}` });

function isTokenValid(t) {
  try {
    const p = JSON.parse(atob(t.split('.')[1]));
    return p.exp * 1000 > Date.now();
  } catch { return false; }
}

function getRoleFromToken(t) {
  try { return JSON.parse(atob(t.split('.')[1])).role || null; } catch { return null; }
}

function logout() {
  localStorage.clear();
  window.location.href = '/';
}

function showSessionExpired() {
  const overlay = document.createElement('div');
  overlay.className = 'fixed inset-0 bg-black/50 flex items-center justify-center z-50';
  overlay.innerHTML = `
    <div class="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full text-center">
      <p class="text-gray-700 font-semibold mb-2">Session expirée</p>
      <p class="text-sm text-gray-500 mb-5">Votre session a expiré. Veuillez vous reconnecter.</p>
      <button onclick="logout()" class="w-full bg-[#005F02] text-white rounded-lg py-2.5 text-sm font-semibold hover:bg-[#004a01]">
        Se reconnecter
      </button>
    </div>`;
  document.body.appendChild(overlay);
}

document.getElementById('btn-logout').addEventListener('click', logout);

// ── Auth guard ────────────────────────────────────────────────────────────────
const _tok = token();

if (!_tok || !isTokenValid(_tok)) {
  showSessionExpired();
} else {
  const role = getRoleFromToken(_tok);
  if (role === 'DRIVER')      { window.location.href = '/dashboard-driver'; }
  else if (role === 'SUPER_ADMIN') { window.location.href = '/dashboard-admin'; }
  else { loadSettings(); }
}

// ── Load current settings ─────────────────────────────────────────────────────
async function loadSettings() {
  try {
    const res = await fetch(`${API}/owner/settings`, { headers: authHeader() });
    if (res.status === 401) { showSessionExpired(); return; }
    if (!res.ok) {
      const json = await res.json().catch(() => ({}));
      showGlobalError(json.detail || `Erreur serveur (${res.status}) — impossible de charger les paramètres.`);
      return;
    }
    const { data } = await res.json();
    document.getElementById('wa-number').value           = data.whatsapp_number || '';
    document.getElementById('email-display').textContent = data.email || '—';
    document.getElementById('email-toggle').checked      = !!data.email_alerts_enabled;
  } catch {
    showGlobalError('Erreur réseau — impossible de charger les paramètres. Vérifiez votre connexion.');
  }
}

function showGlobalError(msg) {
  const banner = document.createElement('div');
  banner.className = 'alert-err text-sm mb-4';
  banner.textContent = msg;
  const main = document.querySelector('main');
  if (main) main.prepend(banner);
}

// ── Section 1: Change password ────────────────────────────────────────────────
async function changePassword() {
  const current  = document.getElementById('pw-current').value.trim();
  const next     = document.getElementById('pw-new').value;
  const confirm  = document.getElementById('pw-confirm').value;
  const msgEl    = document.getElementById('pw-msg');

  if (!current || !next)   { showMsg(msgEl, 'err', 'Remplissez tous les champs.'); return; }
  if (next !== confirm)    { showMsg(msgEl, 'err', 'Les mots de passe ne correspondent pas.'); return; }
  if (next.length < 6)     { showMsg(msgEl, 'err', 'Le nouveau mot de passe doit contenir au moins 6 caractères.'); return; }

  const res = await fetch(`${API}/auth/change-password`, {
    method: 'PATCH',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ current_password: current, new_password: next }),
  });

  if (res.status === 401) { showSessionExpired(); return; }
  const json = await res.json().catch(() => ({}));
  if (res.ok) {
    showMsg(msgEl, 'ok', json.message || 'Mot de passe modifié.');
    document.getElementById('pw-current').value = '';
    document.getElementById('pw-new').value     = '';
    document.getElementById('pw-confirm').value = '';
  } else {
    showMsg(msgEl, 'err', json.detail || 'Erreur lors du changement de mot de passe.');
  }
}

// ── Section 3: WhatsApp ───────────────────────────────────────────────────────
async function saveWhatsApp() {
  const number = document.getElementById('wa-number').value.trim();
  const msgEl  = document.getElementById('wa-msg');

  const res = await fetch(`${API}/owner/whatsapp`, {
    method: 'PATCH',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ whatsapp_number: number }),
  });

  if (res.status === 401) { showSessionExpired(); return; }
  const json = await res.json().catch(() => ({}));
  if (res.ok) {
    showMsg(msgEl, 'ok', json.message || 'Numéro enregistré.');
  } else {
    showMsg(msgEl, 'err', json.detail || 'Erreur lors de la mise à jour.');
  }
}

// ── Section 4: Email alerts ───────────────────────────────────────────────────
async function saveEmailAlerts() {
  const enabled = document.getElementById('email-toggle').checked;
  const msgEl   = document.getElementById('email-msg');

  const res = await fetch(`${API}/owner/email-alerts`, {
    method: 'PATCH',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  });

  if (res.status === 401) { showSessionExpired(); return; }
  const json = await res.json().catch(() => ({}));
  if (res.ok) {
    showMsg(msgEl, 'ok', json.message || 'Préférences mises à jour.');
  } else {
    showMsg(msgEl, 'err', json.detail || 'Erreur lors de la mise à jour.');
    document.getElementById('email-toggle').checked = !enabled; // revert on error
  }
}

// ── Helper ────────────────────────────────────────────────────────────────────
function showMsg(el, type, text) {
  el.textContent = text;
  el.className   = (type === 'ok' ? 'alert-ok' : 'alert-err') + ' text-sm';
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 4000);
}
