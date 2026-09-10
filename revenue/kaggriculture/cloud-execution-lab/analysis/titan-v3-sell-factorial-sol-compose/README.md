# TITAN V3 SELL objective × certified-pressure interaction gate

This package closes the composition decision between two different SELL changes:

1. an **own-value objective**, which ranks plans by TITAN's own receipts plus continuation value rather than subtracting rival receipts; and
2. a **receipt-invariance-certified pressure repair**, which may move a sale across a pressure boundary only when the exact official-engine receipt is invariant through the declared rival-delay bound.

The earlier same-sized proxy rule is not this second arm. A zero score under one proxy rival quantity can be a rounded-price plateau rather than a dominance certificate. The `certified_pressure` input must therefore bind the stronger reviewed candidate: non-certified lots retain parent order, and only lots with exact receipt invariance through the public delay bound may be demoted.

Independent singleton screens cannot establish that the two valid changes compose. They target the same final market queue, and an antagonistic interaction can erase either gain. `interaction_gate.py` consumes four complete evaluator reports from one predeclared grid:

- `control`: neither change;
- `own_value`: objective change only;
- `certified_pressure`: receipt-invariance pressure repair only;
- `both`: both changes.

The gate runs no games and edits no runtime. It is an evidence consumer intended for the existing cloud evaluator and pre-interpreter candidate-action capture path.

## Evidence contract

All four reports must have identical evaluator provenance, opponents, seeds, limits, and RNG seed. Every report must contain the same complete `opponent × seed × seat` grid. Each game must be complete and bind:

- a 720-state / 719-action lifecycle;
- 719 pre-interpreter returned candidate actions;
- a candidate-action stream SHA-256;
- a complete trace SHA-256;
- terminal scores equal to the retained terminal bank snapshot.

The four entrypoint fingerprints must be distinct. If two arms have the same captured candidate-action stream for a cell, their deterministic trace and terminal banks must also be identical. Score or trace drift without returned-action activation is rejected as detached evidence. Finite inputs whose differences or aggregates overflow are rejected before a decision packet can be emitted.

## Decision rule

For every arm against control, the gate requires:

- at least one changed candidate-action stream;
- positive mean own-cash delta;
- nonnegative median own-cash delta;
- at least as many positive as negative cells;
- nonnegative mean margin delta;
- no new losses and no lost wins;
- the same non-regression conditions in every opponent-by-seat stratum.

The composed arm is selected only when it clears control and is noninferior to every eligible singleton globally and in every opponent-by-seat stratum. A larger pooled mean cannot rescue composition after a singleton-relative stratum regression. Otherwise the best eligible singleton is selected deterministically. The possible verdicts are:

- `SELECT_BOTH`
- `SELECT_OWN_VALUE`
- `SELECT_CERTIFIED_PRESSURE`
- `NO_SAFE_ADVANCE`
- `INACTIVE`

Every result explicitly keeps `promotion_authorized=false` and `hosted_leaderboard_claim=false`.

## Factorial diagnostics

For each paired cell, with terminal own cash `Y`, the gate computes:

```text
own-value main effect       = ((Y_own - Y_control) + (Y_both - Y_pressure)) / 2
certified-pressure main     = ((Y_pressure - Y_control) + (Y_both - Y_own)) / 2
interaction                 = Y_both - Y_own - Y_pressure + Y_control
```

The same difference-in-differences interaction is retained for margin. These diagnostics distinguish additive gains from cancellation or synergy; selection still follows the fail-closed non-regression gates above.

## Usage

```bash
python -B interaction_gate.py \
  --control /evidence/control.json \
  --own-value /evidence/own-value.json \
  --certified-pressure /evidence/certified-pressure.json \
  --both /evidence/both.json \
  --head "$GITHUB_SHA" \
  --output /evidence/FACTORIAL-DECISION.json \
  --markdown /evidence/FACTORIAL-DECISION.md
```

The JSON output retains the shared provenance, every per-cell arm state, five pairwise comparisons, factorial effects, opponent-by-seat strata, and the deterministic selection packet.

## Contracts

```bash
PYTHONDONTWRITEBYTECODE=1 python -B -m py_compile \
  interaction_gate.py test_interaction_gate.py
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest -v test_interaction_gate.py
```

The suite covers positive composition, antagonism, singleton selection, interaction arithmetic, pooled-mean/stratum conflicts, inactive arms, duplicate cells, malformed provenance, nonfinite values, finite arithmetic overflow, boolean identities, lifecycle truncation, fingerprint aliasing, detached action/trace/score evidence, and strict JSON parsing.

## Boundary and custody

This package does not copy, modify, or claim custody of either candidate implementation. The own-value source and bound gameplay evidence remain with their existing owners. The pressure arm must bind a clean exact-source implementation of the stronger receipt-invariance certificate; the disproved proxy-zero partition is not a valid input under the `certified_pressure` label. The four-arm producer must pin both reviewed candidate byte sets, the canonical control closure, evaluator, engine, opponents, seeds, and both seats before invoking this gate.

No canonical archive, configuration, release pointer, provider state, or Kaggle submission is changed here.
