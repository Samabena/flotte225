# Reference: Saving SRS Sections

## Output directory
All SRS files save to `docs/srs/` relative to the project root.
Create it if it doesn't exist: `mkdir -p docs/srs`

## Filenames
| Section | Filename |
|---------|----------|
| 1. Product Overview | `docs/srs/01-product-overview.md` |
| 2. Functional Requirements | `docs/srs/02-functional-requirements.md` |
| 3. Non-Functional Requirements | `docs/srs/03-non-functional-requirements.md` |
| 4. Interface Requirements | `docs/srs/04-interface-requirements.md` |
| Compiled SRS | `docs/srs/FULL-SRS.md` |

## After saving each section
Tell the user: "✅ Saved to docs/srs/[filename]"

## Progress file
Update `docs/srs/srs-progress.json` after every completed section:
```json
{
  "discovery": false,
  "functional": false,
  "nonfunctional": false,
  "interfaces": false,
  "lastUpdated": "[ISO date]"
}
```

## Compiling FULL-SRS.md
Read all 4 section files in order and assemble under this header:
```
# [Product Name] — Software Requirements Specification
*Lightweight Agile SRS | Generated: [date]*

---
[contents of 01-product-overview.md]
---
[contents of 02-functional-requirements.md]
---
[contents of 03-non-functional-requirements.md]
---
[contents of 04-interface-requirements.md]
```