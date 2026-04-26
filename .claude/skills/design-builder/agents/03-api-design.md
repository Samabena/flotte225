# Agent 3 — API Design

Define all FastAPI endpoints — the contract between the frontend and backend. A well-defined
API spec before coding eliminates ambiguity and lets frontend and backend be developed in
parallel. This section covers routes, request/response shapes, auth middleware, and error formats.

## References to read before starting
- `references/questioning.md`
- `references/saving.md`

## Step 0 — Use SRS and database context
You already know:
- Auth: JWT tokens (from SRS NF-02)
- All features: F-01 through F-09 (9 functional requirements)
- Database tables: from Section 2 — tenants, users, documents, submissions, recipients, audit_logs

Do not ask about auth type or what features exist.

## Step 1 — Ask only for gaps (one at a time)
1. "Do you want API versioning? (e.g. all routes under `/api/v1/...` — recommended for future flexibility)"
2. "Any rate limiting requirements? (e.g. max uploads per minute) — or skip for now"
3. "FastAPI auto-generates Swagger docs at `/docs`. Do you want to keep that enabled in production, or only in dev/staging?"

## Step 2 — Confirm before saving
Present the full endpoint table grouped by domain and ask:
"Here's your API Design. Does everything look right?
(yes to save / tell me what to change)"

## Step 3 — Save
Save to `docs/design/03-api-design.md`:

```markdown
# 3. API Design

## Base URL
All endpoints are prefixed with `/api/v1` [or as decided].

## Authentication
Protected routes require a JWT Bearer token in the Authorization header:
`Authorization: Bearer <token>`

Tokens are issued on login and expire after [duration]. The auth middleware validates
the token and injects the current `tenant_id` and `user_id` into every request context,
ensuring tenant isolation at the route level.

## Standard Error Response
All errors return a consistent JSON shape:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": {}
  }
}
```

## Endpoints

### Auth
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| POST | `/api/v1/auth/register` | Register a new tenant + owner user | No |
| POST | `/api/v1/auth/login` | Login and receive JWT token | No |
| POST | `/api/v1/auth/logout` | Invalidate current token | Yes |
| GET | `/api/v1/auth/me` | Get current user profile | Yes |
| PATCH | `/api/v1/auth/me` | Update profile (name, email, password) | Yes |

### Documents
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| POST | `/api/v1/documents/upload` | Upload invoice or credit note file | Yes |
| GET | `/api/v1/documents` | List all documents for tenant (paginated) | Yes |
| GET | `/api/v1/documents/{id}` | Get document details + extracted data | Yes |
| GET | `/api/v1/documents/{id}/preview` | Preview extracted data before submission | Yes |
| DELETE | `/api/v1/documents/{id}` | Soft-delete a document | Yes |

### Submissions
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| POST | `/api/v1/submissions` | Submit a transformed document via PEPPOL | Yes |
| GET | `/api/v1/submissions` | List submission history for tenant (paginated) | Yes |
| GET | `/api/v1/submissions/{id}` | Get submission details + status | Yes |

### Recipients
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| GET | `/api/v1/recipients` | List all saved recipients for tenant | Yes |
| POST | `/api/v1/recipients` | Create a new recipient | Yes |
| PATCH | `/api/v1/recipients/{id}` | Update recipient details | Yes |
| DELETE | `/api/v1/recipients/{id}` | Soft-delete a recipient | Yes |

### Tenant
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| GET | `/api/v1/tenant` | Get current tenant info | Yes |
| PATCH | `/api/v1/tenant` | Update tenant settings | Yes |

## Request / Response Examples

### POST /api/v1/auth/login
**Request:**
```json
{ "email": "owner@company.com", "password": "secret123" }
```
**Response 200:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": { "id": "uuid", "email": "...", "role": "owner" }
}
```

### POST /api/v1/documents/upload
**Request:** `multipart/form-data` with `file` field
**Response 201:**
```json
{
  "id": "uuid",
  "original_filename": "invoice_001.pdf",
  "file_type": "pdf",
  "status": "uploaded",
  "created_at": "2026-03-16T10:00:00Z"
}
```

### POST /api/v1/submissions
**Request:**
```json
{
  "document_id": "uuid",
  "recipient_id": "uuid"
}
```
**Response 201:**
```json
{
  "id": "uuid",
  "status": "pending",
  "peppol_message_id": "...",
  "submitted_at": "2026-03-16T10:05:00Z"
}
```

## OpenAPI / Swagger
FastAPI automatically generates interactive docs at:
- `/docs` (Swagger UI) — [enabled in: dev + staging / all environments]
- `/redoc` (ReDoc) — [enabled in: dev + staging / all environments]

---
*Completed: [date]*
```

Update `docs/design/design-progress.json` → `"api": true`.
Tell the user: "✅ Section 3 complete — API Design saved."
