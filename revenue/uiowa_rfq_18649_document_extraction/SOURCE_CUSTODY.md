# UIOWA-032 source custody

Original extractor: ZZ-Sol, PR #16120. Repair: ZZ-SABLE-6D4F, GPT-6 Astra Pro.
Operation: `uiowa032-source-custody-sable6d4f-20260919`.

## Captured bytes, not a second source revision

`extract()` reads a bounded snapshot once. TXT, DOCX and PDF parsers consume that same byte string; `document.bytes` and `document.sha256` describe it. A source revision arriving after parsing cannot become the hash of older extracted text. This is byte binding, not a filesystem transaction or evidence-truth claim. Concurrent writes during the initial read remain possible. Retain a source copy for durable custody.

Path-based parser APIs remain available; their new keyword-only `raw` parameter permits the dispatcher to share its snapshot. The high-level `extract` entry is the bounded metadata-producing interface. PDF parsing uses `PdfReader(BytesIO(raw))`, which is documented in the [official pypdf 6.0.0 streaming guide](https://pypdf.readthedocs.io/en/6.0.0/user/streaming-data.html). API documentation is not an execution receipt.

## Preserve source and unrelated files

`--output` rejects normalized, symlink and hard-link aliases of the source with `OUTPUT_ALIASES_INPUT`. Distinct existing reports remain replaceable. Writes stage a complete UTF-8 report in the destination directory, then replace that directory entry. They do not truncate a symlink/hard-link target. Failed staging or replacement retains the previous report and removes only this write's temporary file. I/O errors return the JSON error envelope and exit 2. No power-loss durability or arbitrary concurrent parent-directory protection is claimed.

## Word content controls

Block-level `w:sdt/w:sdtContent` and `w:customXml` wrappers are traversed, including nested controls and their headings/tables. Existing direct-body `paragraph N` and `table N` locators keep their numbering. Wrapped content gets an exact part path, such as `word/document.xml:/w:document/w:body/w:sdt[1]/w:sdtContent[1]/w:p[1]`. The `w` prefix means the existing WordprocessingML namespace. Unsupported body elements and empty controls produce warnings. Tracked changes are disclosed, not adjudicated into an accepted/rejected view.

The existing v1 envelope and fields remain. Segment sequence IDs are local, not globally stable: bind them to document SHA-256. Consumers must preserve an unfamiliar part locator or diagnose it as unsupported, never invent a page number. Headers, footnotes, style inheritance, row-level controls, nested table layout and all revision forms are not comprehensively supported. Existing PDF reading-order and OCR limits remain.

## Reproduce

From this directory:

```sh
python -m unittest -v test_extract test_integrity
python -O -m unittest -v test_extract test_integrity
python -m py_compile extract.py test_extract.py test_integrity.py make_synthetic_corpus.py
```

The 30 source-custody regressions use temporary fictional files and path-bound sibling imports. Retained baseline plus these regressions: 17 passing, 15 failures, 4 errors. Repaired source: 36 passing normally and 36 with actual optimized Python; repeated after resumption on September 19, 2026. Environment: CPython 3.13.5/Linux, pypdf 5.9.0. Source Git blob `0e870205f9d33760277e4ef69c5a6832b2a047fa`; test blob `c259a5a5a77e4299b27733e917139fb127cc5ec5`.

The unchanged requirements declare `pypdf>=6,<7`. Execution on that family and Windows remains unverified in this receipt. Hosted CI, independent review and merge state are separate provider facts, recorded on the PR. These tests do not establish University findings, approval, external delivery or source authenticity.
