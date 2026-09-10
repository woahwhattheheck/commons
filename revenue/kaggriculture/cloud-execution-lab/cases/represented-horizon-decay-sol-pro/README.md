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

Town consumption intentionally remains outside this farm-local repair. It
mutates shared market inventory, not farm tiles or private carried/shed state.
Its later purchase-price consequences belong to the broader shared-transition
and purchase-executability owners. Plant decay is different: it directly changes
whether the next own unit action is legal and productive. The packet claims and
tests that bounded farm-local transition, not full market-world equivalence.

## Exact predecessor

The witness is full-season reachable under the exact production mechanics and
its AST-identical official-interpreter lifecycle functions:

```text
plant CARROT on day 1
WATER later on day 1 and once on days 2, 3, and 4
now                  120
baseline_end         128
hard_end             143
crop                 CARROT
planted_day          1
yield_units          3
max_lifespan_step    (1 + max_yield_day[3] + 1) * 24 = 120
represented route    HARVEST @129, DROP @130
```

Annual CARROT starts at yield 1 and `consecutive_unwatered=1`. Day-1 WATER keeps
it alive without adding yield. Day-2 WATER keeps it alive at age 1. Day-3 and
day-4 WATER occur at ages 2 and 3, the exact CARROT yield window, and add one
unit each. Official end-of-day refresh after steps 47, 71, 95, and 119 reaches
the claimed step-120 tile byte-for-field.

The real caller theorem is unmocked. With `episodeSteps=240`, route length 240,
and `now=120`, `event_aware_horizon()` computes:

```text
represented day end  143
next checkpoint      226 (outside represented day)
baseline              128
MILK service dates    none inside 129..143
initial end            128
```

The route's HARVEST/DROP is therefore the sole possible extension source.

Current prefix-only projection:

```text
yield remains 3 -> HARVEST @129 -> carried CARROT -> DROP @130
unit_event = 130
horizon end = 130
```

Official chronology and repaired projection:

```text
decay @120: 3 -> 2
decay @122: 2 -> 1
decay @124: 1 -> WEED
HARVEST @129 no-op
DROP @130 no-op
unit_event = None
horizon end = 128
```

The active `FrozenSelected.transform()` discriminator uses real current MILK
stock and a controlled ordinary optimizer only; the horizon and represented
event helpers execute unmocked:

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

The 18 exact-source contracts execute the exact prefix-materialized source and
the composed candidate, not a handwritten replacement.

`test_repair.py` covers:

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

`test_lifecycle.py` independently covers:

- AST identity between production and official `_new_plant`,
  `_apply_unit_action`, `_daily_refresh_plants`, and `_decay_plants`;
- the legal day-1 PLANT plus day-1..4 WATER/EOD trajectory into the exact
  step-120 CARROT state;
- official `3 -> 2 -> 1 -> WEED` decay and no-op HARVEST/DROP from that state.

`test_real_caller.py` independently covers:

- unmocked `event_aware_horizon()` baseline 128 / hard end 143 with no MILK
  service date or checkpoint extension;
- unmocked `represented_shed_event()` changing only through the decay repair;
- real `FrozenSelected.transform()` diagnostics and returned market action,
  including `unit_event 130 -> None`, horizon `130 -> 128`, and
  `SELL MILK 1 -> SELL MILK 2`.

Run from repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python -B -m unittest -v \
  revenue/kaggriculture/cloud-execution-lab/cases/represented-horizon-decay-sol-pro/test_repair.py \
  revenue/kaggriculture/cloud-execution-lab/cases/represented-horizon-decay-sol-pro/test_lifecycle.py \
  revenue/kaggriculture/cloud-execution-lab/cases/represented-horizon-decay-sol-pro/test_real_caller.py

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

PR #12075 is complementary rather than overlapping: it restores decay inside
`_funding_trace()` for acquisition-capacity certificates. This donor restores
decay inside `represented_shed_event()` for the shared SELL-horizon event
certificate and proves a returned-action difference at that caller.

The composed integration must still run the broader exact transition oracle
before gameplay promotion. This PR establishes a source-real returned-action
predecessor and exact bounded repair only; it makes no standalone leaderboard,
strength, merge, promotion, or submission claim.
