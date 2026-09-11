# R04 row-shed — current-root production donor

Fleet lane: `TITAN-V31-8E3-ROW-SHED-PRODUCTION-20260911-01`.

## Why this exists

S33 opponent-diverse field work identified row-shed as the highest-value fresh R04 factor: over 1,920 games per arm against 16 published agents, the row-shed arm was better than the #12507 configuration in 1,912 cells, worse in 6 and unchanged in 2, with no additional opponent-level loss and a reported +421.1/game versus V3.0. That receipt was produced on the earlier a612 lineage, so it is predecessor evidence, not authority to land stale ancestry.

This carrier is deliberately anchored on #12535 exact head `ccb128a10c40cb71c4f8ff07b05a88578679dc6c`, whose gameplay ancestry is shipped V3.1 `8e3d92a286806f9f9525973ee7d359b629a11487` (#12537). It therefore inherits B5 CARROT + JIT + H4 + rival-gated L3 + sale-fertilizer unchanged. The branch does not use the stale a612 carrier as merge authority.

## Exact mechanism

Current `ROW_ORDER` ranks each leading SELL row by the price drop implied by the row's requested quantity. Native tapes intentionally contain availability-style rows such as `SELL item 1000`; if only a few units are actually in the projected shed, those impossible units can dominate row priority even though they cannot execute.

The donor changes only the ranking quantity when `r04_row_shed=true`:

`ranking_qty = min(requested_qty, projected_shed[item])`

The emitted SELL row is not resized. No row is added or removed. The existing leading-SELL boundary, stable sort, custom-`marketParams` bypass, later market rows, worker commands, E184 debts, H4, B5, JIT, L3, evening flush and terminal liquidation remain under their existing owners.

`r04_row_shed` is wired default OFF. With the key off, `order_sells(..., shed=None)` executes the exact pre-S33 scoring path.

## Current-root custody

The dedicated workflow is self-invalidating. It requires:

- PR base SHA exactly #12535 head `ccb128a...`;
- live `titan/v3.1-20260911` still exactly shipped `8e3d92a...`;
- #12535 branch still exactly `ccb128a...`;
- base R04 blob exactly `7edacbfb4916b8f241b689ded6643240ca02a9ec`;
- base `apply_v3.py` blob exactly `a43d6c470ab05d87803fb016966d1cc54fab9d17`;
- exactly four additive donor/proof paths on the branch.

CI applies `row_shed.patch` only ephemerally, compiles the patched production files, runs the focused contract, then reverses the patch and requires a clean checkout.

## Focused contract

The contract freezes the intended S33 distinction with an explicit counterexample: at public inventory 9,800, a requested `SELL WHEAT 1000` outranks `SELL CARROT 1` under the old score, but with projected shed `{WHEAT: 1, CARROT: 1}` the realizable price-drop score correctly puts CARROT first. It also proves requested quantities are unchanged, post-barrier rows are unchanged, zero stock cannot gain fake priority, the v3 wrapper uses current projected shed only when enabled, custom market parameters still bypass ROW_ORDER, and the new key is default OFF through `apply_v3.py`.

## Integration boundary

This is a durable current-root donor, not a default flip or Kaggle action. The final production consumer must recompose this exact reviewed delta above the then-current convergence parent — including the #12541 fail-closed L3 repair if it lands first — regenerate deterministic FILES/manifest/package receipts, and run a current-package paired gate with B5+JIT retained. Cattle remains orthogonal and is owned by #12540/#12505.

No evaluator/opponent, provider, leaderboard, submission or spend mutation is included here.
