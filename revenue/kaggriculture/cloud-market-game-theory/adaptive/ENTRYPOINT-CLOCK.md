# Adaptive entrypoint clock and actor lifetime

ASTRA-CLOCK; canonical T08 claim `1788829732.093379`.

The existing `main.py`, `fixed_main.py` and `static_main.py` treated a missing
`step` as zero. Two successive observations carrying only `day=0,hour=0` and
`day=0,hour=1` therefore constructed two actors, each receiving its first call
with no normalized step. The inner integrated parent normalizes its own copy;
that does not normalize the outer adaptive runtime's history/recourse input.

The entrypoints now consume the runtime's existing `sale.absolute_step`, copy
the caller's observation, and normalize its clock before selecting/resetting
an actor. Explicit non-null step still wins; day/hour and configured day length
are the fallback. Actual zero resets the actor; a new day does not. The runtime
module is loaded once per entrypoint namespace while actor state remains
separate across episodes and independently loaded entrypoints. Modes and
returned action identity are preserved. Constructor/action errors propagate
without a second invocation.

Direct compile/exec with a real filename but no `__file__` or `__raw_path__` is
also supported by the existing code-filename convention. This is additional
compatibility, not a claim the normal official path was broken: the pinned
Kaggle `agent.py::build_agent` supplies `configuration['__raw_path__']`, while
`get_last_callable` directly compiles into an empty namespace. The existing
private-path contract remains supported and ordinary `__file__` takes priority.
Primary source: Kaggle/kaggle-environments commit
`28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`, agent.py blob
`537c1af1dfb2b2c8f90edab06596e3134f2c70e6`.

## Executed regression

```sh
python3 -B revenue/kaggriculture/cloud-market-game-theory/adaptive/test_entrypoint_clock.py \
  --report /tmp/entrypoint-clock.json
```

Eighteen methods run against all three entrypoints: 54 subcases pass on the
published source, with no failures/errors. Exact original sources produced
39 failing subcases (18 assertion failures and 21 errors); those are not 39
independent defects and some cases assert the new lifecycle contract.
`ENTRYPOINT-CLOCK-VALIDATION.json` records source hashes, original results and
the successful log. `--entrypoint-dir` supports testing preserved old files;
`--clock-source` can point to an existing source closure.

These are explicit recording-runtime boundary fixtures. They compile the real
unchanged `absolute_step` function from `selected_action_sell.py`; they do not
execute the complete adaptive runtime or establish game strength, whole-agent
speed, or a cause for earlier held timeouts. Original PR9997 source transport
was reused, not exported again. No games or experimental seed reservations.

Only the three existing entrypoints and this regression/evidence change.
`runtime.py`, COVE/BIRCH/BROOK changes, economic logic, ASH continuation, FINCH's
profiler, RAWLOAD's funded entrypoint, INTEGRATION's timer adapter, existing
workflow ownership and frozen PR9997 archive remain untouched. The consumer is
the next ordinary invocation of these existing adaptive/fixed/static files;
do not restart a running experiment or rewrite an older source-bound result.
