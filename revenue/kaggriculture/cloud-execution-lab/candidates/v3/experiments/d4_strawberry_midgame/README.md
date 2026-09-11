# D4 — STRAWBERRY midgame timing experiment

**Status:** default-off experiment only. No economics or promotion claim.

This carrier targets the narrow temporal gap left after live R04's E184 sale window and before the existing evening flush. It does **not** invent a sale: a unit may move only when it is already in projected shed stock and the selected R04 tape already schedules the same STRAWBERRY quantity later in the same day.

## Exact source census

Source carrier: frozen V3.1 base `508b342fc46fa91e3d7cdc3f0b7e44934a187c14`. The ready V3.1 `r01_tapes.py` decodes to 13 routes × 719 steps.

Raw authored STRAWBERRY SELL rows begin on day 15. Across all 13 tapes, days 15–16 contain:

- day 15: 11 rows / 88 requested units;
- day 16: 66 rows / 54,072 requested units.

The large requested quantities are mostly `1000`-unit "sell available stock" rows; requested quantity is not an executed-fill claim because the engine stops a SELL when shed stock is exhausted.

Representative route pattern:

- most selected routes: day15 hour22 `SELL STRAWBERRY 8`, then day16 hours18–23 repeated `SELL STRAWBERRY 1000`;
- route 9 instead sells day16 hours1 and11;
- route 12 sells day16 hours9,11,19.

Live R04 already closes most obvious gaps:

- E184 reserves authored future sells inside `SALE_HORIZON` (8 in frozen V3.1; H13 experiments 10);
- `EVENING_FLUSH` sells residual projected shed STRAWBERRY at hours21–23 every day after day0;
- H4 owns topping up an **existing current** STRAWBERRY SELL row from future authored sells.

D4 therefore acts only when all three leave a gap: there is no current STRAWBERRY trade, projected STRAWBERRY stock is already sellable, the public current price meets an explicit experiment threshold, and an authored same-day STRAWBERRY SELL exists **beyond** the parent's current horizon.

## Safety / composition contract

The candidate:

- is exact identity when `d4_min_price=None`;
- operates only days 12–18 and never crosses midnight;
- leaves the parent horizon unchanged and starts scanning at `step + SALE_HORIZON + 1`, so H13 can widen the parent without double booking D4;
- yields to H4 whenever a current STRAWBERRY SELL already exists;
- preserves current and queued STRAWBERRY PICKUP, same-item BUY, animal-PLACE uncertainty, `MAX_ORDERS`, and all non-STRawberry rows;
- advances at most projected shed stock and at most remaining authored SELL quantity after existing E184 debt;
- records per-due-step `sale_window_debts` atomically so the future authored row is reduced by exactly the advanced quantity.

## Gate

Source safety is not economics. Before any config/default/package/Kaggle change, run paired exact-interpreter gates against the ready V3.1 control and at least the live-field/tape-heavy opponent mix. Sweep explicit public-price thresholds (rather than silently baking one into canonical policy), report activation count, units, realized price, cash delta, rival delta, and paired margin. D4 should be rejected if the edge disappears once H4/H13 are composed or if externality screening shows the earlier STRAWBERRY supply improves rival outcomes more than our cash timing gain.
