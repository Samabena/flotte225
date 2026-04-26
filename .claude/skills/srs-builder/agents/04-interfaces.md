# Agent 4 — Interface Requirements

Capture the UI approach and all external system integrations. This section
defines the boundaries of the system — what it looks like and what it connects to.

## References to read before starting
- `references/questioning.md`
- `references/saving.md`
- `references/prd-reader.md`

## Step 0 — PRD check
Follow the prd-reader reference. Look for:
- Platform mentions (web, mobile, desktop)
- Design system or UI framework mentions
- Any listed integrations (Stripe, Auth0, SendGrid, etc.)
- Authentication method mentions
- Device or browser requirements

Show what you found:
```
📄 Found these interface details in your PRD:

- Platform:        [found or "not mentioned"]
- Design system:   [found or "not mentioned"]
- Integrations:    [found or "not mentioned"]
- Auth method:     [found or "not mentioned"]
- Device support:  [found or "not mentioned"]

I'll confirm each and ask about anything not mentioned.
```

## Step 1 — Ask only for missing info
Only ask questions the PRD did not answer.

1. "What type of interface will your product have?
   (Web App / Mobile App / Desktop / API Only / Web + Mobile)"

2. (If not API Only) "Any design system or component library?
   (Tailwind / Material UI / shadcn/ui / custom / TBD)"

3. (If not API Only) "Must the interface be mobile responsive? (yes / no)"

4. (If not API Only) "Which browsers or platforms must it support?"

5. "What third-party services will you integrate with?
   (e.g. Stripe, Auth0, SendGrid, Twilio, AWS S3 — or 'none')"

6. "How will users authenticate?
   (Email + Password / OAuth / Both / Magic Link / API Key)"

7. "Will your app consume any external APIs? (or 'none')"

8. "Any hardware interfaces? (cameras, printers, sensors — or press Enter to skip)"

## Step 2 — Confirm
Show summary and ask: "Does this look right? (yes / make changes)"

## Step 3 — Save
Save to `docs/srs/04-interface-requirements.md`:

```markdown
# 4. Interface Requirements

## User Interface
- **Type:** [value]
- **Design System:** [value]
- **Mobile Responsive:** [yes / no]
- **Supported Browsers/Platforms:** [value]

## Authentication
- **Method:** [value]

## Third-Party Integrations
| Service | Purpose |
|---------|---------|
| [name] | [what it's used for] |

## External APIs Consumed
[value or "None"]

## Hardware Interfaces
[value or "None"]

---
*Captured: [date] | Source: [PRD / User input / Mixed]*
```

Update `docs/srs/srs-progress.json` → `"interfaces": true`.
Tell the user: "✅ Section 4 complete — Interface Requirements saved."