# H3 × H4 composition — frozen Arlene panel

Factor-level 2×2 on the retained ready-to-submit V3.1 R04 package, seeds `2611151001..2611151008`, both seats (16 paired cells). H3 is the reviewed no-late E184 reservation factor (`reserve_sales` skipped at step >=648). H4 is a local semantic mirror of PR #12344's STRAWBERRY same-row top-up. This is **not** an exact packaged H4-branch proof.

| contrast | mean ΔM | median | + / 0 / − | range |
|---|---:|---:|---:|---:|
| H3 − control | +204.75 | +183 | 16 / 0 / 0 | +110 .. +339 |
| H4 − control | +24.375 | +16 | 10 / 0 / 6 | −15 .. +116 |
| H3+H4 − control | +229.125 | +200 | 16 / 0 / 0 | +137 .. +357 |
| H4 given H3 | +24.375 | +16 | 10 / 0 / 6 | −15 .. +116 |
| H3 given H4 | +204.75 | +183 | 16 / 0 / 0 | +110 .. +339 |
| factorial interaction | 0.0 | 0 | 0 / 16 / 0 | 0 .. 0 |

The effects are **exactly additive cell-for-cell** on this panel: interaction is zero in all 16 cells. That means H3 and H4 do not mechanically collide here. It also means H4's six negative incremental cells are real rather than being caused by H3. H3 alone is positive in every cell; adding H4 raises the pooled mean but regresses H3 on seeds 2611151004 (−15 both seats), 2611151005 (−10 both seats), and 2611151008 (−15 both seats).

Decision implication: if integration requires singleton-relative cell/stratum non-regression, prefer H3 alone and HOLD H4 despite the larger combined pooled mean. If the policy permits small paired negatives, the combined arm deserves a broader exact-package panel because the mean remains higher and all combined-vs-control cells stay positive. Do not infer either merge decision from this factor-level receipt alone.

Exact per-cell deltas are in `H3-H4-ARLENE-FACTORIAL-20260911.json`. No default, merge, package pointer, provider, or Kaggle state changes are authorized by this evidence.
