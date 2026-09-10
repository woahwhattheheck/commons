# TITAN V3 funding town-consumption closure

This candidate closes one exact projection gap in the current selected SELL
runtime. `funded_minimum_now(...)` protects inherited market acquisitions by
replaying the represented market tape through `_funding_trace(...)`. The current
trace applies unit actions and market orders, but it does not apply the official
engine's deterministic public town-consumption stage after each turn. That can
understate future `BUY_PRODUCT` prices and certify withholding a current sale
that is actually needed to fund an inherited purchase.

The carrier is additive and default-off. It does not modify the canonical
runtime. It byte-binds the exact current `frozen_selected.py` Git blob, inserts a
small official-order-equivalent helper, invokes it after every projected market
stage, compiles the postimage, and emits a strict JSON receipt.

## Exact predecessor

Public state and inherited route:

- current step: `0`;
- current cash: `$31`;
- market WHEAT inventory: `10000`;
- eight unlocked `BAKERY` instances;
- one MILK unit in the shed and a current `SELL MILK 1`;
- inherited `BUY_PRODUCT WHEAT 1` at step `22`;
- default shop interval `4`, town-center interval `24`;
- current funding stress: `32` WHEAT units.

The predecessor omits town consumption. Under its stress-only projection, the
step-22 WHEAT purchase is quoted at `$31`, so it reports `minimum_now=0` and may
withhold the MILK sale.

The official stage consumes WHEAT after market processing at steps
`0,4,8,12,16,20`: eight BAKERies consume 48 units, and the town center consumes
one more at step 0. The exact pre-purchase inventory is therefore `9951`; a
WHEAT buy quotes the post-buy inventory `9950`, costing `$32`. With only `$31`,
the inherited purchase fails unless the current MILK sale is retained. The
successor reports `minimum_now=1`.

## Closure

Pinned objects:

- source Git blob: `fc7baf5c179818a55037f6a61d92984d81d1a21c`;
- official engine Git blob: `3c202c7ee921da239356789e266b694635103fc4`.

The injected helper mirrors `_town_consume` for the public deterministic subset:

1. after every projected market stage, apply every unlocked shop instance;
2. preserve duplicate shops;
3. apply the official two-unit multiplier to single-product shops;
4. apply the town center on its configured interval;
5. exclude FERTILIZER from town-center consumption;
6. preserve the existing rival `stress_units` scenario as additional pressure;
7. fail closed through the existing funding-certificate fallback on malformed
   public shop state.

## Validation

From this directory:

```bash
python -m unittest -v test_town_consumption_closure.py
python -m py_compile town_consumption_closure.py test_town_consumption_closure.py
python town_consumption_closure.py \
  --source ../../frozen_selected.py \
  --output /tmp/frozen_selected_town.py \
  --receipt /tmp/town-consumption-receipt.json
python -m py_compile /tmp/frozen_selected_town.py
```

The tests cover exact source/engine closure, the end-to-end `minimum_now 0 -> 1`
predecessor, official `$31 -> $32` price separation, duplicate and
single-product shop semantics, town-center/FERTILIZER behavior, no-event
identity, malformed-shop fail closure, postimage compilation, and strict receipt
serialization.

No hosted strength, release-selection, canonical-runtime, provider, Kaggle, or
submission claim is made. After independent source review, the one-tree owner
should consume only the generated helper/call postimage and run action-active,
paired official-engine regression cells before promotion.
