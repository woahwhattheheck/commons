# TITAN V2 delayed-rival stress-scenario ablation

Operation: `titan-v2-delayed-rival-ablation-20260909-sol-caliber-01`

## Exact hypothesis

Frozen V1 and V2 have byte-identical 66-byte entrypoints and identical retained
closure files except `scheduler.py`. V2 added two hypothetical placements for
the currently observed rival supply:

- the next turn, `observed_next_turn`; and
- immediately before the final delayed batch, `observed_before_delayed_batch`.

Every candidate sale plan must improve against both new placements as well as
the three original scenarios. This may over-constrain execution by treating one
public rival-supply estimate as if that same quantity could materialize at
multiple mutually exclusive times.

This experiment removes only those two V2-only scenario append blocks from a
temporary copy of exact frozen V2. It deliberately preserves V2's:

- tuple-capable rival schedule scorer;
- 100% continuation value;
- forced-feasibility admission and Boolean-first priority;
- all-shed target domain;
- receipt/capacity feasibility;
- inherited future-sale reconstruction; and
- per-index market-order rewrite.

## Predecessor-discriminating source witness

The focused contract imports and executes the real frozen and materialized
schedulers. At a real CARROT market state:

- inventory: `10055`;
- PET_CAFE absorption active;
- current step: `542`;
- horizon dates: `542, 546, 550`;
- quantity: `20`;
- reference plan: sell `18` now and `2` at step `550`;
- observed rival quantity: `3`.

Exact frozen V2 preserves the reference because a V2-only delayed-rival
placement vetoes every alternative. The one-factor ablation selects `13` now
and carries `7`; against the three historical scenarios its relative-value
gains are exactly `+4, +1, +1`. This is executable policy divergence, not a
standalone replica of the optimizer and not a game-strength claim.

## Hosted screen

The path-scoped workflow materializes one closure-distinct candidate and runs
identical official-interpreter cells for frozen V2 control and the ablation:

- opponents: frozen V1 and public Arlene;
- seeds: four fixed development seeds;
- seats: both;
- total: 32 games / 16 paired control-candidate cells.

The inherited strict comparator binds engine, loader, evaluator, opponent bank,
seed grid, limits, Python, entrypoint bytes, closure identities, complete cells,
trace digests, and daily bank checkpoints. It ranks own terminal cash before
margin and requires non-negative average own-cash performance in both opponent
strata. `NO_ACTION_SIGNAL`, action-only deltas, mixed results, regression,
partial/error cells, or provenance drift fail closed while retaining artifacts.

## Scope

This is additive causal evidence only. It does not modify frozen V1/V2,
canonical TITAN, runtime configuration, selected archives, pointers, defaults,
provider state, or Kaggle state. It does not overlap the target-domain,
continuation-value, or forced-feasibility ablations already owned by other
swarm lanes.
