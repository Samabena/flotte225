# 2. Database Design

## Multi-Tenancy Strategy
Owner-scoped row-level isolation. No `tenants` table — each OWNER acts as their own tenant. Every data table has an `owner_id` or `driver_id` column that scopes queries. SUPER_ADMIN bypasses these filters.

## Soft Deletes
Vehicles only — via `status` field (`active` / `paused` / `archived`) + `archived_at` timestamp. All other records use hard delete (with activity logs capturing the data snapshot before deletion).

## Primary Keys
SERIAL integers across all tables (consistent with existing SQLAlchemy codebase).

---

## Entity Relationship Overview

```
users ──────────────────────────────────────────────────────────┐
  │                                                              │
  ├──[owner]──► vehicles ──► vehicle_drivers ◄──[driver]── users│
  │                  │                                          │
  │                  ├──► fuel_entries ◄──[driver]──────── users│
  │                  ├──► maintenance                           │
  │                  └──► activity_logs                         │
  │                                                              │
  ├──[owner]──► webhook_state                                   │
  ├──[owner]──► owner_subscriptions ──► subscription_plans      │
  ├──[owner]──► report_schedules                                │
  └──[user]───► otp_codes                                       │
```

---

## Table Definitions

### `users`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| company_name | VARCHAR(255) | NULLABLE | OWNER only; NULL for DRIVER rows |
| full_name | VARCHAR(255) | NOT NULL | |
| email | VARCHAR(255) | UNIQUE, NULLABLE | OWNER/SUPER_ADMIN login identifier; NULL for DRIVER rows |
| username | VARCHAR(100) | UNIQUE, NULLABLE | DRIVER login identifier; NULL for OWNER/SUPER_ADMIN rows |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt |
| role | VARCHAR(20) | NOT NULL | `OWNER` / `DRIVER` / `SUPER_ADMIN` |
| owner_id | INT | FK → users.id, NULLABLE | DRIVER only: the OWNER who created this account |
| is_active | BOOLEAN | NOT NULL, DEFAULT false | OWNER: false until email verified; DRIVER: true on creation |
| is_suspended | BOOLEAN | NOT NULL, DEFAULT false | Set by SUPER_ADMIN |
| is_disabled | BOOLEAN | NOT NULL, DEFAULT false | DRIVER only: set by their OWNER to block login |
| driving_status | BOOLEAN | NOT NULL, DEFAULT false | DRIVER: currently on mission |
| active_vehicle_id | INT | FK → vehicles.id, NULLABLE | DRIVER: current vehicle |
| whatsapp_number | VARCHAR(20) | NULLABLE | OWNER: for WA notifications |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

> **Added in feature: Owner-Managed Driver Access Control** — 2026-04-19
> `username` and `owner_id` columns support username-based login and owner-scoped driver isolation.
> `is_disabled` allows owners to block driver login without deleting the account.
> CONSTRAINT: a row must have either `email` OR `username` set, never both.

---

### `otp_codes`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| user_id | INT | FK → users.id, NOT NULL | |
| code | VARCHAR(6) | NOT NULL | 6-digit code |
| purpose | VARCHAR(20) | NOT NULL | `EMAIL_VERIFY` / `PASSWORD_RESET` |
| expires_at | TIMESTAMPTZ | NOT NULL | now() + 15 minutes |
| used_at | TIMESTAMPTZ | NULLABLE | Set on first use — then invalid |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

---

### `vehicles`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| owner_id | INT | FK → users.id, NOT NULL | Data isolation key |
| name | VARCHAR(255) | NOT NULL | Free label |
| brand | VARCHAR(100) | NOT NULL | |
| model | VARCHAR(100) | NOT NULL | |
| year | INT | NULLABLE | |
| license_plate | VARCHAR(50) | UNIQUE, NOT NULL | |
| vin | VARCHAR(50) | NULLABLE | |
| fuel_type | VARCHAR(20) | NOT NULL | `Essence` / `Diesel` / `GPL` |
| initial_mileage | INT | NOT NULL | Starting odometer |
| status | VARCHAR(20) | NOT NULL, DEFAULT `active` | `active` / `paused` / `archived` |
| archived_at | TIMESTAMPTZ | NULLABLE | Soft delete timestamp |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

---

### `vehicle_drivers`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| vehicle_id | INT | FK → vehicles.id, NOT NULL | |
| driver_id | INT | FK → users.id, NOT NULL | |
| assigned_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| | | UNIQUE(vehicle_id, driver_id) | No duplicate assignments |

---

### `fuel_entries`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| vehicle_id | INT | FK → vehicles.id, NOT NULL | |
| driver_id | INT | FK → users.id, NOT NULL | |
| date | DATE | NOT NULL | Date of refueling |
| odometer_km | INT | NOT NULL | Current reading |
| quantity_litres | DECIMAL(8,2) | NOT NULL | |
| amount_fcfa | DECIMAL(10,2) | NOT NULL | |
| distance_km | INT | NULLABLE | Computed: current − previous odometer |
| consumption_per_100km | DECIMAL(6,2) | NULLABLE | Computed: (litres ÷ distance) × 100 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 24h edit window starts here |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

---

### `maintenance`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| vehicle_id | INT | FK → vehicles.id, UNIQUE, NOT NULL | One record per vehicle |
| last_oil_change_km | INT | NULLABLE | Odometer at last oil change |
| insurance_expiry | DATE | NULLABLE | |
| inspection_expiry | DATE | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

---

### `activity_logs`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| owner_id | INT | FK → users.id, NOT NULL | Fleet owner (for filtering) |
| driver_id | INT | FK → users.id, NOT NULL | Who performed the action |
| vehicle_id | INT | FK → vehicles.id, NOT NULL | |
| fuel_entry_id | INT | FK → fuel_entries.id, NULLABLE | Null if entry was deleted |
| action | VARCHAR(20) | NOT NULL | `CREATE` / `UPDATE` / `DELETE` |
| data_before | JSONB | NULLABLE | Null for CREATE |
| data_after | JSONB | NULLABLE | Null for DELETE |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

---

### `webhook_state`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| owner_id | INT | FK → users.id, UNIQUE, NOT NULL | One record per owner |
| last_sent_at | TIMESTAMPTZ | NULLABLE | |
| last_status_code | INT | NULLABLE | HTTP response code |
| last_payload_summary | JSONB | NULLABLE | Summary of last sent payload |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

---

### `subscription_plans`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| name | VARCHAR(50) | UNIQUE, NOT NULL | `starter` / `pro` / `business` |
| display_name | VARCHAR(100) | NOT NULL | e.g. "Plan Pro" |
| price_fcfa | INT | NOT NULL, DEFAULT 0 | Monthly price |
| max_vehicles | INT | NULLABLE | null = unlimited |
| max_drivers | INT | NULLABLE | null = unlimited |
| max_ai_reports_month | INT | NULLABLE | null = unlimited, 0 = none |
| features | JSONB | NOT NULL | Feature flags map |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

---

### `owner_subscriptions`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| owner_id | INT | FK → users.id, UNIQUE, NOT NULL | One plan per owner |
| plan_id | INT | FK → subscription_plans.id, NOT NULL | |
| feature_overrides | JSONB | NULLABLE | Per-owner overrides by SUPER_ADMIN |
| assigned_by | INT | FK → users.id, NULLABLE | SUPER_ADMIN who assigned |
| assigned_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

---

### `report_schedules`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | SERIAL | PK | |
| owner_id | INT | FK → users.id, UNIQUE, NOT NULL | One config per owner |
| enabled | BOOLEAN | NOT NULL, DEFAULT false | |
| frequency | VARCHAR(20) | NULLABLE | `weekly` / `monthly` |
| last_sent_at | TIMESTAMPTZ | NULLABLE | |
| last_status | VARCHAR(20) | NULLABLE | `sent` / `failed` |
| ai_reports_used_month | INT | NOT NULL, DEFAULT 0 | Pro plan monthly counter |
| usage_reset_at | DATE | NULLABLE | Date counter was last reset |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

---

## Key Indexes

| Index | Columns | Reason |
|---|---|---|
| idx_users_email | `users(email)` | Login lookup |
| idx_vehicles_owner | `vehicles(owner_id, status)` | Owner dashboard queries |
| idx_vehicles_plate | `vehicles(license_plate)` | Duplicate plate check |
| idx_fuel_vehicle_date | `fuel_entries(vehicle_id, date DESC)` | Odometer validation + history |
| idx_fuel_driver | `fuel_entries(driver_id, created_at DESC)` | Driver history (last 10) |
| idx_activity_owner | `activity_logs(owner_id, created_at DESC)` | Audit log pagination |
| idx_activity_driver | `activity_logs(driver_id)` | Log filter by driver |
| idx_activity_vehicle | `activity_logs(vehicle_id)` | Log filter by vehicle |
| idx_vd_driver | `vehicle_drivers(driver_id)` | Driver's assigned vehicles |

---
*Completed: 2026-04-06*
