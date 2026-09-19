# UIOWA-136 — Bidder attachment assembly and navigation tool

Work orders **UIOWA-136**, **UIOWA-136B** and **OPS-DOCBYTES-AUDIT** (RFQ-18649 lane).
Seat **OP5-TOPAZ**, Claude Opus 5.

Turns a manifest of prepared proposal components into an orderly submission folder:
stable filenames, an attachment index, section/page cross-references, and working
document navigation in both a rendered PDF and a rendered DOCX.

## The one rule this tool exists to enforce

A **declared attachment that is not on disk becomes a visible placeholder row** in the
index. It is never dropped — which would make an incomplete pack look complete — and
never substituted with invented content, which would make it look supplied.

The **filesystem is the ground truth.** A manifest that says `"provided": true` for a
file that is not there *loses to the filesystem*: the row reads `PLACEHOLDER-NOT
SUPPLIED` and an `ERROR`-severity issue records the contradiction. Size, digest and
page number for an absent document stay `UNKNOWN` — never `0`, never `n/a`, never a
score.

There is **no readiness percentage and no maturity rating** anywhere in the output. The
completeness block reports counts and names: how many required attachments were
declared, which are present, which are not. A count of observed documents is not a
rating, and a test (`test_no_readiness_score_or_percentage_is_emitted_anywhere`)
enforces that mechanically.

## Run it

Python 3 stdlib only. No pip, no network, no `reportlab`, no `python-docx`.

```
python3 bid_pack.py --manifest fixtures/manifest.json --out sample_output
python3 bid_pack.py --manifest fixtures/manifest.json --out /tmp/x --strict   # exit 1 on any ERROR
python3 packcheck.py sample_output/proposal.pdf sample_output/proposal.docx   # exit 1 on any defect
python3 packcheck.py --sweep <directory>                                     # audit every .pdf/.docx under a tree
python3 -m unittest test_bid_pack test_packcheck -v
```

Observed output of the first command (this is the real run, not an illustration):

```
assembled -> sample_output
  proposal.pdf: 9 pages (23790 bytes), pagination settled in 2 pass(es)
  sections: 7   attachments: 6
  required attachments declared 5 / present 2 / NOT SUPPLIED 3 (ATT-FIN-02, ATT-QUAL-02, ATT-QUAL-03)
  status: SUBMISSION_INCOMPLETE
  [WARN ] ATTACHMENT_NOT_SUPPLIED   required attachment ATT-FIN-02 (Certified Cost Rate Schedule) is declared but no file was supplied; emitted as a placeholder
  [WARN ] ATTACHMENT_NOT_SUPPLIED   required attachment ATT-QUAL-02 (Certificate of Insurance) is declared but no file was supplied; emitted as a placeholder
  [WARN ] ATTACHMENT_NOT_SUPPLIED   required attachment ATT-QUAL-03 (Key Personnel Resumes) is declared but no file was supplied; emitted as a placeholder
  [WARN ] XREF_UNRESOLVED           section S-SCOPE references 'S-APPENDIX-C', which is not a section or an attachment in this pack
```

## Files

| File | What it is |
|---|---|
| `bid_pack.py` | Manifest schema, validation, assembler, cross-reference resolver, CLI. |
| `pdfwrite.py` | Hand-written PDF writer **and reader**: xref table, outline (bookmark) tree, internal `/Link` annotations, cp1252/WinAnsi text, fixed-point paginator. |
| `docxwrite.py` | Hand-written OOXML `.docx` writer **and reader** via `zipfile`: heading styles, `w:bookmarkStart`, internal `w:hyperlink w:anchor`, `docProps` title. |
| `fixtures/` | The synthetic proposal. **Fiction — see below.** |
| `sample_output/` | A committed run of the assembler over `fixtures/`. |
| `packcheck.py` | **UIOWA-136B.** Independent structural validator for the rendered PDF and DOCX. Does *not* use `pdfwrite`'s reader. |
| `test_bid_pack.py` | 35 `unittest` tests for the assembler. |
| `test_packcheck.py` | 35 `unittest` tests for the validator — most of them corrupt the real rendered document on purpose. |

Output of a run (`sample_output/`): `proposal.pdf`, `proposal.docx`, `00-INDEX.md`,
`attachment_index.csv`, `bid_pack.json` (versioned + content-digested),
`documents/NN-*.md`, `attachments/A NN-*` including `*.PLACEHOLDER.txt` for every
absent attachment.

## The fixture is fiction, and it is labelled fiction

`fixtures/` describes **Northgate Assessment Partners LLC**, which does not exist. No
content in it is a representation about any real bidder, any real University of Iowa
requirement, or any real document. The fiction notice is carried into the rendered PDF
title page, into `00-INDEX.md`, and into the header of every generated section file; a
test asserts it reaches the rendered bytes.

It is built to show **both** halves of a real submission:

* **Strength.** 7 sections, 10 cross-references of which **9 resolve**; the attachment
  index page numbers **match the rendered PDF** (verified by reopening the file, not by
  trusting the builder); 21 internal PDF links and 16 DOCX bookmarks with **zero
  dangling**; two supplied attachments carried with measured byte counts and SHA-256.
* **Gap.** **3 of 5 required attachments are not supplied** (`ATT-FIN-02` certified cost
  rate schedule, `ATT-QUAL-02` certificate of insurance, `ATT-QUAL-03` key personnel
  resumes) — each one a placeholder row with `UNKNOWN` size and digest, each one a
  `*.PLACEHOLDER.txt` in the folder that disowns itself in its own body text. One
  cross-reference (`[[S-APPENDIX-C]]`) points at a section that does not exist and
  survives into the page as `[UNRESOLVED REFERENCE: S-APPENDIX-C]` rather than being
  quietly deleted. Two body sections *cite* attachments that were never supplied, and
  the resolved prose says `PLACEHOLDER, NOT SUPPLIED` inline.

## Page numbers are converged, not asserted

Resolved cross-reference prose contains page numbers ("Section 4 …, page 6"), and page
numbers depend on how that prose wraps — a circular dependency. The assembler iterates
pagination to a **fixed point** (2 passes on the fixture) and **raises
`PaginationError` rather than printing a page number that never settled**. A test
monkeypatches the anchor map to never converge and asserts the refusal.

## What is working vs. what is draft

**Working, and exercised by a test that opens the artifact:**
- Manifest validation and refusal (missing keys, duplicate ids, unknown schema, absolute
  and `../` source paths).
- Stable, sortable filenames; case-insensitive collision detection (a pack that is fine
  on Linux and silently overwrites a file on a reviewer's Windows or macOS machine is
  the exact failure this order is about).
- Attachment index in Markdown, CSV and JSON, all three agreeing.
- PDF: real outline, real internal links, aligned monospace index columns, `/Lang`,
  `/Title`, readback.
- DOCX: heading-level navigation, bookmarks, internal anchors, readback.
- Placeholder emission for absent attachments and absent section bodies.
- Non-WinAnsi characters reported as a loss instead of silently mangled (the `.md` and
  `.docx` outputs keep the original character; only the PDF cannot).

**Draft / not implemented, stated rather than hidden:**
- **Not tagged PDF/UA.** Navigation is implemented (outline, links, language, title);
  semantic tagging for assistive technology is **not**. "Accessible document
  navigation" in this lane means an outline and working links, and nothing more is
  claimed.
- Helvetica line wrapping uses an **approximate** advance width (no AFM metrics are
  embedded), so a wrapped line may stop slightly short of the right margin. Courier is
  exact at 0.6 em, which is why the index tables use it — column alignment in the index
  had to be real.
- PDF content streams are uncompressed (larger files, readable-back bytes).
- No page numbers in the `.docx`. A `.docx` is reflowable; asserting a page number
  without a layout engine would be inventing one.
- No tables or images in either renderer; the index is a monospace table.
- Attachment ordering is manifest order. Solicitation-mandated ordering is **UNKNOWN**
  (below).

## University inputs that remain UNKNOWN

Nothing here was derived from a real University of Iowa document. These stay UNKNOWN
until a real input is supplied, and the tool does not guess any of them:

1. **The actual required-attachment list for RFQ-18649.** The fixture's five "required"
   attachments are invented. `readiness.note` says so in the output itself: whether this
   list is the list the University requires is UNKNOWN.
2. **Mandated submission format** — PDF vs. DOCX vs. both, and whether a combined single
   file or a folder is expected.
3. **Mandated filename convention.** The `NN-slug` / `ANN-slug` scheme is this tool's
   own, chosen for stable sort order. If the solicitation prescribes names, they go in
   the manifest's `filename` field, which overrides.
4. **Mandated attachment ordering** and whether the attachment index must appear in
   front matter or as an appendix.
5. **Page-limit, font and margin requirements**, if any. Letter/72pt/Helvetica-11 is this
   tool's default, not a requirement read anywhere.
6. **Accessibility requirements.** Whether PDF/UA tagging or a specific WCAG conformance
   level is required is UNKNOWN; if it is, this renderer does not meet it and would need
   replacing rather than extending.
7. **The eBid/portal upload mechanics** — size caps, permitted file types, per-file vs.
   archive upload. Nothing here uploads anything.
8. **Whether any of the placeholder attachments actually exist** on the bidder's side.
   The tool reports only what is on disk in the pack.

## Scope discipline

No real University findings, no live data, no network calls, no outreach, no scheduling,
no submission. No invented attachment content: every fixture attachment says in its own
first line that it is a synthetic fixture. No page count, byte count or digest appears in
any output that was not measured from bytes actually written.

This lane does not read or write any other seat's lane. It consumes nothing from
`uiowa_rfq_18649_synthetic_collection/` — that collection carries assessment *evidence*,
and this order is about *submission packaging*, which is a different artifact. A future
integration could feed report sections produced by the report-structure lane into this
manifest's `sections` list unchanged; the manifest format is deliberately plain enough
for that, and it is **not** done here.


---

# UIOWA-136B — Structural validator (`packcheck.py`)

## Why it exists

`pdfwrite.py` writes a PDF and also reads it back, and the UIOWA-136 tests assert
against that readback. That is better than trusting the builder's own report — and it
is **still circular in one specific way**: the writer and the reader are the same
author making the same assumptions. If both misunderstand the format in the same
place, they agree perfectly, all 35 tests are green, and **the file still does not
open in Acrobat or Preview**.

`packcheck.py` therefore does not import `pdfwrite`'s reader. It parses the bytes from
scratch and checks them against the format's own internal rules.

The sharpest example is in the test suite: `test_xref_offset_off_by_one_is_caught`
shifts one cross-reference offset by a single byte. `packcheck` reports
`xref_offsets_resolve` as a defect. **`pdfwrite`'s own reader returns exactly the same
9 pages it returned before the corruption** — because it scans for `N 0 obj` headers
and never consults the xref table at all. The test asserts both facts side by side.
That is the circularity, demonstrated rather than argued.

## What it checks

**PDF (17 checks on the sample):** `%PDF-` header · `%%EOF` present (truncation) ·
objects present · `startxref` points at a real `xref` · xref subsection header · entry
count · **every in-use xref offset lands on the object it claims** · trailer `/Size`
greater than the highest real object number · every `/Length` equals the real stream
byte count · every indirect `N 0 R` resolves · `/Root` is a `/Catalog` · `/Pages`
exists · `/Count` equals the real `/Kids` length · every kid is `/Type /Page` · every
`/Dest` targets a page in *this* document · every `/Annots` entry is a `/Link` · every
font a content stream requests is in that page's `/Resources` · the outline chain
terminates and does not loop.

**DOCX (6 checks on the sample):** zip integrity · required parts present · every XML
part well-formed (`xml.etree`) · every relationship target resolves to a real part ·
every `w:hyperlink w:anchor` matches a real `w:bookmarkStart` · `bookmarkStart` and
`bookmarkEnd` balanced.

## Result on the committed sample — verbatim

```
sample_output/proposal.pdf: 17 check(s) run, 0 defect(s), 0 not run
sample_output/proposal.docx: 6 check(s) run, 0 defect(s), 0 not run

0 defect(s) across 2 file(s).
```

## What a pass means, and what it does not

A clean result means **"no structural defect found by these checks."** It does **not**
mean "valid PDF", it does **not** mean the page looks right, and it is **not** a
PDF/UA, WCAG, or any other conformance statement. This module issues no certificate
and makes no compliance claim; the CLI prints that disclaimer on every run and a test
asserts it is there.

**A check that did not run is reported as `NOT RUN`, never as a pass.** Hand it a
Markdown file and it reports `0 check(s) run, 1 not run` — not a clean bill of health.
`test_an_unchecked_file_is_reported_as_not_run_never_as_a_pass` enforces that.

## How it is proved

A validator that passes a file it should reject is worse than no validator, so 22 of
the 27 tests **break the real rendered document on purpose** and assert the named
defect fires: truncation · wrong magic header · xref offset off by one · falsified
`/Length` · reference to a nonexistent object · `/Count` disagreeing with `/Kids` ·
`/Dest` outside the document · font used but not declared · broken outline chain ·
**outline chain that loops** (caught, not hung on) · missing `startxref` · `startxref`
pointing at nothing · trailer `/Size` too small · a file with no objects · empty bytes
· DOCX with a required part removed · DOCX with a dangling relationship · malformed
XML part · hyperlink with no bookmark · unbalanced bookmarks · a `.docx` that is not a
zip · a file that does not exist. Corruptions are byte-length-preserving wherever
possible so the measured defect is the targeted one.

## Limits, stated

- **Structure only.** It cannot tell you a page *looks* right, that text is not
  overlapping, or that a table is readable. Visual inspection is UIOWA-123's lane, not
  this one.
- Single-section classic `xref` tables only; **cross-reference streams and object
  streams (PDF 1.5+) are not parsed.** A file using them would be reported as a
  `startxref`/`xref_subsection` defect, which would be a false positive. The validator
  is calibrated for the files this lane produces and says so rather than claiming
  general-purpose coverage.
- No encryption, no incremental updates, no linearization checks.
- The DOCX side checks package structure and navigation wiring, not schema validity
  against the ECMA-376 XSDs.


---

# OPS-DOCBYTES-AUDIT — kit-wide sweep, and two false positives it exposed in `packcheck` itself

`packcheck.py --sweep <dir>` walks a tree and audits every `.pdf` and `.docx` under
it. Running it across `revenue/` produced two findings, **both of them defects in this
validator rather than in the files it was pointed at.** Both are fixed, and both now
have named regression tests.

### Finding 1 — `word/styles.xml` was demanded but is not required

`REQUIRED_PARTS` listed `word/styles.xml` because this lane's own writer emits it.
OOXML does not require it. The validator reported `document_extraction/fixtures/
sample.docx`, a valid package from another lane, as `DEFECT required_parts`.

**Fixed by** splitting mandatory parts (`[Content_Types].xml`, `_rels/.rels`, plus the
main document part **discovered through `_rels/.rels`** rather than hardcoded) from
conventional ones (`word/styles.xml`, `docProps/core.xml`), which are now reported as a
**`note`**, never a defect. Tests:
`test_absent_conventional_part_is_a_note_not_a_defect`,
`test_main_document_part_is_discovered_not_hardcoded`,
`test_package_with_no_office_document_relationship_is_caught`.

### Finding 2 — `/Length` was measured against a newline that need not exist

The stream-length check searched for `b"\nendstream"`. The end-of-line before
`endstream` is optional and is not part of the stream data, so every Flate-compressed
PDF whose binary data runs straight into the keyword was reported broken — four
streams in `roadef2026/sedge/method.pdf`.

**Fixed by** measuring the bytes between `stream` and `endstream` and accepting the
spec-permitted 0, 1 or 2 bytes of end-of-line, and nothing wider. Tests:
`test_stream_with_no_eol_before_endstream_is_accepted`, and
`test_falsified_stream_length_is_caught` now falsifies by more than the tolerance so it
still measures a real mismatch.

### Third change — `CANNOT ASSESS` is now a distinct outcome

`packcheck` reads classic `xref` tables only. A PDF 1.5+ cross-reference stream or
object stream would previously have been reported as a defect. It now reports
`CANNOT ASSESS`, the file's verdict becomes `CLEAN/PARTIAL` rather than `CLEAN`, and
the unassessed count is printed in the sweep table. Test:
`test_cross_reference_stream_is_reported_as_cannot_assess_not_broken`.

`Report` now carries four outcomes: `ok`, `defect`, `note` (advisory, does not fail the
file) and `not_run` (including `CANNOT ASSESS`). **A check that did not run is never a
pass**, and a sweep of a tree containing no documents prints `Nothing was checked. That
is NOT a pass.`

### Sweep result over `revenue/` — verbatim

```
document                                                                   checks defects notes unassessed  verdict
----------------------------------------------------------------------------------------------------------------------
roadef2026/sedge/method.pdf                                                    16       0     0          0  CLEAN
uiowa_rfq_18649_bid_pack/sample_output/proposal.docx                            7       0     0          0  CLEAN
uiowa_rfq_18649_bid_pack/sample_output/proposal.pdf                            17       0     0          0  CLEAN
uiowa_rfq_18649_document_extraction/fixtures/blank.pdf                         15       0     0          0  CLEAN
uiowa_rfq_18649_document_extraction/fixtures/sample.docx                        6       0     1          0  CLEAN
uiowa_rfq_18649_document_extraction/fixtures/sample.pdf                        15       0     0          0  CLEAN
uiowa_rfq_18649_print_pagination/sample/boundary_citation_split_fixed.pdf      15       0     0          0  CLEAN
uiowa_rfq_18649_print_pagination/sample/boundary_citation_split_naive.pdf      15       0     0          0  CLEAN
uiowa_rfq_18649_print_pagination/sample/boundary_orphan_heading_fixed.pdf      15       0     0          0  CLEAN
uiowa_rfq_18649_print_pagination/sample/boundary_orphan_heading_naive.pdf      15       0     0          0  CLEAN
uiowa_rfq_18649_print_pagination/sample/report_document_fixed.pdf              15       0     0          0  CLEAN
uiowa_rfq_18649_print_pagination/sample/report_document_naive.pdf              15       0     0          0  CLEAN

note    uiowa_rfq_18649_document_extraction/fixtures/sample.docx  conventional_parts: absent (not required by OOXML): word/styles.xml, docProps/core.xml

12 file(s) swept, 0 with defect(s).
```

No file outside `revenue/uiowa_rfq_18649_bid_pack/` was modified. Findings are reported
here, not patched into another lane.

### UNKNOWN after this audit

- Whether any of these documents **render** correctly. Structure only; appearance is
  UIOWA-123's lane.
- Whether the twelve files above are the complete set the University would receive.
  Only what is on the branch was swept.
- Whether `packcheck` carries further false positives against producers not represented
  in this tree. Two were found by pointing it at two unfamiliar producers; there is no
  basis to claim there is not a third.
