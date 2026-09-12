# Gemini FERT floor-buy/apply — full-path source certificate

Status: **constructed full-interpreter research / no current-native engagement or activation claim**.

The all-Gemini convergence ledger correctly separated this historical proposal from the false `$1 FERT warehouse` idea. The warehouse claim is false because a floor-price SELL destroys shed custody instead of creating recoverable public stock. A different seam survives: official `BUY_PRODUCT` *can* buy public FERTILIZER, and at sufficiently high public inventory the one-unit post-buy quote reaches the engine's `$1` price floor.

That price observation alone is not an exploit. Bought FERT lands in the shed; `FERTILIZE` consumes a unit from the acting farmer's carried inventory. A usable path therefore has real custody and action costs:

`BUY_PRODUCT FERTILIZER -> shed -> PICKUP FERTILIZER -> FERTILIZE -> WATER/production -> HARVEST -> sale`.

`fert_floor_apply.py` runs that exact path through the already-authenticated full interpreter used by `opportunity_cost.py`. It does not implement another market model or donor policy.

## Two constructed witnesses

### Minimal one-WATER witness

The first fixture is deliberately short and legible:

- day-3 CARROT at the farmer's shed-access tile;
- one existing yield unit, normal day-3 WATER opportunity;
- rival PASS throughout;
- candidate buys exactly one FERT at step 90, picks it up at 91, fertilizes at 92, then shares the control's WATER/HARVEST/DROP+SELL/DIG path;
- control leaves 91/92 idle.

This asks only whether the complete source path can buy, custody, apply and realize one incremental unit while converging back to equal farm/private physical state.

### Full three-day amortization witness

The source makes FERT active for the current day plus the next two days. For annual crops, each WATER in the in-window period receives the fertilizer bonus, capped by that crop's `max_yield`. A one-WATER fixture therefore understates the strongest mechanically valid form.

The second fixture uses day-10 MELON planted on day 0:

- candidate buys at step 240, PICKUPs at 241 and FERTILIZEs at 242;
- candidate and control then share exactly the same WATER callbacks at steps 243 (day 10), 264 (day 11), and 288 (day 12);
- every intervening callback is executed so EOD resets/aging come from the official interpreter;
- both harvest at step 289 and DROP+SELL at 290;
- the same **two** extra unit callbacks are therefore amortized across the complete three-day fertilizer window.

The official MELON cap is six units. The focused checker expects the interpreter to decide whether the candidate reaches six versus the control's three; this is an authored assertion to be validated, not a pre-declared green result.

## Exact floor boundary

The source-derived floor threshold is defined as the **lowest pre-buy FERT market inventory whose post-buy quote is `$1`**. The helper searches the authenticated engine's own `market_price`, preserving source rounding and shape semantics instead of hard-coding a threshold.

The minimal declared panel is both seats × `{threshold-1, threshold, threshold+100}`. The amortized witness runs both seats at the exact threshold. This provides the immediately-above-floor boundary, the first floor cell, a deeper-floor control, and the full-lifetime value frontier without pretending those inventory levels are naturally reached by V4.

## What a positive witness would mean

If the full interpreter shows the candidate buys for `$1`, custody moves shed -> farmer -> crop, incremental crop units are harvested, final private/farm physical state is equal after liquidation, and own cash is higher, then the historical mechanism is **source-real under constructed idle callback capacity**.

The three-day witness tests an important improvement over the literal post: `PICKUP` and `FERTILIZE` are fixed setup costs, while the fertilizer benefit may span three common WATER callbacks. If three extra MELON units survive the full interpreter, the constructed callback cost is 2/3 of one extra unit action per incremental MELON rather than two actions per one boosted crop unit.

It still does **not** establish field profitability. Those two extra callbacks can be worth far more than `$1` in a live route. Storage headroom, financing, route position, future WATER custody, crop saturation, alternative service, rival actions and the probability of seeing floor FERT all remain outside the constructed theorem.

The zero-cash controls for both witnesses prove an authored BUY row that cannot fund the purchase does not manufacture the yield edge.

## Promotion path

1. Execute the focused checker against the same authenticated reference engine used by `fwd-buy-census` in normal and optimized Python; retain exact output, source hashes and callback counts.
2. Census current composed-V4 observations for natural FERT quotes and shed-adjacent idle capacity; do not synthesize reachability from either fixture.
3. Prefer candidates where one PICKUP/FERTILIZE pair services multiple future WATER days; charge the displaced unit actions against the incumbent returned action and preserve funding/headroom/route obligations.
4. Only a both-seat current-native returned-action change with positive paired economics and no service/storage regressions may become a gameplay proposal.

Until then, the correct V4 form is a source-bound mechanism certificate, not a `price == 1` policy trigger.
