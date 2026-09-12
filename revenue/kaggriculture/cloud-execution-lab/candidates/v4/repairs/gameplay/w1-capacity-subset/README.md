# W1: recover the harvest subset that actually fits

This is a tested semantic repair of the existing W1 helper, housed in the single `main/candidates/v4` workspace. It is not another agent, feature key, integration branch, or production activation. The exact donor helper and its original regression remain untouched under `donor/overlay`.

## Mechanism

The donor admits all eligible WATER-to-HARVEST substitutions or none. Eligible yields `[6, 4]` with only four free storage units therefore recover nothing. This postimage selects the four-unit harvest. For `[6, 5, 5]` with ten free units it selects both five-unit harvests rather than using a largest-first heuristic.

The selector maximizes **whole harvested units**, not cash or expected game margin. Equal totals choose the lexicographically earliest actor-index tuple. It retains at most 101 capacity states; it does not enumerate the powerset at runtime or allocate in proportion to a huge yield value.

All existing W1 eligibility predicates remain unchanged: the actual step-695 pre-EOD callback, strict configuration, dead WATER, crop maturity/future-yield constraints, actor geometry, complete private inventory, and strict market validation. Existing carried cargo and every authored HARVEST/COLLECT_FERTILIZER are reserved first. Unselected actors retain their original WATER commands. There is no credit for future sales or consumption. All-fit behavior bypasses the selector. Every partial set must pass the **unchanged original `_capacity_safe`** before any action substitution is returned; no-fit paths return the exact parent object.

## Exact-source evidence

`MANIFEST.json` binds the original helper/test, repaired helper, regression, and execution counts. Both original files were reconstructed through EOF and matched their Git blob identities before testing. All 15 original helper functions remain source-identical; only the entrypoint's capacity callsite changes, with two new internal functions. Source/test blobs returned by GitHub equal the executed local byte identities.

Original donor tests: **27/27 PASS**. Five new targeted test methods fail on the donor (six failing subcases, including both seats). Final repaired suite: **52/52 PASS normal and 52/52 PASS with `python -O`**, including 17,745 brute-force subset-oracle comparisons and 832 returned-action/capacity/nonmutation cases. `py_compile` passes. Tests also prove that a rejected final capacity certificate blocks the transform and that all-fit behavior does not invoke the new selector.

These are cloud-session CPython 3.13.5 source tests, not hosted CI, materialized-package, official-engine whole-game, or economic-promotion results. No new games were run.

## Reproduce from repository root

```sh
V4=revenue/kaggriculture/cloud-execution-lab/candidates/v4
REPAIR="$V4/repairs/gameplay/w1-capacity-subset"
PYTHONPATH="$REPAIR" python -m unittest discover -s "$V4/donor/overlay/checks" -p test_v4_dead_water_harvest.py
PYTHONPATH="$REPAIR" python -m unittest discover -s "$REPAIR" -p test_v4_w1_capacity_subset.py
PYTHONPATH="$REPAIR" python -O -m unittest discover -s "$V4/donor/overlay/checks" -p test_v4_dead_water_harvest.py
PYTHONPATH="$REPAIR" python -O -m unittest discover -s "$REPAIR" -p test_v4_w1_capacity_subset.py
```

## Single-V4 consumption

The donor preimage is `7bef7daef02c859e572cc0972821ce3aa4017714`; repaired postimage is `f56a453234edaf3e214d61247f761a7cd2e92bb9`. The V4 composer should consume this semantic delta exactly once, preserving any later independent W1 repairs rather than copying an old tree over them. Re-run current composition/package checks and keep existing feature defaults unchanged. Do not execute the legacy r04 materializer against the incompatible current production runtime. No archive, runtime, workflow, evaluator, opponent, or Kaggle state changes accompany this repair.
