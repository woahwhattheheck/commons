# V5 same-tick HARVEST -> PLANT relay

Status: **research-only / default OFF / no canonical runtime hook**.

## Engine theorem

The pinned Kaggriculture interpreter performs one atomic PLANT-demand check from the submitted farmer + hand actions, then applies unit actions sequentially in actor order: farmer first, then hands.

For a mature **non-ongoing** crop (`WHEAT`, `CARROT`, `MELON`), successful `HARVEST` transfers `yield_units` to the harvesting actor and immediately sets the tile to `None`. A later co-located actor executing `PLANT <crop>` therefore sees an empty tile in the **same engine tick**. This is legal only when the seed was already in `private.seeds` at tick start; same-tick `BUY_SEED` is processed later in the market phase and cannot satisfy the atomic plant-demand gate.

This is a different mechanism from the already-verified BUY_SEED/PLANT race: it reuses an existing seed to eliminate the otherwise empty post-harvest tile interval.

## Candidate boundary

`harvest_plant_relay.transform()` rewrites exactly one hand `PASS` to `PLANT <same crop>` only when:

- `player` and `step` are exact public identities;
- standard 10x10 / 24-turn configuration is in force;
- the farmer is selected `HARVEST` on a mature positive-yield non-ongoing crop;
- exactly one hand starts on the farmer's coordinate, and that hand is selected `PASS`;
- no other hand starts on that coordinate;
- a plain-int same-crop seed exists **in excess of every already-selected same-crop PLANT request**, so adding this relay cannot trigger the engine's all-or-nothing PLANT-demand rejection.

The transform preserves the farmer action, every other hand action, the entire market list, action order, and both inputs. It never creates a seed or relies on a market purchase.

## Focused proof

`test_harvest_plant_relay.py` executes the canonical extracted `mechanics._apply_unit_action` in actor order. The positive predecessor proves:

- control: farmer HARVEST leaves the target tile empty;
- candidate: the same farmer HARVEST followed by the co-located hand PLANT leaves a fresh same-crop plant on that coordinate in the same tick;
- farmer harvest inventory is identical in both arms;
- candidate consumes exactly one preexisting seed;
- outside the target tile + one seed, farm/private state is unchanged.

Negative predecessors cover ongoing crops, immature/empty crops, no spare seed after existing PLANT demand, ambiguous/busy/non-colocated hands, reversed actor order, malformed public identity, and nonstandard configuration.

## Evaluation handoff

Do **not** promote from the synthetic proof. First instrument current V5 selected actions against real observations and count exact candidate engagements. Suggested first census: Apex + Arlene, 8 seeds, both seats. Report target crop/day, harvested units, spare seeds, hand index, and whether the control leaves the tile empty through the next selected action.

If engagement is nonzero, run paired control vs transform only on engaged coordinates using the same canonical V5 candidate identity / engine / opponent / seed / seat. Record first divergence, seed spend, next harvest timing, market receipts, field occupancy, and final margin delta. Expand only if the changed cells are mechanically stable and economically positive. A zero-engagement census should park the lane rather than add a production hook.
