# SOL-ASTRA — TITAN L02 branch-creation base repair

Operation: `TITAN-L02-BRANCH-CREATION-BASE-REPAIR-20260909-01`

Source review: merged PR #11795, GitHub review `5160098451`.

## Defect

PR #11795 correctly made the 192-game L02 panel conditional on actual executable L02 changes, but its workflow treated an unavailable push base by substituting `HEAD^`. On a branch-creation push GitHub supplies the all-zero `before` sentinel. A newly pushed multi-commit branch can therefore contain an L02 executable change before the tip commit while the tip itself changes only tests/docs/workflow; `git diff HEAD^ HEAD` then misses the earlier executable change and can incorrectly skip the required panel.

## Repair

- Preserve exact pull-request base SHA and ordinary nonzero push `before` SHA when available.
- Fetch a declared nonzero base if shallow checkout does not contain it.
- Treat zero, missing, or still-unavailable base as unknown and pass `--unknown-base` to `panel_trigger.py`.
- Never replace unknown branch history with `HEAD^`.
- Add a predecessor-discriminating workflow regression requiring the zero sentinel and fail-closed unknown-base path while forbidding the `git rev-parse HEAD^` fallback.

Unit tests remain unconditional. `candidate.py`, `ledger_tranche.py`, and `run_panel.py` still force the 192-game panel when they are observed changed; `workflow_dispatch` and unknown bases still force it. ADVANCE/REJECT gameplay semantics are untouched.

## Scope

Only:

- `.github/workflows/titan-v3-l02-ledger-tranche.yml`
- `revenue/kaggriculture/cloud-execution-lab/candidates/v3-l02-ledger-tranche/test_panel_trigger.py`
- this receipt

No candidate policy, runtime, selected archive, provider, Kaggle submission, or canonical release mutation.

Exact-head repository CI is authoritative for runtime validation; this connector publication does not claim a local full-suite run.
