# Agent 1 — User Story Generator

Translate every functional requirement from the SRS into properly formatted
User Stories with Acceptance Criteria. These become the atomic units of work
developers pick up each sprint.

## References to read before starting
- `references/questioning.md`
- `references/saving.md`
- `references/prd-reader.md`

## Step 0 — PRD check
Follow the prd-reader reference. Look for:
- User stories already written by the BA
- Use cases or user flows described
- Acceptance criteria or definition of done hints
- Personas or user role descriptions

Show what you found:
```
📄 Found these story hints in your PRD:

- Existing user stories:  [N found / none]
- User flows described:   [list or "none"]
- Personas mentioned:     [list or "none"]
```
Use any existing stories as the basis — format them properly and add missing criteria
rather than rewriting from scratch what the BA already defined well.

## Step 1 — Read the SRS
Read `docs/srs/FULL-SRS.md`. Extract:
- Functional requirements table (F-01, F-02...) — your primary input
- Primary user persona from the product overview — for story roles
- Interface decisions — for context in acceptance criteria

## Step 2 — For each functional requirement

Decide: did the PRD already write a story for this?
- **Yes** → format it properly, add or complete acceptance criteria
- **No** → generate 1–3 stories from scratch

**Story format:**
> As a [specific role], I want to [concrete action], so that [clear benefit].

Rules:
- Role = the specific persona from the SRS, not a generic "user"
- One story = one user interaction
- Benefit explains WHY, not just repeats what

**Acceptance Criteria — 3–5 per story:**
- Given [context], when [action], then [expected result]

**Confirm after each requirement:**
"Here are the stories for [F-XX — Feature Name].
Does this look right? (yes / modify / add another story)"

Assign IDs: US-001, US-002...

## Step 3 — Save
Save to `docs/backlog/01-user-stories.md`:

```markdown
# User Stories

Translated from SRS Functional Requirements.
*Source: docs/srs/FULL-SRS.md*

---

## [F-01] — [Feature Name]

### US-001 — [Story Title]
**Priority:** [inherited from F-01 MoSCoW]
**Story:**
> As a [role], I want to [action], so that [benefit].

**Acceptance Criteria:**
- [ ] Given..., when..., then...
- [ ] Given..., when..., then...
- [ ] Given..., when..., then...

---
[repeat for all requirements]

---
*[N] stories from [M] requirements | [date] | Source: [PRD / Generated / Mixed]*
```

Update `docs/backlog/backlog-progress.json` → `"userstories": true`.
Tell the user: "✅ Section 1 complete — User Stories saved."