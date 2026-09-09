# Submitted V2 legacy-feature bisect

Source archive: `e363125093463d1f7a63a01aecb70646344dae5b318952e13a1b1641e2043e58` (377,624 bytes).
Source file-manifest digest: `08e881420e9ea8fa83b6f033d0eee42179a8101ae5026bf62b5ad5d4dd48f3c1`.
Run/receipt manifest digest: `02e1a3b554815fa07ebe552cc05e9434f507910d5ce61d35c0cdf88f8e68c0a5`.

This is a paired local official-interpreter panel, not a hosted Kaggle score prediction. Every variant uses identical source bytes except `TITAN-CONFIG.json`; positive feature effect means the submitted enabled feature produced the better terminal margin. Mirrored seats are retained as exact cells and also collapsed into seed/opponent pairs.

## Variant outcomes

| Variant | Games | W-T-L | Mean margin | Median margin |
|---|---:|---:|---:|---:|
| `baseline` | 32 | 32-0-0 | +19767.062 | +15705.500 |
| `no_redundant_hire` | 32 | 32-0-0 | +19763.562 | +15716.000 |
| `no_market_pressure` | 32 | 32-0-0 | +19515.000 | +15386.500 |
| `no_legacy_features` | 32 | 32-0-0 | +19508.750 | +15375.000 |

## Feature decisions

| Feature | Decision | Hosted-regression cause? | Enabled mean effect | + / 0 / - cells | Trace divergence |
|---|---|---|---:|---:|---:|
| `redundant_hire` | **inconclusive** | `ruled_out_on_this_panel` | +3.500 | 30 / 0 / 2 | 32/32 |
| `market_pressure` | **keep** | `ruled_out_on_this_panel` | +252.062 | 17 / 0 / 15 | 32/32 |
| `legacy_pair` | **keep** | `ruled_out_on_this_panel` | +258.312 | 18 / 2 / 12 | 32/32 |

### `redundant_hire` — inconclusive

Observed effects are small, mixed, or matchup-dependent.

| Opponent | Mean enabled effect | Paired-seat mean | + / 0 / - cells | Diverged |
|---|---:|---:|---:|---:|
| arlene | +6.750 | +6.750 | 8 / 0 / 0 | 8/8 |
| apex | -2.750 | -2.750 | 6 / 0 / 2 | 8/8 |
| reyhan | +5.000 | +5.000 | 8 / 0 / 0 | 8/8 |
| kaito | +5.000 | +5.000 | 8 / 0 / 0 | 8/8 |

Worst enabled-feature cells: apex/2609098601/seat0=-26.000, apex/2609098601/seat1=-26.000, apex/2609098602/seat0=+5.000, apex/2609098602/seat1=+5.000, apex/2609098603/seat0=+5.000.

Best enabled-feature cells: arlene/2609098601/seat0=+12.000, arlene/2609098601/seat1=+12.000, apex/2609098602/seat0=+5.000, apex/2609098602/seat1=+5.000, apex/2609098603/seat0=+5.000.

### `market_pressure` — keep

Enabled feature improved paired mean margin without a severe opponent-level reversal.

| Opponent | Mean enabled effect | Paired-seat mean | + / 0 / - cells | Diverged |
|---|---:|---:|---:|---:|
| arlene | +799.250 | +799.250 | 8 / 0 / 0 | 8/8 |
| apex | +252.750 | +252.750 | 8 / 0 / 0 | 8/8 |
| reyhan | -33.500 | -33.500 | 1 / 0 / 7 | 8/8 |
| kaito | -10.250 | -10.250 | 0 / 0 / 8 | 8/8 |

Worst enabled-feature cells: reyhan/2609098601/seat0=-96.000, reyhan/2609098601/seat1=-96.000, reyhan/2609098602/seat0=-31.000, reyhan/2609098602/seat1=-31.000, kaito/2609098603/seat0=-20.000.

Best enabled-feature cells: arlene/2609098604/seat0=+959.000, arlene/2609098604/seat1=+959.000, arlene/2609098601/seat0=+888.000, arlene/2609098601/seat1=+888.000, arlene/2609098602/seat0=+881.000.

### `legacy_pair` — keep

Enabled feature improved paired mean margin without a severe opponent-level reversal.

| Opponent | Mean enabled effect | Paired-seat mean | + / 0 / - cells | Diverged |
|---|---:|---:|---:|---:|
| arlene | +806.000 | +806.000 | 8 / 0 / 0 | 8/8 |
| apex | +261.000 | +261.000 | 8 / 0 / 0 | 8/8 |
| reyhan | -28.500 | -28.500 | 2 / 0 / 6 | 8/8 |
| kaito | -5.250 | -5.250 | 0 / 2 / 6 | 8/8 |

Worst enabled-feature cells: reyhan/2609098601/seat0=-91.000, reyhan/2609098601/seat1=-91.000, reyhan/2609098602/seat0=-26.000, reyhan/2609098602/seat1=-26.000, kaito/2609098603/seat0=-15.000.

Best enabled-feature cells: arlene/2609098604/seat0=+964.000, arlene/2609098604/seat1=+964.000, arlene/2609098601/seat0=+900.000, arlene/2609098601/seat1=+900.000, arlene/2609098602/seat0=+886.000.

## Result

Neither submitted-V2-only legacy feature is supported as the cause of the hosted regression on this panel; the local source-pinned opponent distribution is non-discriminating because every variant wins every cell.

## Reproduction

```bash
python3 run_bisect.py \
  --source-archive /path/to/titan-submitted-v2-e363.tar.gz \
  --harness-root /path/to/titan-v1-predecessor-public-policy-gauntlet-20260909 \
  --work-dir ./work --jobs 4
```

Panel: 2609098601, 2609098602, 2609098603, 2609098604; both seats; opponents arlene, apex, reyhan, kaito; 128 completed games and 64 validated report receipts required.
