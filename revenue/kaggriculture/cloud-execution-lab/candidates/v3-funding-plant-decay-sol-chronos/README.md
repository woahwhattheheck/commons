# TITAN V3 funding-trace plant-decay chronology closure

Operation: `TITAN-V3-FUNDING-PLANT-DECAY-CHRONOLOGY-20260910-01`

## Exact defect

The active `frozen_selected.py` replays a bounded future own route in `_funding_trace()`. It applies future unit actions and then the represented market rows, but it does not execute the official interpreter's deterministic post-market plant-decay stage. The pinned interpreter orders each turn as:

1. both players' unit stages;
2. joint market execution;
3. public town consumption;
4. `_decay_plants(farm, step)`;
5. optional end-of-day processing.

Within a same-day funding horizon, an expiring crop can therefore retain one or more units in the certificate that do not exist in the official world. A later `HARVEST -> DROP` may fabricate shed occupancy. Because `funded_minimum_now()` protects only acquisitions completed by its baseline trace, that false occupancy can make a real baseline-completed `BUY_ANIMAL` or `BUY_PRODUCT` disappear from `reference_acquisitions`, permitting the optimizer to withhold a current sale that the purchase needs for capacity.

## Reduced executable witness

At step 120:

- shed capacity is 2;
- own shed contains `MILK=1` and the inherited current queue sells that unit;
- the main farmer stands on a mature WHEAT plant planted on day 0 with `yield_units=2` and `max_lifespan_step=120`;
- the represented route is `HARVEST` at 121, `DROP` at 122, and `BUY_ANIMAL GOOSE 1` at 123;
- starting cash is already $300, so only capacity distinguishes the arms.

This lifecycle is season-reachable under the pinned engine: non-ongoing WHEAT planted on day 0 receives `max_lifespan_step = (0 + max_yield_day 4 + 1) * turnsPerDay 24 = 120`; two retained units are within its official maximum yield. The fixture also uses the engine's locked-quadrant layout and a shed-access farmer position.

Official chronology decays the plant from 2 to 1 after the step-120 market. With the inherited MILK sale, the one harvested WHEAT leaves room for the goose; with the sale withheld, the shed is full and the goose purchase fails. The incumbent funding trace omits decay, harvests two WHEAT in both arms, fills the shed in both arms, and incorrectly concludes that the inherited purchase was never completed. On the exact current source, the certificate changes from `minimum_now=0` to `minimum_now=1` after the closure.

## Carrier

`materialize.py` is intentionally additive and fail closed. It:

- authenticates `frozen_selected.py` Git blob `fc7baf5c179818a55037f6a61d92984d81d1a21c`;
- authenticates the runtime binding path through `scheduler.py` blob `a483b24dd72b580d7d8811636b54d2d44f391575` and `mechanics.py` blob `044a4f9c0a4a44dde10ada57563238bcaf82075d`;
- verifies that the source wildcard-imports `scheduler`, that `scheduler` exports an unrebound `import mechanics as m`, and that runtime `mechanics._decay_plants` has the same attribute-free AST digest as the official primitive;
- authenticates official `kaggriculture.py` Git blob `3c202c7ee921da239356789e266b694635103fc4`;
- verifies the official `market -> town -> decay -> end-of-day` call order;
- locates exactly one top-level `_funding_trace()` and exactly one `for t in range(now, end + 1)` loop;
- inserts exactly `m._decay_plants(f, t)` as the final stage of each simulated turn;
- compiles and structurally re-verifies the generated postimage;
- writes a new file and deterministic receipt atomically; and
- refuses source/scheduler/mechanics/engine drift, unresolved runtime binding, aliases, pre-existing outputs, duplicate patches, or ambiguous anchors.

The patch is designed to compose after PR #12053's town-consumption stage: when that helper is present, town consumption remains immediately before plant decay, matching the official chronology. Horizons crossing an end-of-day boundary still require that lane's fail-closed lifecycle rule; this carrier does not claim to model future shop unlocks, daily crop refresh, auto-drop, or RNG.

## Validation

From repository root:

```bash
python -B -m unittest -v \
  revenue/kaggriculture/cloud-execution-lab/candidates/v3-funding-plant-decay-sol-chronos/test_funding_plant_decay.py
```

Materialize without touching canonical source:

```bash
python -B revenue/kaggriculture/cloud-execution-lab/candidates/v3-funding-plant-decay-sol-chronos/materialize.py \
  --source revenue/kaggriculture/cloud-execution-lab/frozen_selected.py \
  --scheduler revenue/kaggriculture/cloud-execution-lab/scheduler.py \
  --mechanics revenue/kaggriculture/cloud-execution-lab/mechanics.py \
  --engine revenue/kaggriculture/cloud-execution-lab/reference/engine/kaggriculture.py \
  --output /tmp/frozen_selected_decay.py \
  --receipt /tmp/funding_decay_receipt.json
```

Twenty-five contracts cover the exact source/scheduler/mechanics/engine identities, runtime call-target binding, chronology order, a season-reachable lifecycle boundary, deterministic parity, wrong-parity no-op, WEED transition, animal noninterference, the capacity killer, canonical nonmutation, byte-identical rematerialization, dependency drift, output aliasing, and town-consumption composition order.

## Disposition boundary

This is `SOURCE_REAL_ACTION_UNMEASURED`. It changes no canonical runtime, config, archive, pointer, game, seed lease, provider, Kaggle submission, or promotion state. Integration should compose this postimage with the reviewed town-consumption and future-sale-solvency closures, then require a fresh-process, both-seat, current-control panel with tested-action activation, zero new losses/lost wins, nonnegative own-cash and margin by opponent x seat, and a hard worst-cell own-cash floor.
