# Project Devlog — Flotte225

A plain-English record of what we built, what broke, how we fixed it, and why we made the decisions we made.
Read this to get a fast understanding of the project's history without reading the code.

---

## 2026-03-30 — Project kickoff: SRS, backlog, and design

### What we built
We started from scratch. The first commit was planning documents only — a full SRS, a 46-story product backlog, and a 7-section system design covering architecture, database, API, UI/UX, integrations, security, and CI/CD. No code yet. The goal was to get all the decisions written down before touching a keyboard, so we could build fast without revisiting the fundamentals every session.

### Key decisions
We chose FastAPI over Django or Flask because the project is API-first and we wanted pydantic validation built in. PostgreSQL over SQLite because we need JSONB for activity logs and the design calls for a production VPS deployment from day one. No React or Vue — the frontend is vanilla JS with Tailwind, served as static files. This keeps the deploy simple and removes a build step entirely. The SaaS plans (Starter free, Pro 9,900 FCFA, Business 24,900 FCFA) are assigned manually by SUPER_ADMIN — no payment gateway at launch, that's a future phase.

### What's next
Start Sprint 1: authentication, OTP verification, and plan infrastructure.

---

## 2026-04-01 — Sprint 1: authentication and plan infrastructure

### What we built
Sprint 1 delivered the full auth flow — registration, email verification via 6-digit OTP, login with role-based JWT, and password reset via OTP. Three roles are supported from the start: OWNER, DRIVER, SUPER_ADMIN. Every new owner is automatically assigned the Starter plan on registration. We also built `require_plan()`, a FastAPI dependency factory that blocks endpoints by plan name, and seeded the three subscription plans plus a SUPER_ADMIN account via a `scripts/seed.py` script. Eighteen tests pass.

### The hard parts
bcrypt compatibility was the first real problem. The latest bcrypt (4.x) broke passlib 1.7.4's hash API at import time. The fix was to pin `bcrypt==3.2.2` in requirements.txt. We also hit a tricky circular FK issue: `users.active_vehicle_id` references `vehicles.id`, but vehicles also reference `users.id` (owner). SQLAlchemy's `create_all` choked on the ordering. We solved it with `use_alter=True` and a named constraint (`fk_users_active_vehicle_id`), which tells Alembic to emit the FK as a separate ALTER TABLE after both tables exist.

### How we solved it
Pinned bcrypt to 3.2.2 in requirements.txt. Added `use_alter=True, name="fk_users_active_vehicle_id"` to the `active_vehicle_id` mapped column. Both fixes went into the initial schema migration.

### Key decisions
OTPs are single-use and previous ones are invalidated when a new request is made. The forgot-password endpoint always returns 200 regardless of whether the email exists — this prevents user enumeration. Role is set at registration and is immutable.

---

## 2026-04-03 — Sprint 2: vehicle management

### What we built
Owners can now register, edit, pause, resume, archive, and restore vehicles. Archiving is a soft delete — the vehicle gets `status="archived"` and an `archived_at` timestamp, data is never lost. Drivers can be assigned to and removed from vehicles. Drivers can see their assigned vehicles and toggle their driving status (on/off mission). Plan limits are enforced: Starter owners are blocked from registering more than 2 vehicles, Pro owners are capped at 15. Twenty-eight tests pass.

### The hard parts
The vehicle limit check on restore was easy to miss. When an owner restores an archived vehicle, that vehicle would push them over their plan limit if they've added others in the meantime. We had to apply the same limit check at restore time, counting only active + paused vehicles.

### How we solved it
Added `_check_plan_vehicle_limit()` in `vehicle_service.py` and called it both at create time and at restore time. Archived vehicles are excluded from the count.

### Key decisions
Archiving a vehicle auto-clears the active driver's state — `driving_status=False` and `active_vehicle_id=None`. This prevents a driver from being stuck "on mission" for a vehicle that no longer exists in the active fleet. Any DRIVER-role user can be assigned to any owner's vehicle (no owner scoping on the driver side).

---

## 2026-04-05 — Sprint 3: fuel entries and audit log

### What we built
Drivers can now log fuel entries: date, odometer reading, liters filled, and cost in FCFA. The system automatically computes consumption in L/100km from the gap between consecutive odometer readings. Drivers can edit or delete their own entries within 24 hours. Owners see all fuel entries across their fleet. Every fuel create, edit, and delete triggers an entry in the `activity_logs` table with the full before/after state stored as JSONB — so owners have a complete audit trail. Twenty-one tests pass.

### The hard parts
Consumption calculation requires knowing the previous odometer reading for the same vehicle. We query for the most recent prior entry at write time and compute `distance_km = current_odometer - previous_odometer`, then `consumption = (liters / distance_km) * 100`. If it's the first entry for the vehicle, consumption is null.

### Key decisions
The 24-hour edit/delete window is enforced by comparing `created_at` to `now()` server-side. We store the raw data_before and data_after in JSONB so the audit log is self-contained — no joins needed to reconstruct what changed.

---

## 2026-04-07 — Sprint 4: maintenance records and alert engine

### What we built
This sprint added maintenance tracking per vehicle (last oil change km, insurance expiry, inspection expiry) and a full alert engine. The maintenance record is auto-created on first GET so the owner never hits a 404. The alert engine runs on-demand via `compute_alerts(db, owner_id)` and returns typed alerts across five categories: insurance expiry, inspection expiry, oil change overdue, abnormal fuel consumption, and monthly cost spike. Twenty-one tests pass, bringing the total to 88.

### The hard parts
The consumption anomaly alert needs at least two fuel entries with a computed consumption — otherwise there's no baseline to compare against. We added a guard that skips the anomaly check if entry count is under 2. The cost spike check also has an edge case: if the previous month has zero spend, dividing by it would crash. We skip the alert entirely in that case rather than flagging a spurious spike.

### Key decisions
Oil change: warning at 400 km since last change, critical at 500 km. Compliance: warning ≤ 30 days to expiry, critical if already expired. Consumption anomaly: deviation > 20% from vehicle average. Cost spike: current month > 30% above previous month. All thresholds came from the PRD and are not configurable at runtime.

---

## 2026-04-09 — Sprint 5 + 6: owner dashboard and super admin UI

### What we built
Sprints 5 and 6 were the first frontend work. Sprint 5 delivered the owner dashboard (`dashboard-owner.html` + `dashboard.js`) with financial KPIs, a spend-by-vehicle donut chart, monthly spend trend, consumption indicators per vehicle, driver status cards, and the alert feed. Sprint 6 added the super admin panel (`dashboard-admin.html` + `admin.js`) with a searchable paginated user table, plan assignment controls, user suspension/deletion, and platform-wide analytics. We also built a plan usage banner for owners showing their current plan limits. The test count grew to 138.

### The hard parts
The owner dashboard needed a `/dashboard/owner` endpoint that aggregates financial, consumption, driver, and alert data in one call. Doing this without N+1 queries took some care — we load vehicles once, then fuel entries for all vehicles in a single query, then join in Python. Chart.js configuration for the donut and line chart required tuning to match the brand palette (green #005F02, gold #C0B87A, cream #F2E3BB).

### Key decisions
The frontend is vanilla JS with no build step — just a `<script>` tag pointing to Tailwind CDN and Chart.js CDN. This was a deliberate choice to keep deployment simple. The API client in each JS file is a thin `fetch()` wrapper that injects the JWT from `localStorage`.

---

## 2026-04-10 — Sprint 7: export, WhatsApp, and admin analytics

### What we built
Sprint 7 added three features. First, PDF and Excel export for fuel and maintenance data — owners can download either format with one click. Second, WhatsApp alert integration using the Meta Cloud API: a daily APScheduler job fires at 08:00 Africa/Abidjan and sends a critical-alerts summary to any owner who has a WhatsApp number set. Third, platform analytics for the super admin: total users, active owners, revenue by plan, and a monthly growth chart. The scheduler was introduced here using APScheduler running as a background thread inside FastAPI's lifespan context. Test count reached 159.

### The hard parts
PDF generation with ReportLab needed careful layout work for the fuel table — long vehicle names overflowed columns. We settled on fixed column widths with text wrapping. WhatsApp integration is silently disabled if the `WHATSAPP_TOKEN` env var is not set, so the scheduler job runs harmlessly in dev without crashing.

### Key decisions
Exports are restricted to Pro and Business plans via `require_plan("pro", "business")`. The WhatsApp job caps at 5 alerts per message to avoid overwhelming owners with long lists. Scheduler jobs catch and log all exceptions so a failure in one owner's job doesn't abort the rest.

---

## 2026-04-12 — Sprint 8: AI reports and webhook integration

### What we built
Sprint 8 is the final sprint and it closes out the full product backlog. We added two new database tables (`report_schedules` and `webhook_state`), two services (`ai_report_service` and `webhook_service`), four new API endpoints, two new APScheduler jobs, and the `reports.html` frontend page. The AI report flow works like this: the owner clicks "Générer un rapport", the backend pulls a fleet snapshot (vehicles, recent fuel entries, maintenance, alerts), builds a structured French prompt, sends it to OpenRouter (configurable model, defaults to Mistral Large), and emails the result via SendGrid. Scheduled reports (Business only) run on a weekly or monthly cadence checked every hour at :30 past. The webhook job dispatches a fleet summary JSON payload to a configured external URL every N hours (default 24). Test count is now 185.

### The hard parts
The monthly quota counter for Pro plan reports needed a reset mechanism. We store `usage_reset_at` as a date and compare it to today's month — if they differ, we zero the counter before checking. The tricky part was making sure the test that pre-loads a schedule with `ai_reports_used_month=5` also sets `usage_reset_at=date.today()`, otherwise the service resets the counter to 0 and the quota check never fires. The webhook `_build_payload` function originally referenced `owner.company_name` which doesn't exist on the User model — caught by tests.

### How we solved it
Set `usage_reset_at=date.today()` in the quota-enforcement test. Replaced `company_name` with `full_name` in the webhook payload. The scheduled-reports plan check initially allowed both Pro and Business, but the design spec says Business only — we tightened `_assert_scheduled_reports_allowed` to reject Pro as well.

### Key decisions
On-demand reports: available to Pro (5/month limit) and Business (unlimited). Scheduled reports: Business only. This matches the wireframe spec ("schedule config — Business only"). The OpenRouter call has a 90-second timeout with no auto-retry on-demand; scheduled jobs log failure and retry on the next cadence. If `OPENROUTER_API_KEY` is not set, the service returns a placeholder string rather than crashing — useful in dev without a real key.

### What's next
The codebase is feature-complete. The remaining work is operational: run the Alembic migration 005 on staging, set the new env vars (OPENROUTER_API_KEY, OPENROUTER_MODEL, WEBHOOK_URL), do an end-to-end smoke test with real API keys, then push to production.
