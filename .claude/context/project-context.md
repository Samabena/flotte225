# Flotte225 — Project Context
*Last updated: 2026-04-09 — Sprint 1 ✅ complete (18 tests). Sprint 2 ✅ complete (46 tests). Sprint 3 ✅ complete (67 tests). Sprint 4 ✅ complete (88 tests). Git repo initialized and pushed to GitHub.*
*Purpose: Read this file at the start of any new conversation to understand the full project state.*

---

## What This Project Is

**Flotte225** is a French-language vehicle fleet management SaaS for Côte d'Ivoire. Fleet owners track fuel consumption, maintenance compliance, and driver activity. Drivers log trips and fuel entries. Owners get AI-generated fleet reports and WhatsApp alerts.

---

## SDLC Phase: Development — Sprint 4 complete, Sprint 5 next

| Phase | Status |
|-------|--------|
| SRS | ✅ Complete — `docs/FULL-SRS.md` |
| Product Backlog | ✅ Complete — `docs/backlog/PRODUCT-BACKLOG.md` (46 stories, 8 sprints) |
| System Design | ✅ Complete — `docs/design/FULL-DESIGN.md` (7 sections) |
| Sprint 1 — Auth + Plan Infrastructure | ✅ Complete — 18 tests passing |
| Sprint 2 — Vehicle Management | ✅ Complete — 46 tests passing (28 new) |
| Sprint 3 — Fuel Entry & Audit Log | ✅ Complete — 67 tests passing (21 new) |
| Sprint 4 — Maintenance & Alert Engine | ✅ Complete — 88 tests passing (21 new) |
| Sprint 5–8 | ⬜ Not started |

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
| `develop` | Integration branch — all built code, Sprint 1 + Sprint 2 |
| `sprint/1-auth-foundation` | Sprint 1 tip commit |
| `sprint/2-vehicle-management` | Sprint 2 tip (= develop HEAD) |

**Convention going forward:** branch from `develop` as `sprint/N-description`, merge back to `develop` when sprint is complete.

---

## Project Structure

```
FlotteApp/
├── backend/
│   ├── app/
│   │   ├── main.py                    ← FastAPI app + CORS middleware
│   │   ├── api/v1/
│   │   │   ├── router.py              ← mounts auth, vehicles, driver routers
│   │   │   └── endpoints/
│   │   │       ├── auth.py            ← /register /verify-email /login /forgot-password /reset-password
│   │   │       ├── vehicles.py        ← /vehicles (CRUD + pause/resume/archive/restore + driver assignment)
│   │   │       └── driver.py          ← /driver/vehicles /driver/activate /driver/deactivate
│   │   ├── core/
│   │   │   ├── config.py              ← pydantic-settings, reads .env
│   │   │   ├── database.py            ← SQLAlchemy engine + get_db()
│   │   │   ├── security.py            ← bcrypt hash/verify + JWT create/decode
│   │   │   └── deps.py                ← get_current_user/owner/driver/admin + require_plan()
│   │   ├── models/
│   │   │   ├── user.py                ← User (OWNER/DRIVER/SUPER_ADMIN)
│   │   │   ├── otp_code.py            ← OTP codes (EMAIL_VERIFY / PASSWORD_RESET)
│   │   │   ├── subscription.py        ← SubscriptionPlan + OwnerSubscription
│   │   │   ├── vehicle.py             ← Vehicle (name, brand, model, license_plate, fuel_type, initial_mileage, status)
│   │   │   └── vehicle_driver.py      ← VehicleDriver junction table (vehicle_id, driver_id)
│   │   ├── schemas/
│   │   │   ├── auth.py                ← RegisterRequest (role field added), LoginRequest, TokenResponse, etc.
│   │   │   └── vehicle.py             ← VehicleCreate, VehicleUpdate, VehicleResponse, DriverSummary, ActivateRequest
│   │   └── services/
│   │       ├── auth_service.py        ← register (role param), verify_email, login, forgot/reset password
│   │       ├── email_service.py       ← SendGrid wrapper (non-blocking)
│   │       └── vehicle_service.py     ← create/update/pause/resume/archive/restore + driver assign/remove + activate/deactivate
│   ├── scripts/
│   │   └── seed.py                    ← seeds 3 plans + SUPER_ADMIN (run once after migration)
│   ├── tests/
│   │   ├── conftest.py                ← PostgreSQL test DB + rollback-per-test fixture (TEST_DATABASE_URL from env)
│   │   ├── test_auth.py               ← 18 tests: US-001–004, US-042–044
│   │   └── test_vehicles.py           ← 28 tests: US-005–009, US-022–023
│   ├── alembic/
│   │   └── versions/
│   │       ├── 001_initial_schema.py  ← users, otp_codes, subscription_plans, owner_subscriptions, vehicles
│   │       └── 002_vehicle_management.py ← adds name/vin/initial_mileage to vehicles, renames plate_number→license_plate, creates vehicle_drivers
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/js/                       ← Vanilla JS (Sprint 4+)
├── docs/
│   ├── FULL-SRS.md
│   ├── backlog/PRODUCT-BACKLOG.md
│   └── design/FULL-DESIGN.md
├── .github/workflows/ci.yml           ← GitHub Actions: Ruff + pytest on push
├── docker-compose.yml                 ← dev
├── docker-compose.prod.yml            ← production
├── .env                               ← local dev (gitignored)
├── .env.example
└── .gitignore
```

---

## Database Schema (Sprints 1–2)

| Table | Key Columns |
|-------|-------------|
| `users` | id, email, password_hash, role, full_name, phone, whatsapp_number, is_verified, is_active, driving_status, active_vehicle_id (FK use_alter), owner_id (FK self) |
| `otp_codes` | id, user_id (FK), code, purpose (EMAIL_VERIFY/PASSWORD_RESET), expires_at, used_at |
| `subscription_plans` | id, name, max_vehicles, max_drivers, price_fcfa, ai_reports_per_month, has_whatsapp, has_export, has_webhook |
| `owner_subscriptions` | id, owner_id (FK unique), plan_id (FK), started_at, expires_at, is_active, assigned_by |
| `vehicles` | id, owner_id (FK), name, brand, model, year, license_plate (unique), vin, fuel_type, initial_mileage, status (active/paused/archived), archived_at |
| `vehicle_drivers` | id, vehicle_id (FK), driver_id (FK), assigned_at — UNIQUE(vehicle_id, driver_id) |

Remaining tables (fuel_entries, maintenance, activity_logs, webhook_state, report_schedules) in `docs/design/02-database-design.md`.

---

## API Endpoints Built

### Auth (`/api/v1/auth`)
| Method | Endpoint | Story | Status |
|--------|----------|-------|--------|
| POST | `/api/v1/auth/register` | US-001 | ✅ |
| POST | `/api/v1/auth/verify-email` | US-002 | ✅ |
| POST | `/api/v1/auth/login` | US-003 | ✅ |
| POST | `/api/v1/auth/forgot-password` | US-004 | ✅ |
| POST | `/api/v1/auth/reset-password` | US-004 | ✅ |

### Vehicles (`/api/v1/vehicles`)
| Method | Endpoint | Story | Status |
|--------|----------|-------|--------|
| GET | `/api/v1/vehicles` | US-005 | ✅ |
| POST | `/api/v1/vehicles` | US-005 | ✅ |
| GET | `/api/v1/vehicles/archived` | US-008 | ✅ |
| GET | `/api/v1/vehicles/{id}` | US-005 | ✅ |
| PATCH | `/api/v1/vehicles/{id}` | US-006 | ✅ |
| POST | `/api/v1/vehicles/{id}/pause` | US-007 | ✅ |
| POST | `/api/v1/vehicles/{id}/resume` | US-007 | ✅ |
| POST | `/api/v1/vehicles/{id}/archive` | US-008 | ✅ |
| POST | `/api/v1/vehicles/{id}/restore` | US-008 | ✅ |
| GET | `/api/v1/vehicles/{id}/drivers` | US-009 | ✅ |
| POST | `/api/v1/vehicles/{id}/drivers` | US-009 | ✅ |
| DELETE | `/api/v1/vehicles/{id}/drivers/{driver_id}` | US-009 | ✅ |

### Driver (`/api/v1/driver`)
| Method | Endpoint | Story | Status |
|--------|----------|-------|--------|
| GET | `/api/v1/driver/vehicles` | US-022 | ✅ |
| POST | `/api/v1/driver/activate` | US-023 | ✅ |
| POST | `/api/v1/driver/deactivate` | US-023 | ✅ |

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

**Result: 46 passed, 2 warnings, 0 errors**

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

## Key Design Decisions

- **Owner isolation:** every query on owner-scoped data filters by `owner_id = current_user.id` at service layer (not just JWT)
- **Vehicle archiving:** soft delete only — `status = "archived"` + `archived_at` timestamp, data preserved; `status` also supports `"paused"` for temporarily unavailable vehicles
- **Oil change alert:** by km — warning at 400 km, critical at 500 km since last oil change (computed from `fuel_entries.odometer_km`)
- **OTP:** single-use, previous OTPs invalidated on new request, enumeration-safe (forgot-password always returns 200)
- **Plan enforcement:** `require_plan("pro")` FastAPI dep + explicit vehicle-count check in `vehicle_service._check_plan_vehicle_limit()` before creation/restore
- **Vehicle limit on restore:** restoring an archived vehicle also checks the plan limit (counts active+paused, not archived)
- **Driver assignment:** any DRIVER-role user can be assigned to any owner's vehicle — no hard owner→driver ownership link
- **Archive resets driver:** archiving a vehicle automatically sets `driving_status=False` and `active_vehicle_id=None` for any active driver on that vehicle; same on driver removal
- **Payment:** no gateway — SUPER_ADMIN manually assigns plans
- **WhatsApp:** Meta Cloud API, silent skip if `WHATSAPP_TOKEN` not set
- **AI reports:** OpenRouter, French system prompt, Pro plan counter resets monthly via APScheduler
- **bcrypt pinned to 3.2.2** — passlib 1.7.4 is incompatible with bcrypt ≥ 4.x (`__about__` removed)
- **use_alter FK named:** `users.active_vehicle_id` FK has `name="fk_users_active_vehicle_id"` to allow SQLAlchemy `drop_all` to work; test conftest uses raw CASCADE DROP to avoid teardown issues
- **TEST_DATABASE_URL** is read from env (default `localhost:5432`) — pass `db:5432` when running tests inside Docker

---

## Important Notes

- `python-jose` used for JWT (not PyJWT) — see `app/core/security.py`
- `passlib[bcrypt]==1.7.4` + `bcrypt==3.2.2` — do not upgrade bcrypt without testing
- SendGrid failures are non-blocking (logged, don't fail the parent request)
- Frontend is static HTML + Vanilla JS — served by Nginx in production
- `SUPER_ADMIN` seed credentials come from `.env` (`SUPER_ADMIN_EMAIL`, `SUPER_ADMIN_PASSWORD`)
- Swagger/ReDoc enabled in dev + staging only (`SHOW_DOCS=false` in production)
- `docker-compose.yml` has obsolete `version:` attribute — harmless warning, leave as-is
