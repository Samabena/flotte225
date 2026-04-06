# Agent 5 — Integration Design

Define how the system connects to external services. The two integrations — A-Cube API
(PEPPOL delivery) and SendGrid (email notifications) — are the core of the product's value.
Getting the flows, error handling, and retry strategy right here prevents hard-to-debug
production failures later.

## References to read before starting
- `references/questioning.md`
- `references/saving.md`

## Step 0 — Use SRS context
You already know:
- A-Cube API: PEPPOL network delivery (F-04)
- SendGrid: email notifications on submission outcome (F-09)
- PEPPOL transformation: extract → map → validate → inject (F-03, F-04)

Do not ask what integrations are needed.

## Step 1 — Ask only for gaps (one at a time)
1. "Do you have A-Cube API sandbox credentials yet, or are we designing based on their docs for now?"
2. "Should the PEPPOL transformation and submission be **synchronous** (the user waits on the page for a result) or **asynchronous** (submitted to a background job, user sees 'processing' then gets updated)? Async is more resilient — I'd recommend it."
3. "What should trigger the email notification — when the document is **sent** to PEPPOL, when **delivery is confirmed**, or **both**?"
4. "What should happen on a failed submission — should it **auto-retry** (e.g. 3 times with backoff), or just fail and let the user retry manually?"

## Step 2 — Confirm before saving
Present the full integration flows and ask:
"Here's your Integration Design. Does everything look right?
(yes to save / tell me what to change)"

## Step 3 — Save
Save to `docs/design/05-integration-design.md`:

```markdown
# 5. Integration Design

## Overview
The system has two external integrations:
1. **A-Cube API** — PEPPOL network delivery of transformed invoices
2. **SendGrid** — Email notifications on submission outcomes

---

## A-Cube API Integration (PEPPOL Delivery)

### Credentials
- Environment: [Sandbox / Production]
- Credentials status: [Available / Pending]
- Auth method: [API Key / OAuth — per A-Cube docs]

### PEPPOL Transformation Pipeline

The full pipeline from uploaded file to PEPPOL delivery:

```
1. UPLOAD
   User uploads file (PDF, DOCX, XLSX, CSV, TXT, PNG, JPEG)
   → stored in object storage / local filesystem
   → document.status = "uploaded"

2. EXTRACTION
   Parse file content using format-specific extractor:
   - PDF/images → OCR or PDF parser
   - DOCX/XLSX/CSV → structured data parser
   - TXT → pattern matching
   → extracted fields stored in document.extracted_data (JSONB)
   → document.status = "extracted"

3. USER REVIEW
   User verifies/corrects extracted fields in the UI
   → any corrections saved back to document.extracted_data

4. TRANSFORMATION
   Map extracted data fields → PEPPOL UBL 2.1 XML schema
   → validate against PEPPOL schema rules
   → transformed payload saved to document.peppol_payload_path
   → document.status = "transformed"

5. INJECTION (A-Cube API)
   POST transformed payload to A-Cube API endpoint
   → A-Cube routes to recipient via PEPPOL network
   → receive peppol_message_id in response
   → submission.status = "sent"

6. DELIVERY CONFIRMATION (optional polling)
   GET submission status from A-Cube using peppol_message_id
   → on confirmed: submission.status = "delivered"
   → on failed: submission.status = "failed", error stored
```

### Async vs Sync
Processing mode: [Synchronous / Asynchronous]

[If async:]
- Upload and extraction happen in the background after file upload
- User is notified (page polling or websocket) when extraction is complete
- Transformation and injection run as background tasks after user confirms review
- Use a task queue (e.g. Celery + Redis, or FastAPI BackgroundTasks for simple cases)

### A-Cube API Calls

| Call | Method | Endpoint | Purpose |
|------|--------|----------|---------|
| Submit document | POST | `/api/send` | Inject PEPPOL document |
| Check status | GET | `/api/status/{message_id}` | Poll delivery status |

*(Exact endpoints subject to A-Cube API documentation)*

### Error Handling & Retry Strategy
- **Retry policy:** [Auto-retry 3x with exponential backoff / Manual retry only]
- **Backoff:** 5s, 30s, 5min
- **On permanent failure:** submission.status = "failed", error_message stored, user notified
- **Idempotency:** use document.id as idempotency key to prevent duplicate submissions

---

## SendGrid Integration (Email Notifications)

### Credentials
- Service: SendGrid
- Auth: API Key (stored in environment variable `SENDGRID_API_KEY`)
- From address: `noreply@[product-domain]`

### Trigger Events

| Event | Trigger | Email to |
|-------|---------|----------|
| Submission sent | submission.status → "sent" | Tenant owner |
| Delivery confirmed | submission.status → "delivered" | Tenant owner |
| Submission failed | submission.status → "failed" | Tenant owner |

*(Active triggers: [as decided by user])*

### Email Templates

**Submission Sent:**
- Subject: `Invoice submitted to PEPPOL — [document filename]`
- Body: recipient name, PEPPOL message ID, timestamp, link to submission detail

**Delivery Confirmed:**
- Subject: `Invoice delivered — [document filename]`
- Body: confirmation message, delivery timestamp, link to submission detail

**Submission Failed:**
- Subject: `Invoice submission failed — [document filename]`
- Body: error summary, link to retry, support contact

### SendGrid API Call
```python
POST https://api.sendgrid.com/v3/mail/send
Authorization: Bearer {SENDGRID_API_KEY}
Body: { to, from, subject, html_content }
```

### Error Handling
- Log SendGrid failures but do not block the main submission flow
- Email delivery failure is non-critical — the PEPPOL delivery has already succeeded
- Retry email once after 60s; if still failing, log and move on

---
*Completed: [date]*
```

Update `docs/design/design-progress.json` → `"integrations": true`.
Tell the user: "✅ Section 5 complete — Integration Design saved."
