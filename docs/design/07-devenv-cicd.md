# 7. Dev Environment & CI/CD

## Local Development Setup

### Prerequisites
- Docker + Docker Compose
- Python 3.11+
- Git

### Quick Start
```bash
git clone https://github.com/your-org/flotte225.git
cd flotte225
cp .env.example .env          # fill in your values
docker-compose up --build     # starts FastAPI + PostgreSQL
```

- App: `http://localhost:8000`
- API docs (Swagger): `http://localhost:8000/docs`
- Frontend: open `frontend/index.html` directly in browser (no build step needed)

---

## Docker Compose Spec

### `docker-compose.yml` (dev + staging)
```yaml
version: "3.9"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./backend:/app        # hot reload in dev
    depends_on:
      db:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: flotte225
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
    # named volume = data survives container restarts
```

### `docker-compose.prod.yml` (production VPS — extends base)
```yaml
version: "3.9"

services:
  backend:
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    # no --reload in production
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./frontend:/usr/share/nginx/html   # serves static frontend
      - ./certbot/conf:/etc/letsencrypt    # SSL certs
    depends_on:
      - backend
    restart: always

  db:
    restart: always
```

---

## Environment Variables

```bash
# .env.example — copy to .env and fill in values
# Never commit .env to git — it's in .gitignore

# ── App ──────────────────────────────────────────
SECRET_KEY=your-secret-key-here-min-32-chars
ENVIRONMENT=development           # development | staging | production
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours
SHOW_DOCS=true                    # false in production

# ── Database ─────────────────────────────────────
DATABASE_URL=postgresql://postgres:postgres@db:5432/flotte225

# ── CORS ─────────────────────────────────────────
CORS_ORIGINS=http://localhost:8000,https://your-staging-domain.onrender.com

# ── Email (SendGrid) ─────────────────────────────
SENDGRID_API_KEY=your-sendgrid-api-key
SENDGRID_FROM_EMAIL=noreply@flotte225.ci

# ── AI Reports (OpenRouter) ──────────────────────
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_MODEL=mistralai/mistral-large

# ── WhatsApp (Meta Cloud API) ────────────────────
WHATSAPP_API_URL=https://graph.facebook.com/v18.0/YOUR_PHONE_NUMBER_ID
WHATSAPP_TOKEN=your-meta-whatsapp-token

# ── Webhook ──────────────────────────────────────
WEBHOOK_URL=                      # leave empty to disable
WEBHOOK_INTERVAL_HOURS=24
```

---

## Branching Strategy

**3-tier branching** — feature → staging → main:

```
main          ← production (VPS). Protected. Only accepts merges from staging.
  │
staging       ← pre-production (Render). Where testers validate features.
  │
  └── feature/US-001-auth-register
  └── feature/US-003-login-redirect
  └── fix/fuel-odometer-validation
  └── feature/US-010-submit-fuel-entry
```

### Flow for each story
```
1. Branch off staging:
   git checkout staging
   git pull
   git checkout -b feature/US-001-auth-register

2. Build the feature + write tests

3. Push and open PR → staging
   - GitHub Actions runs: Ruff + Black + pytest
   - All checks must pass before merge is allowed
   - Merge to staging → auto-deploys to Render

4. Test on staging (real environment, real data)

5. When validated → open PR: staging → main
   - GitHub Actions runs again
   - Merge to main → deploy to production VPS
```

### Branch naming convention
```
feature/US-XXX-short-description    # new stories
fix/short-description               # bug fixes
chore/short-description             # non-feature tasks (deps, config)
```

---

## CI/CD Pipeline (GitHub Actions)

### What GitHub Actions does
GitHub Actions is a built-in automation tool that runs a series of checks automatically every time you push code or open a Pull Request. Think of it as a robot reviewer that checks your code before it reaches staging or production. If any check fails, the merge is blocked until you fix it.

### Pipeline — runs on every push to `feature/*` and every PR to `staging` or `main`

```
Push code / Open PR
        │
        ▼
┌──────────────────┐
│  1. LINT & FORMAT │  ← Ruff checks for Python errors + bad patterns
│                  │     Black checks code is consistently formatted
│                  │     Fails fast if style violations found
└────────┬─────────┘
         │ Pass
         ▼
┌──────────────────┐
│  2. TEST         │  ← pytest runs all tests against a real PostgreSQL
│                  │     container (same as production DB engine)
│                  │     Any failing test blocks the merge
└────────┬─────────┘
         │ Pass
         ▼
┌──────────────────┐
│  3. DEPLOY       │  ← Only on merge to staging or main
│  (auto)          │     staging merge → Render auto-deploys
│                  │     main merge → SSH to VPS + run:
│                  │     docker-compose -f docker-compose.prod.yml up -d
└──────────────────┘
```

### `.github/workflows/ci.yml`
```yaml
name: CI — Flotte225

on:
  push:
    branches: ["feature/*", "fix/*", "staging"]
  pull_request:
    branches: ["staging", "main"]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: flotte225_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r backend/requirements.txt

      - name: Lint with Ruff
        # Ruff checks for unused imports, undefined variables,
        # bad patterns, and Python anti-patterns
        run: ruff check backend/

      - name: Check formatting with Black
        # Black ensures all Python code follows the same style —
        # no arguments about tabs vs spaces, line length, etc.
        run: black --check backend/

      - name: Run tests with pytest
        # pytest finds all test_*.py files and runs them
        # The PostgreSQL service above is the test database
        run: pytest backend/tests/ -v
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/flotte225_test
          SECRET_KEY: test-secret-key-for-ci-only
          ENVIRONMENT: testing
```

---

## Code Quality Tools

| Tool | What it does | When it runs |
|---|---|---|
| **Ruff** | Lints Python — catches errors, unused imports, bad patterns. Fast (written in Rust). | Every push (CI) + recommended as pre-commit hook |
| **Black** | Auto-formats Python code to a consistent style. No config needed. | Every push (CI) — run `black backend/` locally before pushing |
| **pytest** | Runs all tests. Each acceptance criterion in the backlog becomes a test. | Every push (CI) + locally before opening a PR |

### Recommended local workflow
```bash
# Before pushing, run locally:
black backend/          # auto-fix formatting
ruff check backend/     # check for issues
pytest backend/tests/   # run tests

# Then push — CI will verify the same checks passed
```

---
*Completed: 2026-04-06*
