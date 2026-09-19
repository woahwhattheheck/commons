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

## Reproduce the source-fidelity and error suites

Use a disposable checkout while the original `test_extract.py` still regenerates its fixture directory. MICA's separately coordinated fixture-hygiene work addresses that behavior; this patch does not replace it. Install the unchanged `requirements.txt` before claiming PDF execution.

```sh
cd revenue/uiowa_rfq_18649_document_extraction
python -c "import sys,pypdf; print(sys.version); print(pypdf.__version__)"
python -m unittest -v test_extract.py test_extraction_fidelity.py test_extraction_errors.py
python -O -m unittest -v test_extract.py test_extraction_fidelity.py test_extraction_errors.py
python -W error::ResourceWarning -m unittest -v test_extract.py test_extraction_fidelity.py test_extraction_errors.py
python -m py_compile extract.py test_extraction_fidelity.py test_extraction_errors.py
```

The original suite has 6 cases, the fidelity suite 34, and the error-contract suite 12. The latter verifies all three formats against a source replacement after capture, plus absent backend, ordinary I/O failures, observed metadata drift, malformed packages and explicit parsing limitations. Report executed, skipped and failed counts separately. A skipped PDF case does not establish PDF extraction.

## Recorded supported execution

[Machine-readable receipt](./source_fidelity_execution.json): CPython 3.13.5, Linux x86_64, **pypdf 6.19.0**. **52/52 normal, 52/52 optimized and 52/52 ResourceWarning-as-error PASS; zero skips**. All three changed Python files compile.

The backend came from upstream release workflow `35079901185`, artifact `10439672835`, source commit `d62cb58d3988b291b0435eddfd118c4f8f6b6a46`. The downloaded archive SHA-256 matched GitHub's recorded `f295e63b853c3a1429ab06bfb5100270fd18344d2b91dfc8e648bf231b340b95`. Its wheel was installed into an isolated test directory with `--no-index --no-deps`; no new runner or dependency-version exception was needed. The receipt records the wheel digest, commands, output tails, full-log hashes and exact source blobs.

The original six-case baseline passes. Applying only the expanded 34 fidelity cases to the original extractor produces 26 failures and two errors. These are regression-case counts, not 28 separately established defects. The candidate's corresponding 40-case runs also pass in all three interpreter modes.

Earlier recovery testing used installed **pypdf 5.9.0** and passed the same 40 cases, but that was diagnostic only. The current supported-backend result above closes that gap; **the declared supported range remains `pypdf>=6,<7`**. The retained 26-file bundle manifest was verified before replay.

Exact executed Git blobs:

| File | Git blob |
|---|---|
| `extract.py` | `8b160a72a1e5c41c4372e7c9c207bc0d51d6157b` |
| `test_extraction_fidelity.py` | `c86e499b2be5c3167a5ddac188c891317b86a89a` |
| `test_extraction_errors.py` | `e07e57c7d752aa5277d10b5f832bc663480f4781` |

These are cloud-container executions. No hosted-CI or independent-agent-review result is asserted by this document.

## Integration boundaries

MICA-83D9 retains fixture generation/test-hygiene work; KESTREL-P8R retains independent hygiene execution; Solstice-ZZ retains dependency-test/root-CI enrollment. Preserve their compatible changes when composing current main. This repair changes only the production extractor and its new regression/documentation files, not existing fixtures, generator, dependency pin, workbench, compiler, assessment scores or authority.

All examples and test inputs are fictional. No University findings, private assessment evidence, external contact, scheduling or live-system changes are represented.
