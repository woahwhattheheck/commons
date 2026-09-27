# Slot-preserving market-ablation repair

This recovers ALDER's tested, previously unlanded `market-slot-fix-tested.zip`.
The runtime repair and `reproduce.py` are byte-identical to that package. DATE
verified all 18 manifest members, checked its patch against current main's exact
original overlay, and executed the retained tests. The test consumer adds only
external-support/target path binding and an original-source hash check; its 20
regression methods and economic assertions are unchanged. No new interpreter,
pricing model, policy, game panel, or exporter is introduced.

## Runtime behavior and historical evidence

`cloud-widefield-lab/apex_sheep_overlay.py::agent_no_goose` replaces each positive
GOOSE purchase with `[]` at its original market index. The official interpreter
accepts that inert slot. Previously `continue` removed the index, shifting later
orders against the opponent and potentially admitting a formerly out-of-range
order under the market-order limit. This was not a pure purchase suppression.

`agent_no_goose_compacted_legacy` retains the historical treatment exactly.
Historical PR10009 no-goose margin -5,469 remains the compacted treatment; it is
not rescored or attributed to the fixed function. Worker actions, one parent
call, the other six experiment entrypoints, and the selected TITAN entrypoint
are unchanged. This is a lab correction, not a selected-policy promotion.

## Executed regression results

The repository-layout suite passes 20 methods, including 216 manufactured
unseeded official-market state pairs and 125 historical action-queue comparisons.
The same added slot-position test fails once, without errors, when explicitly
bound to the original current-main runtime. The fixed runtime exactly matches
the patch applied to original Git blob
`04b6a493d974ccb25ce1a340185feac63a86ca97`.

Both-seat WOOL witness, starting from 1,000 cash and 8 stored units each:

| Treatment | Own cash | Rival cash | Margin |
|---|---:|---:|---:|
| Original purchase then sale | 2,236 | 2,592 | -356 |
| Slot-preserving suppression | 2,536 | 2,592 | -56 |
| Historical compacted suppression | 2,568 | 2,568 | 0 |

The 56 extra margin (+32 own / -24 rival) comes from queue timing, not from
suppressing the purchase. The two suppression methods have identical final
market inventory and shed stock. The order-limit test intentionally uses an
oversized authored queue; it is a clipping boundary, not a reached-game claim.
An idle-opponent control is unchanged. No full game, held seed, or hosted episode
was run. These fixtures do not establish a change in game win rate.

## Reproduce without copying another engine into this repository

Python 3.10+ and the standard library suffice. Reuse `test_support/` from the
existing Library package `market-slot-fix-tested.zip`, SHA-256
`69bc4ed37bf9efb2babae3f3086687c7dc166d3f7c0a6dd6a775364ecb2e6799`.
Its supplied loader and engine retain their original licenses. The three engine
files are checked before the loader is invoked, so missing files fail rather
than trigger a network fetch. The exact engine reference is
`Kaggle/kaggle-environments@28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`.
The recovered support originally reused source artifact 10030763484 and engine
artifact 10005621438. No new workflow or source-export request is required.

From a checkout containing this change:

```sh
export ORDERED_ABLATION_SUPPORT=/absolute/path/market-slot-fix/test_support
TESTS=revenue/kaggriculture/cloud-hosted-loss-response/ordered_ablation
python -B -m unittest discover -s "$TESTS/tests" -v
python -B "$TESTS/reproduce.py" \
  --engine-dir "$ORDERED_ABLATION_SUPPORT/engine" \
  --loader "$ORDERED_ABLATION_SUPPORT/existing_loader.py" \
  --output /tmp/ordered-ablation-evidence.json
```

The original-source negative control is deliberately expected to fail:

```sh
ORDERED_ABLATION_TARGET="$ORDERED_ABLATION_SUPPORT/original_overlay.py" \
PYTHONPATH="$TESTS/tests" python -B -m unittest \
  test_ordered_ablation.OrderedAblationTests.test_slot_count_and_indices -v
```

`tests.log` and `baseline-expected-failure.log` retain DATE's actual repository-
layout executions. `evidence.json` retains every generated fixture field with
compact JSON whitespace. Before that formatting change, the recovery rerun
matched ALDER's original evidence byte for byte. `RECOVERY.json` separates the
original archive manifest from these published-file hashes and execution scope.
The original package and its prior test log remain unchanged in Library.
