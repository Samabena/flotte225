# Agent — Revision

Handle targeted edits to a specific design section. The goal is to apply the user's change
accurately, warn about any downstream sections that may need updating as a result, and
recompile FULL-DESIGN.md when done.

## References to read before starting
- `references/saving.md`

## Step 1 — Show current state
Read `docs/design/design-progress.json` and display which sections are complete:

```
Here's your current Design Document status:

  1. System Architecture    [✅ complete / ⬜ not started]
  2. Database Design        [✅ complete / ⬜ not started]
  3. API Design             [✅ complete / ⬜ not started]
  4. UI/UX Design           [✅ complete / ⬜ not started]
  5. Integration Design     [✅ complete / ⬜ not started]
  6. Security Design        [✅ complete / ⬜ not started]
  7. Dev Environment & CI/CD[✅ complete / ⬜ not started]

Which section do you want to revise?
```

## Step 2 — Display the chosen section
Read the relevant section file from `docs/design/` and show it in full.
Ask: "What would you like to change?"

## Step 3 — Warn about cascade effects
Before applying the change, check the cascade map below and warn the user if downstream
sections may be affected.

### Cascade Map

| Section changed | May affect |
|----------------|-----------|
| 01 System Architecture | 02 (database hosting context), 07 (docker/deploy config) |
| 02 Database Design | 03 (API response shapes reflect DB fields), 06 (isolation rules reference tables) |
| 03 API Design | 04 (UI screens call these endpoints), 05 (integration calls reference routes) |
| 04 UI/UX Design | Nothing downstream |
| 05 Integration Design | 03 (if new API endpoints are needed), 06 (if new secrets or auth flows) |
| 06 Security Design | 03 (auth middleware changes), 07 (env vars, secrets management) |
| 07 Dev Environment & CI/CD | Nothing downstream |

If cascade is detected, say something like:
"Heads up — changing the [section] may affect [downstream sections]. Want me to flag what
needs updating there too, or just update this section for now?"

## Step 4 — Apply the change
Make the edit to the section file. Be precise — change only what was asked.

If the user agreed to update downstream sections, read and update those too.

## Step 5 — Recompile FULL-DESIGN.md
After all changes are saved, recompile `docs/design/FULL-DESIGN.md` from all 7 section files
(see `references/saving.md` for the compilation format).

Update `lastUpdated` in `design-progress.json` to today's date.

Tell the user: "✅ Revision complete. FULL-DESIGN.md has been updated."

If the SRS or backlog changes prompted this revision, remind the user:
"If your SRS or backlog also changed, consider running `/srs-revise` or `/backlog-revise`
to keep all documents in sync."
