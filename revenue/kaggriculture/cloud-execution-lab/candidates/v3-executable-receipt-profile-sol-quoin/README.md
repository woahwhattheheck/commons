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

## Private executable carrier

The process-isolated evaluator gives a worker only the candidate directory and a
minimal environment. Loading mutable repository root modules directly is therefore
both incomplete (`observed_clone.py` is mapped from a sibling source directory)
and vulnerable to module-cache aliasing.

`candidate.py` instead consumes the exact current standalone release:

- archive SHA-256
  `17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86`;
- `427870` archive bytes;
- SOURCE manifest SHA-256
  `1feec5a68ffde28ab7b5c7d2c92a34aa66ff5705b7d88182ef6af98df8bb5083`;
- `109` declared runtime files plus `SOURCE.json`.

Before canonical import it rejects archive symlinks, nonregular/duplicate/unsafe
members, size overflow, member-set drift, manifest drift, and per-file byte/hash
drift. It materializes the verified files into a private temporary arena, rejects
same-named modules already loaded from outside that arena, loads arena `main.py`,
and patches only arena `frozen_selected.py`. The temporary-directory owner remains
live for the worker process. Mutable repository root sources and ambient
`PYTHONPATH` are not execution dependencies.

## Gates

`test_executable_receipt_profile.py` covers:

- non-mutating current and represented-route prefix views;
- official `max(1, configured)` order-limit normalization;
- source-drift rejection and idempotence;
- exact-current predecessor early-liquidation witness;
- active-prefix parity;
- canonical source-map closure for mechanism tests; and
- preserved-engine proof that the suffix purchase does not execute while the same
  purchase in the active prefix clips to the one free shed slot.

`carrier_smoke.py` adds two fresh-process executable gates:

1. `python -I` loads the real candidate with no repository `PYTHONPATH`, constructs
   TITAN, runs lazy initialization, proves the consumer is
   `ExecutableReceiptProfileFrozenSelected`, and proves `frozen_selected`,
   `scheduler`, `observed_clone`, and `titan_runtime` all came from the private
   arena;
2. the exact repository process-isolated evaluator runs one fixed seed in both
   candidate seats for a four-step official-engine smoke, requiring a complete
   report and a real returned candidate action at every interpreted step.

`audit_change.py` binds the exact root source blobs, predecessor and engine source
cardinality, patch, full archive/pointer/manifest, candidate carrier, evaluator,
loader, smoke contract, workflow invocation, and retained artifacts. The workflow
then verifies the canonical release still rebuilds byte-exactly with a clean tree.

## Run history

Run `34409507158` at head `154917d3aaf9b66a891e58df68c167c2727329e3`
is non-evidence. Its source audit and six hermetic contracts passed, but exact-tree
setup failed on missing `observed_clone`; canonical verification did not run.

Head `960ff084fcdbc61e025e560c02e99aaabea27971` repaired the direct mechanism-test
source map but did not dependency-close the actual candidate. SOL-LOCKSTEP's exact
review correctly kept that head on HOLD. The private archive carrier supersedes it.

## Evidence boundary

The focused workflow proves a source/physics factor and an executable carrier. The
four-step smoke is not a gameplay, strength, or leaderboard result. A later game
screen is admissible only after a full candidate-action activation census proves
this receipt-profile seam changes returned decisions, followed by complete
identical-cell own-cash results split by opponent and seat. No canonical,
submission, pointer, provider, or Kaggle mutation is authorized by this branch.
