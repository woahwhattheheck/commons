# E7 post-town-tick sale: recovered V3.1 source

## Canonical destination and status

This directory is source custody within the sole `main:revenue/kaggriculture/cloud-execution-lab/candidates/v4` workspace. It is NOT an enabled production policy, a new V4 variant, or evidence of a current V4 score improvement. Follow the workspace CANONICAL.json and INTEGRATION.json. Do not execute the legacy r04 materializer against the current production ABI.

## Original source and exact objects

Recovered unchanged from unmerged PR #12459, branch `astra/e7-parent-contract-20260911`, final source commit `24f58903e819825f2d07163f86dc2337a33a01eb`. This is the repaired successor to closed, unmerged #12430. Mechanism authorship and review history remain with those original PRs.

Original paths were beneath `candidates/v3/experiments/`:

| Relative file | Exact Git blob |
| --- | --- |
| e7_post_tick_evening_flush.py | e5ed61613cfa8a6d23809166d9310a8f569a65d4 |
| test_e7_post_tick_evening_flush.py | 999a4c2e2fc3f26fe8ea32e81f8b6b04e28f8bfc |
| e7_post_tick/candidate.py | 83072e8ee2bbe50c4ecee5787180df8163287f21 |

These are exact donor bytes, not a path-adapted runnable V4 package. Their imports and evaluator configuration refer to the original V3.1 R04 layout. Bind dependencies and parent semantics explicitly during the production-ABI port; do not hide import failures with mocks and call that a materialized gate.

## Evidence boundary

Historical source workflow run `34584285975`, job `103214777183`, reported success on original head `24f58903e819825f2d07163f86dc2337a33a01eb`, including E7 coherence/tests and package-byte-neutrality steps. Detailed job-log retrieval returned HTTP 404 during this recovery. No fresh source execution against current main, current V4 package build, paired economics gate, leaderboard gain, or submission is claimed here.

The earlier recovery commit `1b57582d7532268be1a6d83f94d300f91454fb4b` on `titan/v4-20260911` is now donor history only. A Slack rate-limit gap concealed the canonical-main migration during that first recovery; the stale #12620 handoff was corrected in place. Do not continue the retired branch or merge its legacy materializer into current production.

## Required before activation

Port the existing mechanism once, without a duplicate feature key. Rebind to the exact current V4 parent; preserve native market rows and lockstep indexes; demonstrate disabled callable/action identity; run the real materialized source tests and paired/common-gate seeds, seats and opponents with actual activation and economic attribution. Audit terminal-turn withholding, stale pending state, and malformed release state before activation. Recovered code stays unwired until those conditions are met.

This custody addition changes no production runtime, overlay wiring, feature default, workflow, manifest, archive, or Kaggle submission.
