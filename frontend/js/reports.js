/* reports.js — AI Reports & Webhook (Sprint 8) */

const API = '/api/v1';
const token = () => localStorage.getItem('access_token');
const authHeader = () => ({ 'Authorization': `Bearer ${token()}`, 'Content-Type': 'application/json' });

if (!token()) window.location.href = 'index.html';

document.getElementById('btn-logout').addEventListener('click', () => {
  localStorage.clear();
  window.location.href = 'index.html';
});

// ── State ────────────────────────────────────────────────────────────────────
let currentPlan = null;

// ── Init ─────────────────────────────────────────────────────────────────────
async function init() {
  await loadPlan();
  await Promise.all([loadSchedule(), loadWebhookStatus()]);
}

// ── Plan ─────────────────────────────────────────────────────────────────────
async function loadPlan() {
  try {
    const res = await fetch(`${API}/subscription/my-plan`, { headers: authHeader() });
    if (!res.ok) return;
    const data = await res.json();
    currentPlan = data.plan_name;
    renderPlanGating();
  } catch (e) {
    console.error('Erreur chargement plan', e);
  }
}

function renderPlanGating() {
  const banner = document.getElementById('plan-banner');
  const planColors = {
    starter:  'bg-gray-100 text-gray-600',
    pro:      'bg-blue-50 text-blue-700 border border-blue-200',
    business: 'bg-green-50 text-[#005F02] border border-green-200',
  };
  banner.className = `rounded-lg px-4 py-3 text-sm font-medium ${planColors[currentPlan] || 'bg-gray-100 text-gray-600'}`;
  banner.textContent = `Plan actuel : ${currentPlan ? currentPlan.charAt(0).toUpperCase() + currentPlan.slice(1) : '—'}`;
  banner.classList.remove('hidden');

  const ondemandBadge = document.getElementById('badge-plan-ondemand');
  const schedBadge    = document.getElementById('badge-plan-scheduled');

  if (currentPlan === 'starter' || !currentPlan) {
    // On-demand locked
    document.getElementById('ondemand-locked').classList.remove('hidden');
    document.getElementById('ondemand-available').classList.add('hidden');
    ondemandBadge.textContent = 'Starter';
    ondemandBadge.className = 'text-xs px-2 py-1 rounded-full badge-locked font-semibold';

    // Scheduled locked
    document.getElementById('scheduled-locked').classList.remove('hidden');
    document.getElementById('scheduled-available').classList.add('hidden');
    schedBadge.textContent = 'Business';
    schedBadge.className = 'text-xs px-2 py-1 rounded-full badge-locked font-semibold';
  } else if (currentPlan === 'pro') {
    // On-demand available (with quota)
    document.getElementById('ondemand-locked').classList.add('hidden');
    document.getElementById('ondemand-available').classList.remove('hidden');
    ondemandBadge.textContent = 'Pro';
    ondemandBadge.className = 'text-xs px-2 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200 font-semibold';

    // Scheduled locked
    document.getElementById('scheduled-locked').classList.remove('hidden');
    document.getElementById('scheduled-available').classList.add('hidden');
    schedBadge.textContent = 'Business';
    schedBadge.className = 'text-xs px-2 py-1 rounded-full badge-locked font-semibold';
  } else if (currentPlan === 'business') {
    // Both available
    document.getElementById('ondemand-locked').classList.add('hidden');
    document.getElementById('ondemand-available').classList.remove('hidden');
    ondemandBadge.textContent = 'Business';
    ondemandBadge.className = 'text-xs px-2 py-1 rounded-full bg-green-50 text-[#005F02] border border-green-200 font-semibold';

    document.getElementById('scheduled-locked').classList.add('hidden');
    document.getElementById('scheduled-available').classList.remove('hidden');
    schedBadge.textContent = 'Business';
    schedBadge.className = 'text-xs px-2 py-1 rounded-full bg-green-50 text-[#005F02] border border-green-200 font-semibold';
  }
}

// ── Schedule ─────────────────────────────────────────────────────────────────
async function loadSchedule() {
  try {
    const res = await fetch(`${API}/reports/schedule`, { headers: authHeader() });
    if (!res.ok) return;
    const sched = await res.json();
    renderSchedule(sched);
  } catch (e) {
    console.error('Erreur chargement schedule', e);
  }
}

function renderSchedule(sched) {
  const enabledBox = document.getElementById('sched-enabled');
  const freqRow    = document.getElementById('sched-frequency-row');
  const freqSel    = document.getElementById('sched-frequency');
  const quotaLabel = document.getElementById('quota-label');

  enabledBox.checked = sched.enabled;
  if (sched.frequency) freqSel.value = sched.frequency;
  freqRow.classList.toggle('hidden', !sched.enabled);

  // Quota (Pro plan: 5/month)
  if (currentPlan === 'pro') {
    const limit = 5;
    quotaLabel.textContent = `Rapports utilisés ce mois : ${sched.ai_reports_used_month} / ${limit}`;
    quotaLabel.classList.remove('hidden');
    const btn = document.getElementById('btn-generate');
    if (sched.ai_reports_used_month >= limit) {
      btn.disabled = true;
      quotaLabel.className = 'text-sm text-red-500 mt-1';
    } else {
      btn.disabled = false;
      quotaLabel.className = 'text-sm text-gray-400 mt-1';
    }
  }

  // Last scheduled status
  if (sched.last_sent_at || sched.last_status) {
    document.getElementById('sched-status').classList.remove('hidden');
    document.getElementById('sched-last-sent').textContent = sched.last_sent_at
      ? new Date(sched.last_sent_at).toLocaleString('fr-FR')
      : '—';
    const badge = document.getElementById('sched-last-badge');
    if (sched.last_status === 'sent') {
      badge.textContent = 'Envoyé';
      badge.className = 'ml-2 text-xs px-2 py-0.5 rounded-full badge-sent';
    } else if (sched.last_status === 'failed') {
      badge.textContent = 'Échec';
      badge.className = 'ml-2 text-xs px-2 py-0.5 rounded-full badge-failed';
    }
  }
}

document.getElementById('sched-enabled').addEventListener('change', (e) => {
  document.getElementById('sched-frequency-row').classList.toggle('hidden', !e.target.checked);
});

// ── Generate on-demand ───────────────────────────────────────────────────────
document.getElementById('btn-generate').addEventListener('click', async () => {
  const btn = document.getElementById('btn-generate');
  const fb  = document.getElementById('generate-feedback');
  btn.disabled = true;
  btn.textContent = 'Génération en cours…';
  fb.classList.add('hidden');

  try {
    const res = await fetch(`${API}/reports/generate`, {
      method: 'POST',
      headers: authHeader(),
    });
    const data = await res.json();
    if (!res.ok) {
      fb.textContent = data.detail || 'Erreur lors de la génération.';
      fb.className = 'text-sm mt-2 text-red-600';
    } else {
      fb.textContent = `Rapport envoyé par email ! (${data.used}${data.limit ? `/${data.limit}` : ''} ce mois)`;
      fb.className = 'text-sm mt-2 text-green-700';
      await loadSchedule(); // refresh quota display
    }
  } catch (e) {
    fb.textContent = 'Erreur réseau.';
    fb.className = 'text-sm mt-2 text-red-600';
  }

  fb.classList.remove('hidden');
  btn.textContent = 'Générer un rapport';
  btn.disabled = false;
});

// ── Save schedule ────────────────────────────────────────────────────────────
document.getElementById('btn-save-schedule').addEventListener('click', async () => {
  const btn   = document.getElementById('btn-save-schedule');
  const fb    = document.getElementById('schedule-feedback');
  const enabled   = document.getElementById('sched-enabled').checked;
  const frequency = document.getElementById('sched-frequency').value;

  btn.disabled = true;
  fb.classList.add('hidden');

  try {
    const res = await fetch(`${API}/reports/schedule`, {
      method: 'PUT',
      headers: authHeader(),
      body: JSON.stringify({ enabled, frequency: enabled ? frequency : null }),
    });
    const data = await res.json();
    if (!res.ok) {
      fb.textContent = data.detail || 'Erreur lors de la sauvegarde.';
      fb.className = 'text-sm text-red-600';
    } else {
      fb.textContent = 'Configuration enregistrée.';
      fb.className = 'text-sm text-green-700';
      renderSchedule(data);
    }
  } catch (e) {
    fb.textContent = 'Erreur réseau.';
    fb.className = 'text-sm text-red-600';
  }

  fb.classList.remove('hidden');
  btn.disabled = false;
});

// ── Webhook ───────────────────────────────────────────────────────────────────
async function loadWebhookStatus() {
  try {
    const res = await fetch(`${API}/webhook/status`, { headers: authHeader() });
    if (!res.ok) return;
    const data = await res.json();
    renderWebhookStatus(data);
  } catch (e) {
    console.error('Erreur statut webhook', e);
  }
}

function renderWebhookStatus(data) {
  const dot = document.getElementById('webhook-status-dot');
  if (!data.configured) {
    document.getElementById('webhook-unconfigured').classList.remove('hidden');
    document.getElementById('webhook-configured').classList.add('hidden');
    dot.className = 'w-3 h-3 rounded-full bg-gray-300 mt-1 shrink-0';
    dot.title = 'Non configuré';
    return;
  }

  document.getElementById('webhook-unconfigured').classList.add('hidden');
  document.getElementById('webhook-configured').classList.remove('hidden');

  const code = data.last_status_code;
  const isOk = code && code >= 200 && code < 300;
  dot.className = `w-3 h-3 rounded-full mt-1 shrink-0 ${isOk ? 'bg-green-500' : (code ? 'bg-red-400' : 'bg-gray-300')}`;
  dot.title = code ? `HTTP ${code}` : 'Jamais envoyé';

  document.getElementById('webhook-last-sent').textContent = data.last_sent_at
    ? new Date(data.last_sent_at).toLocaleString('fr-FR')
    : '—';
  document.getElementById('webhook-last-status').textContent = code
    ? `${code} ${isOk ? '✓' : '✗'}`
    : '—';
}

document.getElementById('btn-trigger-webhook').addEventListener('click', async () => {
  const btn = document.getElementById('btn-trigger-webhook');
  const fb  = document.getElementById('webhook-feedback');
  btn.disabled = true;
  btn.textContent = 'Envoi en cours…';
  fb.classList.add('hidden');

  try {
    const res = await fetch(`${API}/webhook/trigger`, {
      method: 'POST',
      headers: authHeader(),
    });
    const data = await res.json();
    if (!res.ok) {
      fb.textContent = data.detail || 'Erreur lors de l\'envoi.';
      fb.className = 'text-sm text-red-600';
    } else {
      fb.textContent = `Webhook envoyé (HTTP ${data.last_status_code}).`;
      fb.className = 'text-sm text-green-700';
      renderWebhookStatus(data);
    }
  } catch (e) {
    fb.textContent = 'Erreur réseau.';
    fb.className = 'text-sm text-red-600';
  }

  fb.classList.remove('hidden');
  btn.textContent = 'Envoyer maintenant';
  btn.disabled = false;
});

// ── Boot ──────────────────────────────────────────────────────────────────────
init();
