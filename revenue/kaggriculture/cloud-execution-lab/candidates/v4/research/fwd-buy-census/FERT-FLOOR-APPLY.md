# Gemini FERT floor-buy/apply — full-path source certificate

Status: **constructed full-interpreter research / no current-native engagement or activation claim**.

This package tests the mechanically valid core of the historical FERT floor-buy idea: `BUY_PRODUCT FERTILIZER` can acquire FERT at the public $1 floor; the product lands in the shed; a farmer must then `PICKUP` and `FERTILIZE`; subsequent WATER callbacks can convert that consumed FERT into extra annual-crop yield. Those custody/application callbacks are real opportunity cost.

## Two witnesses, two authority levels

`run_pair()` remains a deliberately constructed one-WATER CARROT mechanism witness. It proves the buy -> shed -> carried inventory -> FERTILIZE -> WATER path and a +1 harvest-unit effect in both seats, but it does **not** claim its initial plant fixture was produced by a natural/current V4 prefix.

`run_amortized_pair()` is the source-reachable prefix witness. Version v4 closes two merged predecessor errors:

1. **No injected day-4 plant.** The predecessor directly called `_new_plant(MELON, plant_day=4)` and then began the official interpreter at step 96 with WATER. That state is not reachable in the predecessor fixture: official EOD step 95 clears all hands, and a real main-farmer PLANT at step 96 consumes that actor's unit action. v4 instead starts with an empty default tile plus one real MELON seed, executes `PLANT MELON` at step 96, and performs its first WATER at step 97.
2. **No injected zero-yield annual crop / premature harvest.** Official `_new_plant` initializes annual crops, including MELON, with `yield_units=1`; the predecessor overwrote that with 0. MELON also has `first_yield_day=10`, so a day-4 plant cannot legally harvest on day 12. v4 keeps the official initial unit and waits until step 336 (day 14, age 10) to HARVEST.

The corrected reachable schedule is:

- step 96 (day 4): `PLANT MELON` from a real seed;
- step 97 plus steps 144 and 192: shared survival WATER;
- step 239: both arms still hold the same live day-4 MELON with `yield_units=1`;
- candidate only: BUY FERT at 240, PICKUP at 241, FERTILIZE at 242;
- both arms: production WATER at 243 / 264 / 288 (ages 6 / 7 / 8);
- step 336: legal HARVEST at age 10;
- step 337: common DROP + SELL liquidation.

Because the reachable annual plant starts at one held unit, the strongest corrected three-WATER result is **candidate 6 vs control 4 = +2**, not the merged predecessor's artificial 6 vs 3 = +3. The two extra unit callbacks are therefore **1.0 callback per incremental unit**, not 2/3. This correction is intentionally a theorem downgrade: false reachability is worse than a smaller source-real edge.

## Boundaries

A positive result remains research evidence only. It does not prove natural/current-native engagement, available idle unit capacity, opponent robustness, policy value, win rate, or activation authority. Rival actions are PASS. Shared market inventory can differ because the candidate sells additional realized crop; the certificate's `same_final_physical` boundary covers both farms and private stocks, excluding cash and the shared market.

The checker binds the exact official engine blobs through `opportunity_cost.ENGINE_BLOBS`, executes both seats, tests the $1 floor boundary, asserts the real PLANT/seed-consumption postimage, verifies pre-FERT and production-yield states, waits for legal MELON harvest age, and covers unfunded controls plus exact-int poison rejection.
