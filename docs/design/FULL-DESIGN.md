# Flotte225 — System Design Document
*Design Phase | Generated: 2026-04-06 | Based on SRS + Backlog v2026-04-06*

---

# 1. System Architecture

## Component Overview

Flotte225 is a multi-tenant SaaS web application. The frontend is served as static HTML/JS/CSS files. The backend is a FastAPI REST API connected to PostgreSQL. Four external services are integrated: SMTP (email), OpenRouter (AI reports), WhatsApp Business API, and configurable webhook endpoints. An embedded APScheduler handles all timed tasks (webhook dispatch, scheduled AI reports).

## Component Diagram

```
[Client Browser — mobile/desktop]
         │ HTTPS
         ▼
  [Nginx Reverse Proxy]  ← production only
         │
         ├──► [Static Frontend files]  (HTML/JS/CSS/Tailwind/Chart.js)
         │
         └──► [FastAPI Backend (Python 3.11+)]
                    │                │
                    ▼                ▼
             [PostgreSQL 15]   [APScheduler]
             (named Docker          │
              volume)               ├──► [SMTP/SendGrid]     (OTP, AI reports, exports)
                                    ├──► [OpenRouter API]    (AI report generation)
                                    ├──► [WhatsApp Biz API]  (fleet alerts)
                                    └──► [Webhook Endpoint]  (external tools)
```

## Deployment

| Environment | Platform | Notes |
|---|---|---|
| Development | Local — Docker Compose | Hot reload, `.env` file, local PostgreSQL container |
| Staging | Render | Auto-deploy from `staging` branch, shared `.env` config |
| Production | VPS + Docker Compose | Nginx reverse proxy, named volumes, `.env.prod` |

## Repository Structure

**Monorepo** — one repository containing both frontend and backend. Chosen for simplicity as a solo developer — shared `docs/`, single `git` history, easier to keep API and frontend in sync.

## Recommended Folder Structure

```
flotte225/
├── backend/
│   ├── app/
│   │   ├── api/              # Route handlers (one file per domain)
│   │   │   ├── auth.py
│   │   │   ├── vehicles.py
│   │   │   ├── fuel.py
│   │   │   ├── maintenance.py
│   │   │   ├── activity.py
│   │   │   ├── alerts.py
│   │   │   ├── export.py
│   │   │   ├── reports.py
│   │   │   ├── webhook.py
│   │   │   ├── whatsapp.py
│   │   │   └── admin.py
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic (alert engine, plan checks, etc.)
│   │   ├── scheduler/        # APScheduler task definitions
│   │   └── core/
│   │       ├── config.py     # Environment variables & settings
│   │       ├── security.py   # JWT, bcrypt, OTP utilities
│   │       └── dependencies.py # FastAPI dependency injection (get_current_user, plan_check)
│   ├── alembic/              # Database migration files
│   ├── tests/
│   ├── main.py               # FastAPI app entry point
│   └── requirements.txt
├── frontend/
│   ├── index.html            # Login
│   ├── register.html
│   ├── dashboard-owner.html
│   ├── dashboard-driver.html
│   ├── vehicles.html
│   ├── fuel-entry.html
│   ├── maintenance.html
│   ├── activity.html
│   ├── reports.html
│   ├── export.html
│   ├── admin-dashboard.html
│   └── js/
│       ├── api.js            # Centralized API client (fetch wrapper + JWT inject)
│       ├── auth.js           # Login, logout, token management
│       ├── translations.js   # French i18n strings
│       └── charts.js         # Chart.js reusable configs
├── docs/
│   ├── FULL-SRS.md
│   ├── backlog/
│   └── design/
├── docker-compose.yml        # Dev & staging
├── docker-compose.prod.yml   # Production overrides (Nginx, volumes)
├── .env.example              # All required env vars documented
└── .gitignore
```

---

# 2. Database Design

## Multi-Tenancy Strategy
Owner-scoped row-level isolation. No `tenants` table — each OWNER acts as their own tenant. Every data table has an `owner_id` or `driver_id` column that scopes queries. SUPER_ADMIN bypasses these filters.

## Soft Deletes
Vehicles only — via `status` field (`active` / `paused` / `archived`) + `archived_at` timestamp. All other records use hard delete (with activity logs capturing the data snapshot before deletion).

## Primary Keys
SERIAL integers across all tables (consistent with existing SQLAlchemy codebase).

## Entity Relationship Overview

```
users ──────────────────────────────────────────────────────────┐
  │                                                              │
  ├──[owner]──► vehicles ──► vehicle_drivers ◄──[driver]── users│
  │                  │                                          │
  │                  ├──► fuel_entries ◄──[driver]──────── users│
  │                  ├──► maintenance                           │
  │                  └──► activity_logs                         │
  │                                                              │
  ├──[owner]──► webhook_state                                   │
  ├──[owner]──► owner_subscriptions ──► subscription_plans      │
  ├──[owner]──► report_schedules                                │
  └──[user]───► otp_codes                                       │
```

## Table Definitions

### `users`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| company_name | VARCHAR(255) | NOT NULL | |
| full_name | VARCHAR(255) | NOT NULL | |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Login identifier |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt |
| role | VARCHAR(20) | NOT NULL | `OWNER` / `DRIVER` / `SUPER_ADMIN` |
| is_active | BOOLEAN | NOT NULL, DEFAULT false | false until email verified |
| is_suspended | BOOLEAN | NOT NULL, DEFAULT false | Set by SUPER_ADMIN |
| driving_status | BOOLEAN | NOT NULL, DEFAULT false | DRIVER: currently on mission |
| active_vehicle_id | INT | FK → vehicles.id, NULLABLE | DRIVER: current vehicle |
| whatsapp_number | VARCHAR(20) | NULLABLE | OWNER: for WA notifications |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### `otp_codes`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| user_id | INT | FK → users.id, NOT NULL | |
| code | VARCHAR(6) | NOT NULL | 6-digit code |
| purpose | VARCHAR(20) | NOT NULL | `EMAIL_VERIFY` / `PASSWORD_RESET` |
| expires_at | TIMESTAMPTZ | NOT NULL | now() + 15 minutes |
| used_at | TIMESTAMPTZ | NULLABLE | Set on first use — then invalid |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### `vehicles`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| owner_id | INT | FK → users.id, NOT NULL | Data isolation key |
| name | VARCHAR(255) | NOT NULL | Free label |
| brand | VARCHAR(100) | NOT NULL | |
| model | VARCHAR(100) | NOT NULL | |
| year | INT | NULLABLE | |
| license_plate | VARCHAR(50) | UNIQUE, NOT NULL | |
| vin | VARCHAR(50) | NULLABLE | |
| fuel_type | VARCHAR(20) | NOT NULL | `Essence` / `Diesel` / `GPL` |
| initial_mileage | INT | NOT NULL | Starting odometer |
| status | VARCHAR(20) | NOT NULL, DEFAULT `active` | `active` / `paused` / `archived` |
| archived_at | TIMESTAMPTZ | NULLABLE | Soft delete timestamp |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### `vehicle_drivers`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| vehicle_id | INT | FK → vehicles.id, NOT NULL | |
| driver_id | INT | FK → users.id, NOT NULL | |
| assigned_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| | | UNIQUE(vehicle_id, driver_id) | No duplicate assignments |

### `fuel_entries`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| vehicle_id | INT | FK → vehicles.id, NOT NULL | |
| driver_id | INT | FK → users.id, NOT NULL | |
| date | DATE | NOT NULL | Date of refueling |
| odometer_km | INT | NOT NULL | Current reading |
| quantity_litres | DECIMAL(8,2) | NOT NULL | |
| amount_fcfa | DECIMAL(10,2) | NOT NULL | |
| distance_km | INT | NULLABLE | Computed: current − previous odometer |
| consumption_per_100km | DECIMAL(6,2) | NULLABLE | Computed: (litres ÷ distance) × 100 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 24h edit window starts here |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### `maintenance`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| vehicle_id | INT | FK → vehicles.id, UNIQUE, NOT NULL | One record per vehicle |
| last_oil_change_km | INT | NULLABLE | Odometer at last oil change |
| insurance_expiry | DATE | NULLABLE | |
| inspection_expiry | DATE | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### `activity_logs`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| owner_id | INT | FK → users.id, NOT NULL | Fleet owner (for filtering) |
| driver_id | INT | FK → users.id, NOT NULL | Who performed the action |
| vehicle_id | INT | FK → vehicles.id, NOT NULL | |
| fuel_entry_id | INT | FK → fuel_entries.id, NULLABLE | Null if entry was deleted |
| action | VARCHAR(20) | NOT NULL | `CREATE` / `UPDATE` / `DELETE` |
| data_before | JSONB | NULLABLE | Null for CREATE |
| data_after | JSONB | NULLABLE | Null for DELETE |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### `webhook_state`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| owner_id | INT | FK → users.id, UNIQUE, NOT NULL | One record per owner |
| last_sent_at | TIMESTAMPTZ | NULLABLE | |
| last_status_code | INT | NULLABLE | HTTP response code |
| last_payload_summary | JSONB | NULLABLE | Summary of last sent payload |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### `subscription_plans`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| name | VARCHAR(50) | UNIQUE, NOT NULL | `starter` / `pro` / `business` |
| display_name | VARCHAR(100) | NOT NULL | e.g. "Plan Pro" |
| price_fcfa | INT | NOT NULL, DEFAULT 0 | Monthly price |
| max_vehicles | INT | NULLABLE | null = unlimited |
| max_drivers | INT | NULLABLE | null = unlimited |
| max_ai_reports_month | INT | NULLABLE | null = unlimited, 0 = none |
| features | JSONB | NOT NULL | Feature flags map |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### `owner_subscriptions`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| owner_id | INT | FK → users.id, UNIQUE, NOT NULL | One plan per owner |
| plan_id | INT | FK → subscription_plans.id, NOT NULL | |
| feature_overrides | JSONB | NULLABLE | Per-owner overrides by SUPER_ADMIN |
| assigned_by | INT | FK → users.id, NULLABLE | SUPER_ADMIN who assigned |
| assigned_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### `report_schedules`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| owner_id | INT | FK → users.id, UNIQUE, NOT NULL | One config per owner |
| enabled | BOOLEAN | NOT NULL, DEFAULT false | |
| frequency | VARCHAR(20) | NULLABLE | `weekly` / `monthly` |
| last_sent_at | TIMESTAMPTZ | NULLABLE | |
| last_status | VARCHAR(20) | NULLABLE | `sent` / `failed` |
| ai_reports_used_month | INT | NOT NULL, DEFAULT 0 | Pro plan monthly counter |
| usage_reset_at | DATE | NULLABLE | Date counter was last reset |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

## Key Indexes

| Index | Columns | Reason |
|---|---|---|
| idx_users_email | `users(email)` | Login lookup |
| idx_vehicles_owner | `vehicles(owner_id, status)` | Owner dashboard queries |
| idx_vehicles_plate | `vehicles(license_plate)` | Duplicate plate check |
| idx_fuel_vehicle_date | `fuel_entries(vehicle_id, date DESC)` | Odometer validation + history |
| idx_fuel_driver | `fuel_entries(driver_id, created_at DESC)` | Driver history (last 10) |
| idx_activity_owner | `activity_logs(owner_id, created_at DESC)` | Audit log pagination |
| idx_activity_driver | `activity_logs(driver_id)` | Log filter by driver |
| idx_activity_vehicle | `activity_logs(vehicle_id)` | Log filter by vehicle |
| idx_vd_driver | `vehicle_drivers(driver_id)` | Driver's assigned vehicles |

---

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

## Endpoints by Domain

### Auth
| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Register new account (OWNER or DRIVER) | No |
| POST | `/api/v1/auth/verify-email` | Submit OTP to activate account | No |
| POST | `/api/v1/auth/login` | Login → returns JWT | No |
| POST | `/api/v1/auth/logout` | Clear client token (frontend) | Yes |
| GET | `/api/v1/auth/me` | Get current user profile + plan info | Yes |
| PATCH | `/api/v1/auth/me` | Update profile (name, company, WhatsApp number) | Yes |
| POST | `/api/v1/auth/forgot-password` | Request OTP for password reset | No |
| POST | `/api/v1/auth/reset-password` | Submit OTP + new password | No |

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

### Driver Status
| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/driver/vehicles` | List vehicles assigned to me | DRIVER |
| POST | `/api/v1/driver/activate` | Activate driving status + select vehicle | DRIVER |
| POST | `/api/v1/driver/deactivate` | Deactivate driving status | DRIVER |

### Fuel Entries
| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/api/v1/fuel-entries` | Submit a new fuel entry | DRIVER (active) |
| GET | `/api/v1/fuel-entries` | Owner: all fleet entries / Driver: last 10 | OWNER \| DRIVER |
| GET | `/api/v1/fuel-entries/{id}` | Get entry details | OWNER \| DRIVER |
| PATCH | `/api/v1/fuel-entries/{id}` | Edit own entry (within 24h) | DRIVER |
| DELETE | `/api/v1/fuel-entries/{id}` | Delete own entry (within 24h) | DRIVER |

### Maintenance
| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/vehicles/{id}/maintenance` | Get maintenance record (auto-creates if missing) | OWNER |
| PUT | `/api/v1/vehicles/{id}/maintenance` | Update maintenance record | OWNER |
| DELETE | `/api/v1/vehicles/{id}/maintenance` | Delete maintenance record | OWNER |

### Dashboard
| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/dashboard/owner` | Full owner analytics | OWNER |
| GET | `/api/v1/dashboard/owner/alerts` | Active maintenance + compliance alerts | OWNER |
| GET | `/api/v1/dashboard/owner/anomalies` | Vehicles with detected anomalies | OWNER |
| GET | `/api/v1/dashboard/driver` | Driver view | DRIVER |

### Activity Log
| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/activity-logs` | Paginated audit log (`?driver_id=&vehicle_id=`) | OWNER |

### Export *(Pro + Business)*
| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/api/v1/export` | Generate PDF or Excel export | OWNER |

### AI Reports *(Pro + Business)*
| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/api/v1/reports/generate` | Trigger on-demand AI report | OWNER |
| GET | `/api/v1/reports/schedule` | Get report schedule config | OWNER |
| PUT | `/api/v1/reports/schedule` | Enable/disable schedule + set frequency | OWNER |

### Webhook
| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/webhook/status` | Last dispatch timestamp + HTTP status | OWNER |
| POST | `/api/v1/webhook/trigger` | Manually trigger webhook dispatch | OWNER |

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

### Plans
| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/plans` | List all available plans + features | Yes |
| GET | `/api/v1/plans/my` | Current owner's plan + usage counters | OWNER |

## OpenAPI / Swagger
- `/docs` and `/redoc` — **dev + staging only**
- Production: disabled via `SHOW_DOCS=false` environment variable

---

# 4. UI/UX Design

## Design System
- **Framework:** Tailwind CSS + Chart.js (vanilla JS — no build step)
- **Responsive:** Mobile-first — optimized for smartphone, works on desktop
- **Language:** French throughout — no toggle
- **Browsers:** Chrome, Firefox, Safari, Edge (latest 2 versions)

## Design Tokens

| Token | Value | Usage |
|---|---|---|
| Primary Green | `#005F02` | Buttons, nav active states, headings |
| Gold Accent | `#C0B87A` | Secondary actions, chart highlights, badges |
| Cream Background | `#F2E3BB` | Page background |
| Surface White | `#FFFFFF` | Cards, modals, forms |
| Critical Red | `#DC2626` | Critical alerts, errors |
| Warning Orange | `#D97706` | Warning alerts, approaching deadlines |
| Success Green | `#16A34A` | Confirmation states |
| Text Primary | `#1A1A1A` | Body text |
| Text Muted | `#6B7280` | Labels, secondary text |
| Border | `#E5E7EB` | Dividers, input borders |
| Font | `Inter / system-ui` | All text |

## Screen Inventory

| File | Screen | Role |
|---|---|---|
| `index.html` | Login | Public |
| `register.html` | Registration | Public |
| `dashboard-owner.html` | Owner Analytics Dashboard | OWNER |
| `dashboard-driver.html` | Driver Operational Dashboard | DRIVER |
| `vehicles.html` | Vehicle Management | OWNER |
| `fuel-entry.html` | Fuel Entry & History | DRIVER |
| `maintenance.html` | Maintenance Records | OWNER |
| `activity.html` | Activity Log | OWNER |
| `reports.html` | AI Reports | OWNER |
| `export.html` | Data Export | OWNER |
| `admin-dashboard.html` | Super Admin Panel | SUPER_ADMIN |

## User Flows

```
PUBLIC
[Login] ──► role check ──► [Owner Dashboard] / [Driver Dashboard] / [Admin Dashboard]
[Register] ──► OTP email ──► verify ──► [Login]

OWNER: Dashboard → Vehicles → Maintenance → Activity Log → Reports → Export
DRIVER: Dashboard → toggle Active → Fuel Entry → view/edit/delete history
ADMIN: User list → suspend/delete/plan changes → Platform analytics
```

## Wireframe Specs (key screens)

**Login:** Centered card, cream bg, email + password, "Se connecter" CTA, forgot password link.

**Owner Dashboard:** Fixed sidebar + scrollable main. KPI cards → charts (bar + line) → consumption table + driver status → alerts + compliance → visualizations (donut + gauges) → anomalies.

**Driver Dashboard:** Single-column mobile layout. Big status toggle → vehicle selector modal → assigned vehicles list → last 10 entries table with edit/delete (locked after 24h).

**Vehicles:** Full-width table with status badges (Active/En pause/Archivé) + slide-in drawer for add/edit. Archived vehicles in collapsible section.

**Fuel Entry:** Form (top) + history table (bottom). Computed consumption preview after odometer input.

**Reports:** Two cards — on-demand generate button (Starter locked) + schedule config (Business only).

**Admin:** Tabs — Utilisateurs (searchable paginated table + row actions) | Analytiques (KPI cards + charts).

## Navigation

**Owner sidebar:** Tableau de bord | Véhicules | Maintenance | Journal | Rapports IA (Pro+) | Export (Pro+) | Mon compte

**Driver top bar (mobile):** Mon tableau de bord | Saisie carburant | Mon compte

Locked items show a lock icon and redirect to upgrade prompt on click.

---

# 5. Integration Design

## Overview

| # | Service | Purpose |
|---|---|---|
| 1 | **SendGrid** | Email — OTP, AI reports, exports |
| 2 | **OpenRouter** | LLM — AI fleet reports (French) |
| 3 | **Meta Cloud API** | WhatsApp Business — fleet alerts |
| 4 | **Webhook (HTTP)** | Push summaries to external tools |

## 1. SendGrid

- Auth: `SENDGRID_API_KEY` | From: `noreply@flotte225.ci`
- Triggers: email verification OTP, password reset OTP, AI report delivery, export delivery
- Templates in French. Failures are non-blocking — log + retry once after 30s.

## 2. OpenRouter (AI Reports)

- Auth: `OPENROUTER_API_KEY` | Model: `OPENROUTER_MODEL` (recommended: mistral-large or claude-haiku)
- Flow: owner triggers → backend builds fleet data snapshot → structured JSON prompt (French system prompt) → LLM returns French report → SendGrid delivers to owner email
- Timeout: 90s. On-demand: no auto-retry. Scheduled: failure logged, next run retries.
- Pro plan counter incremented in `report_schedules.ai_reports_used_month`, reset 1st of month.

## 3. Meta Cloud API (WhatsApp)

- Auth: `WHATSAPP_TOKEN` | URL: `WHATSAPP_API_URL`
- Triggers: critical alerts (expired insurance/inspection), performance anomalies, daily summary
- Silently disabled if `whatsapp_number` not set or env vars missing. Non-blocking failures.

## 4. Webhook

- Config: `WEBHOOK_URL` + `WEBHOOK_INTERVAL_HOURS` (default: 24h)
- Silently disabled if `WEBHOOK_URL` not set
- Payload: owner identity, period covered, alert summary, driver activity delta
- Results stored in `webhook_state`. Manual trigger via `POST /api/v1/webhook/trigger`.

---

# 6. Security Design

## JWT & Authentication

- Access token: 24h, HS256, stored in `localStorage`
- No refresh tokens — re-login on expiry
- Claims: `sub` (user id), `email`, `role`, `exp`, `iat`
- On 401: client clears localStorage, redirects to login

## Password & OTP Security

- bcrypt, 10 rounds minimum. Never stored or logged in plaintext.
- OTP: 6 digits, 15-minute expiry, single-use (`used_at` timestamp)
- Password reset response always identical regardless of email existence (enumeration protection)

## Data Isolation

Two-layer owner scoping:
1. JWT middleware injects `current_user` into every request
2. Service layer always filters by `owner_id == current_user.id`

SUPER_ADMIN uses separate `get_admin_user` dependency — bypasses owner scoping.

## RBAC Dependencies

```python
get_current_user    # any authenticated user
get_current_owner   # OWNER only
get_current_driver  # DRIVER only
get_admin_user      # SUPER_ADMIN only
require_plan("pro") # blocks Starter owners
require_plan("business") # blocks Starter + Pro owners
```

## Transport & API Security

- HTTPS enforced at Nginx. TLS 1.2+ (1.3 preferred). HSTS enabled.
- CORS restricted to `CORS_ORIGINS` env var.
- Pydantic schemas validate all inputs. SQLAlchemy ORM — no raw SQL.
- All secrets in `.env` files — never committed to git. `.env.example` documents all keys.

## Compliance (Côte d'Ivoire — no GDPR/SOC2 required)

- Data minimization, full audit trail, right to deletion (SUPER_ADMIN), secrets out of code.
- Document breach response procedure before production go-live.

---

# 7. Dev Environment & CI/CD

## Quick Start

```bash
git clone https://github.com/your-org/flotte225.git
cd flotte225
cp .env.example .env
docker-compose up --build
# App: http://localhost:8000 | Docs: http://localhost:8000/docs
```

## Docker Compose

**Dev/Staging (`docker-compose.yml`):** FastAPI with `--reload` + PostgreSQL 15 with health check + named volume.

**Production (`docker-compose.prod.yml`):** No `--reload` + Nginx (HTTP→HTTPS, serves static frontend, SSL via Certbot) + `restart: always` on all services.

## Environment Variables (`.env.example`)

```bash
SECRET_KEY=...                    # JWT signing key
ENVIRONMENT=development
ACCESS_TOKEN_EXPIRE_MINUTES=1440
SHOW_DOCS=true                    # false in production
DATABASE_URL=postgresql://postgres:postgres@db:5432/flotte225
CORS_ORIGINS=http://localhost:8000
SENDGRID_API_KEY=...
SENDGRID_FROM_EMAIL=noreply@flotte225.ci
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=mistralai/mistral-large
WHATSAPP_API_URL=https://graph.facebook.com/v18.0/YOUR_PHONE_NUMBER_ID
WHATSAPP_TOKEN=...
WEBHOOK_URL=                      # empty = disabled
WEBHOOK_INTERVAL_HOURS=24
```

## Branching Strategy

```
main      ← production (VPS). Protected. Merges from staging only.
staging   ← pre-production (Render). Testers validate here.
  └── feature/US-XXX-short-description
  └── fix/short-description
  └── chore/short-description
```

**Flow:** branch off staging → build + test → PR to staging (CI must pass) → test on Render → PR to main → deploy to VPS.

## CI/CD Pipeline (GitHub Actions)

Runs on every push to `feature/*`, `fix/*`, `staging` and every PR to `staging` or `main`.

**3 stages:**
1. **Lint** — Ruff (catches errors, bad patterns) + Black (formatting check) → fail fast
2. **Test** — pytest against a real PostgreSQL 15 container → any failure blocks merge
3. **Deploy** — staging merge → Render auto-deploys | main merge → SSH to VPS + `docker-compose -f docker-compose.prod.yml up -d`

**`.github/workflows/ci.yml`** provisions a PostgreSQL service container, installs dependencies, runs Ruff, Black, and pytest with `DATABASE_URL` pointed at the test DB.

## Code Quality Tools

| Tool | Purpose | Runs |
|---|---|---|
| **Ruff** | Python linter — errors, unused imports, anti-patterns | CI + local |
| **Black** | Python auto-formatter — consistent style | CI + local (`black backend/`) |
| **pytest** | Test runner — acceptance criteria become tests | CI + local |

**Local workflow before pushing:**
```bash
black backend/       # fix formatting
ruff check backend/  # check issues
pytest backend/tests/  # run tests
```

---

*End of document — Flotte225 FULL-DESIGN.md | 2026-04-06 | Author: Samuel ABENA*
