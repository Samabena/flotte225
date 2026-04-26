---
name: srs-builder
description: >
  Builds a complete Software Requirements Specification (SRS) through a guided
  4-section conversation: product discovery, functional requirements, non-functional
  requirements, and interface requirements. Outputs a FULL-SRS.md document suitable
  for stakeholders, architects, and developers joining the project.

  Use this skill whenever the user wants to define what a software product must do
  before building it. Triggers on phrases like "let's write the requirements",
  "help me spec this out", "create an SRS", "I need to define what we're building",
  "document the requirements", or any mention of product requirements, functional
  spec, or technical specification. If the user is starting a new project and needs
  to capture what the system must do — this skill applies, even if they don't use
  the word "SRS".
---

# SRS Builder

This skill produces a formal SRS through a structured 4-section conversation.
The output is a document for stakeholders and the development team that answers:
what is this product, what must it do, how well must it perform, and what does
it connect to.

The 4 sections build on each other — discovery establishes the product context,
functional requirements define what it must do, non-functional requirements define
how well, and interface requirements define what it connects to. This order matters
because later sections reference decisions made in earlier ones.

When the SRS is complete, the user runs `/backlog` to generate user stories and a
sprint plan from it. The SRS and the backlog are intentionally separate documents
for separate audiences: the SRS is for stakeholders and architects, the backlog is
for the dev team.

---

## Detecting state

Check if `docs/srs/srs-progress.json` exists in the project.

**Not found → fresh start**
Create `docs/srs/` and an empty progress file (structure in `references/saving.md`).
Welcome the user, explain the 4 sections and that it takes roughly 20–25 minutes,
and ask if they're ready to begin.

**Found → resume or revise**
Read the file and show which sections are complete. If any are incomplete, offer to
resume. If all 4 are done, they're likely here to revise — ask which section and
switch to revision mode.

---

## Building mode — agent sequence

Work through incomplete sections in order. Read each agent file fully and follow
its instructions before moving to the next.

| Section | Agent file | Marks complete |
|---------|-----------|----------------|
| 1. Product Discovery | `agents/01-discovery.md` | `"discovery": true` |
| 2. Functional Requirements | `agents/02-functional.md` | `"functional": true` |
| 3. Non-Functional Requirements | `agents/03-nonfunctional.md` | `"nonfunctional": true` |
| 4. Interface Requirements | `agents/04-interfaces.md` | `"interfaces": true` |

After each agent completes, re-read `srs-progress.json` to confirm it was marked
true before proceeding. This guards against partial saves.

---

## Revision mode

Read `agents/revision.md`. It handles showing current content, applying the edit,
warning about cascade effects, and recompiling FULL-SRS.md.

If the change affects functional or interface requirements, remind the user to
re-run `/backlog` afterward to keep stories and sprints in sync.

---

## Final compilation

Once all 4 sections are true, compile `docs/srs/FULL-SRS.md` by reading each
section file in order. See `references/saving.md` for the exact filenames.

Tell the user their SRS is complete and ready for stakeholder review. Suggest
running `/backlog` as the natural next step.

---

## Shared reference files

Read these only when the agent instructions say to — don't preload all of them upfront.

- `references/questioning.md` — how to ask one question at a time and confirm sections
- `references/moscow.md` — how to explain and apply MoSCoW prioritization
- `references/saving.md` — filenames, progress.json structure, update instructions
- `references/prd-reader.md` — how to extract answers from an existing PRD first