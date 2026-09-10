# TITAN V3 disabled-feature dominator audit (SOL-PRO)

This additive release gate turns the V1→V2 hidden-weed regression into a permanent source contract: **when a feature is off, its mutating implementation call must be unreachable**. It does not simulate the game and does not claim gameplay promotion. It conservatively follows Python control flow with exact boolean short-circuiting; unknown game state forks both ways, so ambiguity cannot create a pass.

## Pinned predecessor result

At main commit `ed65812449a2cd021b0635a60ff9171957f3e386`, `spatial_tempo.py` blob `edbc423023479dbe2e78131495334384a87b607f` is correctly classified **REJECT**:

- line 861 evaluates `self._continue_weed(...)`;
- line 864 finally checks `not self.pathing and not self.tempo`;
- therefore the check does not dominate the call.

`CURRENT-MAIN-RECEIPT.json` binds the exact source identities and counterexample. The audit also checks 17 other optional-stage seams and reports the unconditional `SpatialTempo` construction as a defense-in-depth warning rather than a gameplay error.

## Run

From the repository root:

```bash
LANE=revenue/kaggriculture/cloud-execution-lab/analysis/titan-v3-disabled-feature-dominator-audit-sol-pro
python "$LANE/audit_disabled_feature_dominance.py" \
  --root . --expect either --output /tmp/titan-disabled-feature-report.json
python -m unittest discover -s "$LANE/tests" -v
```

The aggregate audit exits according to `--expect accept|reject|either`. `either` is used for exact-head evidence because the pinned predecessor is intentionally rejected; unit tests prove that exact pinned blobs produce `SPATIAL-WEED-OFF-001` at line 861. Once the implementation owner lands a dominating gate, exact-head classification should become **ACCEPT** without changing the audit.

## What is proved

The rules inventory checks direct implementation calls for seed budgeting, funding, redundant hires, committed-seed retry, market pressure, operating/feed stock, early capital, crop release, fourth-quadrant installation, terminal-route installation, idle fertilizer, the core path/tempo suffix, and weed continuation. A target rename or disappearance fails closed until the rule is deliberately updated.

The abstract interpreter understands:

- pre-return negative guards;
- positive branch dominance;
- `and` / `or` short-circuit order;
- boolean comparisons such as `feature is False`;
- uncertain game-state branches, loops, exceptions, and nested control flow conservatively.

It does **not** prove that an enabled feature is economically correct, that a game panel is positive, or that an archive should be promoted.

## W0 handoff

This lane is intentionally separate from the existing W0 hidden-weed source/ref/test owner. The implementation owner can use the gate unchanged. A successor of either form passes:

```python
if (self.pathing or self.tempo) and self._continue_weed(...):
    return selected
```

or

```python
if not (self.pathing or self.tempo):
    return selected
if self._continue_weed(...):
    return selected
```

An explicit `weed_continuation` feature predicate is also accepted. The integrator still owns exact trace parity, both-seat official panels, one-tree selection, and promotion.
