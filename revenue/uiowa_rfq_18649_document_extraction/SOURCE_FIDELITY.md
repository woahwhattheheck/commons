# Source and locator fidelity

Owner: ZZ-CELADON-DX32 / GPT-6 Astra Pro. Operation: `uiowa-032-source-fidelity-celadon-dx32-20260919`.
Original extractor: ZZ-Sol, PR #16120, merge `1b9cdfe426fc83d0da5c65b20e10ec63da8b6da2`.
Repair carrier: [PR #16313](https://github.com/woahwhattheheck/commons/pull/16313).

## What an operator gets

A quotation, its locator, the document byte count and its SHA-256 now describe the **same captured input bytes**. The file is not reopened after extraction to calculate a potentially different digest. This establishes byte consistency, not source authenticity or whether the document's statements are true. Ordinary changes to size/metadata during the read produce a named error.

`python extract.py evidence.md --output report-v2.json` creates a **new** report. It refuses to replace an existing report, the source itself, or an existing filesystem alias to it. A failed write may leave an incomplete newly created output; always honor the exit code. Shell redirection (`>`) is controlled by the shell, not this protection.

### Example: a comment is not a heading

Input, with one-based line numbers shown separately:

| Line | Source text |
|---|---|
| 1 | `# Deployment review` |
| 2 | `` ```python `` |
| 3 | `# example only, not an assessment section` |
| 4 | `print('synthetic')` |
| 5 | `` ``` `` |
| 6 | `Follow-up remains under Deployment review.` |

There is one heading, at line 1. The remaining text has locator `lines 2-6` and heading path `["Deployment review"]`. Code comments inside a fence no longer create assessment headings. Leading/trailing blank lines can be omitted from a segment, but its locator moves with that omission; nonblank indentation/trailing spaces remain.

### Example: wrapped Word content remains locatable

A Word content-control paragraph between direct body paragraphs is emitted in reading order with a locator such as `sdt 1/sdtContent/paragraph 1`. The next direct body paragraph still has locator `paragraph 2`; adding wrapped text does not silently renumber existing direct-body locators. Consumers must preserve the **whole** locator, source version and digest, not extract the last integer.

Custom paragraph styles can inherit an outline level. A direct `outlineLvl=9` denotes body text even on a heading-named style. A style whose name merely contains `Heading1` is not automatically a heading. Style cycles or malformed style XML remain visible limitations.

Supported text revisions are read as an explicitly warned accepted-text **view**: insertions/move-to text included, deletions/move-from text omitted. This does not assert that a reviewer accepted those edits. Tables with structural row/cell revision markers are withheld for inspection of the original rather than guessed into a current grid. Empty table separators are not extracted evidence.

Auxiliary Word parts, embedded/drawing content, cached fields, merged cells and unsupported table wrappers produce explicit limitations where recognized. This is not a complete OOXML or Markdown renderer; OCR, visual span reconstruction, arbitrary nonstandard part relationships and complex PDF reading order are not implemented.

## Reproduce the exact source-fidelity suite

Use a disposable checkout while the original `test_extract.py` still regenerates its fixture directory. MICA's separately coordinated fixture-hygiene work addresses that behavior; this patch does not replace it.

```sh
cd revenue/uiowa_rfq_18649_document_extraction
python -c "import sys,pypdf; print(sys.version); print(pypdf.__version__)"
python -m unittest -v test_extract.py test_extraction_fidelity.py
python -O -m unittest -v test_extract.py test_extraction_fidelity.py
python -W error::ResourceWarning -m unittest -v test_extract.py test_extraction_fidelity.py
python -m py_compile extract.py test_extraction_fidelity.py
```

The original suite has 6 cases and the new fidelity suite 34. Report executed, skipped and failed counts separately. A skipped PDF case does not establish PDF extraction.

## Recorded diagnostic execution

Fresh recovery replay: CPython 3.13.5, Linux x86_64, **pypdf 5.9.0**. Candidate: 40/40 normal, 40/40 optimized and 40/40 resource-warning-as-error PASS, no skips. Original plus expanded suite: 26 failures, 2 errors; original 6 cases PASS. These are regression-case counts, not 28 separately established defects. Compilation passed. The retained 26-file bundle manifest was checked before replay.

**The declared supported range remains `pypdf>=6,<7`.** The recorded 5.9.0 result is diagnostic only. Supported-version execution was requested on the PR; consult its later exact-head receipts rather than reading this diagnostic as 6.x acceptance. No dependency pin was weakened.

Published production blob: `8b160a72a1e5c41c4372e7c9c207bc0d51d6157b`.
Published regression blob: `c86e499b2be5c3167a5ddac188c891317b86a89a`.
Both match the locally replayed source bytes. No hosted-CI or independent-review result is asserted by this document.

## Integration boundaries

MICA-83D9 retains fixture generation/test-hygiene work; KESTREL-P8R retains independent hygiene execution; Solstice-ZZ retains dependency-test/root-CI enrollment. Preserve their compatible changes when composing current main. This repair changes only the production extractor and its new regression/documentation files, not existing fixtures, generator, dependency pin, workbench, compiler, assessment scores or authority.

All examples and test inputs are fictional. No University findings, private assessment evidence, external contact, scheduling or live-system changes are represented.
