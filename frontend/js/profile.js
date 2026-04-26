const API = '/api/v1';
const token = () => localStorage.getItem('access_token');

if (!token()) window.location.href = '/';

function logout() {
  localStorage.clear();
  window.location.href = '/';
}

function formatPrice(fcfa) {
  if (!fcfa) return 'Gratuit';
  return new Intl.NumberFormat('fr-FR').format(fcfa) + ' FCFA/mois';
}

function usageText(used, max) {
  if (max === null || max === undefined) return `${used} / illimité`;
  return `${used} / ${max}`;
}

function usagePct(used, max) {
  if (!max) return 0;
  return Math.min(100, Math.round((used / max) * 100));
}

function barClass(pct) {
  if (pct >= 100) return 'full';
  if (pct >= 80) return 'warn';
  return '';
}

function setBar(barId, pct) {
  const el = document.getElementById(barId);
  el.style.width = pct + '%';
  el.className = `usage-bar-fill ${barClass(pct)}`;
}

function setFeature(id, enabled) {
  const el = document.getElementById(id);
  if (enabled) {
    el.textContent = 'Inclus';
    el.className = 'feature-yes';
  } else {
    el.textContent = 'Non inclus';
    el.className = 'feature-no';
  }
}

async function loadProfile() {
  const res = await fetch(`${API}/subscription/my-plan`, {
    headers: { Authorization: `Bearer ${token()}` },
  });

  if (res.status === 401) { logout(); return; }

  const json = await res.json();
  const d = json.data;
  if (!d) return;

  const plan = d.plan;
  const planName = plan.name;

  // Plan badge
  const badge = document.getElementById('plan-badge');
  badge.textContent = planName.charAt(0).toUpperCase() + planName.slice(1);
  badge.className = `inline-block px-4 py-1 rounded-full text-base font-bold plan-badge-${planName}`;

  document.getElementById('plan-price').textContent = formatPrice(plan.price_fcfa);

  if (d.expires_at) {
    const exp = new Date(d.expires_at).toLocaleDateString('fr-FR');
    document.getElementById('plan-expires').textContent = `Expire le ${exp}`;
  } else {
    document.getElementById('plan-expires').textContent = planName === 'starter' ? 'Plan gratuit — aucune expiration' : 'Pas de date d\'expiration configurée';
  }

  // Usage bars
  const vehPct = usagePct(d.active_vehicles, plan.max_vehicles);
  document.getElementById('veh-count').textContent = usageText(d.active_vehicles, plan.max_vehicles);
  setBar('veh-bar', vehPct);

  const drvPct = usagePct(d.active_drivers, plan.max_drivers);
  document.getElementById('drv-count').textContent = usageText(d.active_drivers, plan.max_drivers);
  setBar('drv-bar', drvPct);

  if (plan.ai_reports_per_month === 0) {
    document.getElementById('ai-section').classList.add('hidden');
  } else {
    document.getElementById('ai-count').textContent = plan.ai_reports_per_month === null ? 'Illimité' : `quota : ${plan.ai_reports_per_month}/mois`;
    document.getElementById('ai-bar').style.width = plan.ai_reports_per_month === null ? '30%' : '0%';
  }

  // Features
  setFeature('feat-export', plan.has_export);
  setFeature('feat-whatsapp', plan.has_whatsapp);
  setFeature('feat-ai', plan.ai_reports_per_month !== 0);
  setFeature('feat-webhook', plan.has_webhook);

  // Upgrade CTA
  const cta = document.getElementById('upgrade-cta');
  const upgradeText = document.getElementById('upgrade-text');
  if (planName === 'starter') {
    cta.classList.remove('hidden');
    upgradeText.textContent = 'Passez au plan Pro (9 900 FCFA/mois) pour débloquer l\'export, WhatsApp, les rapports IA et jusqu\'à 15 véhicules.';
  } else if (planName === 'pro') {
    cta.classList.remove('hidden');
    upgradeText.textContent = 'Passez au plan Business (24 900 FCFA/mois) pour les rapports IA illimités, les webhooks et des véhicules illimités.';
  }

  document.getElementById('loading').classList.add('hidden');
  document.getElementById('content').classList.remove('hidden');
}

loadProfile();
