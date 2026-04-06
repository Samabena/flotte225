# Reference: SRS Reader

Before starting Section 1, read the existing project documents to extract decisions already made.
The goal is to arrive at each agent pre-loaded with known answers so you only ask about true gaps.

## Step 1 — Read the SRS

Read `docs/srs/FULL-SRS.md`. Extract and note:

**Tech stack** (from Product Overview):
- Backend framework
- Database
- Frontend approach
- Known constraints

**Functional requirements** (from Functional Requirements):
- All F-01 through F-0N features, descriptions, and MoSCoW priorities

**Non-functional requirements** (from Non-Functional Requirements):
- Performance targets
- Security requirements (auth method, encryption, hashing)
- Scalability targets (concurrent users at launch and at scale)
- Availability target (uptime %)
- Compliance requirements (GDPR, SOC2, PEPPOL, etc.)

**Interface requirements** (from Interface Requirements):
- UI type and design system
- Third-party integrations (APIs, services)
- Auth method
- Browser and device support

## Step 2 — Read the Backlog

Read `docs/backlog/PRODUCT-BACKLOG.md`. Note:
- Sprint structure and MVP scope
- Any technical decisions implied by story acceptance criteria
- Record the file date or lastUpdated for `backlogVersion` in progress.json

## Step 3 — Present what you found

Show the user a brief summary before starting Section 1:

```
📄 I've read your SRS and backlog. Here's what I already know:

- Backend:      [value]
- Database:     [value]
- Frontend:     [value]
- Auth:         [value]
- Integrations: [list]
- Scale target: [value]
- Compliance:   [list]
- Features:     [count] functional requirements across [N] sprints

I'll use these throughout all 7 design sections and only ask about gaps.
```

## What this means per agent

Use this map to know what to skip asking vs. what to ask:

| Agent | Already known (skip) | Still needs asking |
|-------|---------------------|-------------------|
| 01 Architecture | Tech stack, product type | Deployment target, containers, environments, repo structure |
| 02 Database | Entities derived from F-01 to F-09 | Multi-tenancy isolation strategy, soft deletes, extra fields |
| 03 API Design | Auth type (JWT), all features | API versioning, rate limiting, Swagger preference |
| 04 UI/UX | Design system, browser support | Brand colors, UI inspiration, dashboard layout |
| 05 Integrations | Which integrations (A-Cube, SendGrid) | Credentials status, sync vs async, notification triggers |
| 06 Security | Auth method, compliance requirements | JWT token expiry, refresh token strategy, GDPR specifics |
| 07 Dev/CI-CD | Tech stack for containers | Git platform, CI/CD tool, branching strategy, linting tools |
