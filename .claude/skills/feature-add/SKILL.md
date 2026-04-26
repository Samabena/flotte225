---
name: feature-add
description: Add a new feature to an existing project without breaking any planning documents. Reads all existing planning docs (SRS, backlog, sprint plan, design, project context) to understand the current state, then cascades the new feature through every relevant document in the correct order. Use when the user says "add a feature", "I want to add X", "new requirement: X", "I forgot to add X", "add to the backlog", "slot this into the sprints", or describes any new capability they want to include in the project.
triggers:
  - /feature-add
  - add a feature
  - new feature
  - I want to add
  - I forgot to add
  - add to the backlog
  - new requirement
---

# Feature Add Skill

You are a precision planning assistant. Your job is to add a new feature to an existing project by cascading it through all planning documents in the correct order, without breaking numbering, formatting, or existing flows.

---

## Phase 1 — Understand the Feature

If the user has not already described the feature, ask **one question only**:

> "Describe the feature in plain language — what should the system do, and who benefits?"

Do not ask multiple questions. Gather everything from a single response. If the description is ambiguous, make reasonable assumptions and state them clearly before proceeding.

---

## Phase 2 — Discover Existing Documents

Before touching anything, find and read all planning documents. **Do not assume fixed paths** — search for them.

### 2.1 Document Discovery

Search the project for:

| Document Type | Where to look | Priority order |
|--------------|--------------|----------------|
| SRS | `docs/srs/FULL-SRS.md`, `docs/SRS*.md`, `**/SRS*.md`, `**/requirements*.md` | Use first match |
| Backlog | `docs/backlog/PRODUCT-BACKLOG.md`, `**/BACKLOG*.md`, `**/backlog*.md` | Use first match |
| Sprint Plan | `docs/SPRINT_PLAN.md`, `SPRINT_PLAN.md`, `**/sprint*.md`, `**/SPRINT*.md` | Use first match |
| Design/Architecture | `docs/design/FULL-DESIGN.md`, `docs/ARCHITECTURE*.md`, `**/design*.md`, `**/ARCHITECTURE*.md` | Use first match |
| Project Context | `context/PROJECT_CONTEXT.md`, `.claude/context/*.md`, `**/project-context*.md` | Use first match |

Read every document you find. Do not skip any — each one informs where to place the feature.

### 2.2 State Analysis

After reading, answer these questions internally (do not output them):

1. **Existing feature list** — what features already exist? Is this feature already partially or fully described?
2. **Document numbering** — what numbering scheme does each doc use? (e.g., `## 3.9`, `STORY-14`, `TASK-42`)
3. **Next available IDs** — what is the next SRS section number, next story ID, next task ID?
4. **Sprint state** — which sprints are completed, in-progress, or not started? What sprint is it logical to slot this into?
5. **Dependencies** — does this feature depend on anything not yet built? Does anything existing depend on this?
6. **Design impact** — does this feature require new DB tables, new API endpoints, new components, or new integrations?
7. **Conflicts** — does this feature contradict or change existing requirements?

If the feature already exists in the documents, stop and tell the user: *"This feature (or something very similar) already exists as [reference]. Do you want to extend it or add a variant?"*

---

## Phase 3 — Plan the Cascade

Before writing anything, output a **cascade plan** for the user to confirm:

```
## Feature: [Feature Name]

**Summary:** [One sentence describing what this adds]
**Assumptions:** [Any assumptions you made, or "none"]
**Conflicts detected:** [Any conflicts with existing features, or "none"]

### What will be updated:

1. ✏️ SRS → Section [X.Y]: Add requirement "[short title]"
2. ✏️ Backlog → Add story [STORY-N]: "[story title]" ([M] story points, [Priority])
3. ✏️ Sprint Plan → Slot into [Sprint N] — [reason why this sprint]
   - [N] new tasks under this sprint
4. ✏️ Design/Architecture → [what changes, or "No changes needed"]
5. ✏️ Project Context → Update [which sections]

Proceed? (yes / adjust [what])
```

Wait for the user to confirm or request adjustments before writing anything.

---

## Phase 4 — Execute the Cascade

Once confirmed, update each document **in this exact order**:

### Order matters — always cascade top to bottom:
1. SRS first (source of truth for requirements)
2. Backlog second (derives from SRS)
3. Sprint Plan third (derives from backlog)
4. Design/Architecture fourth (only if impacted)
5. Project Context last (reflects the new state)

---

### 4.1 SRS Update

**Rules:**
- Add to the **Functional Requirements** section (or the closest equivalent)
- Match the exact numbering scheme: if existing requirements use `### 3.8 Feature Name`, add `### 3.9 New Feature`
- Use the same writing style as existing requirements (imperative language: "The system SHALL...", "The system MUST...")
- Never renumber existing sections
- Add a reference note if this requirement depends on or extends an existing one
- If the SRS has a table of contents, add the new entry

**Format to insert:**
```markdown
### [N.N] [Feature Name]

[Description of what the system must do. Written in the same style as existing requirements.]

**Acceptance criteria:**
- [Criterion 1]
- [Criterion 2]
- [Criterion 3]

**Dependencies:** [SRS section refs, or "None"]
**Priority:** [Must Have / Should Have / Could Have / Won't Have]
```

---

### 4.2 Backlog Update

**Rules:**
- If there is a separate backlog file (`PRODUCT-BACKLOG.md`): add a new row to the user stories table and a new sprint entry
- If the backlog is embedded in the Sprint Plan (as a "Backlog Summary" table): add a new row to that table
- Match the existing ID format exactly (e.g., if existing IDs are `STORY-1`, next is `STORY-N`; if `US-001`, next is `US-002`)
- Story points: estimate based on complexity relative to existing stories (look at what 1, 2, 3, 5, 8 point stories look like)
- Priority column: use the same priority labels as existing rows
- SRS Ref column: point to the section you just added

**Table row format (match existing column order exactly):**
```
| [ID] | As a [user], I want [capability] so that [benefit] | [Phase/Epic] | [Priority] | [SRS ref] |
```

---

### 4.3 Sprint Plan Update

**Rules for sprint selection — in priority order:**
1. If there is an incomplete sprint that handles the same epic/phase as this feature → add to that sprint
2. If the feature depends on something in a future sprint → add to the sprint AFTER that dependency
3. If the feature is small (≤ 3 story points) and an in-progress sprint has capacity → add to that sprint
4. If none of the above → add to the last non-completed sprint, or create a new sprint at the end

**Never:**
- Add to a sprint marked as completed (✅ / `[x]`)
- Add tasks that depend on future sprints into an earlier sprint
- Renumber or rename existing sprints

**Task format to insert (match existing task format exactly):**
```markdown
- [ ] **[TASK-N]** — [Task description]
  - [Sub-task if needed]
  - Acceptance: [brief acceptance criterion]
```

If a new sprint is needed, use this structure:
```markdown
## Sprint [N]: [Sprint Name]

**Goal:** [One sentence sprint goal]
**Duration:** 2 weeks
**Dependencies:** Sprint [N-1]

### User Stories
| Story ID | Description | Points |
|----------|-------------|--------|
| [ID] | [Story] | [N] |

### Technical Tasks
- [ ] **[TASK-N]** — [task]

### Definition of Done
- [ ] Feature works end-to-end
- [ ] Tests written and passing
- [ ] Documentation updated

### Risks / Spikes
- [Any risks, or "None"]
```

---

### 4.4 Design/Architecture Update

**Only update if the feature requires:**
- A new database table or column
- A new API endpoint or external integration
- A new system component or service
- A change to existing data models

**If no design impact:** skip this step and note "No design changes required."

**If update needed:**
- Add only the changed/new element — do not rewrite existing sections
- Match the existing diagram style (Mermaid, tables, etc.)
- Add a note: `> **Added in feature: [Feature Name]** — [Date]`

---

### 4.5 Project Context Update

Update these sections:
- **What's In Progress** — if this is being built now
- **What's Next** — if this is queued for a future sprint
- **Key Decisions & Notes** — add one bullet: `**[Date]** — Added feature: [name]. [One sentence why / what it does.]`
- **File Inventory** — if new files will be created, add them with status "Not Started"
- Do NOT change: Current Status percentage, Completed Phases, or How to Resume — unless the feature is being added to the active sprint

---

## Phase 5 — Confirm and Report

After all updates are complete, output this report:

```
✅ Feature Added: [Feature Name]

### Documents Updated:
- **SRS** → Added section [N.N]: [title] (file: [path])
- **Backlog** → Added [STORY-N]: [story title] ([X] pts, [Priority]) (file: [path])
- **Sprint Plan** → Added [N] tasks to [Sprint Name] (file: [path])
- **Design** → [Updated / No changes needed] (file: [path if updated])
- **Project Context** → Updated (file: [path])

### Summary:
[2-3 sentences describing what was added and why it fits where it was placed.]

### Next steps:
- If you're actively building: pick up [TASK-N] from [Sprint Name]
- If you want to adjust priority: update the MoSCoW label in the backlog
- If this changes the architecture significantly: run /design-builder revision mode
```

---

## Edge Cases

**If no SRS exists:**
Tell the user: *"No SRS found. I can add this directly to the sprint plan and backlog, but you won't have a formal requirement. Say 'yes' to proceed, or run /srs-builder first."*

**If no sprint plan exists:**
Add to backlog only and note: *"No sprint plan found. Feature added to backlog. Run /agile-sprint-designer to create a sprint plan."*

**If the feature is large (> 8 story points):**
Recommend splitting: *"This feature is large. I suggest splitting it into [N] sub-features: [list]. Should I add them as separate stories, or keep as one epic?"*

**If there is a conflict with an existing requirement:**
Stop and report the conflict clearly before making any changes: *"This feature conflicts with [existing requirement ref]: [describe conflict]. Options: (1) replace the old requirement, (2) add as a variant, (3) cancel. What would you like to do?"*

**If a sprint is frozen / marked complete:**
Never add tasks to it. Always add to the next available sprint and note: *"Sprint [N] is complete — added to Sprint [N+1] instead."*
