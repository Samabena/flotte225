# Agent 6 — Security Design

Define how the system protects user data, enforces tenant isolation, and meets compliance
requirements. Security decisions made here directly affect the database schema, API middleware,
and infrastructure config — so this section formalizes what the SRS specified at a high level
into concrete implementation rules.

## References to read before starting
- `references/questioning.md`
- `references/saving.md`

## Step 0 — Use SRS context
You already know from NF-02 and NF-06:
- Passwords: bcrypt hashing
- Transport: HTTPS enforced, TLS
- Auth: JWT tokens with expiry
- Storage: at-rest encryption
- Compliance: GDPR, SOC2, PEPPOL

Do not ask about these — they are confirmed requirements.

## Step 1 — Ask only for gaps (one at a time)
1. "How long should access tokens stay valid? (Common choices: 15 minutes, 1 hour, 24 hours — shorter is more secure)"
2. "Do you want **refresh tokens** (user stays logged in silently, token renews in background) or just **re-login on expiry** (simpler)?"
3. "For GDPR: do you need a **right-to-erasure** flow (user can request all their data be deleted) at launch, or is that a post-MVP feature?"

## Step 2 — Confirm before saving
Present all security decisions and ask:
"Here's your Security Design. Does everything look right?
(yes to save / tell me what to change)"

## Step 3 — Save
Save to `docs/design/06-security-design.md`:

```markdown
# 6. Security Design

## Authentication & JWT Lifecycle

### Token Strategy
| Token | Lifetime | Storage | Notes |
|-------|----------|---------|-------|
| Access Token | [value, e.g. 1 hour] | Memory / HttpOnly cookie | Short-lived, sent with every request |
| Refresh Token | [e.g. 7 days / N/A] | HttpOnly cookie (if used) | Silent renewal / not used |

### JWT Claims
```json
{
  "sub": "user_uuid",
  "tenant_id": "tenant_uuid",
  "role": "owner",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### Token Flow
1. User logs in → server issues access token (+ refresh token if enabled)
2. Client sends `Authorization: Bearer <token>` on every protected request
3. FastAPI middleware validates token signature, expiry, and tenant_id
4. On expiry: [refresh silently / redirect to login]

---

## Password Security

- **Hashing:** bcrypt with cost factor 12 (slows brute-force attacks)
- **Minimum length:** 8 characters
- **No plaintext storage:** passwords are never logged or stored
- **Reset flow:** time-limited reset token sent via email (expires in 1 hour)

---

## Tenant Data Isolation

Every database query that touches tenant data must include a `tenant_id` filter.
This is enforced at two levels:

1. **JWT middleware:** injects `tenant_id` from the token into request context
2. **Service layer:** all queries include `WHERE tenant_id = :current_tenant_id`

This prevents any cross-tenant data leakage even if a bug exists at the route level.
Audited via the `audit_logs` table.

---

## Transport Security

- **HTTPS:** enforced at the reverse proxy (Nginx) — HTTP redirects to HTTPS
- **TLS:** TLS 1.2 minimum, TLS 1.3 preferred
- **HSTS:** `Strict-Transport-Security` header enabled in production
- **CORS:** restricted to known frontend origins only

---

## Data at Rest

- **Database:** PostgreSQL at-rest encryption via [cloud provider disk encryption / pgcrypto for sensitive fields]
- **File storage:** uploaded documents encrypted at rest in storage layer
- **Environment secrets:** API keys, DB credentials stored in environment variables — never in code

---

## GDPR Compliance

| Control | Implementation |
|---------|---------------|
| Data minimization | Only collect data necessary for invoicing |
| Purpose limitation | Data used only for PEPPOL delivery and history |
| Retention policy | Documents and submissions retained for [e.g. 7 years] per accounting regulations |
| Right to access | Tenant can export all their data via account settings |
| Right to erasure | [At launch / Post-MVP] — soft-delete user + documents, anonymize audit logs |
| Data breach notification | Incident response procedure documented |

---

## SOC2 Relevant Controls

| Control | Implementation |
|---------|---------------|
| Access control | Role-based (owner / staff), JWT-enforced |
| Audit logging | All actions logged in `audit_logs` table |
| Availability | 99.9% uptime target, health check endpoints |
| Incident response | TBD — document procedure before go-live |
| Vendor management | A-Cube and SendGrid SOC2 compliance verified |

---

## API Security

- **Input validation:** Pydantic schemas enforce type + length on all inputs
- **SQL injection:** SQLAlchemy ORM with parameterized queries — no raw SQL
- **File uploads:** type validation (allowlist), size limit enforced
- **Rate limiting:** [if decided] — applied at Nginx or FastAPI middleware level

---
*Completed: [date]*
```

Update `docs/design/design-progress.json` → `"security": true`.
Tell the user: "✅ Section 6 complete — Security Design saved."
