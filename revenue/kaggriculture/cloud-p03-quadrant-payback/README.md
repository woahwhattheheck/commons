# P03 — fourth-quadrant complete-chain payback gate

This packet tests the existing, disabled fourth-quadrant producer without mutating the canonical runtime. It materializes six candidate-only archives by changing exactly three effective leaves: the existing feature flag, `cash_reserve`, and `max_start_day`. Product (`WHEAT`) and amount (`13`) remain pinned.

The hard gate is not “the route started.” A candidate activation counts only when its represented tape contains a physically ordered BUY_LAND → seed → plant/service → harvest → deposit → sale chain that settles by step 718, is fully prefunded before future sale proceeds, and has conservative observed terminal proceeds strictly greater than land + seed + labor + service costs. Missing costs, future quotes, incomplete chains, same-turn seed/land funding, and horizon misses all fail closed.

## Exact grid

| Variant | cash reserve | latest configured start day |
|---|---:|---:|
| `fq-r6000-d8` | 6,000 | 8 |
| `fq-r7500-d8` | 7,500 | 8 |
| `fq-r9000-d8` | 9,000 | 8 |
| `fq-r6000-d12` | 6,000 | 12 |
| `fq-r7500-d12` | 7,500 | 12 |
| `fq-r9000-d12` | 9,000 | 12 |

## Promotion rule

The analyzer requires official-engine matched rows covering current, Arlene, and one retained responsive policy; both seats; and disjoint development/holdout seeds. Promotion is `GO` only when exactly one variant has complete profitable activations, positive aggregate heldout delta, and no negative heldout opponent × seat bucket. Everything else is `HOLD`. This packet does not authorize a Kaggle upload, canonical config flip, runtime merge, or spending.

## Local checks

```bash
cd revenue/kaggriculture/cloud-p03-quadrant-payback
python -m unittest -v test_quadrant_payback.py
python compose_variants.py \
  --archive ../cloud-execution-lab/exports/titan-current.tar.gz \
  --pin PIN.json \
  --output /tmp/p03-variants
```
