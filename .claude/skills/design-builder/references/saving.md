# Reference: Saving Design Sections

## Output directory
All design files save to `docs/design/` relative to the project root.
Create it if it doesn't exist.

## Filenames

| Section | Filename |
|---------|----------|
| 1. System Architecture | `docs/design/01-system-architecture.md` |
| 2. Database Design | `docs/design/02-database-design.md` |
| 3. API Design | `docs/design/03-api-design.md` |
| 4. UI/UX Design | `docs/design/04-ui-ux-design.md` |
| 5. Integration Design | `docs/design/05-integration-design.md` |
| 6. Security Design | `docs/design/06-security-design.md` |
| 7. Dev Environment & CI/CD | `docs/design/07-devenv-cicd.md` |
| Compiled Design Doc | `docs/design/FULL-DESIGN.md` |

## After saving each section
Tell the user: "✅ Saved to docs/design/[filename]"

## Progress file
Update `docs/design/design-progress.json` after every completed section:

```json
{
  "architecture": false,
  "database": false,
  "api": false,
  "uiux": false,
  "integrations": false,
  "security": false,
  "devenv": false,
  "lastUpdated": "[ISO date]",
  "backlogVersion": "[date of PRODUCT-BACKLOG.md or 'unknown']"
}
```

## Compiling FULL-DESIGN.md
Read all 7 section files in order and assemble under this header:

```
# [Product Name] — System Design Document
*Design Phase | Generated: [date] | Based on SRS + Backlog v[backlogVersion]*

---
[contents of 01-system-architecture.md]
---
[contents of 02-database-design.md]
---
[contents of 03-api-design.md]
---
[contents of 04-ui-ux-design.md]
---
[contents of 05-integration-design.md]
---
[contents of 06-security-design.md]
---
[contents of 07-devenv-cicd.md]
```
