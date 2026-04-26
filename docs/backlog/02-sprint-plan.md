# Sprint Plan

- **Sprint Length:** 2 weeks
- **Sprint Capacity:** 20 story points
- **Total Estimated Stories:** 49
- **Total Story Points:** 159
- **Sprints to Full Product:** 9 sprints (18 weeks)

---

## 🏃 Sprint 1 — Foundation: Authentication & Plan Infrastructure
*20 / 20 story points*
*Goal: Users can register, verify their email, log in to their role dashboard, reset their password, and the plan enforcement layer is in place.*

| ID | Story | Priority | Points |
|----|-------|----------|--------|
| US-001 | Register an account | Must Have | 3 |
| US-002 | Email verification via OTP | Must Have | 3 |
| US-003 | Login & role-based redirect | Must Have | 2 |
| US-004 | Password reset via OTP | Must Have | 3 |
| US-042 | Super admin seed script | Must Have | 2 |
| US-043 | Default Starter plan on registration | Must Have | 2 |
| US-044 | Enforce plan limits at API level | Must Have | 5 |

---

## 🏃 Sprint 2 — Vehicle Management
*18 / 20 story points*
*Goal: Owners can fully manage their fleet (create, edit, pause, archive) and assign drivers. Drivers can see their assigned vehicles and toggle driving status.*

| ID | Story | Priority | Points |
|----|-------|----------|--------|
| US-005 | Register a vehicle | Must Have | 3 |
| US-006 | Edit a vehicle | Must Have | 2 |
| US-007 | Pause and resume a vehicle | Should Have | 2 |
| US-008 | Archive a vehicle (soft delete) | Must Have | 3 |
| US-009 | Assign/remove drivers from a vehicle | Must Have | 3 |
| US-022 | Driver views assigned vehicles | Must Have | 2 |
| US-023 | Toggle driving status | Must Have | 3 |

---

## 🏃 Sprint 3 — Fuel Entry & Audit Log
*17 / 20 story points*
*Goal: Drivers can submit, edit, and delete fuel entries. Owners can view all fleet entries. Every action is automatically recorded in the audit log.*

| ID | Story | Priority | Points |
|----|-------|----------|--------|
| US-010 | Submit a fuel entry | Must Have | 5 |
| US-011 | View my fuel entry history | Must Have | 2 |
| US-012 | Edit a fuel entry (within 24h) | Must Have | 3 |
| US-013 | Delete a fuel entry (within 24h) | Must Have | 2 |
| US-014 | Owner views fleet fuel entries | Must Have | 2 |
| US-024 | Automatic activity logging | Must Have | 3 |

---

## 🏃 Sprint 4 — Maintenance & Alert Engine
*17 / 20 story points*
*Goal: Owners can record maintenance data. The alert engine fires compliance alerts (insurance, inspection, oil change) and detects consumption and cost anomalies.*

| ID | Story | Priority | Points |
|----|-------|----------|--------|
| US-015 | Manage maintenance records | Must Have | 3 |
| US-016 | Oil change tracking by mileage | Must Have | 3 |
| US-026 | Maintenance & compliance alerts | Must Have | 5 |
| US-027 | Abnormal consumption detection | Should Have | 3 |
| US-028 | Monthly cost spike detection | Should Have | 3 |

---

## 🏃 Sprint 5 — Owner Dashboard
*17 / 20 story points*
*Goal: The owner dashboard is fully operational — financial charts, consumption table, driver status panel, alerts section, and filterable activity log.*

| ID | Story | Priority | Points |
|----|-------|----------|--------|
| US-017 | Fleet financial summary & charts | Must Have | 5 |
| US-018 | Fleet consumption indicators | Must Have | 3 |
| US-019 | Driver status panel | Must Have | 2 |
| US-020 | Alerts, anomalies & compliance on dashboard | Must Have | 5 |
| US-025 | Filter activity log | Should Have | 2 |

---

## 🏃 Sprint 6 — Super Admin & Subscription UI
*20 / 20 story points*
*Goal: Super admin can manage all users and plans. Owners see their plan, usage, upgrade prompts. Dashboard visualizations are complete.*

| ID | Story | Priority | Points |
|----|-------|----------|--------|
| US-021 | Dashboard visualizations (donut, gauges) | Should Have | 3 |
| US-036 | View & search all users | Must Have | 3 |
| US-037 | Suspend & reactivate a user | Must Have | 2 |
| US-038 | Permanently delete a user | Must Have | 2 |
| US-039 | View any owner's fleet (admin) | Must Have | 2 |
| US-040 | Manage subscription plans per owner | Must Have | 3 |
| US-045 | Upgrade prompt for locked features | Must Have | 3 |
| US-046 | Owner views current plan & usage | Should Have | 2 |

---

## 🏃 Sprint 7 — Export, WhatsApp & Admin Analytics
*20 / 20 story points*
*Goal: Owners can export data to PDF/Excel and receive WhatsApp alerts. Super admin has platform-wide analytics.*

| ID | Story | Priority | Points |
|----|-------|----------|--------|
| US-031 | Export fleet data (PDF / Excel) | Should Have | 8 |
| US-034 | Configure WhatsApp notifications | Should Have | 2 |
| US-035 | Receive WhatsApp fleet alerts | Should Have | 5 |
| US-041 | Platform-wide analytics (admin) | Should Have | 5 |

---

## 🏃 Sprint 8 — AI Reports & Webhook Integration
*20 / 20 story points*
*Goal: Owners can generate and schedule AI-powered fleet reports by email. Webhook integration delivers fleet summaries to external tools.*

| ID | Story | Priority | Points |
|----|-------|----------|--------|
| US-032 | Generate on-demand AI fleet report | Should Have | 8 |
| US-033 | Configure scheduled AI reports | Should Have | 5 |
| US-029 | Automated webhook dispatch | Could Have | 5 |
| US-030 | View last webhook status | Could Have | 2 |

---

## 🏃 Sprint 9 — Driver Access Management
*10 / 20 story points*
*Goal: Drivers can no longer self-register. Owners provision driver accounts via username/password, manage credentials (disable / reset / remove), and each owner's driver list is fully isolated from other owners.*

| ID | Story | Priority | Points |
|----|-------|----------|--------|
| US-047 | Owner creates driver account with username/password | Must Have | 5 |
| US-048 | Owner disables / removes / resets driver credentials | Must Have | 3 |
| US-049 | Owner views isolated driver list | Must Have | 2 |

**Dependencies:** Sprints 1–2 (auth foundation + vehicle management)

---

## 🔮 Future Backlog
Items deferred — not in current scope.

| ID | Story | Priority | Notes |
|----|-------|----------|-------|
| — | Payment gateway integration | Won't Have (yet) | Future phase — OI-01 |
| — | SMS OTP fallback | Won't Have (yet) | Future phase — OI-03 |
| — | Multi-language support | Won't Have (yet) | Not planned at launch — OI-04 |
| — | Mobile native app (iOS/Android) | Won't Have (yet) | Out of scope — OI-05 |

---

*Updated: 2026-04-19 | Source SRS: docs/FULL-SRS.md | 9 sprints × 2 weeks = 18 weeks*
