# Flotte225 — Project Context
*Last updated: 2026-04-06 — Sprint 1 scaffold complete. Auth endpoints + tests written. Ready to run.*
*Purpose: Read this file at the start of any new conversation to understand the full project state.*

---

## What This Project Is

**Flotte225** is a French-language vehicle fleet management SaaS for Côte d'Ivoire. Fleet owners track fuel consumption, maintenance compliance, and driver activity. Drivers log trips and fuel entries. Owners get AI-generated fleet reports and WhatsApp alerts.

---

## SDLC Phase: Development — Sprint 1 in progress

| Phase | Status |
|-------|--------|
| SRS | ✅ Complete — `docs/FULL-SRS.md` |
| Product Backlog | ✅ Complete — `docs/backlog/PRODUCT-BACKLOG.md` (46 stories, 8 sprints) |
| System Design | ✅ Complete — `docs/design/FULL-DESIGN.md` (7 sections) |
| Sprint 1 — Auth + Plan Infrastructure | 🔄 Scaffold built, not yet tested against DB |
| Sprint 2–8 | ⏳ Not started |

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | FastAPI (Python 3.11+) |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 + Alembic migrations |
| Auth | JWT HS256 (24h access token), bcrypt (10 rounds), OTP 6-digit (15 min) |
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

## Project Structure

```
FlotteApp/
├── backend/
│   ├── app/
│   │   ├── main.py                    ← FastAPI app + CORS middleware
│   │   ├── api/v1/
│   │   │   ├── router.py              ← mounts all endpoint routers
│   │   │   └── endpoints/
│   │   │       └── auth.py            ← /register /verify-email /login /forgot-password /reset-password
│   │   ├── core/
│   │   │   ├── config.py              ← pydantic-settings, reads .env
│   │   │   ├── database.py            ← SQLAlchemy engine + get_db()
│   │   │   ├── security.py            ← bcrypt hash/verify + JWT create/decode
│   │   │   └── deps.py                ← get_current_user/owner/driver/admin + require_plan()
│   │   ├── models/
│   │   │   ├── user.py                ← User (OWNER/DRIVER/SUPER_ADMIN)
│   │   │   ├── otp_code.py            ← OTP codes (EMAIL_VERIFY / PASSWORD_RESET)
│   │   │   ├── subscription.py        ← SubscriptionPlan + OwnerSubscription
│   │   │   └── vehicle.py             ← Vehicle placeholder (FK needed by User)
│   │   ├── schemas/
│   │   │   └── auth.py                ← RegisterRequest, LoginRequest, TokenResponse, etc.
│   │   └── services/
│   │       ├── auth_service.py        ← register, verify_email, login, forgot/reset password
│   │       └── email_service.py       ← SendGrid wrapper (non-blocking)
│   ├── scripts/
│   │   └── seed.py                    ← seeds 3 plans + SUPER_ADMIN (run once after migration)
│   ├── tests/
│   │   ├── conftest.py                ← PostgreSQL test DB + rollback-per-test fixture
│   │   └── test_auth.py               ← 12 tests: US-001 → US-004
│   ├── alembic/                       ← migrations (run autogenerate after models stabilize)
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/js/                       ← Vanilla JS (Sprint 4+)
├── docs/
│   ├── FULL-SRS.md
│   ├── backlog/PRODUCT-BACKLOG.md
│   └── design/FULL-DESIGN.md
├── .github/workflows/ci.yml           ← GitHub Actions: Ruff + Black + pytest
├── docker-compose.yml                 ← dev
├── docker-compose.prod.yml            ← production (extends base)
├── .env.example
└── .gitignore
```

---

## Database Schema (Sprint 1 tables)

| Table | Key Columns |
|-------|-------------|
| `users` | id, email, password_hash, role, full_name, phone, whatsapp_number, is_verified, is_active, driving_status, active_vehicle_id (FK), owner_id (FK self) |
| `otp_codes` | id, user_id (FK), code, purpose (EMAIL_VERIFY/PASSWORD_RESET), expires_at, used_at |
| `subscription_plans` | id, name, max_vehicles, max_drivers, price_fcfa, ai_reports_per_month, has_whatsapp, has_export, has_webhook |
| `owner_subscriptions` | id, owner_id (FK unique), plan_id (FK), started_at, expires_at, is_active, assigned_by |
| `vehicles` | id, owner_id, plate_number, brand, model, year, fuel_type, status, archived_at *(placeholder — Sprint 2)* |

Full schema (all 11 tables) in `docs/design/02-database-design.md`.

---

## API Endpoints Built

| Method | Endpoint | Story | Status |
|--------|----------|-------|--------|
| POST | `/api/v1/auth/register` | US-001 | ✅ Built |
| POST | `/api/v1/auth/verify-email` | US-002 | ✅ Built |
| POST | `/api/v1/auth/login` | US-003 | ✅ Built |
| POST | `/api/v1/auth/forgot-password` | US-004 | ✅ Built |
| POST | `/api/v1/auth/reset-password` | US-004 | ✅ Built |
| GET | `/health` | — | ✅ Built |

All other endpoints from `docs/design/03-api-design.md` are not yet built.

---

## Sprint 1 — Auth + Plan Infrastructure (in progress)

| Story | Description | Status |
|-------|-------------|--------|
| US-001 | User registration (OWNER, bcrypt, Pydantic) | ✅ Code written |
| US-002 | Email verification via OTP (SendGrid) | ✅ Code written |
| US-003 | Login + role-based JWT | ✅ Code written |
| US-004 | Password reset via OTP | ✅ Code written |
| US-042 | Super admin seed script | ✅ `scripts/seed.py` |
| US-043 | Auto-assign Starter plan on registration | ✅ In auth_service.register() |
| US-044 | require_plan() dependency at API level | ✅ In core/deps.py |

**Next steps to activate:**
```bash
cp .env.example .env                  # fill in SECRET_KEY
docker-compose up --build
docker-compose exec backend alembic revision --autogenerate -m "initial schema"
docker-compose exec backend alembic upgrade head
docker-compose exec backend python scripts/seed.py
# Swagger: http://localhost:8000/docs
```

**Tests:** 12 tests written in `tests/test_auth.py` — not yet run against DB.

---

## Sprint Plan Overview

| Sprint | Stories | Goal |
|--------|---------|------|
| Sprint 1 | US-001–004, 042–044 | Auth + plan infrastructure |
| Sprint 2 | US-005–009 | Vehicle management |
| Sprint 3 | US-010–014 | Driver management |
| Sprint 4 | US-015–021 | Fuel entries + owner dashboard |
| Sprint 5 | US-022–026 | Maintenance + alerts |
| Sprint 6 | US-027–031, 034–037 | Driver dashboard + activity log + export |
| Sprint 7 | US-038–041, 045–046 | Super admin + WhatsApp |
| Sprint 8 | US-032–033, 029–030 | AI reports + webhook |

Full plan in `docs/backlog/02-sprint-plan.md`.

---

## Key Design Decisions

- **Owner isolation:** every query on owner-scoped data filters by `owner_id = current_user.id` at service layer (not just JWT)
- **Vehicle archiving:** soft delete only — `status = "archived"` + `archived_at` timestamp, data preserved
- **Oil change alert:** by km — warning at 400 km, critical at 500 km since last oil change (computed from `fuel_entries.odometer_km`)
- **Multi-role owner:** an OWNER can also drive — `driving_status` + `active_vehicle_id` on `users` table regardless of role
- **OTP:** single-use, previous OTPs invalidated on new request, enumeration-safe (forgot-password always returns 200)
- **Plan enforcement:** `require_plan("pro")` / `require_plan("business")` FastAPI dependencies — enforced server-side
- **Payment:** no gateway — SUPER_ADMIN manually assigns plans via `PUT /api/v1/admin/users/{id}/subscription`
- **WhatsApp:** Meta Cloud API, silent skip if `WHATSAPP_TOKEN` not set or owner has no `whatsapp_number`
- **AI reports:** OpenRouter, French system prompt, 90s timeout, Pro plan counter `ai_reports_used_month` resets monthly via APScheduler
- **Branching:** feature/US-XXX → staging → main (3-tier, feature per story)

---

## Important Notes

- `python-jose` used for JWT (not PyJWT) — see `app/core/security.py`
- `passlib[bcrypt]` used for password hashing — rounds=10
- SendGrid failures are non-blocking (logged, don't fail the parent request)
- Frontend is static HTML + Vanilla JS (no Jinja2, no build step) — served by Nginx in production
- `SUPER_ADMIN` seed credentials come from `.env` (`SUPER_ADMIN_EMAIL`, `SUPER_ADMIN_PASSWORD`)
- Swagger/ReDoc enabled in dev + staging only (`SHOW_DOCS=false` in production)
