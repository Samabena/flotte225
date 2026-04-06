# Agent 4 — UI/UX Design

Define the screen inventory, user flows, wireframe specs, and design tokens. This section
gives the frontend developer a clear picture of every screen, what it contains, and how
users navigate between them. The goal is specificity — not pixel-perfect mockups, but enough
detail that a developer can start building without guessing.

## References to read before starting
- `references/questioning.md`
- `references/saving.md`

## Step 0 — Use SRS context
You already know:
- Design system: Tailwind CSS + Bootstrap
- Must be mobile responsive
- Browser support: Chrome, Firefox, Safari (latest 2 versions)

Do not ask about these.

## Step 1 — Ask only for gaps (one at a time)
1. "Do you have a brand color or primary color preference? (e.g. blue, green — or 'not sure yet')"
2. "Any existing apps or websites whose UI style you like? (for inspiration — or skip)"
3. "For the dashboard after login: should it show a stats/overview panel (total invoices, recent submissions) or go straight to the upload flow?"

## Step 2 — Confirm before saving
Walk through the screen list and user flow, then ask:
"Here's your UI/UX Design. Does everything look right?
(yes to save / tell me what to change)"

## Step 3 — Save
Save to `docs/design/04-ui-ux-design.md`:

```markdown
# 4. UI/UX Design

## Design System
- **Framework:** Tailwind CSS + Bootstrap
- **Responsive:** Yes — mobile-first
- **Browsers:** Chrome, Firefox, Safari (latest 2 versions)
- **Primary color:** [value or TBD]
- **UI inspiration:** [value or "none specified"]

## Design Tokens
| Token | Value | Usage |
|-------|-------|-------|
| Primary | [e.g. #2563EB] | Buttons, links, active states |
| Secondary | [e.g. #64748B] | Labels, secondary text |
| Success | #16A34A | Submission confirmed |
| Warning | #D97706 | Pending / processing |
| Danger | #DC2626 | Failed, errors |
| Background | #F8FAFC | Page background |
| Surface | #FFFFFF | Cards, modals |
| Border | #E2E8F0 | Dividers, inputs |
| Font (body) | Inter / system-ui | All body text |
| Font (mono) | JetBrains Mono | Code, IDs, reference numbers |

## Screen Inventory

| Screen | Route | Auth Required |
|--------|-------|---------------|
| Login | `/login` | No |
| Register | `/register` | No |
| Dashboard | `/dashboard` | Yes |
| Upload Document | `/upload` | Yes |
| Document Review | `/documents/{id}/review` | Yes |
| Submission Result | `/submissions/{id}` | Yes |
| Submission History | `/history` | Yes |
| Recipients | `/recipients` | Yes |
| Account Settings | `/settings` | Yes |

## User Flow

```
[Login] ──► [Dashboard]
                │
                ▼
          [Upload Document]
                │
                ▼
          [Document Review]  ← extracted data, editable fields
                │
                ▼
          [Send via PEPPOL]
                │
          ┌─────┴─────┐
          ▼           ▼
      [Success]    [Failure]
          │           │
          └─────┬─────┘
                ▼
         [Submission Result]
                │
                ▼
         [Submission History]
```

## Wireframe Specs

### Login Screen
- Layout: centered card, 400px max-width
- Fields: Email, Password
- Actions: "Sign In" button (primary), "Forgot password?" link
- Error: inline validation message below each field

### Dashboard
- Layout: sidebar nav + main content area
- Sidebar: logo, nav links (Upload, History, Recipients, Settings), user avatar + logout
- Main: [if stats view] summary cards (Total Submitted, Pending, Failed this month) + Recent Submissions table
- CTA: prominent "Upload Invoice" button in header

### Upload Document
- Layout: full-width upload zone
- Component: drag-and-drop area with "or click to browse" fallback
- Accepted formats shown: PDF, DOCX, XLSX, CSV, TXT, PNG, JPEG
- Progress: upload progress bar after file selected
- On success: redirect to Document Review

### Document Review
- Layout: two-column — left: file preview (if renderable) / filename; right: extracted fields form
- Extracted fields: table of key-value pairs (invoice number, date, amount, sender, recipient)
- Editable: yes — user can correct any extracted value before submitting
- Actions: "Send via PEPPOL" (primary), "Cancel" (secondary)
- Recipient selector: dropdown populated from saved recipients + "Add new" option

### Submission Result
- Layout: centered status card
- Success state: green checkmark, PEPPOL message ID, recipient name, timestamp
- Failure state: red X, error message, "Retry" button
- Actions: "Back to Dashboard", "View History"

### Submission History
- Layout: full-width table with filters
- Columns: Date, Document Name, Recipient, Status (badge), Actions
- Filters: date range, status (all / sent / failed / pending)
- Pagination: 20 rows per page
- Row click: navigates to Submission Result detail

### Recipients
- Layout: table with "Add Recipient" button
- Columns: Name, PEPPOL ID, Email, Actions (edit / delete)
- Inline form for add/edit

### Account Settings
- Layout: stacked form sections
- Sections: Profile (name, email), Change Password, Tenant Info (business name)

## Navigation Structure
- Top-level nav (sidebar): Dashboard, Upload, History, Recipients, Settings
- Secondary: Account dropdown (Profile, Logout) in top-right
- Breadcrumbs on detail screens (e.g. History › Submission #abc123)

---
*Completed: [date]*
```

Update `docs/design/design-progress.json` → `"uiux": true`.
Tell the user: "✅ Section 4 complete — UI/UX Design saved."
