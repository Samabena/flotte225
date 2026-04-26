# Agent 1 — Product Discovery

Collect the product overview for Section 1 of the SRS. This section sets the
context for everything that follows — later agents will reference the product
name, primary user, and product type established here.

## References to read before starting
- `references/questioning.md`
- `references/saving.md`
- `references/prd-reader.md`

## Step 0 — PRD check
Follow the prd-reader reference. If `docs/prd.md` exists, extract and show:
```
📄 Found your PRD. Here's what I extracted:

- Product name:     [extracted or "not found"]
- What it does:     [extracted or "not found"]
- Primary user:     [extracted or "not found"]
- Problem solved:   [extracted or "not found"]
- Product type:     [extracted or "not found"]
- Tech stack:       [extracted or "not found"]
- Constraints:      [extracted or "not found"]
- Success metric:   [extracted or "not found"]

✅ I'll use what was found and only ask about the gaps.
```

## Step 1 — Ask only for missing info
Only ask questions not answered by the PRD. Always confirm PRD values before using them.

1. "What is the **name** of your product?"
2. "In **one sentence**, what does [product name] do?"
3. "Who is the **primary user**? (e.g. 'freelance designer', 'small business owner')"
4. "What **problem** does [product name] solve for [user]?"
5. "What **type of product** is this? (web app / mobile app / SaaS / API / desktop)"
6. "What **tech stack** are you planning? (or 'TBD')"
7. "Any **known constraints**? (deadline, team size, budget, compliance) — press Enter to skip."
8. "What does **success** look like in 3–6 months?"

## Step 2 — Confirm before saving
Show all collected values and ask:
"Here's your Product Overview. Does everything look right?
(yes to save / tell me what to change)"

## Step 3 — Save
Save to `docs/srs/01-product-overview.md`:

```markdown
# 1. Product Overview

## Product Name
[value]

## What It Does
[value]

## Primary User
[value]

## Problem Being Solved
[value]

## Product Type
[value]

## Tech Stack
[value]

## Known Constraints
[value or "None specified"]

## Definition of Success
[value]

---
*Completed: [date] | Source: [PRD / User input / Mixed]*
```

Update `docs/srs/srs-progress.json` → `"discovery": true`.
Tell the user: "✅ Section 1 complete — Product Overview saved."