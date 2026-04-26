# Agent 1 — System Architecture

Establish the deployment topology and technical structure of the system. This section
sets the context for everything that follows — how the database is hosted, how the API
is deployed, how the frontend is served, and how the team's environments are organized
all flow from architecture decisions made here.

## References to read before starting
- `references/questioning.md`
- `references/saving.md`
- (srs-reader already ran — use the extracted values)

## Step 0 — Use SRS context
You already know from the SRS:
- Backend: FastAPI (Python)
- Database: PostgreSQL
- Frontend: JavaScript + Tailwind CSS + Bootstrap
- Product type: Multi-tenant SaaS web app

Do not ask about these. Use them as given inputs in the output.

## Step 1 — Ask only for gaps (one at a time)
1. "Where are you planning to deploy? (e.g. AWS, GCP, Railway, Render, Fly.io, DigitalOcean, VPS — or TBD)"
2. "Do you want to use Docker / Docker Compose for local development and/or deployment?"
3. "How many environments do you need? (e.g. dev, staging, production)"
4. "Will the frontend and backend live in the same repository (monorepo) or separate repos?"

## Step 2 — Confirm before saving
Show all collected values and ask:
"Here's your System Architecture. Does everything look right?
(yes to save / tell me what to change)"

## Step 3 — Save
Save to `docs/design/01-system-architecture.md`:

```markdown
# 1. System Architecture

## Component Overview
The e-invoicing system is a multi-tenant SaaS web application built on FastAPI (Python)
with a PostgreSQL database, JavaScript/Tailwind/Bootstrap frontend, and two external
service integrations: A-Cube API (PEPPOL delivery) and SendGrid (email notifications).

## Component Diagram

```
[Client Browser]
      │ HTTPS
      ▼
[Nginx / Reverse Proxy]
      │
      ▼
[FastAPI Backend]──────► [PostgreSQL Database]
      │
      ├──► [A-Cube API (PEPPOL Network)]
      └──► [SendGrid (Email)]
```

## Deployment Target
[value]

## Containerization
[Docker / Docker Compose strategy — or "None"]

## Environments
| Environment | Purpose |
|-------------|---------|
| dev | Local development — Docker Compose, hot reload |
| staging | Pre-production testing — mirrors production config |
| production | Live system — [deployment target] |

## Repository Structure
[Monorepo / Separate repos — with brief reasoning]

## Recommended Folder Structure
```
[project-root]/
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── api/              # Route handlers (endpoints)
│   │   ├── models/           # SQLAlchemy database models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic layer
│   │   └── core/             # Config, security, dependencies
│   ├── tests/
│   └── requirements.txt
├── frontend/                 # JS + Tailwind + Bootstrap
│   ├── static/
│   └── templates/
├── docs/                     # SRS, backlog, design docs
└── docker-compose.yml
```

---
*Completed: [date]*
```

Update `docs/design/design-progress.json` → `"architecture": true`.
Tell the user: "✅ Section 1 complete — System Architecture saved."
