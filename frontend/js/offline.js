/* offline.js — PWA glue: service worker, offline write queue (IndexedDB),
   connection indicator, and auto-sync on reconnect.

   Usage from a page:
     Flotte.queueOrSend({ type:'fuel', url:'/api/v1/fuel', body }) // body gets a client_uuid
     Flotte.onSync(() => reloadMyList())                            // refresh after a sync flush
*/
(function () {
  const API_TOKEN = () => localStorage.getItem('access_token');
  const DB_NAME = 'flotte225';
  const STORE = 'outbox';
  const listeners = [];

  // ── Service worker registration ─────────────────────────────────────────────
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js').catch((e) =>
        console.warn('SW registration failed', e)
      );
    });
  }

  // ── Tiny IndexedDB wrapper ──────────────────────────────────────────────────
  function openDB() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: 'id', autoIncrement: true });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  function tx(mode, fn) {
    return openDB().then(
      (db) =>
        new Promise((resolve, reject) => {
          const t = db.transaction(STORE, mode);
          const store = t.objectStore(STORE);
          const out = fn(store);
          t.oncomplete = () => resolve(out._result !== undefined ? out._result : out);
          t.onerror = () => reject(t.error);
        })
    );
  }

  function addRecord(rec) {
    return tx('readwrite', (store) => {
      const r = { _result: undefined };
      const req = store.add(rec);
      req.onsuccess = () => (r._result = req.result);
      return r;
    });
  }

  function allRecords() {
    return tx('readonly', (store) => {
      const r = { _result: [] };
      const req = store.getAll();
      req.onsuccess = () => (r._result = req.result || []);
      return r;
    });
  }

  function removeRecord(id) {
    return tx('readwrite', (store) => store.delete(id));
  }

  function uuid() {
    return window.crypto && crypto.randomUUID
      ? crypto.randomUUID()
      : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
          const r = (Math.random() * 16) | 0;
          return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
        });
  }

  // ── Connection / pending indicator ──────────────────────────────────────────
  let badge;
  function ensureBadge() {
    if (badge) return badge;
    badge = document.createElement('div');
    badge.id = 'flotte-net-badge';
    badge.style.cssText =
      'position:fixed;bottom:1rem;left:50%;transform:translateX(-50%);z-index:9999;' +
      'font-family:Inter,system-ui,sans-serif;font-size:.8rem;font-weight:600;' +
      'padding:.5rem .9rem;border-radius:9999px;box-shadow:0 4px 14px rgba(0,0,0,.18);' +
      'display:none;';
    document.body.appendChild(badge);
    return badge;
  }

  async function refreshBadge(state) {
    const b = ensureBadge();
    const pending = (await allRecords()).length;
    if (state === 'syncing') {
      b.style.display = '';
      b.style.background = '#005F02';
      b.style.color = '#fff';
      b.textContent = 'Synchronisation…';
      return;
    }
    if (!navigator.onLine) {
      b.style.display = '';
      b.style.background = '#FEF3C7';
      b.style.color = '#92400E';
      b.textContent = pending
        ? `Hors ligne · ${pending} saisie(s) en attente`
        : 'Hors ligne';
      return;
    }
    if (pending) {
      b.style.display = '';
      b.style.background = '#FEF3C7';
      b.style.color = '#92400E';
      b.textContent = `${pending} saisie(s) en attente`;
      return;
    }
    b.style.display = 'none';
  }

  // ── Sync ───────────────────────────────────────────────────────────────────
  let syncing = false;
  async function sync() {
    if (syncing || !navigator.onLine) return;
    const items = await allRecords();
    if (!items.length) return;
    syncing = true;
    refreshBadge('syncing');
    let flushed = 0;
    for (const item of items) {
      try {
        const res = await fetch(item.url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${API_TOKEN()}`,
          },
          body: JSON.stringify(item.body),
        });
        // 2xx → done. Idempotent: a re-sent client_uuid returns the stored row.
        if (res.ok) {
          await removeRecord(item.id);
          flushed++;
        } else if (res.status === 401) {
          break; // auth expired — keep queue, retry after re-login
        }
        // other errors: leave queued, continue to next item
      } catch {
        break; // network dropped again — stop, keep the rest
      }
    }
    syncing = false;
    refreshBadge();
    if (flushed) listeners.forEach((fn) => { try { fn(flushed); } catch {} });
  }

  // ── Public API ───────────────────────────────────────────────────────────────
  async function queueOrSend({ type, url, body }) {
    const payload = { ...body, client_uuid: body.client_uuid || uuid() };

    if (navigator.onLine) {
      try {
        const res = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${API_TOKEN()}`,
          },
          body: JSON.stringify(payload),
        });
        const json = await res.json().catch(() => ({}));
        if (res.ok) return { ok: true, queued: false, data: json.data, json };
        // Validation / auth errors are real — surface them, don't queue.
        if (res.status >= 400 && res.status < 500) {
          return { ok: false, queued: false, status: res.status, json };
        }
        // 5xx → fall through to queue
      } catch {
        // network error → fall through to queue
      }
    }

    await addRecord({ type, url, body: payload, createdAt: Date.now() });
    refreshBadge();
    return { ok: true, queued: true };
  }

  window.addEventListener('online', () => { refreshBadge(); sync(); });
  window.addEventListener('offline', () => refreshBadge());
  window.addEventListener('load', () => { refreshBadge(); sync(); });

  window.Flotte = {
    uuid,
    queueOrSend,
    sync,
    pendingCount: async () => (await allRecords()).length,
    onSync: (fn) => listeners.push(fn),
  };

  // ── "Install this app" prompt (Add to Home Screen) ───────────────────────────
  // "Plus tard" snoozes for a week (so the prompt comes back) — we only hide it
  // for good once the app is actually installed.
  const SNOOZE_KEY = 'flotte225-install-snooze';     // ms timestamp to hide until
  const INSTALLED_KEY = 'flotte225-installed';
  const SNOOZE_MS = 7 * 24 * 60 * 60 * 1000;
  const isStandalone = () =>
    window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true;
  const isSnoozed = () => {
    if (localStorage.getItem(INSTALLED_KEY) === '1') return true;
    return Date.now() < parseInt(localStorage.getItem(SNOOZE_KEY) || '0', 10);
  };

  window.addEventListener('appinstalled', () => {
    localStorage.setItem(INSTALLED_KEY, '1');
  });

  function showInstallBanner(onInstall, iosHint) {
    if (isSnoozed() || isStandalone()) return;
    const bar = document.createElement('div');
    bar.style.cssText =
      'position:fixed;left:50%;bottom:1rem;transform:translateX(-50%);z-index:9998;' +
      'width:min(92%,26rem);background:#fff;border:1px solid #e6e6e6;border-radius:.9rem;' +
      'box-shadow:0 8px 28px rgba(0,0,0,.18);padding:.85rem 1rem;font-family:Inter,system-ui,sans-serif;';
    bar.innerHTML =
      '<div style="display:flex;align-items:center;gap:.75rem;">' +
        '<div style="font-size:1.5rem;">📲</div>' +
        '<div style="flex:1;font-size:.85rem;color:#1f2937;">' +
          '<strong style="color:#005F02;">Installer Flotte225</strong><br>' +
          (iosHint
            ? 'Appuyez sur <strong>Partager</strong> puis « Sur l\'écran d\'accueil ».'
            : 'Ajoutez l\'app à votre écran d\'accueil pour un accès rapide.') +
        '</div>' +
      '</div>' +
      (iosHint ? '' :
        '<div style="display:flex;gap:.5rem;margin-top:.7rem;justify-content:flex-end;">' +
          '<button id="fl-inst-no" style="background:none;border:none;color:#6b7280;font-size:.8rem;font-weight:600;cursor:pointer;">Plus tard</button>' +
          '<button id="fl-inst-yes" style="background:#005F02;color:#fff;border:none;border-radius:.5rem;padding:.45rem .9rem;font-size:.8rem;font-weight:700;cursor:pointer;">Installer</button>' +
        '</div>') +
      (iosHint ? '<button id="fl-inst-no" style="position:absolute;top:.4rem;right:.6rem;background:none;border:none;color:#9ca3af;font-size:1.1rem;cursor:pointer;">×</button>' : '');
    bar.style.position = 'fixed';
    document.body.appendChild(bar);

    const close = () => {
      localStorage.setItem(SNOOZE_KEY, String(Date.now() + SNOOZE_MS));
      bar.remove();
    };
    const no = bar.querySelector('#fl-inst-no');
    if (no) no.addEventListener('click', close);
    const yes = bar.querySelector('#fl-inst-yes');
    if (yes) yes.addEventListener('click', async () => { bar.remove(); await onInstall(); });
  }

  // Android / Chromium: capture the native prompt and offer our own button.
  let deferredPrompt = null;
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    showInstallBanner(async () => {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      const choice = await deferredPrompt.userChoice;
      deferredPrompt = null;
      // If they dismissed the native dialog, snooze; "accepted" → appinstalled fires.
      if (choice && choice.outcome !== 'accepted') {
        localStorage.setItem(SNOOZE_KEY, String(Date.now() + SNOOZE_MS));
      }
    }, false);
  });

  // iOS Safari: no beforeinstallprompt — show manual instructions instead.
  const isIOS = /iphone|ipad|ipod/i.test(window.navigator.userAgent);
  if (isIOS && !isStandalone()) {
    window.addEventListener('load', () => setTimeout(() => showInstallBanner(() => {}, true), 1500));
  }
})();
