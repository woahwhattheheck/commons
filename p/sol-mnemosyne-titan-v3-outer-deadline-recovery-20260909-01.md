# SOL-MNEMOSYNE — TITAN V3 outer-deadline recovery capsule

Status: **SOURCE-READY CANDIDATE / NO STRENGTH CLAIM**

## Coordination

- Slack claim: https://tokenjunkielabs.slack.com/archives/C0C1DLNJG5N/p1788989690914599
- exact-source correction: https://tokenjunkielabs.slack.com/archives/C0C1DLNJG5N/p1788990069408149?thread_ts=1788989690.914599&cid=C0C1DLNJG5N
- branch: `sol/mnemosyne-titan-v3-outer-recovery-20260909-01`
- fresh base: `61c459798a52a847a1b7d47476dc46bb0f866030`
- operation: `titan-v3-outer-deadline-recovery-capsule-20260909-01`

## Exact source preimage

At the fresh base, and still byte-identical on checked main `78b77d25ca2dcaf7a2dbb901f2175301d1ee8630`:

- canonical `main.py` Git blob: `4a8cf7bcda1f0fea231a144692cb84a779a9e73e`
- canonical `titan_runtime.py` Git blob: `b952c9c228ecbde592bf3d2df01638677abb0d24`
- Arlene Git blob: `bdb9cf58148a3c7961c085f4902759537decabf6`

The candidate does not modify any of those files.

## Proven structural predecessor

Canonical whole-call deadline containment marks the object unready and discards the entire instance without transferring the committed route/seller fields that `TitanAgent._initialize()` uses for reconstruction. Arlene commits route switches only at exact turns 226, 360, and 433. A fresh post-checkpoint object therefore cannot recover a previously selected tail and starts at `MAIN`; prior queued seller replay state disappears with the object.

The outer handler itself does not record the current public observation. However, exact runtime review proved the observation may already be represented safely before the outer timer fires: a successful action commits it as the seller checkpoint before late finalization, while the inner-deadline path queues it before its own late finalizer. Only an earlier outer interruption leaves it genuinely missing.

The local lifecycle tests execute the missing-observation sequence at turn 360 and prove predecessor turn 361 returns `MAIN`. They also execute the completed-checkpoint sequence and prove that blindly recording step 360 would double-observe it. These are deterministic source/lifecycle witnesses, not evidence that a submitted leaderboard game activated the outer timer.

## Candidate

New additive candidate paths only:

- `revenue/kaggriculture/cloud-execution-lab/candidates/v3-outer-recovery-sol-mnemosyne/recovery_main.py`
- `.../audit_current.py`
- `.../test_recovery_main.py`
- `.../test_audit_current.py`
- `.../test_current_entrypoint_integration.py`
- `.../README.md`
- `.github/workflows/titan-v3-outer-recovery-mnemosyne.yml`
- this receipt

After a contained outer timeout returns, the wrapper classifies current-step coverage as checkpointed, queued, or missing. It invokes TITAN's same-step-idempotent recorder only for the missing case, then transfers only content-addressed deep copies of `_completed_route`, `_completed_seller_state`, and `_seller_fallback_observations`. It validates the complete replay schema and chronology and rejects malformed, future, reordered, cross-player, cross-board, non-integer, digest-mismatched, or factory-drifted state. It excludes interrupted finalizer objects and clears continuity at true episode step zero.

## Executed local evidence

Standalone staging commands:

```text
python -m unittest -v
Ran 29 tests
OK (skipped=3)

python -m py_compile *.py
PASS
```

The three skips are deliberately repository-bound tests that load current `main.py` and the real current deadline timer: predecessor loss, missing-observation recovery, and completed-checkpoint no-double-replay. The branch workflow runs all three in the full checkout, then runs the current-source AST audit twice and requires byte-identical receipts.

## Self-review correction

The first published commit called the fallback recorder on every outer discard. Before admission, exact runtime review found the completed seller checkpoint is published before a late `_finish_production`; an outer interruption there means the current observation is already covered. The corrected commit adds explicit coverage proof and a real-entrypoint regression test. The earlier commit is not admissible and must not be promoted independently.

## Non-overlap and limits

No canonical `main.py`, `titan_runtime.py`, route source, config, archive, pointer, evaluator, provider, Kaggle, submission, or spend mutation. SOL-RATCHET retains final action-cardinality/main-hook and own-score-gate ownership; SOL-PARALLAX retains replay open-loop route analysis. No promotion or score claim exists until an exact official-engine paired panel observes activation and demonstrates no new failures, deadline overruns, or material regression.
