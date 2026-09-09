# SOL-BULWARK — TITAN V2 target-domain ablation receipt

- Operation: `titan-v2-target-domain-ablation-20260909-sol-bulwark-01`
- Starting main: `d0a64314ec699e468613641754d679340c74f735`
- Frozen V1 scheduler Git blob: `cbc502a92fe9d790cfaf763f6990d1057bc9b82d`
- Frozen V2 scheduler Git blob: `7c068b7078c3d7c09bb3836590ad42b0af934cdf`
- Frozen V1/V2 entrypoint SHA-256:
  `2e4897fb3aa8b0bee3e97709808c3aa25fa5055bcf5ce7d433b493eb334870f2`
- Canonical/frozen/runtime/config/archive/pointer mutation: **none**
- Provider/Kaggle action: **none**

## Boundary

This experiment changes one expression in a temporary copy of frozen V2. It
restores V1's scheduler ownership domain—baseline SELL products plus previously
pending scheduler intent—while leaving every other V2 source byte unchanged.

The repository receives only additive experiment code, tests, workflow, and this
receipt. Frozen V1, frozen V2, canonical TITAN, release archives, current
pointers, and provider state remain untouched.

## Local acceptance

- `python -m unittest -v test_materialize.py test_compare.py`: **11/11 PASS**
- `python -m py_compile materialize.py compare.py test_materialize.py test_compare.py`: PASS

Contracts cover exact one-factor copying, target-domain semantics, duplicate
patch needles, source-blob drift, non-regular members, complete paired grids,
closure distinction, provenance drift, action-only no-score changes, broad own
cash upside, and regressions.

## Hosted evidence

The path-scoped workflow materializes the exact frozen V2 closure, runs identical
control/ablation official-interpreter games against frozen V1 and public Arlene
on both seats, and retains:

- source and patched closure identities;
- the exact unified scheduler diff;
- complete evaluator reports;
- per-cell action-trace and terminal-score deltas;
- first daily-bank divergence checkpoints;
- per-opponent own-cash and margin strata; and
- a machine-readable causal verdict.

Only `UPSIDE_SCREEN` exits green. That verdict is still development evidence,
not promotion or a hosted leaderboard claim.
