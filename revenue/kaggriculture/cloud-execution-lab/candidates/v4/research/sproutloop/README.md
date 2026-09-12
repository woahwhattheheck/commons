# SPROUTLOOP — zero-age non-ongoing crop conversion census

**Status:** research-only, default-OFF, no runtime/config/archive/Kaggle mutation.

This lane source-binds a previously unregistered engine mechanic rather than adding another V4 controller. In the exact current official engine Git blob `3c202c7ee921da239356789e266b694635103fc4`, a newly planted **non-ongoing** crop starts with `yield_units = 1`, while `HARVEST` has no crop-age gate. WHEAT, CARROT, and MELON are non-ongoing. The interpreter applies unit actions before market orders, so on an owned shed-adjacent empty tile a pre-bought seed can follow this four-callback source-level cycle:

`PLANT -> HARVEST -> DROP + SELL -> DIG`

The point is not that this is automatically good policy. The point is that it creates a cash-conversion frontier that V4 should measure instead of silently treating every crop as a long-horizon production asset.

## Exact market-only bound

`sproutloop.py` authenticates the full engine Git blob before parsing source contracts and market constants. With no rival sales, no town consumption, no travel, no weeds, and no opportunity cost, reserving step 0 for seed purchase leaves a one-worker structural cap of 179 four-callback loops across steps 1..718.

Current exact arithmetic:

| crop | seed | base quote | base spread | profitable consecutive sell quotes (cap 719) | single-worker units under 179-cycle cap | gross spread at that cap |
|---|---:|---:|---:|---:|---:|---:|
| MELON | 80 | 250 | +170 | 131 | 131 | +14,868 |
| WHEAT | 10 | 25 | +15 | >=719 | 179 | +2,062 |
| CARROT | 20 | 35 | +15 | 158 | 158 | +851 |

For MELON, the quadratic glut curve makes the frontier self-limiting: the 131st consecutive own quote is still 81, while the next quote falls below seed cost. That is a **mechanism bound**, not expected value. Rival MELON sales can collapse it sooner; town-center consumption can lift it; worker time can dominate it; the current route may already use the same tile/actions for higher-value work.

## Why this is a distinct lane

This is production-side conversion evidence, not another market-crash controller. Existing crash/sale-window owners retain liquidation timing and price-impact policy. Existing opening-book owners retain early seed budgeting. Existing terrain/weed owners retain empty-tile protection. SPROUTLOOP only establishes and measures the source-bound seed→immediate-product loop and hands a concrete gate to the single current-native assembler.

A production experiment should therefore be fail-closed and default-OFF: only use currently free/compatible worker+tile capacity, require live quote headroom over seed cost plus an opportunity-cost reserve, and let existing sale/crash logic own disposal timing. No activation recommendation is made here.

## Reproduce

From this directory:

```bash
python -B -m unittest -v test_sproutloop.py
python -O -B -m unittest -v test_sproutloop.py
python -B sproutloop.py \
  --engine ../../../../reference/engine/kaggriculture.py \
  --pretty
```

The analyzer fails closed on engine blob drift, any change to the non-ongoing initial-yield expression, a new HARVEST age gate, DIG semantics drift, or reversal of unit-before-market resolution.
