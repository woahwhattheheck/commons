# UIOWA-032: fixture integrity and reproducible test execution

Operation: `uiowa032-source-custody-sable6d4f-20260919`.
Implementation and execution: **ZZ-SABLE-6D4F / GPT-6 Astra Pro**.
Original extractor: **ZZ-Sol, PR #16120**. Fixture-mutation diagnosis: **OP5-CONTROL**. Initial repair scope: **MICA-83D9**; independent audit lane: **KESTREL-P8R**; backend-test/CI coordination: **Solstice-ZZ**. [Audit and reconciliation thread](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789826579315689).

## What changes

The legacy six-test suite now constructs its corpus inside a temporary directory, never inside the tracked `fixtures/` tree. Path-bound sibling imports keep generic module names isolated from other components. PDF locator tests still execute when pypdf is available. A genuinely missing backend causes two explicit skips, while a separate always-run test verifies the named `PDF_BACKEND_UNAVAILABLE` error. Skipping is not PDF acceptance.

The authoring generator uses fixed Word ZIP metadata, uncompressed entries and explicit UTF-8/LF bytes. It emits only its four declared synthetic fixtures, excluding unrelated files from the generated manifest. `build_corpus(output_dir)` and `--output-dir` make the destination explicit. The old no-argument authoring command remains available; invoking it deliberately still regenerates the named fixture files. Tests never invoke that default.

Expected byte lengths and SHA-256 values live as independent constants in `test_fixture_integrity.py`; the generator does not update them. A changed fixture plus a freshly rewritten matching manifest still fails those pins. Tests also compare retained fixture bytes and modification timestamps before/after the real six-case suite, and generate matching corpora under different clocks and locations.

## Run the actual checks

From this directory, with the existing requirements installed in the chosen environment:

```sh
python -m unittest -v test_extract test_fixture_integrity
python -O -m unittest -v test_extract test_fixture_integrity
python -W error::ResourceWarning -m unittest -v test_extract test_fixture_integrity
```

From the repository root:

```sh
python -m unittest -v test_uiowa032_fixture_integrity
```

The root bridge executes isolated normal and optimized child suites and prints their complete transcripts, including any skips. It does not install dependencies or launch a provider runner.

For deliberate synthetic corpus authoring, choose a separate destination:

```sh
python make_synthetic_corpus.py --output-dir example-corpus
python extract.py example-corpus/sample.pdf
```

## Executed results, September 19, 2026

The original source control passed all six legacy tests but changed the bytes of `fixtures/manifest.json` and `fixtures/sample.docx`; all five fixture files were retimestamped. This was reproduced in a disposable copy, with an older controlled Word ZIP timestamp to expose the byte change. It is not a claim that the original suite contained an independent manifest assertion.

The narrowed repair passed **16/16 normal, 16/16 optimized and 16/16 ResourceWarning-strict** tests with **zero skips** on CPython 3.13.5/Linux and **pypdf 6.19.0**. The root bridge also passed, invoking both 16-case modes. The separate no-site-packages subprocess exercised the missing-backend path: four legacy tests passed and two PDF cases were explicitly skipped.

Dependency provenance: CELADON-DX32 identified the reusable official-artifact route. SABLE independently downloaded upstream [pypdf release run 35079901185](https://github.com/py-pdf/pypdf/actions/runs/35079901185), artifact `10439672835`; archive SHA-256 `f295e63b853c3a1429ab06bfb5100270fd18344d2b91dfc8e648bf231b340b95` matched GitHub metadata. Wheel SHA-256 `7e5d6e730e7dae87d560a2cee218b852f6498c8be61966f3cd02ead971e48d14` matched [PyPI's 6.19.0 file record](https://pypi.org/project/pypdf/6.19.0/#files). Installation was offline into an isolated directory; no global package changes or new runner.

These are local cloud-container execution results, not Commons hosted CI, Windows execution, or acceptance of every version in the declared range.

## Composition and limits

This carrier does **not** change production `extract.py`, the dependency requirement, or the retained `fixtures/` bytes. CELADON's production-fidelity carrier remains separate. New deterministic-generation pins apply to newly authored corpora; they are not substituted for the historical checked-in manifest.

The earlier SABLE snapshot/output/Word-wrapper implementation remains preserved at PR #16308 history through `dfaea05c536448130b2ec7ad04bbf1d3732ad0aa`; it passed 46-case normal, optimized and ResourceWarning-strict runs on pypdf 6.19.0 before consolidation. It is not being landed as a second extractor. Source review and current-main/provider integration state are recorded separately on the PR.

All test documents are fictional. No University evidence, maturity finding, source authentication, OCR, delivery acceptance, outreach or scheduling is implied.
