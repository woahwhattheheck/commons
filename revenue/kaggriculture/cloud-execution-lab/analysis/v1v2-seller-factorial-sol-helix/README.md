# TITAN V1/V2 seller-policy factorial — SOL-HELIX

Operation: `titan-v3-v1v2-seller-factorial-20260909-01`

## Why this exists

The frozen V2 scheduler changed several seller semantics at once. Two source-proven
changes are especially easy to confound:

1. **Artificial-horizon carry value** changed from V1's `0.95` modeled receipt to
   V2's full `1.00` modeled receipt. This can make spendable cash tie stock that
   remains exposed beyond the short planning horizon.
2. **Residual reference stock** changed from V1's forced horizon-end reference sale
   to V2's continuation-value treatment. This changes the optimizer's baseline and
   can hide otherwise executable liquidation schedules.

A one-factor carry ablation cannot tell whether the second seam contributes
independent recovery or interacts with the first. This package runs the exact 2×2:

| Arm | Carry factor | Residual reference stock |
|---|---:|---|
| `control` | 1.00 | continuation value |
| `carry_095` | 0.95 | continuation value |
| `force_end` | 1.00 | append at horizon end |
| `both` | 0.95 | append at horizon end |

All arms derive from the frozen V2 bundle. No canonical runtime, selected archive,
provider pointer, configuration, or Kaggle artifact is changed.

## Evidence custody

`materialize.py` verifies every file declared by `runtime/variants/v2/FREEZE.json`,
including the exact frozen scheduler SHA-256 and Git blob. It patches only the two
literal source seams, with before/after cardinality assertions. Each generated arm
contains a `bound_entry.py` that hashes its entire sibling closure before importing
`candidate.py`; post-binding mutation fails before the evaluator can call `agent`.

The workflow runs each arm in a separate matrix job with `fail-fast: false` and
`cancel-in-progress: false`. Every job uploads its materialization receipt, bound
bundle, shard reports, and final arm report under `if: always()`. A fifth job rejects
missing cells, duplicate cells, nonfinite scores, incomplete games, mismatched heads,
different evaluator/loader/engine identities, opponent drift, or unequal grids.
This prevents a cancelled arm from being mistaken for a negative result.

## Analysis

The unit of inference is an opponent/seed group averaged over both candidate seats.
The report computes:

- each non-control arm's own-cash and margin delta against frozen V2;
- carry and forced-reference main effects;
- the `A×B` interaction (`both - carry - force_end + control`);
- per-opponent strata, trace activation, catastrophic-group checks, and deterministic
  90% bootstrap intervals for mean own-cash effects.

A `SCREEN_KEEP_*` verdict means only that an arm deserves a current-V3 port and a
larger confirmation panel. It is not promotion authorization and is not a Kaggle or
leaderboard claim. `SCREEN_CONTROL` means the controlled panel found no arm that met
the development-screen gate. Structural failures produce `INVALID` and authorize no
scoring conclusion.

## Acceptance

```bash
cd revenue/kaggriculture/cloud-execution-lab/analysis/v1v2-seller-factorial-sol-helix
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  python -m unittest -v test_factorial.py
python -m py_compile materialize.py run_arm.py factorial_report.py test_factorial.py
```

The GitHub workflow performs the exact-source materialization and the 128-game
official-engine factorial against Arlene, Apex, Public BT12, and submitted V1 on four
fixed seeds and both candidate seats.
