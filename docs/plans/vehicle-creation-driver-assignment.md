# Plan: Assign Driver During Vehicle Creation

**Date:** 2026-05-09  
**Status:** Ready to implement  
**Scope:** Frontend-only — backend already supports this feature

---

## Goal

Allow an owner to optionally assign an existing driver to a vehicle at the moment of creation, directly from the "Nouveau véhicule" modal.

- Driver selection is optional (no driver = current behavior, unchanged)
- Vehicle table display stays identical
- Driver side reflects the assignment as before (via existing VehicleDriver junction)

---

## Why No Backend Changes Are Needed

The backend is already fully wired:

| Capability | Endpoint / Model | Status |
|---|---|---|
| Accept `driver_ids` on vehicle creation | `POST /vehicles` (`VehicleCreate.driver_ids`) | ✅ Done |
| List owner's drivers | `GET /drivers` → `DriverResponse` | ✅ Done |
| Vehicle–driver junction table | `VehicleDriver` (vehicle_id, driver_id) | ✅ Done |
| Uniqueness constraint | `UNIQUE(vehicle_id, driver_id)` | ✅ Done |

---

## Implementation Steps

### Step 1 — Load drivers when the "Add" modal opens (`vehicles.js`)

Add a `loadDriversForSelect()` async function:
- Calls `GET /api/v1/drivers`
- Populates `<select id="v-driver">` with one `<option>` per driver (value = driver `id`, label = driver `full_name`)
- Prepends a blank/default option: `"— Aucun chauffeur (optionnel) —"` (value = `""`)

Call `loadDriversForSelect()` inside `openAddModal()`.

### Step 2 — Add driver select field to `vehicles.html`

Below the "Kilométrage initial" field, add:

```html
<div>
  <label class="block text-xs font-semibold text-gray-600 mb-1">
    Chauffeur <span class="text-gray-400 font-normal">(optionnel)</span>
  </label>
  <select id="v-driver" class="input-field">
    <option value="">— Aucun chauffeur —</option>
  </select>
</div>
```

This field appears only in the creation modal. It is not shown/used in the edit flow.

### Step 3 — Include `driver_ids` in the POST payload (`vehicles.js`)

In `submitForm()`, after reading the other fields:

```javascript
const driverIdRaw = document.getElementById('v-driver').value;
const driver_ids = driverIdRaw ? [parseInt(driverIdRaw)] : undefined;
```

Pass `driver_ids` in the POST body:

```javascript
body: JSON.stringify({ name, license_plate, brand, model, year, fuel_type, initial_mileage, ...(driver_ids && { driver_ids }) }),
```

If no driver is selected, `driver_ids` is omitted entirely — backend treats it as `null`, behavior is identical to today.

### Step 4 — Reset the select on modal close (`vehicles.js`)

In `openAddModal()` and the modal close/cancel handler, reset:

```javascript
document.getElementById('v-driver').value = '';
```

---

## What Does NOT Change

- Vehicle table columns — **unchanged**
- Edit modal — **not touched**
- All existing create/edit/archive flows — **zero regression**
- Backend code and DB schema — **no changes**

---

## Risk Assessment

| Risk | Level | Mitigation |
|---|---|---|
| Regression on existing vehicle create | None | `driver_ids` is optional; omitting = current behavior |
| Regression on vehicle edit | None | Edit path not modified |
| Driver list API failure | Low | If `GET /drivers` fails, select stays empty; creation still works |
| DB conflict (duplicate assignment) | None | Backend enforces UNIQUE constraint and returns 400 |

---

## Files to Modify

| File | Change |
|---|---|
| `frontend/vehicles.html` | Add `<select id="v-driver">` field below mileage input |
| `frontend/js/vehicles.js` | Add `loadDriversForSelect()`, call on modal open, include `driver_ids` in POST |

