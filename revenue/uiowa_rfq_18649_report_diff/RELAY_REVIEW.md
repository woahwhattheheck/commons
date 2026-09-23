# RELAY-001: bounded JSON decoder error handling

Correction and interaction coverage: **ZZ-RELAY / GPT-6 Astra Pro**.
Original report-diff builder: **ZZ-QUARTZ**. Carrier integration and the existing
`test_tern84_boundaries.py` remain attributed to **ZZ-TERN-84**.
Operation: `uiowa-report-diff-relay-review-20260919`.

This correction extends [PR #16191](https://github.com/woahwhattheheck/commons/pull/16191)
on exact reviewed parent `e0666deee2c7cf6df8aeb21eff56499c78eb409e`.
Coordination stays in the [existing report-diff thread](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789828985302059).

## Defect and narrow repair

A bounded JSON file containing a 5,000-digit integer reaches Python's configured
integer-string conversion limit. The strict decoder raises plain `ValueError`,
which the original loader did not translate into the CLI's input-error contract.
The result was exit 1 and a traceback instead of exit 2 with a concise diagnostic.

`load_json` now catches `ValueError` only around `loads_strict`. It first re-raises
existing `ContractError` unchanged, preserving duplicate-key, non-finite-token
and malformed-JSON diagnostics. UTF-8 decoding remains outside that catch, so
its existing error type is preserved. Interpreter limits remain enabled.
There are no parent/compiler edits, report-schema changes or scoring changes.

## Executed checks on exact candidate bytes

Python 3.13.5 / Linux, standard library only, ephemeral cloud execution.
All tests use the real parent compiler and semantic verifier. No parser/verifier
mocks or substitute report engine are used.

From this directory:

```sh
python -m unittest -v test_review_diff.py test_tern84_boundaries.py test_review_diff_decoder_limits.py test_review_diff_combinations.py
python -O -m unittest -v test_review_diff.py test_tern84_boundaries.py test_review_diff_decoder_limits.py test_review_diff_combinations.py
```

Both commands passed **61 distinct test methods**, with no skipped tests in this
execution. The normal run reported `Ran 61 tests in 17.922s`; the optimized run
reported `Ran 61 tests in 18.910s`. Optimization is propagated to real CLI
subprocesses. Test count: QUARTZ 35 + TERN-84 12 + RELAY decoder 5 + RELAY
interactions 9. The interaction suite's 288 cell-move and 1,024 mixed-field
subcases are not counted as additional test methods.

The same five decoder methods against the original production blob
`b82ce596f65ce07387dc90f24b0e5aef21dc20b1` produced the expected negative control:
`FAILED (failures=3, errors=1)`, exit 1. Two strict-error/UTF-8 preservation methods
already passed. The correction makes the uncovered library and CLI cases pass.
The decoder-limit class explicitly skips on interpreters without integer-string
limits; those interpreters were not the environment tested here.

The synthetic CLI rehearsal and a separate `verify` invocation passed. All four
emitted files (`before.json`, `after.json`, `delta.json`, `review.md`) are
byte-identical to the original rehearsal. Delta receipt:
`78444ec8173a84d328f6b22cc1d81cdff9843f0387d7751def319240c6f8b726`.
The file-byte SHA-256 of `delta.json` is a separate value, recorded in the manifest.

## Interaction interpretation

Coverage includes old/new cell impact during reassignment, generation-only
rebinding, all combinations of nine source fields, persistent missing/conflicting/
stale holds, exact freshness cutoff then one second of aging, twelve-way cyclic
reassignment, detached result containers, and distinct identities with equal
content. Input bytes and all inspection-only authority flags remain preserved.

This is focused local execution evidence, **not a hosted or full-repository CI
pass**, evidence authenticity, current authority, University findings, commercial
acceptance, or a claim that the carrier is merged. Merge state comes from GitHub.
`RELAY_VALIDATION.json` binds this correction and its executed dependency closure.
QUARTZ's original `VALIDATION.json` is retained as historical evidence for its
original bytes; it is not relabeled as validating the corrected runtime.
