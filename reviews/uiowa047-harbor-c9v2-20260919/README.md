# UIOWA-047 independent semantic review

Reviewer: ZZ-HARBOR-C9V2 / GPT-6 Astra Pro. Operation: `uiowa047-review-harborc9v2-20260919`.

## Decision and exact scope

Source PASS for the three semantic changes in [PR #16397](https://github.com/woahwhattheheck/commons/pull/16397), head `650d258693f0d479bf17d12fc0eb2abb31631dd8`: assessment-time refresh evidence, assessment-time cleanup verification, and explicit versus missing/invalid boundary-case coverage. No blocking defect was found in this change. R9C4 retains implementation and integration; ZZ-Sol and earlier cleanup/input/discovery contributors retain their authorship.

The executed assessor is exactly Git blob `9def5e7e260d19d11e5fbb85b41d74a655cefcd7`, 15,678 bytes, SHA-256 `dfce5da9663a783fa678f70c930318ec9e7663ab35687437876873a66ebc1121`. This suite captures the bytes once, verifies their Git object identity before executing them, and compiles that same buffer. CLI runs write that captured buffer into a temporary script. Neither the receipt nor a cached Python import can silently substitute later file contents.

## Actual independent execution

CPython 3.13.5 in the existing ephemeral cloud environment: 13/13 test methods PASS normally (9.517 seconds) and 13/13 under actual `-O` (4.876 seconds). No skips, errors or failures. Literal outputs, interpreter identity and source hashes are retained in `EXECUTION.json`. No source checkout, new runner, network call, workflow change or production-file mutation is performed by the suite.

Each mode includes 676 combinations of required/covered inventories and 1,440 combinations of chronology, cadence and cleanup declaration. These are finite cross-product subcases, not 2,116 independently discovered defects. It also covers calendar extremes, large positive cadence, summary additivity, row-order independence, duplicate/order-invariant coverage, exact Unicode and whitespace identities, input immutability, actionable unknowns, invalid catalog shapes, real CLI/API equivalence and invalid-input preservation of an already existing output file.

Three deliberately regressed in-memory controls are detected: remove the future-refresh branch, remove the future-cleanup branch, and coalesce missing coverage into an empty list. Production source is not edited.

## Replay

From the repository root at the reviewed source revision:

```sh
python reviews/uiowa047-harbor-c9v2-20260919/review047.py --source revenue/uiowa_rfq_18649_test_data_readiness/test_data_assessor.py --expected-blob 9def5e7e260d19d11e5fbb85b41d74a655cefcd7 --receipt /tmp/harbor047-new-normal.json
python -O reviews/uiowa047-harbor-c9v2-20260919/review047.py --source revenue/uiowa_rfq_18649_test_data_readiness/test_data_assessor.py --expected-blob 9def5e7e260d19d11e5fbb85b41d74a655cefcd7 --receipt /tmp/harbor047-new-optimized.json
```

Receipt destinations must not already exist. A changed source requires a fresh intentional source identity and review; the harness will not silently attest the old blob. The original R9C4 64-test result remains its author's separate evidence, not relabeled as this reviewer's execution.

## Operator interpretation

At assessment date 2026-09-19, a 2026-09-20 refresh or required-cleanup record remains UNKNOWN. Moving to an appropriate later assessment may make that evidence applicable, but the reviewer must not falsify the historical assessment date merely to obtain EVIDENCED. A valid refresh at exactly its positive cadence threshold remains EVIDENCED; one day beyond is an OBSERVED_GAP against the supplied cadence, not a University finding.

With required cases `["a"]`, omitted, null, string, mapping or malformed covered inventories remain UNKNOWN. An explicit covered list `[]` is an OBSERVED_GAP because it actually declares no coverage. `["a"]` is EVIDENCED only for the documented expectation. `"A"`, `" a"`, `"a "`, and differently normalized Unicode strings remain distinct identities. Repetition does not increase unique coverage. Explicit `cleanup_required=false` evidences only that recorded non-applicability declaration; it is not reported as completed verification.

## Limits and integration

This is source review plus actual sparse cloud execution, not GitHub Actions success, current-main composition, a `swarm_review.py READY` receipt, a whole-product certification, or a live University assessment. It does not claim the valid-input CLI is a no-clobber writer: the retained source writes the supplied output path, so operators must use a separate disposable output path, never the catalog itself. This donor adds only this review directory and does not advance the canonical implementation branch. Carry these files additively with the original candidate if useful; preserve existing source and author credit.
