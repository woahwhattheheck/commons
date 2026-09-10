# TITAN V3 represented-horizon plant-decay closure

Operation: `TITAN-V3-REPRESENTED-HORIZON-PLANT-DECAY-CLOSURE-20260910-01`

This is an additive, source-bound composition donor. It stacks on the executable
market-prefix donor in PR #12056 and changes no canonical runtime, configuration,
archive, pointer, provider, Kaggle, game bank, or submission state.

## Exact custody

- Stack base / PR #12056 head:
  `5d1b376d33858dd827e7e20051cc49648d313034`
- Canonical `frozen_selected.py` Git blob:
  `fc7baf5c179818a55037f6a61d92984d81d1a21c`
- Prefix materializer Git blob:
  `f14341425ad6bf697702e0167c7c4ae3264d434b`
- Production mechanics Git blob:
  `044a4f9c0a4a44dde10ada57563238bcaf82075d`
- Official interpreter Git blob:
  `3c202c7ee921da239356789e266b694635103fc4`

`repair.py` authenticates all four inputs, invokes the exact #12056 materializer
in memory, and then applies exactly two reversible insertions to that candidate.
A source, prefix-carrier, mechanics, interpreter, or preimage drift fails closed.

## Source-real defect

`FrozenSelected.transform()` calls `represented_shed_event()` to decide whether a
later represented unit stage can add goods to the shed beyond the inherited
eight-turn SELL horizon. The helper starts from the exact post-unit/pre-market
own state and advances:

1. the represented current market stage;
2. each later represented unit stage;
3. each later represented market stage.

The official interpreter advances a different chronology on every turn:

```text
own unit stage -> market -> town consumption -> plant decay
```

The current projection omits `_decay_plants(farm, step)` entirely. An annual crop
therefore remains harvestable in the copied world after the official world has
already reduced its yield to zero and replaced it with a WEED. A later
HARVEST -> DROP can fabricate `unit_event`; every product then inherits the
longer horizon, so the omission can change the returned current SELL action.

Town consumption intentionally remains outside this physical-own-state helper.
It mutates shared market inventory, not farm tiles or private carried/shed state.
Its economic consequences belong to the broader shared-transition owner. Plant
decay is different: it directly changes whether the next own unit action is
legal and productive.

## Exact predecessor

The witness is mechanics-valid and metadata-valid:

```text
now                  120
baseline_end         128
hard_end             130
crop                 CARROT
planted_day          1
yield_units          3
max_lifespan_step    (1 + max_yield_day[3] + 1) * 24 = 120
represented route    HARVEST @129, DROP @130
```

Current prefix-only projection:

```text
yield remains 3 -> HARVEST @129 -> carried CARROT -> DROP @130
unit_event = 130
```

Official chronology and repaired projection:

```text
decay @120: 3 -> 2
decay @122: 2 -> 1
decay @124: 1 -> WEED
HARVEST @129 no-op
DROP @130 no-op
unit_event = None
```

The active `FrozenSelected.transform()` discriminator uses real current MILK
stock and a controlled ordinary optimizer:

```text
prefix-only predecessor: false horizon -> returned SELL MILK 1
prefix + decay closure:  no false event -> returned SELL MILK 2
```

The test also proves both insertions are independently necessary:

- removing current-step decay revives a yield-1 crop at step 121;
- removing future-step decay revives a yield-2 crop at step 123.

Pre-expiry annual crops, ongoing crops (`max_lifespan_step=-1`), and no-plant
worlds preserve the prefix donor's event and returned-state behavior.

## Bounded repair

After represented current market execution:

```python
m._decay_plants(f, now)
```

After every represented future market stage:

```python
m._decay_plants(f, t)
```

The insertion point is not cosmetic. The supplied current state is post-unit and
pre-market; decay belongs after current market/town and before the next unit
stage. A future event is checked immediately after that turn's units, then its
market is represented, then decay prepares the following unit stage. Returning
an event before same-step decay is correct because the shed addition already
occurred earlier in official turn order.

## Contracts

`test_repair.py` executes the exact prefix materialized source and the composed
candidate, not a handwritten replacement. It covers:

- exact canonical source, prefix carrier, mechanics, and interpreter binding;
- exact official `market -> town -> decay` chronology binding;
- reversible two-insertion source closure;
- metadata-valid annual expiration;
- independent current-boundary and future-boundary mutation killers;
- pre-expiry, ongoing-crop, and no-plant identity controls;
- active `FrozenSelected.transform()` returned-action discrimination;
- state, route, observation, and authored-action nonmutation;
- malformed/duplicate preimage fail closure;
- deterministic JSON receipt and unified patch.

Run from repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python -B -m unittest -v \
  revenue/kaggriculture/cloud-execution-lab/cases/represented-horizon-decay-sol-pro/test_repair.py

python -B \
  revenue/kaggriculture/cloud-execution-lab/cases/represented-horizon-decay-sol-pro/repair.py \
  --repo . --format json

python -B \
  revenue/kaggriculture/cloud-execution-lab/cases/represented-horizon-decay-sol-pro/repair.py \
  --repo . --format patch
```

## Composition and disposition

Apply the prefix selection from #12056 before this chronology closure. The
in-prefix HIRE executability owner and represented purchase executability owner
remain authoritative for whether their market requests actually complete. This
donor neither reimplements nor weakens those contracts.

The composed integration must still run the broader exact transition oracle
before gameplay promotion. This PR establishes a source-real returned-action
predecessor and exact bounded repair only; it makes no standalone leaderboard,
strength, merge, promotion, or submission claim.
