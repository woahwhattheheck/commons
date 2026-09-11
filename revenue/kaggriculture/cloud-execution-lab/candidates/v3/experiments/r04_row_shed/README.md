# R04 row-shed — current-root production donor

Fleet lane: `TITAN-V31-6E5-ROW-SHED-PRODUCTION-20260911-02`.

## Evidence and root

S33 field work reported 1,920 games per arm against 16 published agents: row-shed beat the #12507 configuration in 1,912 cells, lost 6, tied 2, added no opponent-level loss, and reported +421.1/game versus V3.0. That result came from stale a612 ancestry, so it is predecessor evidence only.

This carrier is recomposed on #12535 exact head `6e5e3c7cc5302d6db4b702cc4fd7c8ca721d7b8a`, a direct current-root custody stack above shipped V3.1 `8e3d92a286806f9f9525973ee7d359b629a11487`. It inherits shipped B5 CARROT + JIT + H4 + rival-gated L3 + sale-fertilizer; #12535's new optimization-safe builder guard is also retained.

## Mechanism

Current `ROW_ORDER` scores a leading SELL using the requested quantity. Availability-style tape rows such as `SELL item 1000` can therefore rank impossible units that are not in the shed. Default-OFF `r04_row_shed` changes only the ranking quantity to:

`min(requested_qty, projected_shed[item])`

The emitted SELL row/quantity is unchanged. No row is added/removed. The existing leading-SELL boundary, stable sort, custom-marketParams bypass, worker actions, E184 debt, H4, L3, B5/JIT, evening flush and terminal liquidation keep their existing ownership/order.

## Custody and tests

The dedicated workflow requires PR base and #12535 branch both equal `6e5e3c7...`, live canonical still `8e3d92a...`, base R04 blob `7edacbfb...`, base `apply_v3.py` blob `a43d6c47...`, and exactly four additive donor/proof paths. It applies `row_shed.patch` ephemerally, compiles the patched production files, runs six focused contracts, reverses the patch, and requires a clean checkout.

The key test freezes an explicit false-priority case: at market inventory 9,800, requested `SELL WHEAT 1000` outranks `SELL CARROT 1` under old scoring; with projected shed `{WHEAT:1,CARROT:1}`, realizable scoring correctly puts CARROT first while WHEAT remains requested at exactly 1000.

## No-isolation integration theorem

This is the one durable row-shed donor and is routed to fleet spine #12511. Final production consumption must recompose this exact reviewed delta above the then-current convergence parent, including #12541's fail-closed L3 repair if it lands first, regenerate FILES/V3-MANIFEST/package receipts with #12535's immutable builder, and run a current-package paired gate retaining B5+JIT. Cattle remains orthogonal under #12540/#12505.

No default flip, package receipt, evaluator/opponent, provider, Kaggle, leaderboard or submission mutation is performed here.
