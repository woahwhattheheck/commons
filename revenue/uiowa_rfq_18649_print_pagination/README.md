# UIOWA-123 — printed report pagination

A report renderer that produces **real PDFs** and then **inspects every page**
for the four defects that make a printed assessment report unreadable. It ships
a deliberately broken renderer alongside the corrected one, because an
inspector that has never gone red is not evidence of anything.

**Python 3 standard library only. No network, no install, no font files.**

> **FICTIONAL CONTENT.** Example State University is invented. No finding,
> citation, locator or figure describes the University of Iowa or any real
> institution, system or person.

---

## The honest limit, stated first

The work order's completion bar reads *"every page is visually checked."*

**No human has looked at these PDFs.** There is no renderer and no pair of eyes
in this environment, so that claim is not made anywhere in this lane.

What *is* done: every page is checked **geometrically**. The box of every
placed glyph run on every page is measured against the printable content box,
plus three structural checks across pages. That is **broader** than eyeballing
(it examines all 1,100+ runs, not whatever the eye lands on) and **different in
kind** (it cannot see that a table is ugly or that a break is merely awkward).

**Outstanding, and owed:** a human opening `sample/*.pdf` and confirming the
pages read well. The six PDFs are shipped so it takes one pass. Every output
file and the CLI itself print `VISUAL CHECK BY A HUMAN: OUTSTANDING`, and a
test asserts that string is present — so the claim cannot quietly appear later.

## Run it

```bash
cd revenue/uiowa_rfq_18649_print_pagination
python3 printreport.py                          # all three documents -> sample/
python3 printreport.py --document fixtures/report_document.json --out /tmp/out
python3 -m unittest test_printreport -v         # 39 tests
```

Real output:

```
document                   render pages  defects  CLIPP  ORPHA  TABLE  CITAT
----------------------------------------------------------------------------
report_document            naive      4       65     64      0      1      0
report_document            fixed      4        0      0      0      0      0
boundary_orphan_heading    naive      2        1      0      1      0      0
boundary_orphan_heading    fixed      2        0      0      0      0      0
boundary_citation_split    naive      2        1      0      0      0      1
boundary_citation_split    fixed      2        0      0      0      0      0

fixed-renderer defects across all documents: 0
```

## The four defects

Each is named in the work order and each is detected geometrically, not guessed.

| Defect | What it does to a reader |
|---|---|
| `CLIPPED_TEXT` | A glyph run falls outside the printable box — cut off at the page edge, unreadable. |
| `ORPHANED_HEADING` | A heading is the last thing on its page; its body starts overleaf. |
| `TABLE_HEADER_SEPARATED` | Rows continue onto a page whose header row was left behind. The columns are unlabelled. |
| `CITATION_SPLIT` | A citation breaks across a page boundary, tearing a source locator in half. |

## Two renderers, on purpose

**`naive`** paginates by *counting blocks instead of measuring them* — the
single most common real pagination bug. It reserves one line for a paragraph
that will wrap to twenty, sizes table columns to their natural content width
with no check against the page, writes the table header once, and has no
keep-together for headings or citations.

**`fixed`** measures every block after wrapping, keeps a heading with the first
two lines of what follows, repeats table headers on every continuation page,
keeps citations atomic, and wraps wide cells instead of letting them run off
the edge.

`naive` is the **negative control**. The test suite asserts it really produces
each defect before asserting `fixed` produces none, and a further test asserts
that *every defect class the inspector defines is demonstrated by some fixture*
— so a detector cannot rot into a no-op unnoticed.

## The rule that outranks looking tidy

> **No text is ever dropped to make a page fit.**

Clipping a cell, eliding a line or truncating a locator produces a clean page
that has silently deleted evidence from the report. `audit_text_conservation()`
compares every non-whitespace character of the source against every character
placed on a page, and a test proves the audit can fail by deleting runs.

Compared as **multisets**, not ordered strings. Two legitimate behaviours make
an ordered comparison wrong, and both were found by the audit failing on
correct output:

- a table is placed **column-major within each wrapped line** while the source
  reads row-major;
- the fixed renderer **deliberately repeats the table header** on each
  continuation page, so placed characters legitimately exceed source
  characters (+111 on the main report). A test asserts `fixed` adds characters
  and `naive` adds none — that difference *is* the table-header fix.

Note what conservation deliberately does **not** claim. The naive renderer also
loses nothing, because it places its overflow *below the bottom of the page*
rather than dropping it. Conservation catches a renderer that drops text;
`CLIPPED_TEXT` catches text that is placed but unreadable. Two guarantees, both
needed.

## Characters the font cannot carry

The base-14 encoding is Latin-1. A character outside it becomes a literal `?`
in the PDF **with nothing complaining** — the same silent loss this lane exists
to prevent. So it is detected, and the fix is recorded rather than silent:

- `TRANSLITERATE` maps a small set of typographic characters to an ASCII
  equivalent that means the same thing (em dash → `--`, curly quotes →
  straight, ellipsis → `...`). Applied **once at load**, so layout, the
  conservation audit and the PDF all see identical text.
- Every substitution is **counted and printed** in the inspection report.
  This guard caught **9 em dashes in this lane's own fixture** on its first run
  that would have printed as `?`.
- Anything *not* in that table is left alone and reported as unencodable.
  Inventing an ASCII stand-in for a character we do not understand would be
  the failure being guarded against. A probe containing `你好 α` reports them
  rather than rendering `??`.

## Why the boundary fixtures are computed, not hand-written

`CLIPPED_TEXT` and `TABLE_HEADER_SEPARATED` arise naturally from the realistic
report. The other two depend on content landing at a precise offset — the
orphaned-heading window is roughly one line height (12.4pt) in a 684pt content
box, about 1.8% of positions.

Rather than tune prose until a defect appeared, the padding was **searched
for**: pad sizes were enumerated until the naive renderer left the heading as
the last line on its page, and that value was pinned. Each fixture's `note`
field says so and says that changing the padding stops the defect reproducing.
A fixture that admits it was solved for is more honest than one that looks
natural.

## What the tests found

Two defects were found by tests rather than by reading the code, which is the
only reason they are worth listing:

1. **The conservation audit was asserting the wrong property.** It compared
   ordered strings and failed on *both* renderers with nothing actually
   missing. The multiset formulation above is the correct guarantee.
2. **A table row taller than a whole page overflowed instead of splitting.**
   A row that fits on *a* page is moved whole; a row that fits on *no* page has
   nowhere to go, and the renderer emitted it in full and let it run off the
   bottom. It now splits across pages with the header re-emitted on each
   continuation. The hostile test feeding one cell 12,000 characters is what
   exposed it, and a paired negative-control test asserts the same input still
   breaks the naive renderer.

## Hostile and missing input

| Input | Behavior |
|---|---|
| Missing file / malformed JSON | `DocumentError` naming the file; CLI exits `2` |
| Unknown block kind | Rejected, naming the kind |
| Duplicate block ids | Rejected — duplicates would merge two blocks in the inspector's page map and hide a real defect |
| Table row with the wrong number of cells | Rejected, naming the count |
| Empty table, heading with no text, bad heading level | Rejected |
| Several problems at once | **All** reported in one raise |
| Document with no blocks | Renders one page, zero defects, no crash |
| One cell with more text than a page holds | Splits across pages, header repeated, zero defects, nothing lost |
| Unbreakable token wider than its column | Hard-split — never allowed to overflow, never dropped |
| `(`, `)`, `\` in content | Escaped; unescaped they would terminate a PDF string early and corrupt the page |

## Files

```
printreport.py               renderer + layout + inspector + PDF writer + CLI
test_printreport.py          39 unittest cases
fixtures/report_document.json          22-item report: long findings, multiline
                                       citations, a table wider than the column,
                                       three roadmap phases
fixtures/boundary_orphan_heading.json  computed pad -> orphaned heading in naive
fixtures/boundary_citation_split.json  computed pad -> split citation in naive
sample/*_naive.pdf, *_fixed.pdf        six real PDFs, before and after
sample/inspection_*.md, *.json         per-page findings for each render
```

## What is real vs. draft vs. UNKNOWN

**Working and tested:** the renderer, both layout modes, the inspector, the
conservation audit, the transliteration record, the PDF writer and its
structural verifier. 39 tests pass.

**Draft:** the visual design is deliberately plain — one monospaced family, no
rules, no shading. Courier was chosen because its metrics are exact without a
font file, which makes every measurement in this lane checkable by hand. A real
engagement would use a proportional font, which needs a metrics table or an
embedded font and changes nothing about the pagination logic.

**UNKNOWN / outstanding:**

- **Human visual confirmation of every page.** Owed, not done. See above.
- The **real report template** — this lane renders its own document model. A
  real template's blocks map onto `heading` / `paragraph` / `citation` /
  `table`, but that mapping has not been done against another seat's landed
  report structure and should not be assumed.
- **Paper size and margins.** US Letter with 0.75in margins is assumed; the
  University's print standard is unknown.
- **Proportional-font metrics** and **embedded Unicode fonts**, both out of
  scope for a stdlib-only renderer and both named rather than faked.
