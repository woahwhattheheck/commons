# Page inspection — `naive` renderer

> **FICTIONAL CONTENT. Example State University is an invented organization. No finding, citation, locator or figure here describes the University of Iowa or any real institution, system or person.**

Every page was checked **geometrically**: the box of every placed glyph run on every page was measured against the printable content box. **No human has visually inspected these pages.** That step is outstanding — see README.md.

| | |
|---|---|
| renderer | `naive` |
| pages | 4 |
| glyph runs checked | 287 |
| defects found | **65** |
| PDF structurally valid | True |
| all characters encodable | True |
| no text lost | True (10148 source chars, 10148 placed; +0 from deliberately repeated table headers) |

### Characters substituted before rendering

These typographic characters cannot be carried by the base-14 font encoding. They were replaced once, at load, with a recorded ASCII equivalent, so the substitution is visible here rather than appearing as `?` in the PDF.

| Character | Replaced with | Occurrences |
|---|---|---|
| `—` (U+2014) | `--` | 9 |

## Defects by class

| Defect | Count | What it does to a reader |
|---|---|---|
| `CLIPPED_TEXT` | 64 | A glyph run falls outside the printable content box. On paper this text is cut off at the page edge and cannot be read at all. |
| `ORPHANED_HEADING` | 0 | A heading is the last thing on its page and the body it introduces begins on the next page. The reader turns the page to find out what the heading was about. |
| `TABLE_HEADER_SEPARATED` | 1 | Table rows continue onto a page whose header row was left behind. The columns on that page are unlabelled. |
| `CITATION_SPLIT` | 0 | A citation block is broken across a page boundary, so a source locator is torn in half and the reference cannot be followed. |

## Every defect, with its page

| Page | Defect | Block | Detail |
|---|---|---|---|
| 2 | `CLIPPED_TEXT` | `t-items` | run ends at x=726.6pt, past the right margin 558.0pt (column runs off the side of the page) |
| 2 | `CLIPPED_TEXT` | `t-items` | run ends at x=867.6pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=569.4pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=607.8pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=954.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=569.4pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=624.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=954.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=569.4pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=624.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=954.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=569.4pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=624.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=954.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=569.4pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=624.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=954.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=569.4pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=607.8pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=954.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=569.4pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=624.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=954.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=569.4pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=624.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=954.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=596.4pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=624.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=997.2pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=754.2pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=596.4pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=624.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=997.2pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=754.2pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=596.4pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=607.8pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=997.2pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=754.2pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=596.4pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=624.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=997.2pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=754.2pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=596.4pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=624.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=997.2pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=754.2pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=624.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=959.4pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=624.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=959.4pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=607.8pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=959.4pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=624.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=1002.6pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=624.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=1002.6pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=624.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=1002.6pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=624.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=1002.6pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=607.8pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=1002.6pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=624.0pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `CLIPPED_TEXT` | `t-items` | run ends at x=1002.6pt, past the right margin 558.0pt (column runs off the side of the page) |
| 3 | `TABLE_HEADER_SEPARATED` | `t-items` | table rows appear on page 3 with no header row on that page |
