# H01 — bounded-horizon residual reference

Operation: `TITAN-V3-HORIZON-RESIDUAL-PORT-20260910-01`

## Why this lane exists

The submitted V1 and V2 closures differ only in `scheduler.py`. A completed frozen-V2
2×2 factorial isolated two adjacent seller-policy changes across 128 complete official
games: four opponents, four seeds, and both candidate seats for each of four arms. The
run was GitHub Actions `34409194076` on PR #11825.

The arm that forces residual, unscheduled stock into the finite-horizon **reference**
was selected by every economic screen and improved mean grouped candidate-own terminal
cash by **+227.25** versus control. The neighboring V1-style `0.95` continuation-value
scalar reduced that metric by **−605.9375** and is deliberately not included here.

This is predecessor evidence, not a claim that the rebased current V3 tree already has
+227.25 uplift. Current-tree admission requires a closure-distinct matched official
panel.

## Exact intervention

Before H01, each seller path constructs a reference schedule from:

1. the current inherited SELL quantity;
2. retained pending future intent; and
3. unchanged future route SELL rows inside the seller's existing bounded horizon.

It also computes `rem`, the target stock not represented by those rows. H01 changes only
the final reference construction:

```python
if rem > 0:
    reference.append((existing_horizon_end, rem))
reference = coalesce(reference)
```

The direct seller uses its existing `end`. `FrozenSelected` uses its existing per-product
`item_end`. An existing row at that date is coalesced; every prior date and quantity is
retained. H01 does not extend the horizon, change the optimizer, alter continuation
value, move a queue slot, emit a SELL, or guarantee that residual stock is actually sold.
It changes the baseline against which candidate sale schedules must strictly improve.

## Fail-closed and default-off behavior

The package key `horizon_residual` ships `false`. With the key off, the inherited seller
method returns the predecessor coalescing expression exactly and does not import the H01
module or add a diagnostic. With the key on, the helper validates integer dates and
nonnegative quantities, preserves its input, and checks quantity conservation. Any
active validation error is recorded as `HORIZON_RESIDUAL_ERROR_<Type>` and the caller
returns the predecessor reference.

Contracts cover off identity, residual-only append, same-date coalescing, zero-residual
identity, active fail-closed behavior, key transport, both seller paths, exact source
anchor cardinality, and explicit exclusion of the losing `.95` scalar.

## Scope exclusions

H01 does not own target traversal, all-shed priority, multi-lot selection, HIRE reserve,
future-rival scenarios, order indices, sheep policy, canonical archive/pointer, provider
state, Kaggle state, or submission. Those surfaces remain unchanged.
