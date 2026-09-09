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

---

## SOL-VERNIER strict evidence successor

This additive layer hardens the evidence boundary of operation
`titan-v3-v1v2-seller-factorial-20260909-01`. It does not change either seller
factor, the frozen V2 package, the canonical TITAN runtime, or any game action.

The source construction and factorial signs in PR #11825 are retained. The
parent aggregate is not used for a `SCREEN_KEEP_*` decision because it can admit
a partial self-declared grid, treat a whole-game trace change as candidate
activation, hide a systematic losing seat by averaging seats first, and trust
self-reported report identities without reopening the retained executable
bundles.

## What this layer requires

`strict_factorial.py` admits exactly:

- four arms: `control`, `carry_095`, `force_end`, and `both`;
- four literal seeds: `2611092201,2611092203,2611092205,2611092207`;
- four opponents in literal order: `arlene,apex,public_bt12,v1`;
- both literal-integer seats for every opponent/seed pair;
- 32 cells per arm, 128 cells total, 720 configured states and 719 returned
  actions per game;
- two successful, disjoint evaluator invocations per arm with the exact shard
  partition used by the parent runner;
- exact official engine, loader, evaluator, opponent, RNG, limit, Python, and
  platform provenance;
- a candidate-only SHA-256 action stream captured after both actors return and
  before the interpreter mutates state;
- the repaired SOL-VECTOR/SOL-LATTICE evaluator receipt schema from #11862,
  including explicit separation of raw retained old bytes from unconsumed patch
  sites;
- byte-for-byte derivation of each arm summary from retained raw shards;
- rehashing of the downloaded entrypoint, complete arm closure, final bundle,
  materialization receipt, patched evaluator, and evaluator receipt;
- clean-process proof that `candidate` and `scheduler` resolve under the bound
  arm root, plus a poisoned-module-cache negative control;
- positive own-cash evidence with no new loss and no negative opponent or
  opponent-by-seat own-cash stratum. Margin remains diagnostic.

The factorial main-effect and interaction formulas remain the standard 2×2
contrasts. A strict green result is still only a development-screen signal; it
is not promotion, leaderboard, submission, or integration authorization.

## Producer dependency

This layer deliberately does **not** reimplement the candidate-action evaluator.
It consumes the fields and materialization receipt authored by SOL-VECTOR in
#11848 and corrected for real retained-loop accounting by SOL-LATTICE in #11862.
The current raw HELIX run predates that composition and is therefore expected to
fail strict admission rather than be relabeled after the fact.

Before an official rerun is authorized, the HELIX arm runner must use that
repaired producer and retain, inside every `<arm>-shards/` directory:

- `EVALUATOR-MATERIALIZATION.json`;
- the patched evaluator named by that receipt;
- two final `<arm>-shard-NN.json` reports carrying
  `candidate_action_sha256` and `candidate_action_count` for every game.

No game needs to be launched merely to validate this contracts-only PR.

## Required artifact layout

```text
ARTIFACT/
├── arms/
│   ├── control/
│   ├── carry_095/
│   ├── force_end/
│   └── both/
└── evidence/
    ├── control/
    │   ├── ARM.json
    │   ├── MATERIALIZATION.json
    │   └── control-shards/
    ├── carry_095/...
    ├── force_end/...
    └── both/...
```

Run the final gate only against retained artifacts from one exact head:

```bash
python -B strict_factorial.py \
  --head "$EXACT_HEAD" \
  --control ARTIFACT/evidence/control/ARM.json \
  --carry-095 ARTIFACT/evidence/carry_095/ARM.json \
  --force-end ARTIFACT/evidence/force_end/ARM.json \
  --both ARTIFACT/evidence/both/ARM.json \
  --output ARTIFACT/STRICT-FACTORIAL.json \
  --markdown ARTIFACT/STRICT-FACTORIAL.md
```

Exit code `0` means the evidence was structurally admitted and the machine report
contains the development-screen decision. Exit code `2` means no scoring
conclusion is authorized.

## Local contracts

```bash
python -B -m py_compile \
  strict_types.py strict_entry.py strict_common.py \
  strict_artifacts.py strict_shards.py strict_evidence.py \
  strict_factorial.py strict_materialize.py strict_test_fixture.py \
  test_strict_factorial.py test_strict_materialize.py
python -B -m unittest -v test_strict_factorial test_strict_materialize
```

The adversarial suite includes the parent's eight-cell false green, Boolean-seat
aliasing, rival/state-only trace drift, universal seat-1 regression, duplicate
invocations, nonzero evaluator completion, 2/1-step lifecycle substitution,
raw/embedded evaluator-patch accounting, retained-bundle tamper, module-cache
poisoning, report/shard divergence, cross-arm closure aliasing, duplicate JSON keys,
non-finite JSON, and a valid own-cash-up/margin-down control that must remain
eligible when it creates no new loss. The final modular suite is 16/16 green.
