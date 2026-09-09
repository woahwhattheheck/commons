# TITAN V3 horizon-liquidity ablation — SOL-KEPLER

Operation: `titan-v3-horizon-liquidity-20260909-sol-kepler-01`

## Source-proven seam

Submitted V1 used `0.95 * modeled_future_receipt` for stock left beyond its
artificial planning horizon. Submitted V2 changed that factor to `1.0`.
Current V3 retains full carry inside `selected_sell_core.MarketPath.score`, the
actual optimizer imported by `FrozenSelected`; it does not use
`scheduler.optimize_lot` for this decision.

With full carry, realizing one unit now can tie retaining it even though only
the sale creates spendable cash and removes execution risk. This packet
restores only the V1 carry factor in the production-selected optimizer. It does
not patch root `scheduler.MarketPath`, alter receipts or remaining units, or
change products, target selection, rival scenarios, route ownership, queue
ordering, capacity rules, terminal liquidation, or any canonical file.

## Runtime boundary

`candidate.py` loads canonical `main.py` and replaces its `_new_instance` hook.
The hook imports and patches `selected_sell_core` before canonical lazy
initialization, then invokes the original constructor. Its subclass delegates
the entire base `score()` and rescales only the carry contribution already
encoded in the returned relative value. Canonical prelude, whole-call deadline,
fallback, reconstruction, FinalPressure ordering, config, and every later
runtime transform remain in the original entrypoint.

## Evidence gate

`audit_change.py` fails closed unless it can bind the V1/V2 historical factor,
the current selected-core full-carry expression, and FrozenSelected's import and
call of that optimizer. Pure tests prove exact base-call delegation, unchanged
receipt/remaining fields, unchanged terminal and fully realized scores,
idempotence, conflicting-install rejection, install-before-construction, and
canonical entrypoint delegation.

The workflow then runs an identical-cell official-engine baseline/candidate
screen against Arlene, submitted V1, Apex, and Public BT12. `ADVANCE` requires
actual trace activation, positive mean own cash and margin, nonnegative Arlene
and V1 strata, and no material stratum regression. A green workflow is not a
leaderboard claim; the retained JSON/markdown verdict is authoritative.
