# Reference: Saving Backlog Sections

## Output directory
All backlog files save to `docs/backlog/` relative to the project root.
Create it if it doesn't exist: `mkdir -p docs/backlog`

## Filenames
| Section | Filename |
|---------|----------|
| 1. User Stories | `docs/backlog/01-user-stories.md` |
| 2. Sprint Plan | `docs/backlog/02-sprint-plan.md` |
| Compiled backlog | `docs/backlog/PRODUCT-BACKLOG.md` |

## After saving each section
Tell the user: "✅ Saved to docs/backlog/[filename]"

## Progress file
Update `docs/backlog/backlog-progress.json` after every completed section:
```json
{
  "userstories": false,
  "sprintplan": false,
  "lastUpdated": "[ISO date]",
  "srsVersion": "[date of FULL-SRS.md when backlog was generated]"
}
```

The `srsVersion` field is used by the revision agent to detect when the SRS has
changed and the backlog may be stale. Always set it when first generating the backlog.

## Compiling PRODUCT-BACKLOG.md
Read both section files in order and assemble:
```
# [Product Name] — Product Backlog
*Generated from docs/srs/FULL-SRS.md | [date]*

---
[contents of 01-user-stories.md]
---
[contents of 02-sprint-plan.md]
```