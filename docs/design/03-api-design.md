# 3. API Design

## Base URL
All endpoints are prefixed with `/api/v1/`.

## Authentication
Protected routes require: `Authorization: Bearer <token>`

The JWT middleware validates the token, injects `current_user` (id, role, plan) into every request, and enforces role-based access. Plan checks run as a second dependency layer on gated endpoints.

## Standard Response Envelope
```json
{ "success": true, "data": {}, "message": "" }
```

## Standard Error Format
```json
{ "success": false, "error": { "code": "PLAN_LIMIT_EXCEEDED", "message": "..." } }
```

---

## Endpoints by Domain

### Auth
| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Register new OWNER account (DRIVER role blocked) | No |
| POST | `/api/v1/auth/verify-email` | Submit OTP to activate account | No |
| POST | `/api/v1/auth/login` | Login → returns JWT. Dual-mode: email+password (OWNER/ADMIN) or username+password (DRIVER) | No |
| POST | `/api/v1/auth/logout` | Clear client token (frontend) | Yes |
| GET | `/api/v1/auth/me` | Get current user profile + plan info | Yes |
| PATCH | `/api/v1/auth/me` | Update profile (name, company, WhatsApp number) | Yes |
| POST | `/api/v1/auth/forgot-password` | Request OTP for password reset | No |
| POST | `/api/v1/auth/reset-password` | Submit OTP + new password | No |

---

### Vehicles
| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/vehicles` | List owner's active vehicles | OWNER |
| POST | `/api/v1/vehicles` | Create a new vehicle | OWNER |
| GET | `/api/v1/vehicles/archived` | List archived vehicles | OWNER |
| GET | `/api/v1/vehicles/{id}` | Get vehicle details | OWNER |
| PATCH | `/api/v1/vehicles/{id}` | Update vehicle fields | OWNER |
| POST | `/api/v1/vehicles/{id}/pause` | Set vehicle status to Paused | OWNER |
| POST | `/api/v1/vehicles/{id}/resume` | Set vehicle status to Active | OWNER |
| POST | `/api/v1/vehicles/{id}/archive` | Archive vehicle (soft delete) | OWNER |
| POST | `/api/v1/vehicles/{id}/restore` | Restore archived vehicle | OWNER |
| GET | `/api/v1/vehicles/{id}/drivers` | List drivers assigned to vehicle | OWNER |
| POST | `/api/v1/vehicles/{id}/drivers` | Assign a driver to vehicle | OWNER |
| DELETE | `/api/v1/vehicles/{id}/drivers/{driver_id}` | Remove driver from vehicle | OWNER |

---

### Driver Management (Owner-provisioned)
> **Added in feature: Owner-Managed Driver Access Control** — 2026-04-19

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/api/v1/drivers` | Create a driver account (username + password, no email) | OWNER |
| GET | `/api/v1/drivers` | List owner's drivers (scoped to `owner_id = me`) | OWNER |
| PATCH | `/api/v1/drivers/{id}/status` | Enable or disable a driver's login (`{"is_disabled": true/false}`) | OWNER |
| PATCH | `/api/v1/drivers/{id}/password` | Reset a driver's password | OWNER |
| DELETE | `/api/v1/drivers/{id}` | Permanently remove a driver (clears vehicle assignments, preserves logs) | OWNER |

---

### Driver Status
| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/driver/vehicles` | List vehicles assigned to me | DRIVER |
| POST | `/api/v1/driver/activate` | Activate driving status + select vehicle | DRIVER |
| POST | `/api/v1/driver/deactivate` | Deactivate driving status | DRIVER |

---

### Fuel Entries
| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/api/v1/fuel-entries` | Submit a new fuel entry | DRIVER (active) |
| GET | `/api/v1/fuel-entries` | Owner: all fleet entries / Driver: last 10 | OWNER \| DRIVER |
| GET | `/api/v1/fuel-entries/{id}` | Get entry details | OWNER \| DRIVER |
| PATCH | `/api/v1/fuel-entries/{id}` | Edit own entry (within 24h) | DRIVER |
| DELETE | `/api/v1/fuel-entries/{id}` | Delete own entry (within 24h) | DRIVER |

---

### Maintenance
| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/vehicles/{id}/maintenance` | Get maintenance record (auto-creates if missing) | OWNER |
| PUT | `/api/v1/vehicles/{id}/maintenance` | Update maintenance record | OWNER |
| DELETE | `/api/v1/vehicles/{id}/maintenance` | Delete maintenance record | OWNER |

---

### Dashboard
| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/dashboard/owner` | Full owner analytics (spend, consumption, drivers, gauges) | OWNER |
| GET | `/api/v1/dashboard/owner/alerts` | Active maintenance + compliance alerts | OWNER |
| GET | `/api/v1/dashboard/owner/anomalies` | Vehicles with detected anomalies | OWNER |
| GET | `/api/v1/dashboard/driver` | Driver view (assigned vehicles + last 10 entries + status) | DRIVER |

---

### Activity Log
| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/activity-logs` | Paginated audit log (`?driver_id=&vehicle_id=`) | OWNER |

---

### Export *(Pro + Business)*
| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/api/v1/export` | Generate PDF or Excel export | OWNER |

**Request body:**
```json
{
  "dataset": "fuel_entries | analytics | maintenance | activity_logs",
  "format": "pdf | xlsx",
  "date_from": "2026-01-01",
  "date_to": "2026-04-06"
}
```

**Response:**
```json
{
  "file_url": "/downloads/export_2026-04-06_fuel.pdf",
  "expires_at": "2026-04-06T11:30:00Z"
}
```

---

### AI Reports *(Pro + Business)*
| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/api/v1/reports/generate` | Trigger on-demand AI report (sends email) | OWNER |
| GET | `/api/v1/reports/schedule` | Get current report schedule config | OWNER |
| PUT | `/api/v1/reports/schedule` | Enable/disable schedule + set frequency | OWNER |

---

### Webhook
| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/webhook/status` | Last dispatch timestamp + HTTP status | OWNER |
| POST | `/api/v1/webhook/trigger` | Manually trigger webhook dispatch | OWNER |

---

### Admin *(SUPER_ADMIN only)*
| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/admin/users` | Paginated user list (`?search=`) | SUPER_ADMIN |
| GET | `/api/v1/admin/users/{id}` | Get user details | SUPER_ADMIN |
| POST | `/api/v1/admin/users/{id}/suspend` | Suspend user account | SUPER_ADMIN |
| POST | `/api/v1/admin/users/{id}/reactivate` | Reactivate user account | SUPER_ADMIN |
| DELETE | `/api/v1/admin/users/{id}` | Permanently delete user + cascade data | SUPER_ADMIN |
| GET | `/api/v1/admin/users/{id}/fleet` | View owner's fleet (read-only) | SUPER_ADMIN |
| GET | `/api/v1/admin/users/{id}/subscription` | View owner's current plan | SUPER_ADMIN |
| PUT | `/api/v1/admin/users/{id}/subscription` | Change owner's plan | SUPER_ADMIN |
| PATCH | `/api/v1/admin/users/{id}/features` | Toggle per-owner feature flags | SUPER_ADMIN |
| GET | `/api/v1/admin/analytics` | Platform-wide stats + plan distribution | SUPER_ADMIN |

---

### Plans
| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/plans` | List all available plans + features | Yes |
| GET | `/api/v1/plans/my` | Current owner's plan + usage counters | OWNER |

---

## Key Request / Response Examples

### POST `/api/v1/auth/login`
```json
// Request
{ "email": "owner@flotte225.ci", "password": "secret" }

// Response 200
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": 1, "role": "OWNER", "full_name": "Konan Yao" }
}
```

### POST `/api/v1/auth/verify-email`
```json
// Request
{ "email": "owner@flotte225.ci", "code": "847291" }

// Response 200
{ "success": true, "message": "Email vérifié. Vous pouvez maintenant vous connecter." }
```

### POST `/api/v1/fuel-entries`
```json
// Request
{
  "vehicle_id": 3,
  "date": "2026-04-06",
  "odometer_km": 45820,
  "quantity_litres": 40.5,
  "amount_fcfa": 32400
}

// Response 201
{
  "id": 88,
  "distance_km": 320,
  "consumption_per_100km": 12.66,
  "created_at": "2026-04-06T10:30:00Z"
}
```

### POST `/api/v1/driver/activate`
```json
// Request
{ "vehicle_id": 3 }

// Response 200
{ "success": true, "driving_status": true, "active_vehicle_id": 3 }
```

### POST `/api/v1/export`
```json
// Request
{
  "dataset": "fuel_entries",
  "format": "pdf",
  "date_from": "2026-01-01",
  "date_to": "2026-04-06"
}

// Response 200
{
  "file_url": "/downloads/export_2026-04-06_fuel.pdf",
  "expires_at": "2026-04-06T11:30:00Z"
}
```

## OpenAPI / Swagger
- `/docs` (Swagger UI) — **dev + staging only**
- `/redoc` — **dev + staging only**
- Production: disabled via `SHOW_DOCS=false` environment variable

---
*38 endpoints across 12 domains | Completed: 2026-04-06*
