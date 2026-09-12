# Gemini FERT floor-buy/apply — full-path source certificate

Status: **constructed full-interpreter research / no current-native engagement or activation claim**.

The all-Gemini convergence ledger correctly separated this historical proposal from the false `$1 FERT warehouse` idea. The warehouse claim is false because a floor-price SELL destroys shed custody instead of creating recoverable public stock. A different seam survives: official `BUY_PRODUCT` *can* buy public FERTILIZER, and at sufficiently high public inventory the one-unit post-buy quote reaches the engine's `$1` price floor.

That price observation alone is not an exploit. Bought FERT lands in the shed; `FERTILIZE` consumes a unit from the acting farmer's carried inventory. A usable path therefore has real custody and action costs:

`BUY_PRODUCT FERTILIZER -> shed -> PICKUP FERTILIZER -> FERTILIZE -> WATER/production -> HARVEST -> sale`.

`fert_floor_apply.py` runs that exact path through the already-authenticated full interpreter used by `opportunity_cost.py`. It does not implement another market model or donor policy.

## Constructed witness

The fixture is deliberately narrow and legible:

- day-3 CARROT at the farmer's shed-access tile;
- one existing yield unit, normal day-3 WATER opportunity;
- rival PASS throughout;
- candidate buys exactly one FERT at step 90, picks it up at 91, fertilizes at 92, then shares the control's WATER/HARVEST/DROP+SELL/DIG path;
- control leaves 91/92 idle.

The source-derived floor threshold is defined as the **lowest pre-buy FERT market inventory whose post-buy quote is `$1`**. The helper searches the authenticated engine's own `market_price`, preserving source rounding and shape semantics instead of hard-coding a threshold.

The declared panel is both seats × `{threshold-1, threshold, threshold+100}`. That provides the immediately-above-floor boundary, the first floor cell, and a deeper-floor control without pretending those inventory levels are naturally reached by V4.

## What a positive witness means

If the full interpreter shows the candidate buys for `$1`, custody moves shed -> farmer -> crop, one extra CARROT is harvested, final private/farm physical state is equal after the common DIG, and own cash is higher, then the historical mechanism is **source-real under idle callback capacity**.

It does **not** establish field profitability. The candidate spends two extra unit callbacks (`PICKUP FERTILIZER`, `FERTILIZE`). Those callbacks can be worth far more than `$1` in a live route. Storage headroom, financing, route position, future WATER, crop saturation, alternative service, rival actions and the probability of seeing floor FERT all remain outside the constructed theorem.

The zero-cash control proves an authored BUY row that cannot fund the purchase does not manufacture the yield edge.

## Promotion path

1. Execute the focused checker against the same authenticated reference engine used by `fwd-buy-census` in normal and optimized Python; retain exact output, source hashes and callback counts.
2. Census current composed-V4 observations for natural FERT quotes and shed-adjacent idle capacity; do not synthesize reachability from this fixture.
3. For any natural candidate, charge the displaced unit actions against the incumbent returned action and preserve funding/headroom/route obligations.
4. Only a both-seat current-native returned-action change with positive paired economics and no service/storage regressions may become a gameplay proposal.

Until then, the correct V4 form is a source-bound mechanism certificate, not a `price == 1` policy trigger.
