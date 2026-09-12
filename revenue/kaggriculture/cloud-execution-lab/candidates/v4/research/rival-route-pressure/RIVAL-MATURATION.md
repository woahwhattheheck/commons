# RIVAL-MATURATION — public crop-age pressure from Apex/Gemini

This is an additive theorem/oracle inside the existing **PARALLAX** `rival-route-pressure` authority. It does not add a controller, opponent ID, feature key, route chooser, SELL retimer, default, archive or Kaggle mutation.

Pinned official engine blob: `3c202c7ee921da239356789e266b694635103fc4`.

## Source idea retained

The visible Apex V7 strategy watches rival STRAWBERRY/MELON crops approaching harvest and tries to sell before that competing supply lands. The useful mechanism is not the Apex identity or its hard-coded steps; it is the **public crop-age / standing-yield signal**.

PARALLAX already measures public rival standing `yield_units`. The missing piece was bounded near-future maturation pressure: a crop can have little or no harvestable yield now while source mechanics make a larger burst possible within the next few callbacks/days.

## Exact source mechanics used

- Annual crops (WHEAT/CARROT/MELON) start with one held unit and gain yield immediately from WATER during the source-defined watering window. Fertilized WATER may add two units, capped at crop `max_yield`.
- Ongoing crops (TOMATO/STRAWBERRY) accumulate at eligible EOD refreshes after `first_yield_day`; fertilized+watered production may add two units, capped at `max_yield`.
- HARVEST cannot collect a crop before `first_yield_day`.
- A live PLANT cannot source-validly have `consecutive_unwatered >= 2`; that state would already have become a WEED.

`rival_maturation.py` therefore emits an intentionally generous **single-harvest burst ceiling**. For future eligible service it grants the rival successful survival and fertilizer, so the bound may overstate what the rival can actually realize. It never reads rival private shed, seed, fertilizer inventory or orders.

## Why this is stronger than hard-coded front-run steps

A fixed `step=381/403/499...` front-run only matches one visible opponent script. The public-state version works on any opponent and naturally goes cold when no relevant crop is present.

For every visible target crop it reports:

- harvestable units now;
- earliest source maturity step;
- upper-bound single-harvest burst by horizon end;
- incremental units that could mature during the horizon.

Default target products are STRAWBERRY and MELON because those were the surfaced Apex/Gemini ambush seam, but the oracle can be asked for any official crop.

## Safety / non-claims

This is **pressure evidence only**:

- `decision_authority=false`;
- `sale_timing_authority=false`;
- `opponent_identity_used=false`;
- `private_rival_state_used=false`.

The burst ceiling assumes the rival can service the crop and, for upper-bound purposes, may receive fertilizer-enhanced increments. It is not cumulative sale volume across multiple harvest cycles, not a proof the rival will harvest or sell, and not a price/margin theorem.

Any runtime consumer must combine it with existing PARALLAX standing yield, known town absorption, market-pressure/TOWNSELL row ownership, current public inventory/price state, and a current-native both-seat economics gate. That keeps the best part of the Gemini exploit while removing identity overfit and fixed-step brittleness.
