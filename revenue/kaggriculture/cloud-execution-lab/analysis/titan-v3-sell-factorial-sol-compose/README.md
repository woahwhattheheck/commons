# TITAN V3 SELL objective × pressure interaction gate

This package closes a decision gap between two independently promising SELL changes:

1. an **own-value objective**, which ranks plans by TITAN's own receipts plus continuation value rather than subtracting rival receipts; and
2. **strict-dominance market pressure**, which preserves the parent order among exposed commodities and only moves exposed sales ahead of zero-exposure sales.

Independent singleton screens cannot establish that the changes compose. They can target the same market queue, and an antagonistic interaction can erase either gain. `interaction_gate.py` therefore consumes four complete, source-bound evaluator reports from one predeclared grid:

- `control`: neither change;
- `own_value`: objective change only;
- `strict_pressure`: pressure containment only;
- `both`: both changes.

The gate runs no games and edits no runtime. It is an evidence consumer intended for the existing cloud evaluator and candidate-action capture path.

## Evidence contract

All four reports must have identical evaluator provenance, opponents, seeds, limits, and RNG seed. Every report must contain the same complete `opponent × seed × seat` grid. Each game must be complete and bind:

- a 720-state / 719-action lifecycle;
- 719 pre-interpreter returned candidate actions;
- a candidate-action stream SHA-256;
- a complete trace SHA-256;
- terminal scores equal to the retained terminal bank snapshot.

The four entrypoint fingerprints must be distinct. If two arms have the same captured candidate-action stream for a cell, their deterministic trace and terminal banks must also be identical. Score or trace drift without returned-action activation is rejected as detached evidence.

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
- `SELECT_STRICT_PRESSURE`
- `NO_SAFE_ADVANCE`
- `INACTIVE`

Every result explicitly keeps `promotion_authorized=false` and `hosted_leaderboard_claim=false`.

## Factorial diagnostics

For each paired cell, with terminal own cash `Y`, the gate computes:

```text
own-value main effect     = ((Y_own - Y_control) + (Y_both - Y_pressure)) / 2
strict-pressure main      = ((Y_pressure - Y_control) + (Y_both - Y_own)) / 2
interaction               = Y_both - Y_own - Y_pressure + Y_control
```

The same difference-in-differences interaction is retained for margin. These diagnostics distinguish additive gains from cancellation or synergy; selection still follows the fail-closed non-regression gates above.

## Usage

```bash
python -B interaction_gate.py \
  --control /evidence/control.json \
  --own-value /evidence/own-value.json \
  --strict-pressure /evidence/strict-pressure.json \
  --both /evidence/both.json \
  --head "$GITHUB_SHA" \
  --output /evidence/FACTORIAL-DECISION.json \
  --markdown /evidence/FACTORIAL-DECISION.md
```

The JSON output retains the shared provenance, all per-cell arm states, five pairwise comparisons, factorial effects, opponent-by-seat strata, and the deterministic selection packet.

## Contracts

```bash
PYTHONDONTWRITEBYTECODE=1 python -B -m py_compile \
  interaction_gate.py test_interaction_gate.py
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest -v test_interaction_gate.py
```

The suite covers the positive composition case, antagonism, singleton selection, interaction arithmetic, pooled-mean/stratum conflicts, inactive arms, duplicate cells, malformed provenance, nonfinite banks, boolean identities, lifecycle truncation, fingerprint aliasing, detached action/trace/score evidence, and strict JSON parsing.

## Boundary and custody

This package does not copy, modify, or claim custody of either candidate implementation. The own-value source and its bound gameplay evidence remain with their existing PR owners. The strict-pressure source remains with its existing owner and must first produce a clean, exact-source artifact. The four-arm producer must pin those reviewed bytes, the canonical control closure, the evaluator, engine, opponents, seeds, and both seats before invoking this gate.

No canonical archive, configuration, release pointer, provider state, or Kaggle submission is changed here.
