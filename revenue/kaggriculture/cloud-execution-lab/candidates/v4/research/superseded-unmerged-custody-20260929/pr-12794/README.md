# Passive town market baseline

Status: additive V4 research; no runtime/action policy or activation key. Owner: ASTRA-TOWNCURVE.

This package answers a specific market question: with both players taking no actions, how far can town-center and unlocked-shop demand move each product's inventory/price over the standard 720-observation episode?

`passive_town_baseline.py` binds exact official engine Git blob `3c202c7ee921da239356789e266b694635103fc4`. It uses the engine's own `_town_consume` and `_end_of_day` with **two real passive farms**. Keeping both farms is important: end-of-day weed spawning consumes RNG draws before the shop unlock `rng.choice`, so a simplified shop-only RNG loop produces the wrong seed-to-shop sequence.

The run emits:

- `curves.csv`: per-step/per-product min, p05, p50, mean, p95 and max inventory/price across requested seeds, plus an exact passive-town envelope.
- `crossings.csv`: first visible step each seed reaches or passes each product's engine `T` deficit. Step 719 is terminal-only and is not an actionable sale window.
- `shop_paths.csv`: exact unlocked-shop sequence for every seed.
- `summary.json`: pinned engine/config provenance and product crossing summary.

The envelope is stronger than the 100-seed sample: for each product it computes the exact lower/upper passive inventory reachable over **any** legal shop-identity sequence with the standard deterministic unlock count. Bounds are product-wise; one joint shop sequence need not realize every product extreme simultaneously. `classify()` can compare a public observation with this envelope, but it never emits an action and `WITHIN_PASSIVE_ENVELOPE` means only “town-only flow is mechanically possible,” not “town flow caused this state.”

## Exact run

From `revenue/kaggriculture/cloud-execution-lab`:

```bash
python candidates/v4/research/passive-town-baseline/test_passive_town_baseline.py
python -O candidates/v4/research/passive-town-baseline/test_passive_town_baseline.py
python candidates/v4/research/passive-town-baseline/passive_town_baseline.py \
  --engine reference/engine/kaggriculture.py \
  --seed-start 1 --seed-count 100 \
  --out-dir candidates/v4/research/passive-town-baseline/results
```

The focused suite pins the engine blob, verifies all 100 sampled paths remain within the exact envelope, checks FERTILIZER as the no-town-demand control, binds seed 1's shop sequence (thereby testing weed-RNG ordering), and asserts the requested STRAWBERRY/WOOL crossing receipt.

## Preflight expectation (not an activation claim)

A source-mirrored preflight predicts seeds 1–100 will produce: STRAWBERRY `T=100` crossing in 97/100 seeds (first visible step min 261, median 349, max 681); WOOL `T=105` crossing in 55/100 (min 201, median 389, max 657); FERTILIZER remains inventory 10,000 / price $100 throughout town-only flow. The exact-engine suite intentionally asserts those values so any mismatch fails loudly rather than laundering the preflight as a receipt.

No production config, controller, composer, archive, workflow definition, or Kaggle submission is changed here. Economic use still requires current-V4/opponent evidence; passive inflation is a baseline, not a trading strategy.
