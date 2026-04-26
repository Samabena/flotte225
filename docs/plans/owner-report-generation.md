# Plan — Owner Report Generation (Deterministic Template, PDF, FR)

## Context

FlotteApp owners currently see fleet performance only on the live dashboard (`dashboard-owner.html`) and via narrative AI reports (`/reports`). They have asked for a separate, deterministic, owner-readable report system in French that:
- Uses a **single saved template** (so every report has the same structure)
- Produces **PDFs** suitable for printing/sharing
- Covers the **whole fleet** OR a **single driver**
- Lets the owner pick the **date range**

This complements (does not replace) the existing AI narrative reports under `/reports`. New menu item: **"Rapports"**, distinct from **"Rapports IA"**.

Plan gating reuses the existing pattern: **Pro & Business only** (`require_plan("pro", "business")`), like exports and AI reports.

## Confirmed design decisions

| Decision | Choice |
|---|---|
| Generation engine | Deterministic Jinja2 template → PDF |
| Template storage | File in repo (`backend/app/templates/reports/`) |
| Output format | PDF only |
| Date range | Owner picks (presets + custom from/to) |
| Menu placement | New "Rapports" item, separate from "Rapports IA" |
| Per-driver mode | Pick one driver from dropdown |
| Plan gating | Pro & Business only |
| HTML→PDF library | **WeasyPrint** (clean CSS, professional output) |

## Architecture overview

```
Frontend (reports-template.html + js)
  └─ POST /api/v1/reports/template/fleet     → PDF blob → download
  └─ POST /api/v1/reports/template/driver/{driver_id} → PDF blob → download

Backend (reports.py endpoint)
  └─ template_report_service.py
       ├─ build_fleet_context(owner, db, from, to)   ──┐
       ├─ build_driver_context(owner, db, drv, from, to) ─┤
       ├─ render_html(template_name, context)            ──→ Jinja2 → WeasyPrint → PDF bytes
       └─ stream_pdf(bytes, filename)                    ─┘

Templates (Jinja2, French)
  └─ base.html.j2          — shared header/footer/styles
  └─ fleet_report.html.j2  — extends base
  └─ driver_report.html.j2 — extends base
```

## Files to create

### Backend
1. **`backend/app/services/template_report_service.py`** *(new)*
   - `build_fleet_context(owner: User, db: Session, date_from: date, date_to: date) -> dict` — assembles all fleet KPIs for the period:
     - Owner identity: `owner.company_name`, `owner.full_name`, generation timestamp
     - Period totals: total fuel spend (FCFA), total litres, total km, active vehicles count, active drivers count
     - Spend per vehicle (table, top→bottom)
     - Monthly trend (last N months in range)
     - Consumption per vehicle (avg L/100km)
     - Drivers list (full_name, driving_status, active_vehicle_name, fuel entries count in period)
     - Alerts & anomalies (insurance/inspection expiry, consumption anomaly, cost spike)
   - `build_driver_context(owner: User, db: Session, driver_id: int, date_from, date_to) -> dict` — per-driver:
     - Driver identity: `full_name`, `phone`, `username`, `is_disabled`
     - Period activity: total entries, total litres, total amount FCFA, total km, avg consumption
     - Vehicles driven in period (from FuelEntry.vehicle_id distinct)
     - Detailed fuel entries table (date, vehicle, odometer, qty, amount, consumption)
     - Cross-tenant guard: raise 404 if `driver.owner_id != owner.id`
   - `render_pdf(template_name: str, context: dict) -> bytes` — Jinja2 → HTML → WeasyPrint → PDF bytes
   - **Reuses**:
     - `app/services/dashboard_service.py` aggregation helpers (`_get_financial_summary`, `_get_consumption_indicators`) — pass `date_from`/`date_to` if needed (may require small extension to accept date filters)
     - `app/services/alert_service.py` for alerts/anomalies
     - Direct SQLAlchemy queries on `FuelEntry`, `Vehicle`, `User` filtered by `Vehicle.owner_id == owner.id` and `FuelEntry.date BETWEEN`
     - Currency formatter (build a small `format_fcfa` Jinja filter; `1 234 567 FCFA` style with non-breaking space)
     - Date formatter (`format_date` filter, French `dd/mm/yyyy`)

2. **`backend/app/templates/reports/base.html.j2`** *(new)*
   - Shared layout: `<html lang="fr">`, embedded CSS (A4, margins, header with owner company, footer with page number + generation date)
   - Brand color matches existing exports (#005F02 green from `export_service.py`)
   - Block placeholders: `{% block title %}`, `{% block content %}`

3. **`backend/app/templates/reports/fleet_report.html.j2`** *(new)*
   - Title: `Rapport de flotte — {{ company_name }}`
   - Sections (all in French):
     1. **Synthèse exécutive** (KPI cards: dépense totale, véhicules actifs, conducteurs actifs, litres consommés, distance totale)
     2. **Performance des véhicules** (table: véhicule, dépense, consommation moyenne, distance)
     3. **Tendance mensuelle** (table: mois, dépense FCFA, # de pleins; bars built with inline CSS widths — no JS charts)
     4. **Conducteurs** (table: nom, statut, véhicule actif, # pleins période)
     5. **Alertes & anomalies** (table: véhicule, type, sévérité, message)
     6. **Pied de page**: « Rapport généré le {{ generated_at }} par FlotteApp »

4. **`backend/app/templates/reports/driver_report.html.j2`** *(new)*
   - Title: `Rapport conducteur — {{ driver.full_name }}`
   - Sections:
     1. **Identité** (nom, téléphone, identifiant, statut)
     2. **Synthèse de la période** (KPIs: dépense totale, litres, distance, conso moyenne, # pleins)
     3. **Véhicules conduits** (liste)
     4. **Détail des pleins** (table: date, véhicule, kilométrage, litres, montant FCFA, conso L/100km)
     5. **Pied de page** identique au rapport flotte

5. **`backend/app/api/v1/endpoints/reports.py`** *(extend existing file)*
   - `POST /reports/template/fleet` — body: `{date_from: date, date_to: date}` → `StreamingResponse(media_type="application/pdf")` with `Content-Disposition: attachment; filename="rapport-flotte-YYYYMMDD.pdf"`
   - `POST /reports/template/driver/{driver_id}` — same body → per-driver PDF
   - Both use `Depends(get_current_owner)` + `Depends(require_plan("pro", "business"))`
   - Validate `date_from <= date_to`, default range = last 30 days if missing

6. **`backend/requirements.txt`** *(modify)*
   - Add `weasyprint>=60.0` (Jinja2 already comes with FastAPI; verify and add if missing)

7. **`docker-compose.yml`** / Dockerfile *(check + possibly modify)*
   - WeasyPrint needs Pango/Cairo native libs. For Debian-based Python images: `apt-get install -y libpango-1.0-0 libpangoft2-1.0-0` in the Dockerfile.
   - Verify the existing backend image; add the apt step if not present.

### Frontend
8. **`frontend/reports-template.html`** *(new)*
   - Same sidebar pattern as `reports.html` with active state on the new "Rapports" item
   - Two tabs: **« Rapport flotte »** (default) and **« Rapport conducteur »**
   - Shared period picker block:
     - Preset chips: 7 derniers jours / 30 derniers jours / Mois en cours / Mois précédent / Année en cours
     - Custom from/to date inputs
   - Driver tab adds a `<select>` populated from `GET /api/v1/drivers`
   - Submit button: « Générer le PDF »

9. **`frontend/js/reports-template.js`** *(new)*
   - Auth bootstrap (matches `reports.js` pattern: `getToken`, redirect on missing)
   - Preset → from/to computation
   - Drivers fetch on tab switch
   - On submit:
     - `fetch(endpoint, { method: "POST", headers: { Authorization, Content-Type: "application/json" }, body: JSON.stringify({date_from, date_to}) })`
     - On success: `response.blob()` → create object URL → trigger `<a download>` click
     - On 403: show « Cette fonctionnalité nécessite un plan Pro ou Business. »
     - On other errors: show generic French error

10. **Sidebar update** — add `<a href="/reports-template" class="...">Rapports</a>` to:
    - `frontend/dashboard-owner.html`
    - `frontend/reports.html`
    - `frontend/vehicles.html`, `frontend/drivers.html`, `frontend/maintenance.html`, `frontend/activity.html`, `frontend/settings.html`, `frontend/profile.html`, `frontend/fuel-entry.html`
    - Position: just below "Rapports IA" (or where it fits the existing groupings)

11. **`backend/app/main.py`** — confirm static route serves `/reports-template`. If not auto-served by directory listing, add the explicit mount/route alongside the existing pages.

### Tests
12. **`backend/tests/test_template_reports.py`** *(new)*
    - `test_fleet_report_returns_pdf` — Pro plan owner with fleet → 200, `content-type: application/pdf`, payload starts with `%PDF`, filename header set
    - `test_driver_report_returns_pdf` — same, for one driver
    - `test_starter_plan_blocked` — Starter owner → 403
    - `test_driver_cross_tenant_blocked` — owner A requests driver from owner B → 404
    - `test_invalid_date_range_rejected` — `date_from > date_to` → 422
    - `test_empty_range_renders_gracefully` — owner with no fuel entries in window → still 200, template shows « Aucune donnée pour la période sélectionnée »

## Critical files to read before implementation

- `backend/app/api/v1/endpoints/reports.py` — extend in place; preserve existing AI report endpoints
- `backend/app/services/dashboard_service.py` — reuse aggregation; may need to extend `_get_financial_summary` and `_get_consumption_indicators` to accept optional `date_from`/`date_to`
- `backend/app/services/export_service.py` — mirror its StreamingResponse + filename pattern
- `backend/app/services/alert_service.py` — reuse alerts/anomalies for fleet template
- `backend/app/core/deps.py` — confirms `get_current_owner` and `require_plan` signatures
- `backend/app/main.py` — verify static page serving for the new HTML
- `frontend/reports.html` + `frontend/js/reports.js` — copy structure for the new page

## Verification

1. **Install deps**: `cd backend && pip install -r requirements.txt` (and rebuild docker image so Pango/Cairo land)
2. **Run backend**: `cd backend && uvicorn app.main:app --reload`
3. **Run tests**: `cd backend && pytest tests/test_template_reports.py -v`
4. **Manual flow** (Pro/Business owner):
   - Log in → Dashboard → click "Rapports" in sidebar
   - Default tab "Rapport flotte" → preset "30 derniers jours" → "Générer le PDF" → PDF downloads
   - Open the PDF: confirm French, owner company name in header, KPI section, vehicle table, monthly trend, drivers, alerts, page numbers
   - Switch to "Rapport conducteur" tab → pick a driver from the dropdown → custom range → generate → confirm driver-specific PDF
5. **Plan gating check**: Log in as a Starter-plan owner → confirm 403 + French upsell message
6. **Cross-tenant check**: Manually call `POST /reports/template/driver/{other_owner_driver_id}` with curl + token → expect 404

## Open considerations (not blocking)

- **Charts**: We render trend bars with inline CSS widths (no JS charts in PDF). If charts become a stronger requirement later, add `matplotlib` for SVG and embed.
- **Template editability via UI**: out of scope now — file-based template lives in git. A future migration to DB-backed templates is straightforward (add `ReportTemplate` model + admin editor UI).
- **WeasyPrint native deps on macOS**: dev gets them with `brew install pango`. Document in repo README if not already.
