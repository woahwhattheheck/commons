# B9 terminal fertilizer tail (default-OFF experiment)

This narrows Muse's broad "terminal 7-step search" idea to a source-safe zero-route-shift micro-stacker on frozen V3.1.

## Mechanism

At steps 716-717 only, a worker whose parent command is exactly `PASS` may replace that command with `COLLECT_FERTILIZER` only when the worker is already on a shed-adjacent animal tile and the public tile state has `fertilizer_available is True`. Nothing moves; no CARE/FEED/HARVEST/DROP/PLACE command is stolen.

At step 718 the existing parent liquidator remains authoritative. If and only if this wrapper actually collected terminal fertilizer in the same episode, any resulting `SELL FERTILIZER` row is stable-partitioned behind all non-fertilizer parent market rows. This trailing-row rule is essential: the naive collection arm left the parent value-sort unchanged and failed D3 on the frozen Arlene panel (mean ΔM -0.25; mean own +2.0, rival +2.25). Reordering only the newly introduced fertilizer sale behind the existing rows preserves the parent's terminal market interaction before realizing the extra stock.

State is per player and resets on a step rewind/replay. Malformed or ambiguous state fails open to the parent.

## Practice-factor evidence

Exact retained V3.1 package `F0C18AXAL04`, pinned official interpreter/evaluator, frozen seeds `2611151001..2611151008`, both candidate seats:

- vs vendored Arlene: 16 cells = 12 positive / 4 ties / 0 negative; mean ΔM **+4.75**, median +5, range 0..+8; mean Δown +4.5, mean Δrival -0.25.
- vs exact V3.1: 16/16 exact control-equivalent; Δown = Δrival = ΔM = 0 in every cell.

`B9-ECONOMICS-20260911.json` commits every arm/control score pair and the exact package/source custody inherited from the independent #12390 raw-score reproduction. `terminal_fertilizer.py` SHA256 is recorded in that receipt.

This is deliberately tiny and remains **default OFF**. It is not an official promotion gate and does not modify the live overlay, config, manifest, package, evaluator, opponent, or Kaggle submission.
