# TITAN V3.1 S33 row-shed donor

Operation: `TITAN-V31-8E3-S33-ROWSHED-DURABLE-DONOR-20260911-01`

Exact source root: `8e3d92a286806f9f9525973ee7d359b629a11487` (merged #12537, B5 CARROT + JIT shipped).
Exact source R04 blob at that root: `7edacbfb4916b8f241b689ded6643240ca02a9ec`.

## Mechanism

Current R04 `ROW_ORDER` stable-sorts only the leading SELL block by each row's modeled price drop. The current score uses the authored request quantity. Native tapes can contain availability-dump rows such as `SELL item 1000`; if projected own shed holds only a few units, the engine can execute only those few units, but the ordering score currently prices the full 1000-unit request.

S33 changes **only the ranking quantity** to:

`min(requested_quantity, projected_shed_quantity_for_item)`

The submitted market row and authored quantity are not changed. No row is added or removed. No SELL crosses the first non-SELL barrier. The pinned default price curve is unchanged.

The donor helper in `r04_row_shed.py` is a package-neutral executable statement of that transform. Six focused contracts freeze the intended boundary, including the 1000-unit phantom-rank regression.

## Production splice

This branch is deliberately **not** a production integration carrier because #12535/#12541 own the current build/L3 stack. A production consumer should recompose on the then-current V3.1 successor and make the minimum R04 change:

1. add a deterministic `r04_row_shed` gate (default decision belongs to the integration/evidence gate);
2. while `ROW_ORDER` is active, obtain `projected_shed(action, FarmView(observation))` from the same final action being ranked;
3. in `order_sells`, use the bounded quantity above only for the `drop()` score;
4. preserve the existing leading-block stable sort, marketParams override behavior, rows, quantities, H4, B5 CARROT, B5 JIT, sale-fertilizer, and the current L3 gate;
5. rebuild from the immutable 5f6 base through current build custody rather than merging stale a612 package ancestry.

## Evidence / authority boundary

Fleet S33 reported this as the strongest fresh gameplay factor and #12511 records row-shed as the highest-value fresh factor requiring an 8e3/successor recompose. This donor does not restate those field scores as fresh execution on this exact branch. It provides source custody and a collision-free handoff so the field winner cannot remain isolated on stale ancestry.

Local focused contract at publication: `python -m unittest -v test_r04_row_shed.py` -> 6/6 PASS.

No live overlay, `apply_v3.py`, TITAN config/default, FILES/manifest, builder, canonical archive, evaluator/opponent, Kaggle, leaderboard, or submission state is changed by this donor.
