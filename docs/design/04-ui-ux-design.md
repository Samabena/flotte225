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

---

## Screen Inventory

| File | Screen | Role | Route |
|---|---|---|---|
| `index.html` | Login | Public | `/` |
| `register.html` | Registration | Public | `/register` |
| `dashboard-owner.html` | Owner Analytics Dashboard | OWNER | `/dashboard` |
| `dashboard-driver.html` | Driver Operational Dashboard | DRIVER | `/dashboard` |
| `vehicles.html` | Vehicle Management | OWNER | `/vehicles` |
| `fuel-entry.html` | Fuel Entry & History | DRIVER | `/fuel` |
| `maintenance.html` | Maintenance Records | OWNER | `/maintenance` |
| `activity.html` | Activity Log | OWNER | `/activity` |
| `reports.html` | AI Reports | OWNER | `/reports` |
| `export.html` | Data Export | OWNER | `/export` |
| `admin-dashboard.html` | Super Admin Panel | SUPER_ADMIN | `/admin` |

---

## User Flows

```
PUBLIC
──────
[Login] ──► role check ──► [Owner Dashboard]
                       └──► [Driver Dashboard]
                       └──► [Admin Dashboard]

[Register] ──► OTP email ──► verify ──► [Login]

OWNER FLOW
──────────
[Owner Dashboard]
    ├──► [Vehicles] ──► create / edit / pause / archive / assign drivers
    ├──► [Maintenance] ──► update oil change km, insurance, inspection dates
    ├──► [Activity Log] ──► filter by driver or vehicle
    ├──► [Reports] ──► generate on-demand / configure schedule
    └──► [Export] ──► select dataset + format + date range → download

DRIVER FLOW
───────────
[Driver Dashboard] ──► toggle Active ──► select vehicle
    └──► [Fuel Entry] ──► submit entry ──► view last 10 / edit / delete (< 24h)

ADMIN FLOW
──────────
[Admin Dashboard]
    ├──► User list ──► suspend / reactivate / delete
    ├──► Owner detail ──► view fleet / change plan / toggle features
    └──► Platform analytics
```

---

## Wireframe Specs

### Login (`index.html`)
- Layout: centered card on cream background, 420px max-width
- Fields: Email, Password
- Actions: "Se connecter" (primary green button), "Mot de passe oublié?" link
- Below form: "Pas de compte ? S'inscrire" link

### Registration (`register.html`)
- Layout: centered card, 480px max-width
- Fields: Nom de l'entreprise, Nom complet, Email, Mot de passe, Rôle (radio: Propriétaire / Chauffeur)
- Action: "Créer mon compte" button
- Post-submit: OTP verification step shown inline (6-digit code input + resend link)

### Owner Dashboard (`dashboard-owner.html`)
- Layout: fixed sidebar nav (left) + scrollable main area
- **Sidebar:** Logo, nav links (Tableau de bord, Véhicules, Maintenance, Journal, Rapports, Export), user name + logout
- **Top row — KPI cards (3):** Total dépenses flotte | Véhicules actifs | Chauffeurs actifs
- **Row 2 — Charts:** Bar chart (dépenses par véhicule) + Line chart (tendance mensuelle)
- **Row 3:** Consumption table (left) + Driver status list (right)
- **Row 4:** Alerts panel (red/orange badges) + Compliance deadlines (days remaining)
- **Row 5:** Donut chart (répartition dépenses) + Growth gauge + Operational gauge
- **Anomalies section:** Cards per anomalous vehicle with anomaly type label

### Driver Dashboard (`dashboard-driver.html`)
- Layout: single-column mobile card layout
- **Status toggle card:** Big toggle button (Activer / Désactiver ma mission) — green when active, showing current vehicle name
- **Vehicle selector modal:** opens on activate, lists assigned vehicles as selectable cards
- **Assigned vehicles section:** compact list cards (brand, model, plate)
- **Recent entries table:** last 10 entries (date, vehicle, km, litres, FCFA) — edit/delete icons on rows < 24h old

### Vehicle Management (`vehicles.html`)
- Layout: full-width table + "Ajouter un véhicule" button (top-right)
- Table columns: Nom | Marque / Modèle | Plaque | Carburant | Statut (badge) | Chauffeurs | Actions
- Status badges: Active (green) / En pause (orange) / Archivé (gray)
- Row actions: Edit | Pause/Resume | Archive | Manage Drivers
- Archived vehicles: collapsible section at bottom of page with "Restaurer" button
- Add/Edit: slide-in drawer form (not a separate page)

### Fuel Entry (`fuel-entry.html`)
- Layout: two sections — form (top) + history table (bottom)
- Form: Vehicle selector (dropdown of assigned vehicles) | Date | Odometer (km) | Quantity (L) | Amount (FCFA)
- Computed preview: shows estimated consumption after odometer entry
- History table: last 10 entries with edit/delete icons (locked icon after 24h)

### Maintenance (`maintenance.html`)
- Layout: vehicle selector dropdown → form below
- Form fields: Dernier vidange (km) | Expiration assurance (date) | Expiration visite technique (date)
- Alert preview: shows current alert status for each field inline
- Save button per section

### Activity Log (`activity.html`)
- Layout: filter bar (top) + table (below)
- Filters: Chauffeur dropdown | Véhicule dropdown | Clear filters button
- Table columns: Date/Heure | Chauffeur | Véhicule | Action (CREATE/UPDATE/DELETE badge) | Détails (expandable row)
- Expandable row: shows data_before → data_after diff for UPDATE; full snapshot for DELETE

### AI Reports (`reports.html`)
- Layout: two cards side by side (desktop) / stacked (mobile)
- **Card 1 — On-demand:** "Générer un rapport" button + loading spinner + last generated info. Locked state for Starter plan.
- **Card 2 — Scheduled:** Toggle (enable/disable) + frequency selector (Hebdomadaire / Mensuel) + last sent status. Locked for Pro plan (Business only).

### Export (`export.html`)
- Layout: single centered form card
- Fields: Dataset (radio buttons) | Format (PDF / Excel toggle) | Date range (from/to)
- "Exporter" button → triggers download
- Locked state for Starter plan with upgrade prompt card

### Admin Dashboard (`admin-dashboard.html`)
- Layout: tabs (Utilisateurs | Analytiques)
- **Utilisateurs tab:** Search bar + paginated table (Name | Email | Role | Plan badge | Status | Actions)
- Row actions: Voir la flotte | Changer le plan | Suspendre / Réactiver | Supprimer
- **Analytiques tab:** KPI cards (total owners, drivers, vehicles, entries) + Plan distribution bar + Registration trend line chart

---

## Navigation Structure

**Owner sidebar:**
- Tableau de bord
- Véhicules
- Maintenance
- Journal d'activité
- Rapports IA *(Pro+)*
- Export *(Pro+)*
- Mon compte / Déconnexion

**Driver (top bar — mobile):**
- Mon tableau de bord
- Saisie carburant
- Mon compte / Déconnexion

**Locked nav items** (Starter plan) show a lock icon and redirect to upgrade prompt on click.

---
*Completed: 2026-04-06*
