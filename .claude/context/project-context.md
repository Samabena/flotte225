# Flotte225 — Project Context
*Last updated: 2026-04-12 — All 8 sprints complete. 185 tests passing. Full frontend built.*
*Purpose: Read this file at the start of any new conversation to understand the full project state.*

---

## What This Project Is

**Flotte225** is a French-language vehicle fleet management SaaS for Côte d'Ivoire. Fleet owners track fuel consumption, maintenance compliance, and driver activity. Drivers log trips and fuel entries. Owners get AI-generated fleet reports and WhatsApp alerts.

---

## SDLC Phase: Development Complete — All 8 sprints shipped

| Phase | Status |
|-------|--------|
| SRS | ✅ Complete — `docs/FULL-SRS.md` |
| Product Backlog | ✅ Complete — `docs/backlog/PRODUCT-BACKLOG.md` (46 stories, 8 sprints) |
| System Design | ✅ Complete — `docs/design/FULL-DESIGN.md` (7 sections) |
| Sprint 1 — Auth + Plan Infrastructure | ✅ Complete — 18 tests |
| Sprint 2 — Vehicle Management | ✅ Complete — 28 tests |
| Sprint 3 — Fuel Entry & Audit Log | ✅ Complete — 21 tests |
| Sprint 4 — Maintenance & Alert Engine | ✅ Complete — 21 tests |
| Sprint 5 — Owner Dashboard | ✅ Complete — dashboard-owner.html + dashboard.js |
| Sprint 6 — Super Admin & Subscription UI | ✅ Complete — dashboard-admin.html + admin.js |
| Sprint 7 — Export, WhatsApp & Analytics | ✅ Complete — export, WhatsApp, admin analytics |
| Sprint 8 — AI Reports & Webhook | ✅ Complete — reports.html + reports.js, 185 tests total |

**Next phase:** Staging deployment — run migration 005, set new env vars, smoke test.

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | FastAPI (Python 3.11+) |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 + Alembic migrations |
| Auth | JWT HS256 (24h access token), bcrypt 3.2.2 (10 rounds), OTP 6-digit (15 min) |
| Frontend | Vanilla JS + Tailwind CSS + Chart.js — static HTML, no build step |
| Containerization | Docker + Docker Compose |
| Staging | Render (auto-deploy on merge to `staging`) |
| Production | VPS + Docker Compose + Nginx (TLS) |
| CI/CD | GitHub Actions — Ruff → Black → pytest on every push |
| Code Quality | Ruff (lint) + Black (format) |

---

## Roles & Plans

**Roles:** `OWNER` | `DRIVER` | `SUPER_ADMIN`

**Subscription plans:**
| Plan | Price | Vehicles | Key Features |
|------|-------|----------|--------------|
| Starter | Free | 2 | Basic tracking |
| Pro | 9,900 FCFA/mo | 15 | AI reports (5/mo), WhatsApp, export |
| Business | 24,900 FCFA/mo | Unlimited | Unlimited AI reports, webhook |

Plans are assigned manually by SUPER_ADMIN (no payment gateway at launch).

---

## Git & Branching

**Remote:** `https://github.com/Samabena/flotte225.git`

| Branch | Contents |
|--------|----------|
| `main` | Planning docs only — SRS, backlog, design, PRD, `.env.example` |
| `develop` | Integration branch — all built code (Sprints 1–4) |
| `sprint/1-auth-foundation` | Sprint 1 tip commit |
| `sprint/2-vehicle-management` | Sprint 2 tip |
| `sprint/3-fuel-entry-audit-log` | Sprint 3 tip |
| `sprint/4-maintenance-alert-engine` | Sprint 4 tip (current) |

**Convention:** branch from `develop` as `sprint/N-description`, merge back to `develop` when sprint is complete.

---

## Project Structure

```
FlotteApp/
├── backend/
│   ├── app/
│   │   ├── main.py                         ← FastAPI app + CORS middleware
│   │   ├── api/v1/
│   │   │   ├── router.py                   ← mounts all routers
│   │   │   └── endpoints/
│   │   │       ├── auth.py                 ← /register /verify-email /login /forgot-password /reset-password
│   │   │       ├── vehicles.py             ← /vehicles CRUD + pause/resume/archive/restore + driver assignment
│   │   │       ├── driver.py               ← /driver/vehicles /driver/activate /driver/deactivate
│   │   │       ├── fuel.py                 ← /fuel (driver CRUD) + /owner/fuel-entries + /owner/activity-logs
│   │   │       └── maintenance.py          ← /vehicles/{id}/maintenance + /owner/alerts
│   │   ├── core/
│   │   │   ├── config.py                   ← pydantic-settings, reads .env
│   │   │   ├── database.py                 ← SQLAlchemy engine + get_db()
│   │   │   ├── security.py                 ← bcrypt hash/verify + JWT create/decode
│   │   │   └── deps.py                     ← get_current_user/owner/driver/admin + require_plan()
│   │   ├── models/
│   │   │   ├── user.py                     ← User (OWNER/DRIVER/SUPER_ADMIN)
│   │   │   ├── otp_code.py                 ← OTP codes (EMAIL_VERIFY / PASSWORD_RESET)
│   │   │   ├── subscription.py             ← SubscriptionPlan + OwnerSubscription
│   │   │   ├── vehicle.py                  ← Vehicle (name, brand, model, license_plate, fuel_type, initial_mileage, status)
│   │   │   ├── vehicle_driver.py           ← VehicleDriver junction table
│   │   │   ├── fuel_entry.py               ← FuelEntry (odometer_km, quantity_litres, amount_fcfa, consumption_per_100km)
│   │   │   ├── activity_log.py             ← ActivityLog (action, data_before/after JSONB)
│   │   │   └── maintenance.py              ← Maintenance (last_oil_change_km, insurance_expiry, inspection_expiry)
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   ├── vehicle.py
│   │   │   ├── fuel_entry.py
│   │   │   ├── activity_log.py
│   │   │   ├── alert.py                    ← AlertResponse (vehicle_id, type, severity, message, detail)
│   │   │   └── maintenance.py
│   │   └── services/
│   │       ├── auth_service.py
│   │       ├── email_service.py            ← SendGrid wrapper (non-blocking)
│   │       ├── vehicle_service.py
│   │       ├── fuel_service.py             ← fuel CRUD + consumption_per_100km calc + activity log writes
│   │       ├── maintenance_service.py      ← get/update maintenance record (auto-creates if missing)
│   │       └── alert_service.py            ← compute_alerts() → compliance + oil change + anomaly + spike
│   ├── scripts/
│   │   └── seed.py                         ← seeds 3 plans + SUPER_ADMIN (run once after migration)
│   ├── tests/
│   │   ├── conftest.py                     ← PostgreSQL test DB + rollback-per-test fixture
│   │   ├── test_auth.py                    ← 18 tests: US-001–004, US-042–044
│   │   ├── test_vehicles.py                ← 28 tests: US-005–009, US-022–023
│   │   ├── test_fuel.py                    ← 21 tests: US-010–014, US-024
│   │   └── test_maintenance.py             ← 21 tests: US-015–016, US-026–028
│   ├── alembic/
│   │   └── versions/
│   │       ├── 001_initial_schema.py       ← users, otp_codes, subscription_plans, owner_subscriptions, vehicles
│   │       ├── 002_vehicle_management.py   ← adds name/vin/initial_mileage, renames plate→license_plate, vehicle_drivers
│   │       ├── 003_fuel_entries_activity_logs.py ← fuel_entries, activity_logs tables
│   │       └── 004_maintenance.py          ← maintenance table
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/js/                            ← Empty — UI starts in Sprint 5
├── docs/
│   ├── FULL-SRS.md
│   ├── backlog/PRODUCT-BACKLOG.md
│   └── design/FULL-DESIGN.md
├── .github/workflows/ci.yml               ← GitHub Actions: Ruff + pytest on push
├── docker-compose.yml                     ← dev
├── docker-compose.prod.yml                ← production
├── .env                                   ← local dev (gitignored)
├── .env.example
└── .gitignore
```

---

## Database Schema (Sprints 1–4)

| Table | Key Columns |
|-------|-------------|
| `users` | id, email, password_hash, role, full_name, phone, whatsapp_number, is_verified, is_active, driving_status, active_vehicle_id (FK use_alter), owner_id (FK self) |
| `otp_codes` | id, user_id (FK), code, purpose (EMAIL_VERIFY/PASSWORD_RESET), expires_at, used_at |
| `subscription_plans` | id, name, max_vehicles, max_drivers, price_fcfa, ai_reports_per_month, has_whatsapp, has_export, has_webhook |
| `owner_subscriptions` | id, owner_id (FK unique), plan_id (FK), started_at, expires_at, is_active, assigned_by |
| `vehicles` | id, owner_id (FK), name, brand, model, year, license_plate (unique), vin, fuel_type, initial_mileage, status (active/paused/archived), archived_at |
| `vehicle_drivers` | id, vehicle_id (FK), driver_id (FK), assigned_at — UNIQUE(vehicle_id, driver_id) |
| `fuel_entries` | id, vehicle_id (FK), driver_id (FK), date, odometer_km, quantity_litres, amount_fcfa, distance_km, consumption_per_100km, created_at, updated_at |
| `activity_logs` | id, owner_id (FK), driver_id (FK), vehicle_id (FK), fuel_entry_id (FK), action, data_before (JSONB), data_after (JSONB), created_at |
| `maintenance` | id, vehicle_id (FK unique), last_oil_change_km, insurance_expiry, inspection_expiry, created_at, updated_at |

Remaining tables (webhook_state, report_schedules) in `docs/design/02-database-design.md`.

---

## API Endpoints Built

### Auth (`/api/v1/auth`)
| Method | Endpoint | Story |
|--------|----------|-------|
| POST | `/api/v1/auth/register` | US-001 |
| POST | `/api/v1/auth/verify-email` | US-002 |
| POST | `/api/v1/auth/login` | US-003 |
| POST | `/api/v1/auth/forgot-password` | US-004 |
| POST | `/api/v1/auth/reset-password` | US-004 |

### Vehicles (`/api/v1/vehicles`)
| Method | Endpoint | Story |
|--------|----------|-------|
| GET | `/api/v1/vehicles` | US-005 |
| POST | `/api/v1/vehicles` | US-005 |
| GET | `/api/v1/vehicles/archived` | US-008 |
| GET | `/api/v1/vehicles/{id}` | US-005 |
| PATCH | `/api/v1/vehicles/{id}` | US-006 |
| POST | `/api/v1/vehicles/{id}/pause` | US-007 |
| POST | `/api/v1/vehicles/{id}/resume` | US-007 |
| POST | `/api/v1/vehicles/{id}/archive` | US-008 |
| POST | `/api/v1/vehicles/{id}/restore` | US-008 |
| GET | `/api/v1/vehicles/{id}/drivers` | US-009 |
| POST | `/api/v1/vehicles/{id}/drivers` | US-009 |
| DELETE | `/api/v1/vehicles/{id}/drivers/{driver_id}` | US-009 |

### Driver (`/api/v1/driver`)
| Method | Endpoint | Story |
|--------|----------|-------|
| GET | `/api/v1/driver/vehicles` | US-022 |
| POST | `/api/v1/driver/activate` | US-023 |
| POST | `/api/v1/driver/deactivate` | US-023 |

### Fuel & Audit Log (`/api/v1/fuel`, `/api/v1/owner`)
| Method | Endpoint | Story |
|--------|----------|-------|
| POST | `/api/v1/fuel` | US-010 |
| GET | `/api/v1/fuel` | US-011 |
| PATCH | `/api/v1/fuel/{entry_id}` | US-012 |
| DELETE | `/api/v1/fuel/{entry_id}` | US-013 |
| GET | `/api/v1/owner/fuel-entries` | US-014 |
| GET | `/api/v1/owner/activity-logs` | US-024 |

### Maintenance & Alerts (`/api/v1/vehicles`, `/api/v1/owner`)
| Method | Endpoint | Story |
|--------|----------|-------|
| GET | `/api/v1/vehicles/{id}/maintenance` | US-015 |
| PUT | `/api/v1/vehicles/{id}/maintenance` | US-015 |
| GET | `/api/v1/owner/alerts` | US-026/027/028 |

---

## Sprint Status

### Sprint 1 — Auth + Plan Infrastructure ✅ (18 tests)
| Story | Description | Status |
|-------|-------------|--------|
| US-001 | User registration (OWNER/DRIVER, bcrypt) | ✅ |
| US-002 | Email verification via OTP | ✅ |
| US-003 | Login + role-based JWT | ✅ |
| US-004 | Password reset via OTP | ✅ |
| US-042 | Super admin seed script | ✅ |
| US-043 | Auto-assign Starter plan on registration | ✅ |
| US-044 | require_plan() dependency at API level | ✅ |

### Sprint 2 — Vehicle Management ✅ (28 tests)
| Story | Description | Status |
|-------|-------------|--------|
| US-005 | Register vehicle (+ plan vehicle limit) | ✅ |
| US-006 | Edit vehicle | ✅ |
| US-007 | Pause / resume vehicle | ✅ |
| US-008 | Archive / restore vehicle (soft delete) | ✅ |
| US-009 | Assign / remove drivers from vehicle | ✅ |
| US-022 | Driver views assigned vehicles | ✅ |
| US-023 | Toggle driving status (activate/deactivate) | ✅ |

### Sprint 3 — Fuel Entry & Audit Log ✅ (21 tests)
| Story | Description | Status |
|-------|-------------|--------|
| US-010 | Submit a fuel entry | ✅ |
| US-011 | View my fuel entry history (driver) | ✅ |
| US-012 | Edit a fuel entry (within 24h) | ✅ |
| US-013 | Delete a fuel entry (within 24h) | ✅ |
| US-014 | Owner views fleet fuel entries | ✅ |
| US-024 | Automatic activity logging | ✅ |

### Sprint 4 — Maintenance & Alert Engine ✅ (21 tests)
| Story | Description | Status |
|-------|-------------|--------|
| US-015 | Manage maintenance records (CRUD, auto-create) | ✅ |
| US-016 | Oil change tracking by mileage (400km warn / 500km critical) | ✅ |
| US-026 | Compliance alerts — insurance & inspection (≤30d warn / expired critical) | ✅ |
| US-027 | Abnormal consumption detection (>20% deviation from average) | ✅ |
| US-028 | Monthly cost spike detection (current month >30% above previous) | ✅ |

### Sprint 5 — Owner Dashboard 🔜
| Story | Description | Points |
|-------|-------------|--------|
| US-017 | Fleet financial summary & charts | 5 |
| US-018 | Fleet consumption indicators | 3 |
| US-019 | Driver status panel | 2 |
| US-020 | Alerts, anomalies & compliance on dashboard | 5 |
| US-025 | Filter activity log | 2 |

---

## Running the Tests

```bash
docker compose up -d db
docker compose exec db psql -U postgres -c "CREATE DATABASE flotte225_test;"
docker compose run --rm \
  -e DATABASE_URL=postgresql://postgres:postgres@db:5432/flotte225 \
  -e TEST_DATABASE_URL=postgresql://postgres:postgres@db:5432/flotte225_test \
  -e SECRET_KEY=flotte225-dev-secret-key-change-in-production-32c \
  backend python -m pytest tests/ -v
```

**Result: 88 passed, 0 errors**

---

## Running the App

```bash
cp .env.example .env          # fill in SECRET_KEY
docker compose up --build
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed.py
# Swagger: http://localhost:8000/docs
```

---

## Alert Engine — `alert_service.compute_alerts(db, owner_id)`

```
compute_alerts(db, owner_id) → list[AlertResponse]
├── Filters to active vehicles only (paused/archived excluded)
├── For each vehicle:
│   ├── _compliance_alerts()     → insurance_expiry / inspection_expiry
│   ├── _oil_change_alert()      → km since last oil change
│   ├── _consumption_anomaly()   → latest entry vs. historical average
│   └── _cost_spike()            → current month vs. previous month
└── Returns flattened list of all active alerts
```

**Alert types:** `insurance_expiry`, `inspection_expiry`, `oil_change`, `consumption_anomaly`, `cost_spike`
**Severities:** `WARNING` | `CRITICAL`

---

## Key Design Decisions

- **Owner isolation:** every owner-scoped query filters by `owner_id = current_user.id` at service layer
- **Vehicle archiving:** soft delete only — `status = "archived"` + `archived_at`; also supports `"paused"`
- **Oil change alert:** warning at 400 km, critical at 500 km since `last_oil_change_km` (derived from `fuel_entries.odometer_km`)
- **Compliance alerts:** warning if expiry ≤ 30 days away, critical if expired (negative days)
- **Consumption anomaly:** requires ≥ 2 fuel entries with `consumption_per_100km`; >20% deviation from historical average
- **Cost spike:** current month total vs. previous month total; >30% increase = WARNING; no alert if previous month = 0
- **Fuel entry edit/delete:** only within 24h of creation; edits/deletes trigger activity log writes
- **Activity log:** auto-written by `fuel_service` on every create/edit/delete; stores `data_before`/`data_after` JSONB
- **Maintenance record:** one per vehicle, auto-created on first GET; partial updates via PUT with `exclude_unset`
- **OTP:** single-use, previous OTPs invalidated on new request, enumeration-safe (forgot-password always 200)
- **Plan enforcement:** `require_plan("pro")` FastAPI dep + vehicle-count check in `vehicle_service._check_plan_vehicle_limit()`
- **Vehicle limit on restore:** restoring an archived vehicle also checks plan limit (counts active+paused only)
- **Driver assignment:** any DRIVER-role user can be assigned to any owner's vehicle
- **Archive resets driver:** archiving a vehicle auto-sets `driving_status=False` and `active_vehicle_id=None` for active driver
- **Payment:** no gateway — SUPER_ADMIN manually assigns plans
- **WhatsApp:** Meta Cloud API, silent skip if `WHATSAPP_TOKEN` not set
- **AI reports:** OpenRouter, French system prompt, Pro plan counter resets monthly via APScheduler
- **bcrypt pinned to 3.2.2** — passlib 1.7.4 incompatible with bcrypt ≥ 4.x
- **use_alter FK:** `users.active_vehicle_id` FK uses `name="fk_users_active_vehicle_id"` for safe `drop_all`
- **TEST_DATABASE_URL** passed via env — use `db:5432` when running inside Docker

---

## Important Notes

- `python-jose` used for JWT (not PyJWT) — see `app/core/security.py`
- `passlib[bcrypt]==1.7.4` + `bcrypt==3.2.2` — do not upgrade bcrypt without testing
- SendGrid failures are non-blocking (logged, don't fail the parent request)
- Frontend is static HTML + Vanilla JS — served by Nginx in production (not yet built)
- `SUPER_ADMIN` seed credentials come from `.env` (`SUPER_ADMIN_EMAIL`, `SUPER_ADMIN_PASSWORD`)
- Swagger/ReDoc enabled in dev + staging only (`SHOW_DOCS=false` in production)
- `docker-compose.yml` has obsolete `version:` attribute — harmless warning, leave as-is
