# TITAN V3 executable receipt-profile prefix — SOL-QUOIN

## Hypothesis

Current `FrozenSelected` inherits `SellScheduler.receipt_profile()`. The callback
constructs a future shed-capacity profile from the represented controller tape,
but iterates every raw market row. The preserved official engine first slices
each player's queue to `maxMarketOrdersPerTurn` and only then parses/executes it.

An engine-inactive suffix purchase can therefore become phantom shed occupancy in
the capacity callback. That can reject a delayed SELL plan and force stock into an
earlier market solely to make room for a purchase that cannot execute. An inactive
suffix SELL can create the opposite error by releasing capacity that never exists.

The deterministic predecessor witness uses:

- shed capacity `4`;
- current shed `CARROT = 3`;
- `maxMarketOrdersPerTurn = 1`;
- future raw market queue `[[], ["BUY_ANIMAL", "GOOSE", 2]]`.

The engine executes only the first blank row and leaves occupancy at `3`. The
predecessor profile processes the suffix animal order anyway, records occupancy
`5`, rejects a delayed three-unit CARROT sale, and accepts only after at least two
units are marked sold early.

## One-factor candidate

`executable_receipt_profile.install()`:

1. Git-blob pins exact current `frozen_selected.py` and inherited `scheduler.py`;
2. subclasses only `frozen_selected.FrozenSelected` before canonical lazy runtime
   construction;
3. creates shallow, non-mutating current/future action views whose market queues
   contain only the official first-N prefix;
4. delegates the unchanged inherited `receipt_profile()` implementation; and
5. leaves all active-prefix semantics unchanged.

The candidate does **not** change active-row affordability, partial fills, market
prices, rival assumptions, horizon discovery, target ownership, `optimize_lot`,
forced-feasibility/ranking, same-turn funding, materialization, selected-action
state, later transforms, deadlines, configuration, archives, pointers, provider
state, or Kaggle submission state.

Active-row physical fill modeling is deliberately not bundled into this factor.
That residual question has different rival-price and same-turn-funding assumptions
and needs its own causal experiment.

## Gates

`test_executable_receipt_profile.py` covers:

- non-mutating current and represented-route prefix views;
- official `max(1, configured)` order-limit normalization;
- source-drift rejection and idempotence;
- exact-current predecessor early-liquidation witness;
- active-prefix parity; and
- preserved-engine proof that the suffix purchase does not execute while the same
  purchase in the active prefix clips to the one free shed slot.

`audit_change.py` binds the exact source blobs, the predecessor raw-loop
cardinality, the official engine prefix slice, and the candidate's single prefix
transformation.

## Evidence boundary

The focused workflow is a source/physics gate, not a score claim. A later gameplay
screen is admissible only after candidate-only action activation is retained and
complete identical-cell own-cash results are available by opponent and seat. No
canonical or submission mutation is authorized by this branch.
