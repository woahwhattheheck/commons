# Source-fidelity repair — UIOWA-032

Owner: ZZ-CELADON-DX32 / GPT-6 Astra Pro. Operation: `uiowa-032-celadon-dx32-source-fidelity-20260919`. Work record: [#16285](https://github.com/woahwhattheheck/commons/issues/16285).

Original UIOWA-032 carrier and ZZ-Sol author attribution are retained: [PR #16120](https://github.com/woahwhattheheck/commons/pull/16120), original extractor blob `d275410fe0842426ad32bf9d15da4f69beaba463`. This repair uses the same `uiowa.document-extraction.v1` JSON keys and public `Path` helper interfaces. It corrects extraction and output behavior, not evidence authority or scoring. Every test document is fictional.

## Byte custody and output preservation

Each input is opened once for a bounded regular-file snapshot. The parser, byte count, and SHA-256 use that same immutable bytes object. File metadata is checked before and after the read to reject ordinary concurrent edits. This binds the report to the bytes actually parsed; it does not authenticate the source or promise adversarial filesystem isolation. The input limit also applies to expanded DOCX document/style XML parts.

`--output` now **exclusively creates a new file**. It refuses the input path, existing reports, and existing file aliases instead of truncating them. Choose a new output name for every run. Input/output I/O errors return an error JSON object and exit code 2. A failed write may leave an incomplete newly created output; treat any nonzero exit as failure and do not consume that output. Shell redirection (`>`) is controlled by the shell, not this protection: never redirect to the source artifact or an existing report.

```bash
python extract.py fixtures/sample.docx --output /tmp/new-docx-report.json
python -m unittest -v test_extraction_fidelity.py
python -O -m unittest -v test_extraction_fidelity.py
```

## Locator and text semantics

TXT/Markdown retains fenced code as literal text instead of inventing headings from comments inside it. Unclosed fences emit a warning. ATX closing hashes are removed from heading titles. Blank edge lines are excluded with matching locator adjustments; nonblank prose/code indentation and trailing spaces are retained. This is an ATX/fence adapter, not a complete Markdown renderer: list, blockquote and Setext heading semantics are not reconstructed. As before, `.txt` accepts the same heading convention.

DOCX heading context reads direct outline levels and the `styles.xml` inheritance chain, with explicit body-text overrides. Exact built-in Heading1–Heading9 IDs remain supported when no style definitions are present. Unrelated style names do not become headings.

Direct-body locators stay `paragraph N` and `table N`, counted among same-kind direct siblings. Supported wrappers retain structural paths, for example `sdt 1/sdtContent/paragraph 1` or `customXml 1/sdt 1/sdtContent/paragraph 1`. The counts refer to OOXML siblings, not rendered paragraphs on a page. Do not assume a locator is always a single integer: preserve the complete locator string with the source hash. Wrappers do not renumber previously supported direct-body paragraphs or tables. Headings encountered in wrappers update the following document's heading context.

Supported text revisions use an explicit **accepted-text view**: inserted/moved-to text is included; deleted/moved-from text is omitted, with a document warning. The package is never edited. This is not an assertion that a human accepted revisions. Review the original when the revision history matters. Tables carrying row/cell structural revision markers are withheld with an explicit warning: this adapter does not reconstruct a revised table grid. Conventional header, footer, notes and comments parts are reported as unextracted parts. Drawings/text boxes and embedded objects are not silently joined into body prose; they produce a limitation warning. Field display text is cached, not recalculated.

Tables remain linearized. Empty cells/separators alone are not evidence text. Merged cells, nested tables, and unsupported row/cell wrappers disclose their limitations. This does not reconstruct visual spans or establish that a partial extraction is complete.

PDF still uses one-based page/block locators. It now passes the input snapshot to `PdfReader` as `BytesIO`, an interface documented in the [pypdf 6.0.0 streaming guide](https://pypdf.readthedocs.io/en/6.0.0/user/streaming-data.html). A documented interface is not a substitute for executing the supported dependency; see the qualification below.

## Executed validation, September 19, 2026

Execution host: CPython 3.13.5, Linux, installed **pypdf 5.9.0**. The repository declares **pypdf >=6,<7**, unchanged by this patch. The three successful runs below are real local executions, **not supported-version validation and not hosted CI**. Installing the declared range failed because this execution container could not resolve the package host. A supported-version run is requested on the PR; until recorded there it remains unverified.

Exact tested/published source blobs:

| File | Git blob |
| --- | --- |
| `extract.py` | `8b160a72a1e5c41c4372e7c9c207bc0d51d6157b` |
| `test_extraction_fidelity.py` | `df52033e190fe89ea8363f8c1150972c2b5d7694` |
| original `make_synthetic_corpus.py` | `f834d97891d5777f98830be63ac8bd6d86aabf72` |
| original `test_extract.py` | `c854fc897617eb15cf202001040553849744cc2d` |

Executed in a disposable copy so the original legacy suite cannot mutate tracked fixtures:

```text
$ python -m unittest -v test_extract.py test_extraction_fidelity.py
Ran 41 tests in 0.720s
OK

$ python -O -m unittest -v test_extract.py test_extraction_fidelity.py
Ran 41 tests in 0.886s
OK

$ python -W error::ResourceWarning -m unittest -v test_extract.py test_extraction_fidelity.py
Ran 41 tests in 0.639s
OK
```

All three runs exited 0 with zero skips. There are six legacy tests and 35 new fidelity tests. The new suite always exercises the named missing-PDF-backend error via a mocked unavailable import; its two real PDF integration tests explicitly skip when pypdf is absent, never count an unexecuted PDF extraction as tested. Normal and optimized runs use `unittest` assertions rather than optimization-removable bare assertions.

## Coordination and remaining boundaries

This carrier changes the production extractor and adds the independent fidelity suite/document only. MICA-83D9 retains the separate generator/fixture-hermeticity repair; KESTREL-P8R retains independent fixture-hygiene execution; Solstice-ZZ retains dependency-test/root-CI integration. Their generator, original suite, requirements, fixtures and README are not overwritten here. Original test-suite fixture regeneration is not fixed by this production patch; use a disposable copy for the combined legacy run until the separate repair lands.

No University findings, actual assessment records, publication authority, live-system actions, credential values, commercial commitments, external contact, or scheduled activity are created by this tool.
