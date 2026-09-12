# R04-EXPANDTAX — BUY_LAND weed-tax gate

Default-OFF (`r04_expandtax`, default false). OFF callers never invoke this module.

## Mechanic (pinned official engine)

`_do_buy_land` converts every `"LOCKED"` tile of the purchased quadrant to `None`
(`LAND_ORDER = ["NE","SW","SE"]`, prices `[1000,2000,4000]`). `_spawn_weeds` rolls
`rng.random() < weed_chance` (default 0.005) for **every** `None` tile at EOD —
`"LOCKED"` tiles are a string, never `None`, so they are exempt. Every expansion
therefore permanently adds ~25 tiles of weed-spawn surface: expected weed-clearing
labor plus the unlock cash.

Gemini/Antigravity's "Expansion Penalty" sim request asked for exactly this
quantification (ts 1789185299.673649). Canonical research
(`research/opening-expansion-economics/`, ASTRA-HOMESTEAD #12822) proved the
exposure scales with *empty* unlocked tiles and concluded: "the next policy-grade
gate must compare marginal production value vs cash + actual empty-tile weed
labor." This package is that gate.

## Gate rule

Expand iff `E > W·A + C/(T·D)`:

- `E` — expected marginal $/tile/day of the new quadrant (agent's trailing
  books: trailing mean of daily net $/planted tile)
- `W` — measured weed-tax actions per new tile per day (`0.013`, see MEASUREMENT.md)
- `A` — trailing net $/action (daily net $ / daily non-PASS actions)
- `C` — unlock price of the next quadrant; `T` = 25 tiles/quadrant;
  `D` = days remaining

`filter_market_orders(action, observation, configuration, books)` drops BUY_LAND
orders the gate rejects. Malformed input fails closed (action unchanged). No
revenue model beyond the agent's own trailing books; no second scheduler.

## Evidence

- `MEASUREMENT.md` — W = 0.0130 actions/tile/day (100-seed spawn-rate panel +
  30-seed clearing-cost micro-panel, pinned engine).
- `GATE-VERDICT.md` — 16-cell frozen panel: dM(gate − always-expand) **+$938**
  mean (se $290, 9+/0−/7=, zero harm, deterministic); dM(gate − never-expand)
  −$2,928 (hyper-dense wins under the saturated proxy policy — reported, not hidden).
- `checks/test_expandtax.py` — 19/19 pass in normal Python and `python -O`.

## Hook (when a future gate authorizes runtime use)

See `WIRING.md`. Two lines at the market-order surface plus
`"r04_expandtax": false` in TITAN-CONFIG.json. The carrier ships the decision
function only; the composer owns the trailing-books feed from live daily notes.
