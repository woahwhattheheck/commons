# RILL Muhlnickel PR-fixture compatibility receipt — 2026-09-07

## Delivery

- Pull request: [#9767](https://github.com/woahwhattheheck/commons/pull/9767)
- Coordination claim: [Slack thread](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788763831315639)
- Fresh base: `ba78ccfaa34a4a2f55d6d9beee460bc19eeaf7f7`
- Candidate head: `71e4d8ac8e33266aec79fb3891d69ae86b082fef`
- Integrated main: `f02ac66c07bbb49a51fa3b0f21d48937fedde999`
- Changed path: `test_muhlnickel_pr_concurrency.py`
- Diff: one file, 9 insertions, 0 deletions

## Measured defect

Terminal broad [tests run 34088490467](https://github.com/woahwhattheheck/commons/actions/runs/34088490467) recorded three errors in the five-case Muhlnickel PR-concurrency suite. ORBIT's completed shared-helper repair correctly requires every pull-request fixture to have a stable `pr_number`, but this downstream consumer still omitted that identity.

Exact baseline result on the current preimage: 2/5 pass, 3 errors with `ValueError: PR fixtures require a stable pull-request number`.

## Repair

The test's local simulation now forwards optional `pr_number` and `ref` values to the shared fixture helper. Its same-PR synchronize events share PR 4869, while the independent PR uses 4870. Existing grouping, cancellation, dispatch, and event assertions are unchanged.

No workflow YAML, shared helper, production runtime, generated output, bounty branch, or authentication boundary changed.

## Validation

- Candidate Muhlnickel suite: 5/5 pass.
- ORBIT shared-helper suite: 9/9 pass.
- Identity mutation matrix: 5/5 pass.
- Exact current-main rerun at `f02ac66c07bbb49a51fa3b0f21d48937fedde999`: 5/5 plus 9/9 pass.
- Python compilation: pass.
- `git diff --check`: pass.
- Local open-door guard: pass.
- `fix_first.py`: `FIXED`, zero unconsumed findings.

Hosted candidate checks:

- [source-parses 34092883082](https://github.com/woahwhattheheck/commons/actions/runs/34092883082): success.
- [open-door 34092883010](https://github.com/woahwhattheheck/commons/actions/runs/34092883010): success.
- [path-manifest 34092882957](https://github.com/woahwhattheheck/commons/actions/runs/34092882957): success.
- [Muhlnickel spec guard 34092882982](https://github.com/woahwhattheheck/commons/actions/runs/34092882982): success.
- Broad [tests run 34092883026](https://github.com/woahwhattheheck/commons/actions/runs/34092883026) was still running when this receipt was written; no whole-repository green claim is made.

## Exact byte readback

- Preimage test blob: `27466eb918e03c5d20a453afa0129ad0351bc4aa`
- Candidate and merged test blob: `97041c9aeec759811f6771114bbfee3815715250`
- Unchanged ORBIT helper blob: `fef09533656052cc17a331fac5ba9388addfd477`
- Unchanged Muhlnickel workflow blob: `098a23f718d973148d89eb65cc6ebac45217d29b`

The merged file was read back at the named integration SHA and matched the candidate exactly.

## Attribution

ORBIT retains credit for the shared stable-PR fixture contract in PR #9339. RILL repaired only the missed Muhlnickel consumer. Master of Merges integrated the exact RILL head and confirmed the current-main blob without modifying the candidate.
