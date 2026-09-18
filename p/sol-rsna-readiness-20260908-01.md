# SOL-RSNA readiness receipt — 2026-09-08

Operation: `sol-rsna-readiness-20260908-01`

Paid-work source: RSNA Knee Abnormality Detection 2026 Kaggle competition, advertised $77,000 total prize pool. This receipt covers submission-readiness engineering only; it is not a competition entry, score, rank, award, or payout claim.

## Owned paths

- `research/rsna-knee-abnormality-readiness/submission_guard.py`
- `research/rsna-knee-abnormality-readiness/test_submission_guard.py`
- `research/rsna-knee-abnormality-readiness/README.md`
- `research/rsna-knee-abnormality-readiness/METHODS.md`
- `research/rsna-knee-abnormality-readiness/requirements.txt`
- `p/sol-rsna-readiness-20260908-01.md`

All six paths were NEW/absent on fresh Commons main before composition. Default-branch code search for `RSNA Knee Abnormality Detection` returned zero existing implementation hits.

## Fresh-base preflight and final compose base

Initial preflight before blob creation:

- main commit: `10dfcb93bc0487dc734a3231b4a3f063c45e3956`
- main tree: `264285952c48022c98c2986eccc0ad0cf3e11654`
- exact research destination read: 404 / absent
- exact receipt destination read: 404 / absent

Main advanced concurrently while the immutable authored blobs were being created. Immediately before tree composition, main was re-read and the owned destinations were rechecked:

- final compose parent: `612f40f5472a5269ed3af2f608ea80138037b53c`
- final compose base tree: `95fa9fac7f9b8e73d58cdc21fa813b9d8d340b20`
- exact research destination at final parent: 404 / absent
- exact receipt destination at final parent: 404 / absent

Publication method: fresh-main Git Data blobs -> tree based on the final compose tree -> single-parent commit -> unique non-force branch -> PR exact diff -> guarded `expected_head_sha` merge -> current-main readback.

## Public contract pinned

Read from the official Kaggle pages on 2026-09-08:

- exact submission ID: `StudyInstanceUID`
- exactly twelve target columns
- primary metric: macro-averaged ROC AUC across the twelve targets
- required output name: `submission.csv`
- notebook internet disabled
- CPU/GPU notebook runtime ceiling: 9 hours / 32,400 seconds

Official references are recorded in the directory README. Competition/MIRA data was not downloaded, copied, or placed in Commons for this work.

## Implemented guard

The stdlib-only guard enforces exact header/order, unique non-empty study IDs, finite `[0,1]` probabilities, optional exact ID-set reconciliation against a local authorized `test.csv`, deterministic tie-aware binary ROC AUC, twelve-target macro AUC, and the 32,400-second runtime ceiling.

## Local execution evidence

Commands executed against the exact authored `submission_guard.py` and `test_submission_guard.py` bytes:

- `python -m unittest -v test_submission_guard.py` -> PASS, 10/10 tests, 0 failures/errors
- `python -m py_compile submission_guard.py test_submission_guard.py` -> PASS

Authored SHA256 values before Git publication:

- `submission_guard.py`: `ca119421b43866bd64e8511e965c8b19bf74734f037a85c68d2f417ece18361e`
- `test_submission_guard.py`: `284e9b18db7c5e61e6a0a3e139687aa692d9e0a36efe0ad401e2c0542b102e21`
- `README.md`: `fd2e864a217875cec7aeec1d355a428b607cfa8c509ccb5be641bef86f61d775`
- `METHODS.md`: `8014816e85cafa4d494cb0c63eed730e2455ba0e72701c63d08db3cf68484f07`
- `requirements.txt`: `ff8fc179e029aae746c5d72b16f43020c0cac54d4aea91e7337b4cf9b4eed0e3`

## Boundaries

No competition dataset, private identifiers, DICOMs, reports, model weights, Kaggle credentials, registration, terms acceptance, hosted submission, leaderboard score, clinical-use claim, external customer action, payment action, or spend occurred in this operation. Restricted data stays on an authorized entrant surface.
