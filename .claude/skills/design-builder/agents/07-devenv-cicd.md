# Agent 7 — Dev Environment & CI/CD

Define how the team builds, runs, and ships the application. A well-defined dev environment
means any new developer can be productive in under 30 minutes. A clear CI/CD pipeline means
every merge is tested and deployed consistently. This section produces the specs for
docker-compose, environment variables, the CI pipeline, and branching strategy.

## References to read before starting
- `references/questioning.md`
- `references/saving.md`

## Step 0 — Use SRS and architecture context
You already know:
- Backend: FastAPI (Python)
- Database: PostgreSQL
- Frontend: JavaScript + Tailwind CSS + Bootstrap
- Containerization decision: from Section 1

Do not ask about the tech stack.

## Step 1 — Ask only for gaps (one at a time)
1. "What Git platform are you using? (GitHub / GitLab / Bitbucket)"
2. "Do you have a CI/CD tool in mind? (e.g. GitHub Actions, GitLab CI — or TBD)"
3. "What branching strategy do you prefer? (Feature branches → main / GitFlow with dev + main / Trunk-based)"
4. "Any code quality tools you want enforced? (e.g. Black for Python formatting, Ruff for linting — or skip for now)"

## Step 2 — Confirm before saving
Present the full dev environment spec and ask:
"Here's your Dev Environment & CI/CD design. Does everything look right?
(yes to save / tell me what to change)"

## Step 3 — Save
Save to `docs/design/07-devenv-cicd.md`:

```markdown
# 7. Dev Environment & CI/CD

## Local Development Setup

### Prerequisites
- Docker + Docker Compose
- Python 3.11+
- Node.js 20+ (for frontend tooling)
- Git

### Quick Start
```bash
git clone <repo-url>
cd <project-root>
cp .env.example .env        # fill in your values
docker-compose up --build   # starts FastAPI + PostgreSQL
```

App available at: `http://localhost:8000`
API docs at: `http://localhost:8000/docs`

---

## Docker Compose Spec

```yaml
# docker-compose.yml
version: "3.9"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/einvoice
      - SECRET_KEY=${SECRET_KEY}
      - ACUBE_API_KEY=${ACUBE_API_KEY}
      - SENDGRID_API_KEY=${SENDGRID_API_KEY}
      - ENVIRONMENT=development
    volumes:
      - ./backend:/app
    depends_on:
      db:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: einvoice
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
```

---

## Environment Variables

```bash
# .env.example — copy to .env and fill in values

# App
SECRET_KEY=your-secret-key-here          # JWT signing key
ENVIRONMENT=development                   # development | staging | production
DEBUG=true

# Database
DATABASE_URL=postgresql://postgres:postgres@db:5432/einvoice

# A-Cube API (PEPPOL)
ACUBE_API_KEY=your-acube-api-key
ACUBE_API_URL=https://sandbox.acubeapi.com   # change for production

# SendGrid
SENDGRID_API_KEY=your-sendgrid-api-key
SENDGRID_FROM_EMAIL=noreply@yourdomain.com

# File Storage
UPLOAD_DIR=./uploads                     # local dev; replace with S3/GCS in production
MAX_UPLOAD_SIZE_MB=20
```

---

## CI/CD Pipeline

**Platform:** [GitHub Actions / GitLab CI / TBD]

### Pipeline Stages

```
Push / PR
    │
    ▼
1. LINT & FORMAT
   - Python: ruff check + black --check [if enabled]
   - Fail fast on style violations
    │
    ▼
2. TEST
   - Run pytest (unit + integration tests)
   - PostgreSQL test database via service container
   - Fail on any test failure or coverage drop below threshold
    │
    ▼
3. BUILD
   - docker build backend image
   - Tag with commit SHA
    │
    ▼
4. DEPLOY (main branch only)
   - Push image to container registry
   - Deploy to staging → run smoke tests → deploy to production
```

### GitHub Actions Example (if GitHub)

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests/
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
```

---

## Branching Strategy

**Strategy:** [Feature branches → main / GitFlow / Trunk-based]

[If feature branches:]
```
main          ← production-ready, protected branch
  └── feature/US-001-auth-login     ← developer branches off main
  └── feature/US-002-document-upload
  └── fix/submission-status-bug
```

**Rules:**
- No direct commits to `main`
- Every PR requires at least 1 review
- CI must pass before merge
- Delete branch after merge

---

## Code Quality Tools

| Tool | Purpose | When it runs |
|------|---------|-------------|
| [Black] | Python auto-formatter | Pre-commit hook + CI |
| [Ruff] | Python linter | Pre-commit hook + CI |
| [pytest] | Test runner | CI on every push |

---
*Completed: [date]*
```

Update `docs/design/design-progress.json` → `"devenv": true`.
Tell the user: "✅ Section 7 complete — Dev Environment & CI/CD saved."
