# S33 row-shed — current-root donor

## Purpose

This is the durable current-root source/contract carrier for the S33 field result announced in `#titan-kaggriculture` on 2026-09-11. It is based on exact shipped V3.1 commit `8e3d92a286806f9f9525973ee7d359b629a11487` (#12537), where B5 CARROT + JIT are already production/package bytes.

The field gate reported 1,920 games per arm against 16 published agents. The row-shed arm was better than the cattle-OFF score-facing configuration in 1,912/1,920 games (6 worse, 2 same), added no loss against any opponent, and was +421.1/game versus V3.0. Those numbers are fleet evidence; this PR does not recreate or upgrade their authority.

## Mechanism

Current R04 `ROW_ORDER` ranks the contiguous leading SELL block by the price drop implied by each *requested* quantity. Authored tapes can request far more units than the projected shed can actually supply, so an impossible 1000-unit sale can outrank a smaller sale that can really execute.

S33 changes only the ranking quantity:

`q_eff = min(requested_sell_quantity, projected_shed[item])`

The original SELL row, requested quantity, leading-block membership, stable tie order, and every row after the first non-SELL barrier are unchanged. The production consumer should obtain the cap from the existing `projected_shed(action, FarmView(observation))` helper immediately before ROW_ORDER. Missing or malformed projection data falls back to inherited requested-quantity scoring rather than creating a new behavior.

## Current-root / convergence boundary

This carrier intentionally changes no production overlay, config/default, FILES/MANIFEST, package, evaluator, opponent, provider, Kaggle, or submission artifact. It exists so the high-value S33 factor is durable and reviewable while the P0 stack converges.

Integration must preserve B5 CARROT + JIT + H4 + rival-gated L3 + sale-fertilizer and stay orthogonal to the one-key cattle experiment (#12540). The current assembly order is build custody (#12535), L3 correctness (#12541), cattle qualification, then optional factors. Once that parent is stable, the row-shed winner should have exactly one direct-current-root production/package consumer; this experiment branch is not merge authority by itself.

If a separately published a612 row-shed donor appears, its reviewed exact source/test bytes should be consumed or mechanically reconciled rather than creating a second semantic implementation.
