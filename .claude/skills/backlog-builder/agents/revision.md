# Agent: Backlog Revision

Handle targeted corrections to an existing backlog without regenerating everything.

## Step 0 — Check if the SRS changed first

Before anything else, compare `srsVersion` in `docs/backlog/backlog-progress.json`
to the last-modified date of `docs/srs/FULL-SRS.md`.

If they differ, warn the user:
"Your SRS has been updated since this backlog was generated. When requirements
change, many stories are often affected at once. It's usually faster to re-run
/backlog than to patch stories individually.

Regenerate from scratch? (yes / no, I'll patch manually)"

If the user chooses to regenerate, exit and tell them to run /backlog.
If they choose to patch, proceed.

---

## Cascade dependency map

| Section changed | Section affected |
|---|---|
| 01 User Stories | 02 Sprint Plan (totals and capacity change) |
| 02 Sprint Plan | Nothing |

---

## Step 1 — Show current state
Read `docs/backlog/backlog-progress.json`. Display:
```
📊 Current Backlog:
  1. User Stories  [✅ / ⬜]
  2. Sprint Plan   [✅ / ⬜]
```
Ask: "Which section needs correction? (1 or 2)"

## Step 2 — Show current content
Read and display the chosen section file.
Ask: "What needs to change?"

## Step 3 — Warn about cascade
If user stories are being changed, warn:
"Updating stories may change point totals and sprint assignments.
Should I update the sprint plan too? (yes / no)"

## Step 4 — Apply correction
Make the targeted edit. If the user agreed to update the sprint plan, read
`agents/02-sprintplan.md` and regenerate it.

## Step 5 — Recompile
Always recompile `docs/backlog/PRODUCT-BACKLOG.md` at the end.
Update `srsVersion` in `backlog-progress.json` to today's date.
Tell the user: "✅ Backlog updated. PRODUCT-BACKLOG.md recompiled."