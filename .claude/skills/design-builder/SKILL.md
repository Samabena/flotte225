---
name: design-builder
description: >
  Guides a software team through the complete Design phase of the SDLC via a structured
  7-section conversation: system architecture, database design, API design, UI/UX design,
  integration design, security design, and dev environment/CI-CD. Reads the existing SRS
  and product backlog to avoid re-asking decisions already made. Outputs a FULL-DESIGN.md
  document and 7 section files ready for Sprint 1.

  Use this skill whenever the user wants to design the system before coding, plan the
  database schema, define API endpoints, spec out UI screens, design integrations, think
  through security, or set up their dev environment. Triggers on phrases like "let's design
  the system", "create the design document", "we need a system architecture", "what should
  the database look like", "let's spec the API", "design phase", or any mention of moving
  from requirements to technical design. Use this skill before development starts —
  it bridges the gap between the backlog and the first line of code.
---

# Design Builder

This skill produces a complete System Design Document through a structured 7-section conversation.
It bridges the gap between "what we need to build" (SRS + backlog) and "how we build it" (Sprint 1).

The 7 sections build on each other — architecture establishes the deployment context, database
defines the data model, API defines how the frontend talks to the backend, UI/UX defines the
screens, integrations define external service flows, security defines protection rules, and the
dev environment defines how the team works day-to-day. This order matters because later sections
reference decisions made in earlier ones.

---

## Detecting state

Check if `docs/design/design-progress.json` exists in the project.

**Not found → fresh start**
First verify `docs/backlog/PRODUCT-BACKLOG.md` exists. If it doesn't, stop and tell the user:
"I need a completed backlog to start the design phase. Run `/backlog` first to define your
sprint plan, then come back here."

If it exists, create `docs/design/` and an empty progress file (structure in `references/saving.md`).
Welcome the user, explain the 7 sections, and ask if they're ready to begin.

**Found → resume or revise**
Read the file and show which sections are complete. If any are incomplete, offer to resume from
where they left off. If all 7 are done, they're likely here to revise — ask which section and
switch to revision mode.

---

## Building mode — agent sequence

Before starting Section 1, read the SRS and backlog. See `references/srs-reader.md` for how
to extract already-known decisions so you only ask about gaps.

Work through incomplete sections in order. Read each agent file fully before starting it.

| Section | Agent file | Marks complete |
|---------|-----------|----------------|
| 1. System Architecture | `agents/01-system-architecture.md` | `"architecture": true` |
| 2. Database Design | `agents/02-database-design.md` | `"database": true` |
| 3. API Design | `agents/03-api-design.md` | `"api": true` |
| 4. UI/UX Design | `agents/04-ui-ux-design.md` | `"uiux": true` |
| 5. Integration Design | `agents/05-integration-design.md` | `"integrations": true` |
| 6. Security Design | `agents/06-security-design.md` | `"security": true` |
| 7. Dev Environment & CI/CD | `agents/07-devenv-cicd.md` | `"devenv": true` |

After each agent completes, re-read `design-progress.json` to confirm it was marked true
before proceeding. This guards against partial saves.

---

## Revision mode

Read `agents/revision.md`. It handles showing current content, applying the edit,
warning about cascade effects on downstream sections, and recompiling FULL-DESIGN.md.

---

## Final compilation

Once all 7 sections are true, compile `docs/design/FULL-DESIGN.md` by reading each section
file in order. See `references/saving.md` for the exact filenames and header format.

Tell the user their Design Document is complete and Sprint 1 can now begin. Suggest using
the design doc as the reference during development — especially the API and database sections.

---

## Shared reference files

Read these only when the agent instructions say to — don't preload all of them upfront.

- `references/srs-reader.md` — how to extract known answers from FULL-SRS.md before asking questions
- `references/questioning.md` — how to ask one question at a time and confirm sections
- `references/saving.md` — filenames, progress.json structure, compilation format
