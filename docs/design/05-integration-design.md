# 5. Integration Design

## Overview

Flotte225 connects to 4 external services:

| # | Service | Purpose |
|---|---|---|
| 1 | **SendGrid** | Email delivery — OTP codes, AI reports, exports |
| 2 | **OpenRouter** | LLM API — AI fleet report generation (French) |
| 3 | **Meta Cloud API** | WhatsApp Business — fleet alerts & daily summaries |
| 4 | **Webhook (generic HTTP)** | Push fleet summaries to external tools |

---

## 1. SendGrid (Email)

### Credentials
- Auth: API Key → `SENDGRID_API_KEY` environment variable
- From address: `noreply@flotte225.ci`
- Service: SendGrid REST API v3

### Trigger Events

| Event | Trigger | Recipient |
|---|---|---|
| Email verification OTP | User registers | Registering user |
| Password reset OTP | Forgot password request | Requesting user |
| AI report delivery | Report generated (on-demand or scheduled) | Fleet owner |
| Export file delivery | Export generated | Fleet owner |

### Email Templates (French)

| Template | Subject | Key Content |
|---|---|---|
| OTP verification | `Flotte225 — Votre code de vérification` | 6-digit code, expires in 15 min |
| Password reset | `Flotte225 — Réinitialisation de mot de passe` | 6-digit code, expires in 15 min |
| AI report | `Flotte225 — Votre rapport de flotte` | HTML report body + PDF attachment |
| Export | `Flotte225 — Votre export est prêt` | Download link or attachment |

### API Call
```python
POST https://api.sendgrid.com/v3/mail/send
Authorization: Bearer {SENDGRID_API_KEY}
Content-Type: application/json
Body: { to, from, subject, html_content, attachments? }
```

### Error Handling
- SendGrid failures are **non-blocking** — log the error, do not fail the parent operation
- Retry once after 30s on transient failures (HTTP 5xx)
- Permanent failures (4xx) are logged and surfaced as a status indicator in the UI where applicable

---

## 2. OpenRouter (AI Reports)

### Credentials
- Auth: API Key → `OPENROUTER_API_KEY` environment variable
- Model: configurable via `OPENROUTER_MODEL` (recommended: `mistralai/mistral-large` or `anthropic/claude-haiku` — evaluate for French writing quality vs. cost)

### Flow

```
OWNER clicks "Générer un rapport"
        │
        ▼
Backend collects fleet data snapshot:
  - All fuel entries (last 90 days)
  - Maintenance records + alert states
  - Driver activity summary
  - Current anomalies
        │
        ▼
Structured JSON prompt → OpenRouter API
  (system prompt in French, instructs LLM to write
   an easy-to-understand fleet analysis report)
        │
        ▼
LLM returns French natural-language report (HTML or Markdown)
        │
        ▼
Backend formats report → sends via SendGrid to owner email
        │
        ▼
UI shows: "Rapport envoyé à votre adresse email ✓"
```

### Prompt Structure
```
System: "Tu es un analyste de flotte automobile. Rédige un rapport
         clair et compréhensible en français pour un propriétaire
         de véhicules non-technicien. Utilise des phrases simples,
         des recommandations concrètes et évite le jargon."

User:   [Structured JSON: fleet_summary, vehicles, drivers, alerts, anomalies]
```

### API Call
```python
POST https://openrouter.ai/api/v1/chat/completions
Authorization: Bearer {OPENROUTER_API_KEY}
Body: {
  "model": "{OPENROUTER_MODEL}",
  "messages": [{"role": "system", ...}, {"role": "user", ...}],
  "max_tokens": 2000
}
```

### Error Handling
- Timeout: 90 seconds max per API call
- On failure: UI shows error message, no email sent, `report_schedules.last_status = "failed"`
- No auto-retry for on-demand (user retries manually)
- Scheduled reports: log failure + set `last_status = "failed"` — next scheduled run retries automatically

### Rate Limiting (Plan Enforcement)
- Pro plan: counter in `report_schedules.ai_reports_used_month` incremented on each successful generation
- Counter reset to 0 on the 1st of each month via APScheduler job

---

## 3. Meta Cloud API (WhatsApp Business)

### Credentials
- Auth: Bearer token → `WHATSAPP_TOKEN` environment variable
- API base URL: `WHATSAPP_API_URL` environment variable
- Requires: Meta Business account + verified WhatsApp Business number

### Trigger Events

| Event | Condition | Message Type |
|---|---|---|
| Critical alert | Insurance or inspection expired | Immediate alert |
| Performance anomaly | Consumption or cost spike detected | Immediate alert |
| Daily summary | Every 24h (same schedule as webhook) | Summary message |

### Message Flow

```
Alert engine detects critical event
        │
        ▼
Check: owner has whatsapp_number set? → No → skip silently
        │ Yes
        ▼
Check: WHATSAPP_TOKEN + WHATSAPP_API_URL configured? → No → skip silently
        │ Yes
        ▼
POST message to Meta Cloud API
        │
        ▼
Log response (success / failure)
```

### API Call
```python
POST {WHATSAPP_API_URL}/messages
Authorization: Bearer {WHATSAPP_TOKEN}
Body: {
  "messaging_product": "whatsapp",
  "to": "{owner.whatsapp_number}",
  "type": "text",
  "text": { "body": "🚗 Flotte225 — [message content in French]" }
}
```

### Error Handling
- WhatsApp failures are **non-blocking** — alert still recorded in DB regardless
- Log HTTP response code + error body
- No auto-retry — next scheduled run re-evaluates and sends if condition persists

---

## 4. Webhook (Generic HTTP)

### Configuration
- URL: `WEBHOOK_URL` environment variable (no UI config — system admin only)
- Interval: `WEBHOOK_INTERVAL_HOURS` (default: 24)
- If `WEBHOOK_URL` not set: silently disabled, no error raised

### Dispatch Flow

```
APScheduler fires every WEBHOOK_INTERVAL_HOURS
        │
        ▼
Collect delta since last send:
  - New alerts (type, severity, vehicle)
  - Driver activity log entries (CREATE/UPDATE/DELETE)
  - Period covered (last_sent_at → now)
        │
        ▼
POST JSON payload to WEBHOOK_URL
        │
        ▼
Update webhook_state: last_sent_at, last_status_code, last_payload_summary
```

### Payload Structure
```json
{
  "owner": { "name": "...", "email": "..." },
  "period": { "from": "...", "to": "..." },
  "alerts": {
    "total": 3,
    "critical": 1,
    "warning": 2,
    "breakdown": [{ "type": "insurance", "vehicle": "..." }]
  },
  "activity_delta": {
    "created": 5,
    "updated": 2,
    "deleted": 0
  }
}
```

### Error Handling
- On non-2xx response: log failure, store status code in `webhook_state`
- No auto-retry — next scheduled dispatch sends fresh delta
- Manual trigger available via `POST /api/v1/webhook/trigger`

---
*Completed: 2026-04-06*
