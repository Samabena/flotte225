# 6. Security Design

## Authentication & JWT Lifecycle

### Token Strategy

| Token | Lifetime | Storage | Notes |
|---|---|---|---|
| Access Token | 24 hours | `localStorage` (client) | Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Refresh Token | Not used | — | User re-logs in after expiry — simpler, matches SRS |

### JWT Claims
```json
{
  "sub": "1",
  "email": "owner@flotte225.ci",
  "role": "OWNER",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### Token Flow
1. User logs in → server validates credentials → issues signed JWT (HS256, `SECRET_KEY`)
2. Client stores token in `localStorage`, attaches to every request: `Authorization: Bearer <token>`
3. FastAPI dependency `get_current_user` validates signature + expiry + role on every protected route
4. On expiry (HTTP 401): client clears `localStorage` and redirects to login page

---

## Password Security

| Rule | Value |
|---|---|
| Hashing algorithm | bcrypt, minimum 10 rounds |
| Minimum length | 8 characters (enforced at Pydantic schema level) |
| Plaintext storage | Never — not stored, not logged |
| Reset mechanism | 6-digit OTP via email, 15-minute expiry, single-use |

---

## OTP Security

| Property | Value |
|---|---|
| Length | 6 digits |
| Expiry | 15 minutes from generation |
| Invalidation | Immediately on first use (`used_at` timestamp set) |
| Enumeration protection | Password reset always returns same response regardless of email existence |
| Purposes | `EMAIL_VERIFY` (registration) / `PASSWORD_RESET` |

---

## Data Isolation

Owner-scoped row-level isolation enforced at two layers:

**Layer 1 — JWT Middleware:**
`get_current_user` dependency injects `current_user` (id, role) into every request context.

**Layer 2 — Service Layer:**
Every query on owner-scoped data includes an explicit owner filter:
```python
# Example — vehicle query always scoped to owner
db.query(Vehicle).filter(
    Vehicle.owner_id == current_user.id,
    Vehicle.status != "archived"
)
```
Cross-owner data leakage is structurally impossible when this pattern is followed consistently.

**SUPER_ADMIN bypass:**
Admin endpoints use a separate `get_admin_user` dependency that verifies `role == SUPER_ADMIN` and does not apply owner scoping.

---

## Role-Based Access Control (RBAC)

Enforced via FastAPI dependency injection — three dependency types:

```python
get_current_user        # Any authenticated user
get_current_owner       # OWNER role only
get_current_driver      # DRIVER role only
get_admin_user          # SUPER_ADMIN role only
```

Plan enforcement runs as an additional dependency on gated endpoints:
```python
require_plan("pro")      # Blocks if owner plan is Starter
require_plan("business") # Blocks if owner plan is Starter or Pro
```

---

## Transport Security

| Control | Implementation |
|---|---|
| HTTPS | Enforced at Nginx reverse proxy — HTTP redirects to HTTPS |
| TLS | TLS 1.2 minimum, TLS 1.3 preferred |
| HSTS | `Strict-Transport-Security` header in production Nginx config |
| CORS | `CORS_ORIGINS` env var — restricted to known frontend domains only |

---

## API Security

| Control | Implementation |
|---|---|
| Input validation | Pydantic schemas enforce types, lengths, and value constraints on all inputs |
| SQL injection | SQLAlchemy ORM with parameterized queries — no raw SQL |
| XSS | No server-side HTML rendering — frontend is static, API returns JSON only |
| Rate limiting | Not implemented at launch — add Nginx `limit_req` if abuse is detected post-launch |
| Sensitive env vars | `SECRET_KEY`, `DATABASE_URL`, API keys — stored in `.env` files, never committed to git |

---

## Secrets Management

| Variable | Purpose | Where stored |
|---|---|---|
| `SECRET_KEY` | JWT signing key | `.env` / VPS env |
| `DATABASE_URL` | PostgreSQL connection | `.env` / VPS env |
| `SENDGRID_API_KEY` | Email delivery | `.env` / VPS env |
| `OPENROUTER_API_KEY` | AI reports | `.env` / VPS env |
| `WHATSAPP_TOKEN` | WhatsApp API | `.env` / VPS env |
| `WEBHOOK_URL` | External webhook | `.env` / VPS env |

`.env.example` committed to git with all keys listed but no values — serves as documentation.

---

## Compliance

No formal GDPR or SOC2 certification required at launch (market: Côte d'Ivoire). Best-practice controls applied regardless:

| Control | Status |
|---|---|
| Data minimization | Only collect data required for fleet management |
| Audit trail | All driver actions logged in `activity_logs` |
| Right to deletion | SUPER_ADMIN can permanently delete accounts + cascade data |
| Secrets out of code | Enforced via `.env` pattern + `.gitignore` |
| Breach response | Document incident procedure before production go-live |

---
*Completed: 2026-04-06*
