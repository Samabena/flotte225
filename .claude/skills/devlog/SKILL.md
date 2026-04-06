---
name: devlog
description: Write a new plain-English journal entry into docs/devlog/DEVLOG.md capturing what was built, problems encountered and solved, and key decisions made. Keeps a running human-readable history of the entire project — written like a developer's notebook, not a changelog. Use whenever the user says "/devlog", "log what we did", "update the devlog", "write up what we built", "document this session", or after any significant work session. Also used once to backfill the full project history from scratch.
---

# Devlog Skill

Write a new plain-English journal entry into `docs/devlog/DEVLOG.md`.
The devlog is a living notebook — written like a developer explaining their work to a colleague, not a formal document.

---

## Before you start

Read the following to understand what happened:
1. `.claude/context/project-context.md` — current project state and history
2. `docs/devlog/DEVLOG.md` — existing log (to avoid duplicating already-logged work)
3. Run `git log --oneline -20` — recent commits to understand what changed
4. If the user described what they just did in the conversation — use that as the primary source

---

## What a devlog entry looks like

Each entry has this structure:

```
---

## [Date] — [Short title of what happened]

### What we built
[2–5 sentences in plain English. No bullet points. Write it like you're explaining to a teammate who just joined. What exists now that didn't before?]

### The hard parts
[What went wrong, what was confusing, what took longer than expected. Be honest. If nothing was hard — skip this section.]

### How we solved it
[The actual fix or decision. Specific enough that someone reading this months later would understand exactly what was done and why.]

### Key decisions
[Things we chose deliberately: why we picked X over Y, what we ruled out, what we'll revisit later. If no major decisions were made — skip this section.]

### What's next
[One or two sentences on what comes after this. Not a full plan — just the immediate next thing.]
```

---

## Writing rules

- **Plain English only.** No markdown headers inside sections, no bullet points, no code blocks.
- **Be specific.** "We fixed a bug" is useless. "bcrypt 4.x broke passlib's hash API so we replaced passlib with bcrypt directly" is useful.
- **Write in first person plural.** "We built...", "We decided...", "We ran into..."
- **Keep each entry self-contained.** Someone should be able to read one entry without reading the others.
- **Don't repeat what's in the previous entries** — if something was already logged, reference it briefly ("as described in the Sprint 1 entry") rather than re-explaining it.
- **Honest about failures.** If something didn't work or a decision turned out wrong, say so.
- **Length:** Each entry should be 200–600 words. Long enough to be useful, short enough to actually read.

---

## Step 1 — Determine what to log

If `docs/devlog/DEVLOG.md` **does not exist** or is empty:
→ This is a **backfill run**. Write one entry per sprint/major milestone found in the project context and git history. Cover the full project history from the beginning. Each entry gets its own dated section.

If the devlog **already exists**:
→ Read the last entry to find the last logged date.
→ Write only what happened **after** that date.
→ If nothing new happened since the last entry, tell the user and skip writing.

---

## Step 2 — Write the entry (or entries)

Use the template above. Pull facts from:
- The project context file (decisions, what was built, important notes)
- Git commit messages (what changed)
- The current conversation (what the user just described or you just did together)

Do **not** invent details. If you're not sure why a decision was made, write "we chose X" not "we chose X because Y" unless you actually know the reason.

---

## Step 3 — Save the file

If `docs/devlog/DEVLOG.md` does not exist, create it with this header, then append the entries:

```
# Project Devlog — e-invoicing

A plain-English record of what we built, what broke, how we fixed it, and why we made the decisions we made.
Read this to get a fast understanding of the project's history without reading the code.

---
```

If the file exists, **append** the new entry at the **bottom** of the file. Never overwrite existing entries.

---

## Step 4 — Confirm

Tell the user:
- How many entries were written
- The date range covered
- Where the file is: `docs/devlog/DEVLOG.md`

---

## What NOT to do

- Do not copy-paste from project-context.md — rewrite in plain English
- Do not use headers, bullet points, or code blocks inside entry sections
- Do not log things already covered by existing entries
- Do not make the entries sound like release notes ("Added feature X") — write narratively
- Do not skip the "hard parts" section just to sound polished — the problems are the most useful part
