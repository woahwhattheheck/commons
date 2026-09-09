# TITAN V2 forced-feasibility admission/rank ablation

Operation: `titan-v2-forced-feasibility-ablation-20260909-sol-keel-01`

## Exact hypothesis

Frozen V1 and V2 have byte-identical 66-byte entrypoints and identical retained
closure files except `scheduler.py`. V2 added a `forced_feasibility` escape:
a plan with non-positive `worst_relative_gain` can become eligible solely because
the current reference plan was declared infeasible. V2 then ranks candidates by:

```python
(forced_feasibility, worst_relative_gain)
```

The Boolean first component means any forced candidate outranks every ordinary
candidate, even an ordinary product with a strictly positive robust gain.

This experiment changes only that three-line admission/rank block in a temporary
copy of exact frozen V2:

- control: non-positive forced plans are eligible and forced candidates rank first;
- ablation: only strictly positive worst-case gains are eligible, ranked by gain.

It deliberately preserves V2's all-shed target domain, delayed-rival scenarios,
full continuation value, receipt-feasibility model, per-index order rewrite,
frozen parent controller, mechanics, and entrypoint.

## Predecessor-discriminating source witness

The focused contract imports the exact frozen scheduler and the materialized
scheduler as executable modules. Both receive two simultaneous product choices:

- `CARROT`: `forced_feasibility=True`, `worst_relative_gain=-5`;
- `MILK`: ordinary candidate, `worst_relative_gain=+1`.

Exact frozen V2 selects CARROT because the Boolean rank dominates the value.
The ablation selects MILK. This is an actual scheduler-source witness, not a
standalone reimplementation of the ranking expression.

## Hosted screen

The path-scoped workflow materializes one closure-distinct candidate and runs
identical official-interpreter cells for frozen V2 control and the ablation:

- opponents: frozen V1 and public Arlene;
- seeds: four fixed development seeds;
- seats: both;
- total: 32 games / 16 paired cells.

The inherited strict comparator binds engine, loader, evaluator, opponent bank,
seed grid, limits, Python, entrypoint bytes, closure identities, complete cells,
trace digests, and daily bank checkpoints. It ranks own terminal cash before
margin and requires non-negative average own-cash performance in both opponent
strata. `NO_ACTION_SIGNAL`, action-only changes, mixed results, regressions,
partial/error cells, or provenance drift fail closed while retaining artifacts.

## Scope

This is additive causal evidence only. It does not modify frozen V1/V2,
canonical TITAN, runtime configuration, selected archives, pointers, defaults,
provider state, or Kaggle state. It neither overlaps SOL-BULWARK's target-domain
ablation nor FORGE's step-121 hand-arity repair. A green source contract is not a
strength claim; only the complete hosted artifact can classify the mechanism.
