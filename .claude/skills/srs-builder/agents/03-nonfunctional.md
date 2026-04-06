# Agent 3 — Non-Functional Requirements

Define HOW WELL the system must perform. These are the requirements most teams
skip — and the ones that cause production incidents later. They also become part
of the Definition of Done for every sprint in the backlog phase.

## References to read before starting
- `references/questioning.md`
- `references/saving.md`
- `references/prd-reader.md`

## Step 0 — PRD check
Follow the prd-reader reference. Look specifically for:
- Performance targets (load times, response times)
- Security requirements (compliance, encryption)
- Scale targets (expected users, traffic)
- Uptime or SLA mentions
- Compliance requirements (GDPR, HIPAA, SOC2, CCPA...)

Show what you found:
```
📄 Found these NFR hints in your PRD:

- Performance:   [found or "not mentioned"]
- Security:      [found or "not mentioned"]
- Scalability:   [found or "not mentioned"]
- Availability:  [found or "not mentioned"]
- Usability:     [found or "not mentioned"]
- Compliance:    [found or "not mentioned"]

I'll confirm each and fill in smart defaults for anything missing.
```

## Step 1 — Walk through each category

For each category, confirm the PRD value or offer a smart default.

**Performance**
Default: "Pages and API responses load in under 2 seconds on a standard connection."

**Security**
Suggest based on product type:
- Handles payments → "PCI-DSS compliant. All data encrypted in transit (TLS) and at rest."
- General SaaS → "Passwords hashed with bcrypt. HTTPS enforced. JWT tokens with expiry."

**Scalability**
Ask: "How many concurrent users do you expect at launch? And in 1 year?"
Form the requirement from their answer.

**Availability**
Default: "99.9% uptime (~8.7 hours downtime/year)."

**Usability**
Default: "Mobile responsive. Supports Chrome, Firefox, Safari — latest 2 versions."

**Compliance**
Ask: "Any regulatory requirements? (GDPR, HIPAA, SOC2, CCPA — or press Enter to skip)"

## Step 2 — Confirm
Show the full table and ask:
"Here are your Non-Functional Requirements. Look right?
(yes / make changes)"

## Step 3 — Save
Save to `docs/srs/03-non-functional-requirements.md`:

```markdown
# 3. Non-Functional Requirements

How well the system must perform.
These apply as the **Definition of Done** for every sprint.

| ID | Category | Requirement |
|----|----------|-------------|
| NF-01 | Performance | [value] |
| NF-02 | Security | [value] |
| NF-03 | Scalability | [value] |
| NF-04 | Availability | [value] |
| NF-05 | Usability | [value] |
| NF-06 | Compliance | [value or "None specified"] |

---
*[N] NFRs — [date] | Source: [PRD / User input / Mixed]*
```

Update `docs/srs/srs-progress.json` → `"nonfunctional": true`.
Tell the user: "✅ Section 3 complete — Non-Functional Requirements saved."