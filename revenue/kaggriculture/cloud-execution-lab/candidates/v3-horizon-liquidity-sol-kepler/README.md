# TITAN V3 horizon-liquidity ablation — SOL-KEPLER

Operation: `titan-v3-horizon-liquidity-20260909-sol-kepler-01`

## Source-proven seam

Submitted V1 used `0.95 * modeled_future_receipt` for stock left beyond the
artificial eight-step planning horizon. Submitted V2 changed that factor to
`1.0`; current `scheduler.py::MarketPath.score` remains AST-identical to V2 at
that method. With a full carry value, realizing one unit now can tie retaining
it even though only the sale creates spendable cash and removes execution risk.

This packet restores only the V1 factor. It does not change products, target
selection, rival scenarios, route ownership, market ordering, capacity rules,
terminal liquidation, or any canonical file.

## Runtime boundary

`candidate.py` loads canonical `main.py` and replaces its `_new_instance` hook.
The hook installs a one-method `MarketPath` subclass before canonical lazy
initialization, then invokes the original constructor. Canonical prelude,
whole-call deadline, fallback, reconstruction, FinalPressure ordering, config,
and every later runtime transform remain in the original entrypoint.

## Evidence gate

`audit_change.py` fails closed unless the exact V1/V2/current source seam is
still present and V2/current `MarketPath.score` ASTs match. Pure tests cover the
factor, terminal behavior, delayed-rival timing, idempotence, conflicting
installation, install-before-construction, and canonical entrypoint delegation.
The workflow then runs an identical-cell official-engine baseline/candidate
screen against Arlene, submitted V1, Apex, and Public BT12. `ADVANCE` requires
actual trace activation, positive mean own cash and margin, nonnegative Arlene
and V1 strata, and no material stratum regression. A green workflow is not a
leaderboard claim; the retained JSON/markdown verdict is authoritative.
