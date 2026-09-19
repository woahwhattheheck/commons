# UIOWA-136 — Bidder attachment assembly and navigation tool

Work order **UIOWA-136** (RFQ-18649 lane). Seat **OP5-TOPAZ**, Claude Opus 5.

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
python3 -m unittest test_bid_pack -v
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
| `test_bid_pack.py` | 35 `unittest` tests. |

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
