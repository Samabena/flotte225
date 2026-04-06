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
              volume)               ├──► [SMTP Server]       (OTP, AI reports, exports)
                                    ├──► [OpenRouter API]    (AI report generation)
                                    ├──► [WhatsApp Biz API]  (fleet alerts)
                                    └──► [Webhook Endpoint]  (external tools)
```

## Deployment

| Environment | Platform | Notes |
|---|---|---|
| Development | Local — Docker Compose | Hot reload, `.env` file, local PostgreSQL container |
| Staging | Render | Auto-deploy from `main` branch, shared `.env` config |
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
*Completed: 2026-04-06*
