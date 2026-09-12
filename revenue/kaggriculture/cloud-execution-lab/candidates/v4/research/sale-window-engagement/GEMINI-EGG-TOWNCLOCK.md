# Gemini EGG town-clock scarcity frontier

Status: **research-only corrected descendant; no activation or optimality claim**.

## What survives from the Gemini exploit

The literal "short squeeze" proposal is not an engine-legal EGG strategy. In the pinned official engine, `BUY_PRODUCT` can buy only `WHEAT` and `FERTILIZER`; an agent cannot buy public EGG inventory into a dark pool. Holding newly produced EGG also does not remove existing public inventory. The finite EGG curve and its outer bounds are already authenticated in `../market-baseline/EGG-ELASTICITY.json` / `egg_elasticity_bound.py`.

The useful residue is **scarcity timing**. Town shops and the town center consume public inventory. The interpreter executes `_process_market(...)` before `_town_consume(...)`, so an EGG sale on a consumption tick is quoted *before* that tick removes supply. A sale moved to a later turn can capture lower public inventory and a higher quote, provided rival supply and other state changes do not erase the edge.

`gemini_egg_timing.py` searches every later legal PASS/append placement for one already-planned literal `SELL EGG` and delegates transition/economic measurement to the existing pinned full-interpreter `sale_window.compare` harness.

## Stronger witness contract

A changed tape or larger final cash balance is not enough to prove scarcity timing. Delaying a sale can make an intervening HIRE/BUY fail, leaving the candidate with *more* cash despite receiving the same or worse EGG sale proceeds. The frontier therefore records the row-level `sale_cash` already exposed by `sale_window` and calls a candidate scarcity-positive only when:

1. the source sale filled a positive number of EGG units;
2. the target sale filled exactly the same number of units; and
3. `target_sale_cash > source_sale_cash`.

Window cash, margin and terminal margin remain reported as downstream consequences, not mechanism identity.

The enumerator also evaluates **all** literal PASS rows inside the live market cap plus the legal append slot whenever `len(market) < cap`. Row index matters because the engine processes the two players' market queues lockstep; choosing only the first legal row can miss the best or only positive timing witness.

## Fail-closed boundaries

- Source must be one positive literal `SELL EGG` row. No synthetic EGG buy is created.
- Destinations are later literal `PASS` slots or the append position inside the live market-order cap; inherited economic rows are never displaced.
- `sale_window.shift_sale` and `sale_window.compare` preserve opponent actions and all non-market actions and run the complete pinned interpreter.
- `best_positive` means only "strict row-level EGG sale-cash improvement at equal positive fill inside this bounded open-loop tape." It is **not** a policy, current-native strength claim, or promotion signal.
- Empty shed, clipped rows, partial fills, rival supply, failed intervening spending, EOD delivery and other engine effects remain visible because the full interpreter—not an analytical shortcut—decides fills and money.

## Promotion path

1. Run a current-native/gauntlet census of natural EGG SELL exposures.
2. For filled sources, evaluate all bounded later legal placements with this frontier.
3. Require both-seat strict sale-cash improvement plus non-negative rival-aware margin; separately audit any changed intervening spend/funding outcomes.
4. Only then consider extending the opt-in native sale-window target set to EGG. Do **not** widen `native_sale_window.SAFE_PRODUCTS` from elasticity alone.

This keeps the best part of the Gemini idea—the finite EGG price convexity and real town-clock timing opportunity—while killing both the impossible direct market-cornering premise and false positives caused by skipped spending.
