# Gemini EGG town-clock scarcity frontier

Status: **research-only corrected descendant; no activation or optimality claim**.

## What survives from the Gemini exploit

The literal "short squeeze" proposal is not an engine-legal EGG strategy. In the pinned official engine, `BUY_PRODUCT` can buy only `WHEAT` and `FERTILIZER`; an agent cannot buy public EGG inventory into a dark pool. Holding newly produced EGG also does not remove existing public inventory. The finite EGG curve and its outer bounds are already authenticated in `../market-baseline/EGG-ELASTICITY.json` / `egg_elasticity_bound.py`.

The useful residue is **scarcity timing**. Town shops and the town center consume public inventory. The interpreter executes `_process_market(...)` before `_town_consume(...)`, so an EGG sale on a consumption tick is quoted *before* that tick removes supply. A sale moved to a later turn can capture lower public inventory and a higher EGG sale price, provided rival supply and other state changes do not erase the edge.

That corrected descendant is implemented by `gemini_egg_timing.py`: move one already-planned literal `SELL EGG`, keep the opponent tape fixed, and delegate every transition/economic result to the existing pinned full-interpreter `sale_window.compare` harness.

## Exhaustive legal destination census

For every later turn inside the bounded horizon, the frontier considers **every** literal `["PASS"]` row inside the live executable market cap. If the inherited market queue is shorter than the cap, its one next append index is also a legal destination. Inherited non-PASS economic rows are never displaced.

This is intentionally a row-level census rather than a one-destination-per-turn heuristic. Two PASS rows on the same turn can have different lockstep timing relative to the rival queue, and a legal append slot can be distinct from earlier PASS slots. Missing those placements would make the bounded search incomplete even though no policy claim is made.

## Mechanism-correct evidence

A changed action or positive total window cash is **not** enough to prove an EGG scarcity edge. Moving the EGG row can also change whether another `HIRE`, buy, or sale succeeds, so `window_cash_delta > 0` can be positive even when the moved EGG receives the exact same quote.

The full-interpreter observer already records `sold` units and `sale_cash` for every parsed market row. The frontier therefore binds both the baseline source row and candidate target row to those exact records. A candidate is a realized retiming only when the baseline source sold a positive number of units and the target sold the **same** number. It is scarcity-price-positive only when, in addition, `target_sale_cash > source_sale_cash`.

`best_positive` is selected only from those scarcity-price-positive candidates. The report still includes total own-window cash, window margin, and terminal margin when available, but those fields are consequences of the whole replay; they cannot independently establish the EGG timing mechanism. Missing, duplicate, negative, or type-poisoned row-observer metrics fail closed and cannot mint engagement.

## Why this is stronger than a one-step rule

A fixed "wait one turn" patch leaves money on the table when several known town-consumption pulses occur inside the available action tape. The frontier searches the complete bounded legal row set and ranks realized retimings first by whether EGG row cash actually improves, then by the measured EGG sale-cash delta, with whole-window cash and margin only as secondary consequences.

The same full interpreter naturally captures the important counter-case: rival EGG sales in the fixed tape can overwhelm town depletion and make waiting worse. There is no blanket "always hold EGG" rule.

## Fail-closed boundaries

- Source must be one positive literal `SELL EGG` row. No synthetic EGG buy is created.
- Destination must be a later literal PASS slot inside the live executable cap or the one legal append position when the queue is shorter than that cap.
- `sale_window.shift_sale` and `sale_window.compare` preserve opponent actions and all non-market actions and run the complete pinned interpreter.
- Realized retiming requires equal positive filled EGG units at source and target; scarcity-positive additionally requires higher target-row EGG `sale_cash`.
- Whole-window cash or margin cannot by itself establish the mechanism.
- Empty-shed, clipped-row, partial-fill, rival-supply, EOD-delivery, and other engine effects remain visible because the full interpreter—not an analytical shortcut—decides fills and money.
- `best_positive` is bounded open-loop evidence only. It is **not** a policy, current-native strength claim, or promotion signal.

## Promotion path

1. Run a current-native/gauntlet census of natural EGG SELL exposures.
2. For filled sources, evaluate the complete bounded legal later-placement set with this frontier.
3. Require both-seat equal-unit row-cash-positive engagement and non-negative rival-aware margin before authoring any native experiment callback.
4. Only then consider extending the opt-in native sale-window target set to EGG. Do **not** widen `native_sale_window.SAFE_PRODUCTS` from elasticity alone.

This keeps the real part of the Gemini idea—the finite price curve and timing opportunity—while killing both the impossible direct market-cornering premise and false positives caused by unrelated downstream spending changes.
