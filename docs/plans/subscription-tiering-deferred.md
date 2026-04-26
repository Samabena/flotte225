# Plan: Subscription Tiering — Deferred

**Decision date:** 2026-04-26  
**Status:** DEFERRED — all owners have equal (Business-level) access until re-enabled

---

## Context

Subscription tiering (Starter / Pro / Business) was fully designed and implemented in Sprint 6 (US-043–046). After review, the decision was made to remove all privilege enforcement for now so every owner has the same unlimited access while the product is in early traction.

The database models, plan seeding, and admin assignment endpoints are **kept intact** — only the enforcement layer was disabled.

---

## What was removed

| Location | What was disabled |
|---|---|
| `backend/app/core/deps.py` | `require_plan()` now returns `get_current_owner` — no plan check |
| `backend/app/services/vehicle_service.py` | `_check_plan_vehicle_limit()` removed — no vehicle cap |
| `backend/app/services/driver_mgmt_service.py` | `_check_plan_driver_limit()` removed — no driver cap |
| `backend/app/api/v1/endpoints/fuel.py` | Starter 20-entry activity log cap removed |
| `backend/app/api/v1/endpoints/export.py` | `require_plan("pro", "business")` replaced by `get_current_owner` — export open to all |

## What was kept

- `SubscriptionPlan` and `OwnerSubscription` DB models & migrations
- Plan seeding in `scripts/seed.py` (Starter / Pro / Business definitions)
- Auto-assignment of Starter plan on owner registration (`auth_service.py`)
- Admin plan assignment endpoint (`PUT /admin/users/{id}/plan`, US-040)
- Owner plan-view endpoint (`GET /subscription/my-plan`, US-046)

---

## Re-implementation plan

When tiering is re-enabled, restore enforcement in this order:

1. **`deps.py`** — restore `require_plan()` with full DB query and 403 guard
2. **`vehicle_service.py`** — restore `_check_plan_vehicle_limit()` in `create_vehicle()` and `restore_vehicle()`
3. **`driver_mgmt_service.py`** — restore `_check_plan_driver_limit()` in `create_driver()`
4. **`fuel.py`** — restore Starter 20-entry cap on `GET /owner/activity-logs`
5. **`export.py`** — change `get_current_owner` back to `require_plan("pro", "business")`
6. **Frontend** — restore locked-feature UI for Starter users (upgrade prompts, plan comparison table — US-045)
7. **Payment gateway** — integrate actual billing so plan upgrades are self-serve

### Feature flags per plan (from original design)

| Feature | Starter | Pro | Business |
|---|---|---|---|
| Max vehicles | 2 | 15 | Unlimited |
| Max drivers | 3 | 20 | Unlimited |
| Export (PDF/Excel) | Locked | Yes | Yes |
| AI Reports | 0/month | 5/month | Unlimited |
| WhatsApp alerts | No | Yes | Yes |
| Webhooks | No | No | Yes |
| Activity log | Last 20 | 200 | 200 |
| Price (FCFA/month) | Free | 9,900 | 24,900 |
