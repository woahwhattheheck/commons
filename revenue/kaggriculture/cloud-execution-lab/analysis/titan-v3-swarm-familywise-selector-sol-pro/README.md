# TITAN V3 swarm familywise selector

TITAN is currently evaluating many candidate arms in parallel. A correct per-arm
screen is not sufficient when the swarm chooses the best-looking result from the
whole batch: repeated candidate screening, mirrored seat rows, repeated seeds,
and optional early looks can manufacture an apparent winner even when no arm has
selection-safe evidence.

This packet adds the missing gate between **per-arm evidence** and **one-tree
nomination**. It changes no policy, route, runtime, configuration, canonical
archive, release pointer, provider state, Kaggle state, or submission.

## What it closes

The gate composes four evidence requirements in one fail-closed receipt:

1. **Pre-score family registration.** Every arm, candidate closure, common
   control, engine, evaluator, loader, configuration, opponent byte identity,
   seed, seat, family alpha, and maximum number of looks is registered and
   canonically hashed before scores are inspected. Git history supplies the
   ordering proof; changing the family changes the registration digest.
2. **Independent experimental units.** Opponents and both mirrored candidate
   seats are blocked inside one environment-seed effect. They are diagnostics,
   not independent sign draws.
3. **Mechanistic and competitive safety.** Score movement requires a changed
   candidate action-stream digest. A candidate is rejected for any negative own
   cash cell, any W/T/L rank regression, any negative opponent-by-seat own-cash
   mean, or any negative opponent-by-seat margin mean.
4. **Selection correction.** Each arm gets an exact rational one-sided sign tail
   over nonzero seed clusters. Holm's step-down procedure includes every
   registered arm, including rejected and no-signal arms. Family alpha is also
   divided over every predeclared look, so optional peeking cannot silently reuse
   the full threshold.

Distinct candidate closures that behave identically on the panel are reported as
behavior aliases. They remain separate hypotheses; a duplicate-looking result
never shrinks the family after scores are known.

## Why this is not another per-arm selector

The current evidence swarm already contains the pieces this package consumes:
closure-complete arm accounting (PR #11774), seed-cluster correction for mirrored
panels (PR #11998), and W/T/L non-regression (PR #11996). The unclosed boundary is
**cross-arm and cross-look selection**. A swarm can run ten individually correct
5% screens and still choose a false positive unless the ten hypotheses are
accounted for together.

`swarm_family_gate.py` therefore requires one complete family on one exact grid.
It will not accept a folder containing only the surviving or best-looking arms.

## Predecessor-killing witness

`build_multiplicity_witness.py` constructs a deliberately synthetic four-arm
family. Every arm has five positive independent seed clusters, zero negative
cells, action activation, positive own cash, positive margin, and no W/T/L
regression.

Individually, every arm has exact one-sided sign tail:

```text
p = (1/2)^5 = 1/32 = 3.125%
```

A naive 5% per-arm selector would emit four advances. The complete-family Holm
receipt instead gives every tied arm adjusted tail:

```text
p_adjusted = 4 * (1/32) = 1/8 = 12.5%
```

The retained result is `MORE_EVIDENCE`, with zero selection-safe advances. This
is an adversarial statistical fixture, **not real gameplay evidence**.

Retained files:

- `MULTIPLICITY-REGISTRATION-RECEIPT.json`
- `MULTIPLICITY-SELECTION-RECEIPT.json`
- `MULTIPLICITY-WITNESS-SUMMARY.json`

The workflow rebuilds all three into a temporary directory and requires exact
byte identity.

## Input contract

The registration is strict JSON. Unknown fields fail closed.

```json
{
  "schema_version": 1,
  "family_id": "titan-v3-next-family",
  "source_commit": "40 lowercase hex characters",
  "family_alpha": {"numerator": 1, "denominator": 20},
  "max_looks": 1,
  "execution": {
    "control_sha256": "64 lowercase hex characters",
    "engine_sha256": "64 lowercase hex characters",
    "evaluator_sha256": "64 lowercase hex characters",
    "loader_sha256": "64 lowercase hex characters",
    "configuration_sha256": "64 lowercase hex characters",
    "opponents": ["arlene", "v1"],
    "seeds": [1, 2, 3, 4, 5, 6, 7, 8],
    "seats": [0, 1],
    "opponent_sha256": {
      "arlene": "64 lowercase hex characters",
      "v1": "64 lowercase hex characters"
    }
  },
  "candidates": [
    {"arm_id": "candidate-a", "candidate_sha256": "64 lowercase hex characters"},
    {"arm_id": "candidate-b", "candidate_sha256": "64 lowercase hex characters"}
  ]
}
```

Generate and commit the pre-score receipt:

```bash
python swarm_family_gate.py register REGISTRATION.json \
  --output REGISTRATION-RECEIPT.json
```

The panel must reference that exact `registration_sha256`, contain exactly every
registered arm, and include the complete opponent × seed × seat Cartesian grid
for every arm:

```json
{
  "schema_version": 1,
  "family_id": "titan-v3-next-family",
  "registration_sha256": "digest emitted by register",
  "panel_id": "exact-head-development-look-1",
  "look_index": 1,
  "arms": [
    {
      "arm_id": "candidate-a",
      "rows": [
        {
          "opponent": "arlene",
          "seed": 1,
          "seat": 0,
          "control_own": 100,
          "control_rival": 90,
          "candidate_own": 101,
          "candidate_rival": 90,
          "control_action_sha256": "full control action-vector digest",
          "candidate_action_sha256": "full candidate action-vector digest"
        }
      ]
    }
  ]
}
```

The example row is only illustrative; a real panel must include the full
registered grid. Analyze it with:

```bash
python swarm_family_gate.py analyze REGISTRATION.json PANEL.json \
  --output SELECTION-RECEIPT.json
```

## Verdicts

- `REJECT`: a strict own-cash, W/T/L, or opponent-by-seat competitive safety
  condition failed.
- `NO_SIGNAL`: no action-bound positive own-cash signal exists.
- `MORE_EVIDENCE`: the arm is clean but does not clear the spent seed-cluster
  threshold after complete-family correction.
- `ADVANCE_SCREEN`: the arm clears the mechanistic gates and exact adjusted
  threshold. This nominates it for independent confirmation only.

The family receipt may name `recommended_for_confirmation` only among arms that
already clear the familywise gate. The deterministic handoff order prioritizes
worst opponent-by-seat own cash, then mean own cash, then mean margin. It is not a
claim that the observed top arm is the true best policy.

## Validation

```bash
python -m py_compile \
  swarm_family_gate.py \
  test_swarm_family_gate.py \
  build_multiplicity_witness.py
python -m unittest -v test_swarm_family_gate.py
python build_multiplicity_witness.py --output-dir /tmp/titan-familywise-witness
cmp MULTIPLICITY-REGISTRATION-RECEIPT.json \
  /tmp/titan-familywise-witness/MULTIPLICITY-REGISTRATION-RECEIPT.json
cmp MULTIPLICITY-SELECTION-RECEIPT.json \
  /tmp/titan-familywise-witness/MULTIPLICITY-SELECTION-RECEIPT.json
cmp MULTIPLICITY-WITNESS-SUMMARY.json \
  /tmp/titan-familywise-witness/MULTIPLICITY-WITNESS-SUMMARY.json
```

The focused suite currently contains 36 contracts covering exact sign tails,
Holm monotonicity and ties, registration ordering, complete-family enforcement,
cross-arm control drift, exact-grid custody, candidate closure aliasing,
mirrored-seat clustering, repeated-look alpha spending, action-bound score
movement, own-cash regressions, W/T/L regressions, opponent-by-seat margin
regressions, nonfinite/boolean input, deterministic receipts, and CLI readback.

## Statistical boundary

The exact sign calculation assumes independent, exchangeable environment-seed
cluster signs under the null. Blocking prevents known seat/opponent
pseudo-replication; it does not prove that a seed bank is representative of the
hosted leaderboard. `ADVANCE_SCREEN` remains a development-screen result, never
canonical, release, leaderboard, payment, or submission authority.
