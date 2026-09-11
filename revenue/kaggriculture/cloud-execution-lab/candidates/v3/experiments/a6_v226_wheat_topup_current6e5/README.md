# TITAN V3.1 A6 — current-root V226 top-up ablation donor

This directory preserves the reviewed A6 experiment seam on the repaired current-root ancestry without creating another Actions-heavy PR.

## Custody

- parent / build-custody root: `6e5e3c7cc5302d6db4b702cc4fd7c8ca721d7b8a` (#12535)
- shipped gameplay ancestor: `8e3d92a286806f9f9525973ee7d359b629a11487` (#12537)
- current R04 blob at this parent: `7edacbfb4916b8f241b689ded6643240ca02a9ec`
- stale reviewed A6 source: #12532 @ `963645bd36f2c1e99fa7c3508f6c1d49aeb4fb37`

Reviewed stale-donor blobs retained as provenance, not copied blindly:

- baseline `224075864c8806b83d4c34e18697504d9a62a420`
- candidate `e26ac36f481913e147a8ead970e83253fb6c88c7`
- strict reducer `5f5913a8617e394dba8cb992e3bbcb3ef7c3f83e`
- reducer poison tests `0ab0ccf75d7c2cd8a8a349f6655426045a551b8f`

## What changed from the stale donor

The old a612 baseline/candidate stopped the positional `install()` call after `strawberry_topup`. On 8e3/6e5 that would silently leave shipped B5 CARROT + JIT disabled. These current-root adapters therefore use keyword arguments and explicitly preserve:

- sale horizon 8;
- opening 0;
- row order ON;
- evening flush ON;
- sale fertilizer ON;
- cattle-early ON (this is an orthogonal A6 screen; cattle disposition belongs to #12540/#12505);
- kill-late-water OFF;
- strawberry-endgame OFF, max 8;
- no-late-sale-advance ON at 648;
- H4 strawberry top-up ON;
- **B5 CARROT fertilizer ON**;
- **B5 JIT fertilizer ON**.

The candidate still ablates exactly one mechanism: `_v226_topup()`, the bounded dynamic next-step WHEAT-shortage bridge. Native tape WHEAT purchases, V233 sheep-feed buys, V234 rescue buys, worker commands, market rows, and later wrappers stay parent-owned.

## Authority boundary

This branch is a **donor, not economics or production authority**. Parent 6e5 still contains the pre-final L3 rival-gate implementation. Do not spend evaluator capacity or promote A6 from this donor. Once #12565 self-collapses to its terminal five-path L3 production head, make one consumer from that exact head, preserve its then-current tuple by keyword, transplant/adapt the strict #12532 reducer + poison tests, and run paired current-package economics.

Fail-closed future disposition remains:

- zero A6 trace activation -> reject;
- any negative paired-margin cell -> hold;
- non-positive mean paired margin in either self-play or Arlene regime -> hold;
- only positive means in both regimes with zero negative cells may advance to a reviewed V226 reduction gate.

No `overlay/**`, `apply_v3.py`, config/default, FILES/manifest, builder, evaluator/opponent, provider, Kaggle, leaderboard, or submission byte is changed here. No workflow or PR is added deliberately while repository Actions is saturated.
