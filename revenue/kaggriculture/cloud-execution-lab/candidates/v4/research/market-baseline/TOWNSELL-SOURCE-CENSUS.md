# TOWNSELL current-route source census

This packet is the first downstream consumer of merged TOWNSELL (`#12922`,
`5e1e6cd4ac98057c35823b05a7e8488b6a5a4493`) inside the existing
`research/market-baseline` authority. It does not introduce a seller,
controller, feature key, runtime hook, default, composition edge, archive, or
Kaggle path.

## Question

TOWNSELL proves a deterministic mechanism: for the same already-intended SELL,
a town/shop drain after MARKET can make the identical sale weakly more valuable
on the next MARKET callback. That theorem alone is not enough to retime anything.
The current Arlene action still passes through dynamic `room_guard`,
`clamp_sells`, `dead_stock`, and terminal settlement, and a delayed sale can
break cash timing, shed custody, order capacity, or interact with rival flow.

`town_sale_source_census.py` therefore asks only whether the current authored
Arlene route bank exposes a source-shaped landing seam worth executing.

## Fail-closed admission

The census authenticates exact current sources before use:

- current Arlene Git blob `bdb9cf58148a3c7961c085f4902759537decabf6`;
- official engine Git blob `3c202c7ee921da239356789e266b694635103fc4`;
- merged TOWNSELL oracle Git blob `a795cc75dfcaa097e1b081114bbc09fb94e16f86`;
- canonical town timing oracle Git blob `abdbdc74ddc2be60cc46ae53b069998fdb3bff3b`.

It decodes the four current Arlene routes and scans only the executable market
prefix (`[:10]`). It intentionally supplies **zero unlocked shops** to the town
demand oracle. A reported opportunity therefore depends only on guaranteed
town-center demand and never predicts shop RNG.

A source window is called structurally quiet only when all of the following are
true:

1. the authored row is a positive-quantity SELL inside the executable prefix;
2. the same callback has guaranteed town-center demand for that item;
3. the sale is not at the terminal horizon;
4. the next callback has room to append one market row;
5. the next callback has no non-SELL market order that could depend on cash or
   market ordering;
6. the next callback has no authored SELL of the same item;
7. the next callback has no authored DROP/PLACE unit action that can write shed
   custody before MARKET.

These are deliberately stronger than necessary. They are a source-only false-
positive filter, not a claim that a surviving row is safe.

## Required current-native gate

Any positive source-safe window still requires one authenticated current-native
postimage and paired both-seat execution. The field gate must observe that the
specific SELL survives Arlene's dynamic seller guards, prove the item actually
remains in shed custody through the deferred callback, prove no cash deadline or
capacity loss, measure or exclude rival same-item flow, and compare terminal own
cash plus rival/margin effects. Any negative cell blocks promotion.

If the source census is empty, the lane closes `COLD_SOURCE_NO_SAFE_SHAPE`. If it
is nonempty, the only allowed conclusion is
`SOURCE_SAFE_SHAPE_REQUIRES_CURRENT_NATIVE` and an execution handoff. No runtime
wiring follows from source reachability alone.
