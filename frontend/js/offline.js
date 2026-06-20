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
})();
