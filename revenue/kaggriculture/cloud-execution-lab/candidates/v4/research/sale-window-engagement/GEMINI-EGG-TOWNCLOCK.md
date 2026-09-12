# Gemini EGG town-clock scarcity frontier

Status: **research-only corrected descendant; no activation or optimality claim**.

## What survives from the Gemini exploit

The literal "short squeeze" proposal is not an engine-legal EGG strategy. In the pinned official engine, `BUY_PRODUCT` can buy only `WHEAT` and `FERTILIZER`; an agent cannot buy public EGG inventory into a dark pool. Holding newly produced EGG also does not remove existing public inventory. The finite EGG curve and its outer bounds are already authenticated in `../market-baseline/EGG-ELASTICITY.json` / `egg_elasticity_bound.py`.

The useful residue is **scarcity timing**. Town shops and the town center consume public inventory. The interpreter executes `_process_market(...)` before `_town_consume(...)`, so an EGG sale on a consumption tick is quoted *before* that tick removes supply. A sale moved to a later turn can capture the lower public inventory and higher price, provided rival supply and other state changes do not erase the edge.

That is the corrected descendant implemented here: `gemini_egg_timing.py` searches later placements for one already-planned literal `SELL EGG` and delegates every economic result to the existing pinned full-interpreter `sale_window.compare` harness.

## Why this is stronger than a one-step rule

A fixed "wait one turn" patch leaves money on the table when several known town-consumption pulses occur inside the available action tape. The frontier enumerates every legal later PASS/append destination up to a bounded horizon and ranks only **realized retimings** by measured own cash and margin. A target that changes syntax but does not actually refill the sale is not treated as evidence.

This also means the frontier naturally captures the important counter-case: rival EGG sales in the fixed tape can overwhelm town depletion and make waiting worse. There is no blanket "always hold EGG" rule.

## Fail-closed boundaries

- Source must be one positive literal `SELL EGG` row. No synthetic EGG buy is created.
- Destination must be a later literal `PASS` slot or an append position inside the live market-order cap; inherited economic rows are never displaced.
- `sale_window.shift_sale` and `sale_window.compare` preserve opponent actions and all non-market actions and run the complete pinned interpreter.
- `best_positive` means only "best positive own-cash result in this bounded open-loop tape." It is **not** a policy, current-native strength claim, or promotion signal.
- Empty-shed, clipped-row, partial-fill, rival-supply, EOD-delivery and other engine effects remain visible because the full interpreter—not an analytical shortcut—decides fills and money.

## Promotion path

1. Run a current-native/gauntlet census of natural EGG SELL exposures.
2. For filled sources, evaluate bounded later placements with this frontier.
3. Require both-seat realized-retiming engagement and non-negative rival-aware margin before authoring any native experiment callback.
4. Only then consider extending the opt-in native sale-window target set to EGG. Do **not** widen `native_sale_window.SAFE_PRODUCTS` from elasticity alone.

This keeps the best part of the Gemini idea—the price convexity and timing opportunity—while killing the impossible direct market-cornering premise.
