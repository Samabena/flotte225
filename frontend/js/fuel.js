/* fuel.js — Driver fuel entry + history (US-010 – US-014) + route/GPS (Sprint 10) */

const API = '/api/v1';
const token = () => localStorage.getItem('access_token');
const authHeader = () => ({ 'Authorization': `Bearer ${token()}` });

if (!token()) window.location.href = '/login';

document.getElementById('btn-logout').addEventListener('click', () => {
  localStorage.clear();
  window.location.href = '/login';
});

// ── Set today as default date ─────────────────────────────────────────────────
document.getElementById('f-date').value = new Date().toISOString().split('T')[0];

// ── Load assigned vehicles for the form select ────────────────────────────────
let vehicleMap = {};

async function loadVehicles() {
  try {
    const res = await fetch(`${API}/driver/vehicles`, { headers: authHeader() });
    if (res.status === 401 || res.status === 403) {
      window.location.href = '/login'; return;
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

// ── Google Maps / route state ─────────────────────────────────────────────────
let mapsReady = false;
let departureAutocomplete = null;
let destinationAutocomplete = null;

let routeData = {
  departure_place: null,
  departure_lat: null,
  departure_lng: null,
  destination_place: null,
  destination_lat: null,
  destination_lng: null,
  route_distance_km: null,
};

function resetRouteData() {
  routeData = {
    departure_place: null, departure_lat: null, departure_lng: null,
    destination_place: null, destination_lat: null, destination_lng: null,
    route_distance_km: null,
  };
}

// ── Load Google Maps API key then inject the script ───────────────────────────
async function loadMapsApi() {
  try {
    const res = await fetch(`${API}/config/maps`, { headers: authHeader() });
    if (!res.ok) return;
    const { google_maps_api_key } = await res.json();
    if (!google_maps_api_key) return;

    window._mapsInitCallback = initMaps;
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(google_maps_api_key)}&libraries=places&callback=_mapsInitCallback`;
    script.async = true;
    script.defer = true;
    document.head.appendChild(script);
  } catch (e) {
    console.warn('Impossible de charger Google Maps', e);
  }
}

function initMaps() {
  mapsReady = true;

  const ciBounds = new google.maps.LatLngBounds(
    new google.maps.LatLng(4.35, -8.6),
    new google.maps.LatLng(10.74, -2.49)
  );

  // Departure autocomplete (type-to-search, biased to CI)
  departureAutocomplete = new google.maps.places.Autocomplete(
    document.getElementById('f-departure'),
    { bounds: ciBounds, strictBounds: false, fields: ['name', 'formatted_address', 'geometry'] }
  );
  departureAutocomplete.addListener('place_changed', () => {
    const place = departureAutocomplete.getPlace();
    if (!place.geometry) return;
    routeData.departure_place = place.name || place.formatted_address;
    routeData.departure_lat   = place.geometry.location.lat();
    routeData.departure_lng   = place.geometry.location.lng();
    maybeCalculateRoute();
  });

  // Destination autocomplete
  destinationAutocomplete = new google.maps.places.Autocomplete(
    document.getElementById('f-destination'),
    { bounds: ciBounds, strictBounds: false, fields: ['name', 'formatted_address', 'geometry'] }
  );
  destinationAutocomplete.addListener('place_changed', () => {
    const place = destinationAutocomplete.getPlace();
    if (!place.geometry) return;
    routeData.destination_place = place.name || place.formatted_address;
    routeData.destination_lat   = place.geometry.location.lat();
    routeData.destination_lng   = place.geometry.location.lng();
    maybeCalculateRoute();
  });
}

// ── GPS: detect current position as departure ─────────────────────────────────
document.getElementById('btn-gps').addEventListener('click', () => {
  if (!navigator.geolocation) {
    showGpsStatus('La géolocalisation n\'est pas supportée par ce navigateur.', true);
    return;
  }
  showGpsStatus('Localisation en cours…', false);
  document.getElementById('btn-gps').disabled = true;

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;
      routeData.departure_lat = lat;
      routeData.departure_lng = lng;

      if (mapsReady) {
        // Reverse geocode to get a readable place name
        const geocoder = new google.maps.Geocoder();
        geocoder.geocode({ location: { lat, lng } }, (results, status) => {
          document.getElementById('btn-gps').disabled = false;
          if (status === 'OK' && results[0]) {
            const name = results[0].formatted_address;
            routeData.departure_place = name;
            document.getElementById('f-departure').value = name;
            showGpsStatus('Position détectée', false);
            maybeCalculateRoute();
          } else {
            // Fallback: use raw coords as place name
            const fallback = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
            routeData.departure_place = fallback;
            document.getElementById('f-departure').value = fallback;
            showGpsStatus('Position détectée (coordonnées brutes)', false);
            maybeCalculateRoute();
          }
        });
      } else {
        // Maps not loaded — store coords, use coords as display text
        document.getElementById('btn-gps').disabled = false;
        const fallback = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
        routeData.departure_place = fallback;
        document.getElementById('f-departure').value = fallback;
        showGpsStatus('Position détectée', false);
      }
    },
    (err) => {
      document.getElementById('btn-gps').disabled = false;
      const msgs = {
        1: 'Permission refusée. Veuillez autoriser la localisation dans votre navigateur.',
        2: 'Position introuvable. Vérifiez votre connexion GPS.',
        3: 'Délai dépassé. Réessayez.',
      };
      showGpsStatus(msgs[err.code] || 'Erreur de géolocalisation.', true);
    },
    { timeout: 10000, maximumAge: 60000 }
  );
});

function showGpsStatus(msg, isError) {
  const el = document.getElementById('gps-status');
  el.textContent = msg;
  el.className = `text-xs mt-1 ${isError ? 'text-red-500' : 'text-gray-400'}`;
  el.classList.remove('hidden');
  if (!isError) setTimeout(() => el.classList.add('hidden'), 3000);
}

// ── Calculate route distance via Directions API ───────────────────────────────
function maybeCalculateRoute() {
  if (!mapsReady) return;
  if (!routeData.departure_lat || !routeData.destination_lat) return;

  const routeErr = document.getElementById('route-error');
  routeErr.classList.add('hidden');

  const service = new google.maps.DirectionsService();
  service.route(
    {
      origin:      { lat: routeData.departure_lat,   lng: routeData.departure_lng },
      destination: { lat: routeData.destination_lat, lng: routeData.destination_lng },
      travelMode:  google.maps.TravelMode.DRIVING,
    },
    (result, status) => {
      if (status === 'OK') {
        const metres = result.routes[0].legs[0].distance.value;
        routeData.route_distance_km = Math.round(metres / 100) / 10; // 1 decimal
        showDistanceBadge(routeData.route_distance_km, routeData.departure_place, routeData.destination_place);
      } else {
        routeErr.textContent = 'Impossible de calculer la distance. Vérifiez les lieux sélectionnés.';
        routeErr.classList.remove('hidden');
      }
    }
  );
}

function showDistanceBadge(km, from, to) {
  document.getElementById('route-distance-text').textContent =
    `${esc(from)} → ${esc(to)} · ${km.toLocaleString('fr-FR')} km`;
  document.getElementById('route-distance-badge').classList.remove('hidden');
}

document.getElementById('btn-clear-route').addEventListener('click', () => {
  resetRouteData();
  document.getElementById('f-departure').value   = '';
  document.getElementById('f-destination').value = '';
  document.getElementById('route-distance-badge').classList.add('hidden');
  document.getElementById('route-error').classList.add('hidden');
  document.getElementById('gps-status').classList.add('hidden');
});

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

  const body = {
    vehicle_id:      parseInt(vehicle_id),
    date,
    odometer_km:     parseInt(odometer_km),
    quantity_litres: parseFloat(quantity_litres),
    amount_fcfa:     parseFloat(amount_fcfa),
  };

  // Attach route data if a full route was calculated
  if (routeData.departure_place && routeData.destination_place && routeData.route_distance_km) {
    body.departure_place   = routeData.departure_place;
    body.departure_lat     = routeData.departure_lat;
    body.departure_lng     = routeData.departure_lng;
    body.destination_place = routeData.destination_place;
    body.destination_lat   = routeData.destination_lat;
    body.destination_lng   = routeData.destination_lng;
    body.route_distance_km = routeData.route_distance_km;
  }

  const res = await fetch(`${API}/fuel`, {
    method: 'POST',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const json = await res.json().catch(() => ({}));
  if (res.ok) {
    okEl.textContent = 'Saisie enregistrée avec succès !';
    okEl.classList.remove('hidden');
    // Reset form
    document.getElementById('f-odometer').value  = '';
    document.getElementById('f-quantity').value   = '';
    document.getElementById('f-amount').value     = '';
    document.getElementById('f-date').value       = new Date().toISOString().split('T')[0];
    // Reset route
    document.getElementById('btn-clear-route').click();
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

    const routeCell = (e.departure_place && e.destination_place && e.route_distance_km)
      ? `<span class="inline-flex items-center gap-1 text-[#005F02] text-xs" title="${esc(e.departure_place)} → ${esc(e.destination_place)}">
           <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
             <path stroke-linecap="round" stroke-linejoin="round" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 110-5 2.5 2.5 0 010 5z"/>
           </svg>
           ${parseFloat(e.route_distance_km).toLocaleString('fr-FR')} km
         </span>`
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
        <td class="py-2 text-right">${routeCell}</td>
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
loadMapsApi();
