# TITAN V3 — same-turn funding Pareto rank

Operation: `TITAN-V3-SAME-TURN-FUNDING-PARETO-RANK-20260910-01`

## Finding

Current `FrozenSelected` can move an already-planned later `SELL` into an earlier empty row when that is required to fund a fixed `HIRE`, `BUY_LAND`, `BUY_SEED`, or `BUY_ANIMAL`. It generates every conserving candidate, rejects candidates that do not fully execute the same target acquisition, and gives each survivor this rank:

```python
(moved, int(state["money"]), source - target, target - destination, item)
```

The winner is selected with `min()`. Movement is correctly primary, but the positive second component makes equal-minimum-movement candidates prefer **less** certified own cash.

This is not an inference from an aggregate score. It is the literal optimization order at the active final SELL boundary. The helper already records the same value as `remaining_cash_after_target` in its receipt.

## Exact predecessor killer

The checked witness starts with no cash and a first-HIRE cost of 10:

```json
[
  [],
  ["HIRE"],
  ["SELL", "CARROT", 1],
  ["SELL", "WOOL", 1]
]
```

At base inventory, CARROT pays 35 and leaves 25 after the HIRE; WOOL pays 200 and leaves 190. Both candidates:

- move exactly one already-planned unit;
- execute the same previously failing HIRE;
- preserve the full queue length and every untouched row;
- preserve per-product total sale quantities (`CARROT=1`, `WOOL=1`); and
- pass the helper's existing conservative rival-sale receipt calculation.

The predecessor selects CARROT and the one-line candidate selects WOOL, increasing the helper's own certified post-target cash by **165** without increasing moved quantity.

## One-factor candidate

The materializer binds exact current `frozen_selected.py` Git blob `fc7baf5c179818a55037f6a61d92984d81d1a21c` and changes only:

```diff
- (moved, int(state["money"]), source-target, target-destination, item)
+ (moved, -int(state["money"]), source-target, target-destination, item)
```

`min()` therefore retains the existing minimum-movement rule, then maximizes the certificate's remaining own cash. Source distance, destination distance, and item keep their existing deterministic tie order.

## Evidence custody

The exact-head workflow:

1. verifies the immutable current source Git blob and one preimage;
2. proves the patch changes one physical line and one expression only;
3. executes predecessor and candidate implementations on the real current module and current market-price primitives;
4. requires `CARROT/25 -> WOOL/190`, equal one-unit movement, equal acquisition completion, and identical per-item sale totals;
5. runs fail-closed source/ranking contracts;
6. compiles the materialized candidate; and
7. retains machine-readable receipts outside the checkout while proving the repository remains clean.

## Boundary

This branch is additive evidence and a deterministic integration carrier. It does not modify canonical TITAN, configuration, archive, source manifest, release pointers, provider state, Kaggle state, or a submission. The exact witness proves a source objective inversion; it does **not** claim a whole-game or leaderboard improvement. Composition still requires a matched, both-seat, official-interpreter panel with real returned-action activation, own-cash-first admission, no negative opponent-by-seat stratum, and no new loss or lost win.
