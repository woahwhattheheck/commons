# Titan V2 executable-slot capacity ablation

Operation: `titan-v2-market-hole-capacity-20260909-sol-parapet-01`

## Why this exists

Frozen V2 improved several scheduler assumptions, but it also made capacity and
state decisions from raw Python list length instead of the official executable
market prefix.

The frozen admission check does this when a planned sale needs a slot:

```python
if len(orders) >= maxMarketOrdersPerTurn:
    offered = sum(same_item_sales_over_the_whole_list)
    if q > offered:
        return False
```

The output path likewise appends only when `len(market) < limit`, allocates
planned stock to matching `SELL` rows anywhere in the list, and computes
`pending` from every row. The official interpreter instead inspects only
`market[:maxMarketOrdersPerTurn]` and skips a falsy row as a no-op.

That creates two opposite errors:

1. **False full:** ten rows containing `[]` are called full even though replacing
   that active-prefix no-op would execute a new sale without moving a live row.
2. **False offered:** a same-item sale after the execution limit is counted as
   current supply and current execution even though the engine cannot reach it.

Either error can suppress current cash or erase a future plan. This lane changes
only that shared executable-prefix invariant.

## One-factor candidate

`materialize.py` copies frozen V2 into a byte-exact control closure and a
scheduler-only candidate closure. It makes three mutually required edits:

- capacity admission counts existing same-item quantity only in the executable
  prefix and recognizes a falsy row in that prefix as available capacity;
- seller allocation consumes stock only for prefix rows and fills the first
  prefix hole in place before appending;
- pending inventory is derived only from prefix sales.

The candidate never compacts the queue, never reorders a live inherited row,
never uses an inactive suffix hole, and never touches frozen or canonical source.
All other named V2 changes remain exact: all-shed targets, full continuation
value, future-rival scenarios, and forced-feasibility ranking.

## Execution custody

Both generated arms receive `sol_parapet_entry.py`. The generated wrapper embeds
SHA-256 for every underlying file and verifies the whole closure before importing
`candidate.py`. Control and candidate wrappers therefore have distinct
entrypoint hashes, and `compare.py` rejects a report unless each arm names the
entrypoint hash recorded by `MATERIALIZATION.json`.

This closes the common ambiguity where an unchanged thin `candidate.py` hash
could describe two different scheduler closures.

## Deterministic witness

`slot_capacity.py` constructs a ten-row queue with one active-prefix `[]`:

- frozen V2 rejects `SELL CARROT 4` solely because raw length is ten;
- the candidate replaces the hole at the same index;
- every inherited live row remains byte-identical at the same index;
- a truly full prefix rejects;
- a hole or same-item sale only after the limit does not count.

The witness is a source-semantics discriminator, not a strength claim.

## Causal screen

The workflow runs byte-distinct closure-verified control and candidate arms over:

- opponents: frozen Arlene and frozen V1;
- seeds: `539131249,1834999074,2609097301,2611092207`;
- both seats;
- pinned official interpreter and process-isolated loader.

`compare.py` fails closed on source, wrapper, engine, loader, evaluator, opponent,
seed, seat, completion, trace, daily-bank, or grid drift. `UPSIDE_SCREEN` requires:

- at least one changed complete trace;
- positive mean own-cash delta;
- nonnegative median own-cash delta;
- at least as many positive as negative cells;
- nonnegative mean own-cash delta in every opponent × seat stratum.

Anything else is `NO_ACTION_SIGNAL`, `ACTION_NO_SCORE_SIGNAL`, `MIXED`,
`REGRESSION`, or `INVALID` and exits nonzero.

## Boundary

Even an `UPSIDE_SCREEN` does not promote V2 or V3. It only nominates this one
factor for a larger current V1/V2/V3 matched panel. No canonical runtime,
configuration, release archive, pointer, provider, hosted submission, or
leaderboard state changes in this lane.
