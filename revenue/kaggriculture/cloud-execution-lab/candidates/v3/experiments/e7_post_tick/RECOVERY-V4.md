# E7 recovered into the one V4 tree

## Status

Recovered source only; NOT enabled in the production V4 agent. This record does not claim a V4 paired-score gate, leaderboard improvement, or submission authorization.

This preserves the final E7 source from unmerged PR #12459 (`astra/e7-parent-contract-20260911`) rather than resurrecting its superseded PR #12430. Original source commit: `24f58903e819825f2d07163f86dc2337a33a01eb`. Original mechanism and authorship remain with that source PR.

## Exact source objects

The following Git blob IDs were returned by direct reads of the original commit and are reused unchanged:

| File relative to candidates/v3/experiments | Git blob |
| --- | --- |
| e7_post_tick_evening_flush.py | e5ed61613cfa8a6d23809166d9310a8f569a65d4 |
| test_e7_post_tick_evening_flush.py | 999a4c2e2fc3f26fe8ea32e81f8b6b04e28f8bfc |
| e7_post_tick/candidate.py | 83072e8ee2bbe50c4ecee5787180df8163287f21 |

## Evidence and limits

Historical E7 source workflow run `34584285975`, job `103214777183`, reported success on source head `24f58903e819825f2d07163f86dc2337a33a01eb`, including the E7 coherence/tests and package-byte-neutrality steps. Detailed job-log retrieval returned HTTP 404 during this recovery. That historical source result is not a fresh gate against the current V4 parent.

At recovery parent `465f4263da1c98acf78889d67cdd21b61dbba145`, `build_v3.py` consumes the canonical archive, `overlay/`, `apply_v3.py`, and `apply_v4.py`. These experimental paths are outside those package inputs. This recovery changes none of the runtime/overlay/build/config/manifest/frozen archive files, no workflow, and no feature default. No fresh package build or V4 gameplay evaluation is claimed by this source-only commit.

## Promotion requirements

The evaluator entrypoint deliberately retains the original V3.1 R04 configuration; it is not a new V4 parent. Before runtime integration, bind the existing mechanism to the exact canonical V4 parent, demonstrate disabled callable/action identity, run its source tests with the real materialized router, and run paired/common-gate seeds and seats with observed activation and economics. Preserve incumbent native market rows and lockstep slot semantics. In particular, audit terminal-turn withholding, stale pending state, and malformed release state before activation.

Do not make another V4 tree or another E7 feature key. Continue source review from #12459 and consolidate accepted production wiring through the shared V4 integrator seam.
