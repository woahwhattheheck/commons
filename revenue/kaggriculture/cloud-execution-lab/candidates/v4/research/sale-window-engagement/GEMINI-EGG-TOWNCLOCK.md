# Gemini EGG town-clock scarcity frontier

Status: **research-only corrected descendant; no activation or optimality claim**.

## What survives from the Gemini exploit

The literal "short squeeze" proposal is not an engine-legal EGG strategy. In the pinned official engine, `BUY_PRODUCT` can buy only `WHEAT` and `FERTILIZER`; an agent cannot buy public EGG inventory into a dark pool. Holding newly produced EGG also does not remove existing public inventory. The finite EGG curve and its outer bounds are already authenticated in `../market-baseline/EGG-ELASTICITY.json` / `egg_elasticity_bound.py`.

The useful residue is **scarcity timing**. Town shops and the town center consume public inventory. The interpreter executes `_process_market(...)` before `_town_consume(...)`, so an EGG sale on a consumption tick is quoted *before* that tick removes supply. A sale moved to a later turn can capture the lower public inventory and higher price, provided rival supply and other state changes do not erase the edge.

That is the corrected descendant implemented here: `gemini_egg_timing.py` searches later placements for one already-planned literal `SELL EGG` and delegates every transition/economic result to the existing pinned full-interpreter `sale_window.compare` harness.

## Mechanism identity: sale cash, not terminal cash

Moving a sale can change whether unrelated downstream actions execute. For example, a baseline EGG sale can fund a same-turn `$1` HIRE; delaying that sale can make the HIRE fail, leaving the candidate with `$1` **more** terminal cash even when the EGG sells later for exactly the same amount. Ranking that total-cash delta as a scarcity win would confuse "did not pay a wage" with "captured a better EGG quote."

The frontier therefore binds the source and target rows to `sale_window.observed_step`'s successful-commit receipts. A candidate is scarcity-positive only when:

1. the baseline source row fills a positive number of EGG units;
2. the delayed target row fills exactly the same number of EGG units; and
3. `target_sale_cash > source_sale_cash`.

`own_cash_delta`, window margin, and terminal margin are still reported, but only as consequences. They cannot manufacture `best_positive` without a literal improvement in cash earned by the moved EGG sale itself.

## Why this is stronger than a one-step rule

A fixed "wait one turn" patch leaves money on the table when several known town-consumption pulses occur inside the available action tape. The frontier enumerates every legal later PASS/append destination up to a bounded horizon and ranks realized retimings first by **sale-row cash improvement**, then by broader measured consequences. A target that changes syntax, changes downstream spending, or merely refills the same EGG for the same cash is not treated as positive scarcity evidence.

This also means the frontier naturally captures the important counter-case: rival EGG sales in the fixed tape can overwhelm town depletion and make waiting worse. There is no blanket "always hold EGG" rule.

## Fail-closed boundaries

- Source must be one positive literal `SELL EGG` row. No synthetic EGG buy is created.
- Destination must be a later literal `PASS` slot or an append position inside the live market-order cap; inherited economic rows are never displaced.
- `sale_window.shift_sale` and `sale_window.compare` preserve opponent actions and all non-market actions and run the complete pinned interpreter.
- `best_positive` means only "same positive EGG units realized for strictly more EGG sale cash in this bounded open-loop tape." It is **not** a policy, current-native strength claim, or promotion signal.
- Empty-shed, clipped-row, partial-fill, rival-supply, EOD-delivery and other engine effects remain visible because the full interpreter—not an analytical shortcut—decides fills and money.

## Promotion path

1. Run a current-native/gauntlet census of natural EGG SELL exposures.
2. For filled sources, evaluate bounded later placements with this frontier.
3. Require both-seat sale-cash-positive engagement and non-negative rival-aware margin before authoring any native experiment callback.
4. Only then consider extending the opt-in native sale-window target set to EGG. Do **not** widen `native_sale_window.SAFE_PRODUCTS` from elasticity alone.

This keeps the best part of the Gemini idea—the price convexity and timing opportunity—while killing both the impossible direct market-cornering premise and total-cash confounds unrelated to the EGG quote itself.
