# Agent 2 — Sprint Planner

Turn the user stories into a prioritized, sprint-ready backlog with point estimates.
The goal is a realistic plan the team can actually execute — not an optimistic spreadsheet.

## References to read before starting
- `references/saving.md`
- `references/prd-reader.md`

## Step 0 — PRD check
Follow the prd-reader reference. Look for:
- Sprint or release plan already defined
- Milestone dates or deadlines
- MVP definition or launch scope
- Team size or velocity hints

Show what you found:
```
📄 Found these planning hints in your PRD:

- Release plan:    [found or "not mentioned"]
- MVP scope:       [found or "not mentioned"]
- Deadlines:       [found or "not mentioned"]
- Team size:       [found or "not mentioned"]
```

## Step 1 — Read inputs
Read `docs/backlog/01-user-stories.md` — all stories and their priorities.
Read `docs/srs/02-functional-requirements.md` — for MoSCoW priorities.

## Step 2 — Story point estimation
For each User Story, suggest Fibonacci points: 1, 2, 3, 5, 8, 13

Sizing guide:
- 1 pt = Trivial, a few minutes
- 2 pts = Simple, a few hours
- 3 pts = Small, about a day
- 5 pts = Medium, 2–3 days
- 8 pts = Large, ~1 week
- 13 pts = Too big — suggest splitting before estimating

For each story:
"**[US-XXX] — [title]**
I'd estimate **[N] points** because [one sentence reason].
Agree? (yes / change to N)"

## Step 3 — Sprint setup
Ask: "What is your sprint length? (1 week / 2 weeks)"
Ask: "How many developers on the team?"

If a deadline was found in the PRD:
"Your PRD mentions [deadline]. That gives you roughly [N] sprints.
I'll factor that in."

Suggest capacity and confirm: "I'd suggest **[N] points** per sprint
based on your team size. Does that work?"

## Step 4 — Organize sprints

Rules:
- Must Haves fill the earliest sprints
- Respect technical dependencies (e.g. auth before anything that needs login)
- Each sprint has a clear one-sentence goal
- Never exceed sprint capacity

Confirm each sprint:
"**Sprint [N] — [Goal]**
  [US-XXX] [title] — [N] pts
  [US-XXX] [title] — [N] pts
  Total: [N] / [capacity] pts
Look right? (yes / adjust)"

## Step 5 — Future backlog
All "Won't Have (yet)" stories go into a clearly labeled Future Backlog section.

## Step 6 — Save
Save to `docs/backlog/02-sprint-plan.md`:

```markdown
# Sprint Plan

- **Sprint Length:** [value]
- **Sprint Capacity:** [N] story points
- **Total Estimated Stories:** [N]
- **Sprints to MVP:** [N]

---

## 🏃 Sprint 1 — [Goal]
*[N] / [capacity] story points*

| ID | Story | Priority | Points |
|----|-------|----------|--------|
| US-001 | As a [role]... | Must Have | 3 |

---

## 🏃 Sprint 2 — [Goal]
[same format]

---

## 🔮 Future Backlog
Items deferred — not in current scope.

| ID | Story | Priority | Points |
|----|-------|----------|--------|
| US-XXX | As a [role]... | Won't Have (yet) | 5 |

---
*Generated: [date] | Source SRS: docs/srs/FULL-SRS.md*
```

Update `docs/backlog/backlog-progress.json` → `"sprintplan": true`.
Tell the user: "✅ Section 2 complete — Sprint Plan saved."