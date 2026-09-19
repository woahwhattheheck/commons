# Page inspection — `naive` renderer

> **FICTIONAL CONTENT. Example State University is an invented organization. No finding, citation, locator or figure here describes the University of Iowa or any real institution, system or person.**

Every page was checked **geometrically**: the box of every placed glyph run on every page was measured against the printable content box. **No human has visually inspected these pages.** That step is outstanding — see README.md.

| | |
|---|---|
| renderer | `naive` |
| pages | 2 |
| glyph runs checked | 54 |
| defects found | **1** |
| PDF structurally valid | True |
| all characters encodable | True |
| no text lost | True (3683 source chars, 3683 placed; +0 from deliberately repeated table headers) |

## Defects by class

| Defect | Count | What it does to a reader |
|---|---|---|
| `CLIPPED_TEXT` | 0 | A glyph run falls outside the printable content box. On paper this text is cut off at the page edge and cannot be read at all. |
| `ORPHANED_HEADING` | 1 | A heading is the last thing on its page and the body it introduces begins on the next page. The reader turns the page to find out what the heading was about. |
| `TABLE_HEADER_SEPARATED` | 0 | Table rows continue onto a page whose header row was left behind. The columns on that page are unlabelled. |
| `CITATION_SPLIT` | 0 | A citation block is broken across a page boundary, so a source locator is torn in half and the reference cannot be followed. |

## Every defect, with its page

| Page | Defect | Block | Detail |
|---|---|---|---|
| 1 | `ORPHANED_HEADING` | `h-b` | heading ends on page 1 but its following block p-b starts on page 2 |
