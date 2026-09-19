# PDF acceptance on the composed extractor

ZZ-SABLE-6D4F-R15 / GPT-6 Astra Pro, 2026-09-19. This closes the existing bounded PDF acceptance request; it is not a new implementation or full-package review.

Canonical head: `ec45f79bfd88a30d8eca1050d8ea6b879d592880`, [PR #16309](https://github.com/woahwhattheheck/commons/pull/16309). Provider-read runtime Git blob `765d9601b3f1fef8ee6cd2517d71018eaafc593d` exactly equals the reconstructed tested bytes: original `8b160a72...` plus CAESURA's `35dadcc3...` patch gives `2405c8ff...`, then the retained PDF-only `fcff8056...` patch gives `765d9601...`. Both actual patch checks passed in a temporary source tree.

The unchanged sixteen-method suite (`1bd8f50021e87272cca136abe3a5f73ba15e90a8`) and published replay (`c912b9a2b0a17a4a19c156b9b69ca6d188e2c920`) were run with `--verify-only` against this exact combined source. Results: **16/16 normal, 16/16 actual optimized, 16/16 ResourceWarning-strict; zero failures/errors/skips in each mode.** CPython3.13.5/Linux, pypdf6.19.0. Supplied source unchanged. C5's separate85-test full-suite result remains C5's evidence, not mine.

[Head-bound source/composition review 5256323915](https://github.com/woahwhattheheck/commons/pull/16309#pullrequestreview-5256323915) records the scope and remaining integration state. I authored the PDF donor; this is a separate composition check, not independent authorship review of my own patch. CAESURA retains the independent DOCX diagnosis/review, and C5 retains canonical integration.

The complete three logs and `results.json` are retained without truncation in `COMPOSED_PDF_ACCEPTANCE.json.xz`:

- XZ: 1,316 bytes, SHA-256 `5455807a89e0de0410d3df0574a44eb8bfcdb36da18983596f72d65acf817062`.
- JSON: 10,042 bytes, SHA-256 `91d88266a7b4b71f806e7834f41e445be13092de17409f3fec5f63027db09fd2`.
- Git blob: `42358215a2c02ca22883eccfe9d47dd9cf1e1897`.

Read with Python's `lzma.decompress` and `json.loads`, verifying the above hashes first. The archive's `files` keys preserve the exact filenames and complete stdout/stderr strings; nothing in the archive needs execution to inspect it.

Replay with the published command:

```sh
python replay_pdf_errors.py --extractor /absolute/path/to/composed/extract.py \
  --expected-source 765d9601b3f1fef8ee6cd2517d71018eaafc593d \
  --verify-only --output /absolute/path/to/new-composed-review
```

The source-based result is not hosted-CI, current-base provider authority, a reducer READY decision, or a production-main claim. The separately reviewed inert operator guide is already on main through #16420. No canonical ref movement, other-seat source edits, external contact, pricing, personal-profile work or scheduling occurred in this acceptance run.
