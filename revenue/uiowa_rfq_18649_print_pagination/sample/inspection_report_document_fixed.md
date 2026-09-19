# Page inspection — `fixed` renderer

> **FICTIONAL CONTENT. Example State University is an invented organization. No finding, citation, locator or figure here describes the University of Iowa or any real institution, system or person.**

Every page was checked **geometrically**: the box of every placed glyph run on every page was measured against the printable content box. **No human has visually inspected these pages.** That step is outstanding — see README.md.

| | |
|---|---|
| renderer | `fixed` |
| pages | 4 |
| glyph runs checked | 432 |
| defects found | **0** |
| PDF structurally valid | True |
| all characters encodable | True |
| no text lost | True (10148 source chars, 10259 placed; +111 from deliberately repeated table headers) |

### Characters substituted before rendering

These typographic characters cannot be carried by the base-14 font encoding. They were replaced once, at load, with a recorded ASCII equivalent, so the substitution is visible here rather than appearing as `?` in the PDF.

| Character | Replaced with | Occurrences |
|---|---|---|
| `—` (U+2014) | `--` | 9 |

## Defects by class

| Defect | Count | What it does to a reader |
|---|---|---|
| `CLIPPED_TEXT` | 0 | A glyph run falls outside the printable content box. On paper this text is cut off at the page edge and cannot be read at all. |
| `ORPHANED_HEADING` | 0 | A heading is the last thing on its page and the body it introduces begins on the next page. The reader turns the page to find out what the heading was about. |
| `TABLE_HEADER_SEPARATED` | 0 | Table rows continue onto a page whose header row was left behind. The columns on that page are unlabelled. |
| `CITATION_SPLIT` | 0 | A citation block is broken across a page boundary, so a source locator is torn in half and the reference cannot be followed. |

## No defects found

Every glyph run on all 4 pages sits inside the content box; no heading is separated from its body; every page carrying table rows also carries that table's header row; no citation straddles a page break.
