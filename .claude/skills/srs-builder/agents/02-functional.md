# Agent 2 — Functional Requirements

Build the functional requirements table — the definitive list of things the
system must DO. This becomes the input for user stories in the backlog phase,
so clarity and completeness here saves time later.

## References to read before starting
- `references/questioning.md`
- `references/moscow.md`
- `references/saving.md`
- `references/prd-reader.md`

## Step 0 — PRD check
Follow the prd-reader reference. If `docs/prd.md` exists, extract all features,
epics, and functional descriptions. Show them:
```
📄 Found these features in your PRD:

- [feature 1]
- [feature 2]
...

I'll use these as a starting point, suggest priorities, then flag anything missing.
```

## Step 1 — Process PRD features first (if any)
For each feature found in the PRD, follow the moscow reference to suggest a priority:

"**[F-XX] — [Feature]**
I'd suggest **[priority]** because [one sentence reason].
Does that work? (yes / change priority / modify description / remove)"

Assign IDs sequentially: F-01, F-02...

## Step 2 — Suggest missing features
Based on the product type from Section 1, suggest features that seem important
but weren't mentioned. Present as a numbered list:

"Based on your product type, I'd also expect these features.
They weren't in the PRD — want to include any?"

For each: "Include **[Feature]**? (yes / no / modify)"

## Step 3 — Custom features
Ask: "Any other features not covered yet?
(describe them one by one, or say 'done')"

## Step 4 — Review full table
Show the complete table and ask:
"Here's your full Functional Requirements table. Does everything look right?
(yes / make changes)"

## Step 5 — Save
Save to `docs/srs/02-functional-requirements.md`:

```markdown
# 2. Functional Requirements

What the system must **do**.
Each requirement below becomes one or more User Stories in the backlog.

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| F-01 | [feature] | [description] | Must Have |
| F-02 | [feature] | [description] | Should Have |

---
*[N] requirements — [date] | Source: [PRD / User input / Mixed]*
```

Update `docs/srs/srs-progress.json` → `"functional": true`.
Tell the user: "✅ Section 2 complete — Functional Requirements saved."