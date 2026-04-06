---
name: backlog-builder
description: >
  Reads a completed SRS and generates a full Agile product backlog: user stories
  with acceptance criteria for every functional requirement, story point estimates,
  and a sprint plan organized by MoSCoW priority. Outputs PRODUCT-BACKLOG.md.

  Use this skill whenever the user wants to turn requirements into a backlog, write
  user stories, estimate story points, plan sprints, or prepare for development.
  Triggers on phrases like "let's create the backlog", "turn requirements into
  stories", "help me plan the sprints", "estimate the work", "what goes in sprint 1",
  or any mention of user stories or sprint planning. Requires a completed SRS —
  if docs/srs/FULL-SRS.md doesn't exist, tell the user to run /srs first.
---

# Backlog Builder

This skill reads a completed SRS and produces an Agile product backlog — the
bridge between "what we need to build" and "what the team works on next sprint."

It does two things:
- **User stories** — translates each functional requirement into one or more
  stories with acceptance criteria, giving developers clear and testable units of work
- **Sprint plan** — estimates story points, respects MoSCoW priorities and
  dependencies, and organizes stories into sprints the team can execute

The SRS is the single source of truth. The backlog doesn't invent new requirements —
it reshapes what the SRS defines into a form developers can act on. This separation
matters: the SRS is for stakeholders, the backlog is for the dev team.

---

## Detecting state

Check if `docs/backlog/backlog-progress.json` exists.

**Not found → fresh start**
First verify `docs/srs/FULL-SRS.md` exists. If it doesn't, stop and tell the user:
"I need a completed SRS to generate the backlog. Run /srs first to define your
requirements, then come back here."

If it exists, create `docs/backlog/` and an empty progress file
(structure in `references/saving.md`). Briefly explain what you're about to do
and ask if they're ready.

**Found → resume or revise**
Read the file and show which sections are complete. Offer to resume or revise.

---

## Building mode — agent sequence

| Section | Agent file | Marks complete |
|---------|-----------|----------------|
| 1. User Stories | `agents/01-userstories.md` | `"userstories": true` |
| 2. Sprint Plan | `agents/02-sprintplan.md` | `"sprintplan": true` |

After each agent completes, re-read `backlog-progress.json` to confirm it was
marked true before proceeding.

---

## Revision mode

Read `agents/revision.md`. It handles editing a specific section, cascade warnings,
and recompiling PRODUCT-BACKLOG.md.

If the user's SRS has changed since the backlog was generated (compare `srsVersion`
in `backlog-progress.json` to the current FULL-SRS.md date), recommend regenerating
from scratch — a changed SRS typically affects many stories at once.

---

## Final compilation

Once both sections are true, compile `docs/backlog/PRODUCT-BACKLOG.md` by reading
both section files in order. See `references/saving.md` for exact filenames.

Tell the user their backlog is ready and that Sprint 1 is their starting point.

---

## Shared reference files

Read these only when the agent instructions say to.

- `references/questioning.md` — how to ask one question at a time and confirm sections
- `references/moscow.md` — how to explain and apply MoSCoW prioritization
- `references/saving.md` — filenames, progress.json structure, update instructions
- `references/prd-reader.md` — check for sprint or release hints in the original PRD

