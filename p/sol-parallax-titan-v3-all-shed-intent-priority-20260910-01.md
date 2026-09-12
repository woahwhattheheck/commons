# SOL-PARALLAX — TITAN V3 all-shed intent-priority screen

Operation: `titan-v3-all-shed-intent-priority-20260910-01`

## Question

Frozen V2 widened scheduler ownership to every positive non-operating product in
the post-unit shed and traversed those targets in `PRODUCTS` order.  The exact
order-preserving target-domain screen on PR #11862 showed that shrinking
ownership back to inherited/pending products was a regression:

- mean own cash: `-3.875`;
- candidate actions changed: `10/32` paired cells;
- own-negative / positive / zero cells: `8 / 2 / 22`;
- versus V1: `-4.8125` mean own cash, with no positive cell.

A separate exact matched reconciliation compared two candidate trees that
differed only in target-map insertion order inside that narrowed arm.  Restoring
pending-then-baseline priority instead of `PRODUCTS` order contributed:

- mean / total own cash: `+8.375 / +268`;
- own-positive / negative / zero cells: `6 / 0 / 26`;
- mean rival cash: `+2.125`;
- mean margin: `+6.25`;
- all four opponent-by-seat own-cash strata nonnegative.

Those results establish that target narrowing and target priority have opposite
effects.  They do **not** establish that intent priority remains beneficial when
V2's full all-shed ownership is retained.  This branch runs that missing direct
one-factor test.

## Candidate factor

Control is byte-exact frozen V2 scheduler blob:

`7c068b7078c3d7c09bb3836590ad42b0af934cdf`

The candidate preserves the control target set and quantity exactly:

```python
{p: max(0, int(shed.get(p, 0)))
 for p in PRODUCTS
 if shed.get(p, 0) > 0}
```

It changes only traversal priority:

1. products already owned by `self.pending`, in existing insertion order;
2. products offered by the inherited baseline SELL tape, in first-seen order;
3. every remaining product in the original `PRODUCTS` order.

Duplicate keys retain their earliest position.  WHEAT, FERTILIZER, stale keys,
and unknown keys cannot enter the target domain.  With no pending or baseline
SELL intent, candidate order is byte-semantics-equivalent to frozen V2
`PRODUCTS` order.

This targets the scheduler's unchanged strict-`>` rank comparison: equal-ranked
candidates keep the first evaluated product.  No optimizer score, scenario,
quantity, receipt, capacity, route, market-order, actor, or terminal logic is
modified.

## Execution custody

The branch is based on exact head
`5e996707221b9340db982246f164e0c53a7a471e`, the last preserved stack that
completed the closure-bound, candidate-action-bound target-domain experiment.

The hosted workflow:

- verifies the exact frozen V2 scheduler Git blob;
- requires one old expression and one candidate replacement;
- requires `scheduler.py` to be the sole changed package member;
- rehashes complete control and candidate runtime closures before execution;
- generates distinct closure-checking entry wrappers;
- binds engine, loader, evaluator, opponents, seeds, limits, Python, platform,
  and exact Git head;
- captures candidate-only returned-action digests after both agents return and
  before interpretation;
- requires `719` returned actions under the literal `720`-step episode;
- runs eight exact seeds, two opponents (`Arlene`, frozen V1), and both seats:
  `32` paired cells / `64` complete official-horizon games;
- retains control, candidate, materialization, evaluator, execution-binding,
  comparison, and admission evidence for 30 days.

## Win-oriented admission

The inherited classifier must first return exact `UPSIDE_SCREEN`.  A second
independent gate re-derives every score delta and outcome transition from the
paired rows and admits only when all of the following hold:

- at least one candidate action changes;
- mean own cash is positive and median own cash is nonnegative;
- positive own-cash cells are at least negative cells;
- mean margin is positive;
- zero new losses;
- every opponent-by-seat stratum has nonnegative mean and median own cash,
  nonnegative cell balance, nonnegative mean margin, and zero new losses.

The gate rejects duplicate cells, detached score deltas, malformed types,
non-finite values, wrong experiment receipts, source drift, and replacement
cardinality drift.

## Local contracts before publication

- 5 target-map semantic contracts pass;
- 9 win-oriented admission contracts pass;
- all four new Python files compile;
- workflow YAML parses;
- exact frozen-source materialization and the inherited 28-contract harness run
  in the hosted exact-head job.

## Boundary

This is an additive experiment branch.  It does not mutate current `main`,
canonical integrated runtime, frozen V1/V2 packages, `TITAN-CONFIG.json`,
archives, pointers, provider state, Kaggle state, or submission state.

A green result is a V3 integration candidate, not leaderboard or submission
authority.  A failed gate rejects this source factor.
