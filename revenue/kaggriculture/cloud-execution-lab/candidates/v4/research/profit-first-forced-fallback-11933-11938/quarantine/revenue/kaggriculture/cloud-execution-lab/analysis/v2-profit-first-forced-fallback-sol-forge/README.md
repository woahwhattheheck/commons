# TITAN V2 profit-first forced-fallback priority arm

Operation: `titan-v2-profit-first-forced-fallback-20260909-sol-forge-01`

## Why this arm exists

Frozen V2 made two coupled decisions when selecting the single product whose
sale schedule may be changed on a turn:

```python
eligible = positive_gain or forced_feasibility
rank = (forced_feasibility, worst_relative_gain)
```

`forced_feasibility` means the product's inherited reference schedule failed
the scheduler's capacity/admission certificate and `optimize_lot` found a
feasible replacement.  The Boolean-first rank therefore makes every forced
candidate outrank every ordinary candidate, even when the forced candidate has
a negative modeled gain and an ordinary candidate has a positive robust gain.

The existing SOL-KEEL arm correctly exposes that inversion, but its strict
replacement also removes forced admission:

```python
eligible = positive_gain
rank = worst_relative_gain
```

That is a useful combined ablation, not an isolated priority repair.  In an
all-forced/no-positive state it leaves `best=None`, so the controller can retain
the same reference schedule that the feasibility certificate rejected.

This lane isolates the ranking seam while preserving the fallback:

```python
eligible = positive_gain or forced_feasibility
rank = (positive_gain, worst_relative_gain)
```

Every feasible positive-gain candidate now outranks every non-positive forced
candidate.  If no positive candidate exists, the highest-valued forced plan is
still selected.  Positive forced plans compete normally by gain.

## Exact source boundary

The materializer:

- pins frozen V2 scheduler Git blob
  `7c068b7078c3d7c09bb3836590ad42b0af934cdf`;
- pins frozen V1 scheduler Git blob
  `cbc502a92fe9d790cfaf763f6990d1057bc9b82d` in the receipt;
- hash-binds the merged closure copier at
  `e7740bbd2f5ad71f565073445535d6941184288c`;
- replaces exactly one three-line selector block in a temporary copy;
- proves every regular file except `scheduler.py` is byte-identical;
- retains V2 target-domain, future-rival, continuation-value, queue-rewrite,
  and forced-admission markers exactly once; and
- never mutates frozen variants, canonical build paths, configs, archives,
  pointers, provider state, or Kaggle state.

## Predecessor-discriminating contracts

`test_materialize.py` imports the real frozen scheduler and both materialized
arms.  It proves:

| State | Frozen V2 | strict KEEL | profit-first fallback |
|---|---|---|---|
| CARROT `-5 forced`, MILK `+1 ordinary` | CARROT | MILK | MILK |
| CARROT `-5 forced`, no positive candidate | CARROT | no corrective sale | CARROT |
| CARROT `-5 forced`, MILK `-1 forced` | MILK | no corrective sale | MILK |
| CARROT `+2 forced`, MILK `+1 ordinary` | CARROT | CARROT | CARROT |

The second row is the safety discriminator missing from the strict arm.  The
first row isolates the score-facing priority inversion.

## Execution custody

This lane reuses four reviewed SOL-KEEL helpers only through exact Git-blob
bindings:

- closure-verifying, arm-distinct entry wrappers;
- import-time full payload closure and scheduler verification;
- candidate-only returned-action digests captured before interpretation;
- exact official 720-step lifecycle and 719 candidate-action cardinality;
- literal four-seed, two-opponent, both-seat grid;
- distinct invocation IDs and exact engine/loader/evaluator/limit identities;
- opponent and opponent-by-seat own-cash admission; and
- retained raw reports, materialization, binding, evaluator, and comparison
  receipts for every hosted outcome.

The workflow runs frozen V2 control first and this priority-only candidate
second.  A green workflow means only that the exact fixed panel met the broad
own-cash screen.  It is not a leaderboard, promotion, merge, or submission
claim.

## Local/source contracts

From this directory in an exact repository checkout:

```bash
python -B -m unittest -v test_materialize.py test_delegate.py test_workflow.py
```

The hosted workflow additionally materializes both executable closures, runs
`build_integrated.py --check`, executes the official panel, validates live
closures after execution, publishes a readable report, and retains the entire
evidence directory.
