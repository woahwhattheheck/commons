# TITAN V3 represented-horizon executable-prefix closure

## Disposition

This is an additive source/evidence carrier. It does not edit the canonical
runtime, configuration, archive, package pointer, provider state, Kaggle state,
or a submission. It establishes an exact-source returned-action witness for
independent one-tree composition and paired-game testing.

Coordination claim:
`TITAN-V3-REPRESENTED-HORIZON-EXECUTABLE-PREFIX-CLOSURE-20260910-01`.

## Exact source boundary

- claim/base commit: `c51049d671b55d282e0fed5df37a0be7c513a838`
- active `frozen_selected.py` Git blob:
  `fc7baf5c179818a55037f6a61d92984d81d1a21c`
- pinned official interpreter Git blob:
  `3c202c7ee921da239356789e266b694635103fc4`
- consumer: represented post-baseline shed-event detection only
- unchanged lanes: receipt/fill semantics, cash/funding, joint admission,
  ordinary optimizer objective, market materialization, pending carry, producer
  custody, canonical package publication, and submission state

The official interpreter accepts only list-valued market queues and executes
exactly the raw prefix:

```python
q[:max(1, maxMarketOrdersPerTurn)]
```

`represented_shed_event()` violates that boundary twice. It sends the full
current authored queue and every full future route queue into
`apply_represented_market()`. That projection applies SELL, BUY_PRODUCT,
BUY_ANIMAL, and HIRE rows even when they are beyond the executable cap.

A capped suffix can therefore fabricate or erase represented shed goods or
hands. A later route PICKUP followed by DROP/PLACE can appear executable or
impossible, falsely adding or removing `unit_event`. Because every product's
`item_end` includes that shared event, an inert market row can change active
returned SELL quantities.

## Bounded repair

`repair.py` authenticates both source blobs, verifies the interpreter's raw
prefix anchors and the represented-horizon call graph, then applies two exact
reversible replacements:

1. derive the official list/minimum-one/raw-slice prefix once inside
   `represented_shed_event()` and use it for the current represented market;
2. use the same exact prefix for every future represented market stage.

`apply_represented_market()` itself remains unchanged. No authored order is
parsed, reordered, compacted, edited, or deleted. The repair only prevents
engine-inert rows from entering the horizon projection.

Generate a deterministic receipt:

```bash
python revenue/kaggriculture/cloud-execution-lab/cases/represented-horizon-prefix-sol-pro/repair.py \
  --repo . --format json
```

Generate the exact source patch:

```bash
python revenue/kaggriculture/cloud-execution-lab/cases/represented-horizon-prefix-sol-pro/repair.py \
  --repo . --format patch
```

## Predecessor-killing witness

At step 100, `maxMarketOrdersPerTurn=1`, the authored current queue is:

```text
0  []
1  BUY_PRODUCT FERTILIZER 1    # engine-inert suffix
```

The fixed route performs `PICKUP FERTILIZER 1` at step 101 and `DROP` at step
102. Baseline horizon ends at 101.

The predecessor projects row 1, fabricates FERTILIZER, and returns
`unit_event=102`. A controlled ordinary optimizer therefore withholds one unit
of a real active MILK sale:

```text
AUTHORED / CANDIDATE             PREDECESSOR
SELL MILK 2                      SELL MILK 1
BUY_PRODUCT FERTILIZER 1         BUY_PRODUCT FERTILIZER 1
```

The candidate ignores only the capped suffix, returns `unit_event=None`, leaves
the active `SELL MILK 2` unchanged, and preserves the suffix byte-for-byte.
With no suffix, predecessor and candidate returned actions, diagnostics, plans,
and pending state are identical.

The focused suite also covers the future callsite, capped SELL erasure,
active-prefix identity, non-list queue semantics, nonpositive minimum-one caps,
malformed-cap fail-closed parity, exact source custody, reversibility,
nonmutation, and deterministic receipts.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
python -m unittest -v \
  revenue/kaggriculture/cloud-execution-lab/cases/represented-horizon-prefix-sol-pro/test_repair.py
```

## Strength gate for the swarm

Compose the two replacements only on a fresh exact one-tree head. Run a
predeclared both-seat official-interpreter panel against the strongest available
opponents using fresh familywise-reserved seeds. Retain exact returned actions,
`unit_event`, product horizons, first divergence, full trace digests, terminal
own/rival cash, margin, W/T/L, and every opponent-by-seat stratum.

Promotion requires real capped-suffix activation, zero new losses and lost wins,
nonnegative mean margin in every opponent-by-seat stratum, a nonnegative own-cash
tail, and zero action-identical trace or score drift.

## Non-overlap

This lane is deliberately narrower than:

- PR #12043: joint SELL resource/slot admission prefix closure;
- PR #12005: executable-prefix `cash_reserve` closure;
- PR #12018 and purchase-fill successors: `receipt_profile` projection;
- final returned-action/pending carry work;
- own-value or coordinate-ascent objective work; and
- generic queue compaction or canonical release publication.
