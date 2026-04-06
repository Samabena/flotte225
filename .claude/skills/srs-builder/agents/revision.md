# Agent: SRS Revision

Handle targeted corrections to an existing SRS without re-running the full process.

## Cascade dependency map

Changing an early section can make later sections stale. Use this map to warn
the user before they commit to a change:

| Section changed | SRS sections affected | Backlog affected? |
|---|---|---|
| 01 Product Overview | All — it's the foundation | Yes, re-run /backlog |
| 02 Functional Requirements | 03 NFR (if scope changes) | Yes, re-run /backlog |
| 03 Non-Functional | Nothing in SRS | No |
| 04 Interface Requirements | Nothing in SRS | Possibly — check with user |

---

## Step 1 — Show current state
Read `docs/srs/srs-progress.json`. Display status:
```
📊 Current SRS:
  1. Product Overview        [✅ / ⬜]
  2. Functional Requirements [✅ / ⬜]
  3. Non-Functional Req.     [✅ / ⬜]
  4. Interface Requirements  [✅ / ⬜]
```
Ask: "Which section needs correction? (enter number)"

## Step 2 — Show current content
Read and display the chosen section file in full.
Ask: "What needs to change? Describe the correction."

## Step 3 — Warn about cascade
Before making any edit, check the dependency map and warn the user:
"Changing this section may affect [downstream sections].
Proceed and update those too? (yes / just this section)"

If the backlog is affected:
"This change will also affect your user stories and sprint plan.
Re-run /backlog after this to keep everything in sync."

## Step 4 — Apply correction
Make the targeted edit to the section file.
If the user agreed to update downstream SRS sections, read the relevant
agent files and regenerate those sections too.

## Step 5 — Recompile
Always recompile `docs/srs/FULL-SRS.md` at the end by reading all 4 section
files in order (filenames in `references/saving.md`).

Tell the user: "✅ SRS updated. FULL-SRS.md recompiled."