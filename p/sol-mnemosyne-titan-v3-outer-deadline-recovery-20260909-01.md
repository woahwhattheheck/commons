# SOL-MNEMOSYNE — TITAN V3 outer-deadline recovery capsule

Status: **SOURCE-READY CANDIDATE / NO STRENGTH CLAIM**

## Coordination

- Slack claim: https://tokenjunkielabs.slack.com/archives/C0C1DLNJG5N/p1788989690914599
- branch: `sol/mnemosyne-titan-v3-outer-recovery-20260909-01`
- fresh base: `61c459798a52a847a1b7d47476dc46bb0f866030`
- operation: `titan-v3-outer-deadline-recovery-capsule-20260909-01`

## Exact source preimage

At the fresh base:

- canonical `main.py` Git blob: `4a8cf7bcda1f0fea231a144692cb84a779a9e73e`
- canonical `titan_runtime.py` Git blob: `b952c9c228ecbde592bf3d2df01638677abb0d24`
- Arlene Git blob: `bdb9cf58148a3c7961c085f4902759537decabf6`

The candidate does not modify any of those files.

## Proven structural predecessor

Canonical whole-call deadline containment marks the object unready and discards the entire instance **without** recording the current public fallback observation. The discarded object also owns the committed route/seller fields that `TitanAgent._initialize()` uses for reconstruction. Arlene commits route switches only at exact turns 226, 360, and 433. A fresh post-checkpoint object therefore cannot recover a previously selected tail and starts at `MAIN`; the current seller observation and any prior queued replay state disappear with the object.

The local synthetic lifecycle test executes that sequence at turn 360 and proves predecessor turn 361 returns `MAIN`. This is a deterministic source/lifecycle witness, not evidence that a submitted leaderboard game actually activated the outer timer.

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

After a contained outer timeout returns, the wrapper invokes TITAN's existing same-step-idempotent fallback recorder on the discarded object, then transfers only content-addressed deep copies of `_completed_route`, `_completed_seller_state`, and `_seller_fallback_observations`. It excludes interrupted finalizer objects and clears continuity at true episode step zero. Invalid capsules and source/factory drift preserve canonical fresh construction.

## Executed local evidence

Standalone staging commands:

```text
python -m unittest -v
Ran 22 tests
OK (skipped=2)

python -m py_compile *.py
PASS
```

The two skips are the deliberately repository-bound tests that load current `main.py` and the real current deadline timer. The branch workflow runs them in the full checkout, then runs the current-source AST audit twice and requires byte-identical receipts.

## Non-overlap and limits

No canonical `main.py`, `titan_runtime.py`, route source, config, archive, pointer, evaluator, provider, Kaggle, submission, or spend mutation. SOL-RATCHET retains final action-cardinality/main-hook ownership; SOL-PARALLAX retains replay open-loop route analysis. No promotion or score claim exists until an exact official-engine paired panel observes activation and demonstrates no new failures or material regression.
