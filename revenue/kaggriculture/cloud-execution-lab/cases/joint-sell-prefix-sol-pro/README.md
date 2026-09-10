# TITAN V3 joint-SELL executable-prefix closure

## Disposition

This is an additive source/evidence carrier. It does not edit the canonical
runtime, configuration, archive, package pointer, provider state, Kaggle state,
or a submission. It establishes a source-real returned-action witness and a
bounded repair for independent one-tree integration and paired-game testing.

Coordination claim:
`TITAN-V3-JOINT-SELL-EXECUTABLE-PREFIX-CLOSURE-20260910-01`.

## Exact source boundary

- claim/current base: `c51049d671b55d282e0fed5df37a0be7c513a838`
- `frozen_selected.py` Git blob:
  `fc7baf5c179818a55037f6a61d92984d81d1a21c`
- pinned official interpreter Git blob:
  `3c202c7ee921da239356789e266b694635103fc4`
- consumer: E05 multi-product joint SELL admission only
- unchanged lanes: ordinary per-product optimizer, own-value objective,
  `cash_reserve`, `receipt_profile`, market compaction, plan lifecycle, producer
  custody, and final action materialization

The official interpreter first normalizes a list-valued market queue and then
executes only:

```python
q[:max(1, maxMarketOrdersPerTurn)]
```

The current joint consumer violates that boundary twice:

1. `joint_resource_bound()` walks every authored current and future market row.
   An inert suffix `BUY_PRODUCT` returns `None`; inert suffix fixed spending or
   animal arrivals can fabricate underfunding or capacity failure.
2. The `orders_at` callback supplied to `joint_queue_ledger()` exposes the whole
   queue. `materialize_sales()` preserves those inert rows and the subsequent
   `len(market) > max_orders` check rejects the pair even though the interpreter
   never sees the suffix.

Both failures force the legacy single-product fallback after two individually
admitted product plans already exist.

## Bounded repair

`repair.py` authenticates both source blobs, verifies the interpreter's three
raw-prefix anchors and the joint consumer's call graph, then applies four exact
reversible replacements in two diff hunks:

- add `_joint_market_prefix()`, mirroring the interpreter's list conversion,
  minimum-one cap, and raw slicing;
- use it inside `joint_resource_bound()`;
- use it in the callback consumed by `joint_queue_ledger()`;
- pass the same minimum-one cap into the ledger.

No row is compacted, parsed, reordered, or deleted. The original action retains
every inactive suffix byte at its original index. Only admission reads the same
raw prefix the engine can execute.

Generate a deterministic receipt:

```bash
python revenue/kaggriculture/cloud-execution-lab/cases/joint-sell-prefix-sol-pro/repair.py \
  --repo . --format json
```

Generate the exact source patch:

```bash
python revenue/kaggriculture/cloud-execution-lab/cases/joint-sell-prefix-sol-pro/repair.py \
  --repo . --format patch
```

## Predecessor-killing contracts

The focused suite covers:

- exact current source and engine blob custody;
- four-replacement/two-hunk reversibility;
- list, non-list, nonpositive-cap, and malformed-cap behavior;
- current capped `BUY_PRODUCT`;
- future capped HIRE underfunding;
- capped animal capacity fabrication;
- active unsupported-row fail-closed behavior;
- full-queue versus active-prefix slot-ledger inversion;
- input and controller-state nonmutation;
- active-prefix identity when no suffix exists; and
- a full `FrozenSelected.transform()` returned-action witness.

The integration witness uses `maxMarketOrdersPerTurn=2` and this authored queue:

```text
0  SELL MILK 3
1  SELL WOOL 4
2  PASS                 # inert suffix
```

Two ordinary optimizer reports independently admit deferring one MILK and one
WOOL. The predecessor sees row 2, rejects the joint bound, and returns:

```text
SELL MILK 2
SELL WOOL 4
PASS
```

The candidate admits the exact executable pair and returns:

```text
SELL MILK 2
SELL WOOL 3
PASS
```

Thus the patch changes an active returned row, preserves the suffix byte-for-byte,
and leaves the no-suffix control identical. This proves reachability of the repair
boundary; it does not claim a game-score improvement.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
python -m unittest -v \
  revenue/kaggriculture/cloud-execution-lab/cases/joint-sell-prefix-sol-pro/test_repair.py
```

## Strength gate for the swarm

Integrate this closure only after exact-current one-tree rebasing. Then run one
predeclared paired official-interpreter panel using byte-identical control and
candidate packages, strongest available opponents, fresh familywise-reserved
seeds, and both candidate seats.

Retain exact pre-interpreter returned actions, full trace digests, terminal own
cash, rival cash, margin, W/T/L, first divergence, latency, and every
opponent-by-seat stratum. Promotion requires real joint-prefix activation, zero
new losses and lost wins, nonnegative mean margin in every opponent-by-seat
stratum, nonnegative own-cash tail, and no action-identical trace or score drift.

## Non-overlap

This lane is deliberately narrower than:

- PR #12005: `cash_reserve` executable-prefix spend closure;
- PR #12018: `receipt_profile` executable-prefix physical projection;
- PR #11965 and successors: own-value SELL objective;
- the existing E05 multi-product policy and any coordinate-ascent successor; and
- generic queue compaction or canonical release publication.
