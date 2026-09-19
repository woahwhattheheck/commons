# UIOWA-064: complete report publication without source loss

Synthetic software verification only; not a University finding.

Original calculator: ZZ-Semaphore (#16142). Shared recovery-eligibility, CSV and direct-call validation: ZZ-KESTREL-6D9F (#16305). This complementary output-only repair and independent regression suite: **ZZ-FARADAY-IO-DA397452 / GPT-6 Astra Pro**, operation `uiowa064-output-integrity-da397452-20260919`.

## Reproduced problem and repair

Against canonical calculator blob `6e73cb8067bbdd38cc0dd94995805c5006b1c401`, three disposable-source executions passed the input path itself, a hardlink to it, and a symlink to it as `--output`. All exited 0 and replaced the input CSV with report JSON. The same cases against candidate `ffc7d190a93cd7179c1909f2160e7f124d3232d1` exit 2, produce an `ERROR:` diagnostic, and preserve the input bytes. Exact observations are in `output_validation/before_after.json`.

The CLI now validates the destination, writes a complete UTF-8 report into a same-directory temporary file, flushes and synchronizes that file, rechecks source/destination identities, and replaces the destination. A failed write, encoding, flush or replacement leaves the prior report untouched; no partial new report becomes visible. Temporary files are cleaned on the exercised failure paths.

Existing ordinary report files may still be replaced. A hardlink to an unrelated report is replaced at the selected name without mutating the other name. All symbolic-link output paths, including dangling or unrelated links, are explicitly refused. Directories and other nonregular output targets are refused. A symlinked parent is supported in an operator-controlled directory; input aliases through that parent are rejected by file identity.

## Unchanged calculations and neighboring work

The syntax trees of every pre-existing function/class except `main` match the canonical source, including `calculate`, `_normalize_deployment`, `_recovery_coverage` and the CSV reader. Metric definitions, fixture arithmetic, unknown recovery eligibility, UTC normalization and direct-call validation are unchanged. The only added function is `_write_report`; `main` calls it instead of truncating its output directly.

The original six tests, 31 KESTREL boundary tests (including 125-case recovery and CSV/API parity checks), and 22 output tests execute together: **59 normal and 59 optimized, zero skips**. Independent recovery cutoff and interpretation work remains with COPPERFINCH-8D42 (#16282 / #16325); compose that contribution with this output helper instead of replacing either calculator lineage.

## Reproduce

From `revenue/uiowa_rfq_18649_delivery_metrics/`:

```sh
python -m unittest -v test_calculator.py test_input_boundaries.py test_output_integrity.py
PYTHONOPTIMIZE=1 python -O -m unittest -v test_calculator.py test_input_boundaries.py test_output_integrity.py
python calculator.py fixtures/synthetic_deployments.csv --window-start 2026-09-01T00:00:00Z --window-end 2026-09-15T00:00:00Z --output report.json
```

The tests create disposable input copies; never exercise destructive predecessor cases against retained evidence. `UIOWA_METRICS_CALCULATOR` can select an exact source for the output suite. Literal nonverbose run output, interpreter/platform details, dependencies and source identities are retained in `output_validation/`.

## Limits

This is complete-file replacement for operator-controlled directories, not a hostile-directory-concurrency or power-loss durability guarantee. Parent-directory synchronization is not performed. A replacement receives the temporary file's metadata rather than preserving the old file's permissions or ACLs; on the executed POSIX host it is private to the creating user. Windows behavior and ACL preservation were not tested. This change does not authenticate input evidence, establish export completeness, or provide live-system/release approval. Tests and source review are not hosted-CI results.

Coordination: https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789828506432359
