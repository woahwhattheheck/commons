# ASTRA-DEADCAP — terminal acquisition cash-path oracle

Status: **donor defect proven; one authenticated current-native cell is negative; global current-native engagement remains unmeasured; evidence-only.**

This package lives inside the one canonical TITAN V4 research tree. It does not add a controller, feature key, runtime hook, default, archive, or Kaggle change.

## The invariant

The official engine awards terminal reward as player cash. A purchase is therefore strictly dominated by keeping its spend when the purchased asset has no causally reachable path to later cash.

DEADCAP is deliberately conservative. The first certified subfamily is seeds only: a seed purchase is called dead only when even a generous authored-route over-approximation cannot find a later `PLANT <crop>` followed, after the crop's official first-yield age, by any later `SELL <crop>`. HARVEST/DROP feasibility is not required by the oracle, so uncertainty biases toward **REFUSE**, not toward deleting a purchase.

HIRE is explicitly out of scope. Product/animal/land rows are counted for the broad census but are not certified dead by this first package.

## Exact source custody

- donor `r01_tapes.py`: 32,955 bytes, Git blob `a43289b9cc5e34a2481fddf652762a7d92f427ef`, SHA256 `4a60e775e52905048257aff4871a11c5ba49de6ba464177ed6ae4d9bd3120e18`
- official engine: Git blob `3c202c7ee921da239356789e266b694635103fc4`
- authenticated foundation artifact: `10175943272`, archive SHA256 `b567942e4fb4e0571ebf9f8eaaf143d4a9156df3289f09a98db37823ef4d68d9`
- current production pins used by the one-cell probe: `main.py` `4a8cf7bcda1f0fea231a144692cb84a779a9e73e`, `titan_runtime.py` `6d9720f4aa1e6b46e92ee5183897074d8e9ea5a0`, config `3a3bef83899d3010fad623b628d9e95d9978111b`

The post-merge correction adds `current_native_truth.py`, which calls `authenticate_current()` **before** the inherited current-native import/replay. Drift now blocks the authoritative current-native probe before gameplay execution; `test_current_native_truth.py` includes a deliberate source-tamper predecessor.

## Donor census

Across the exact 13 × 719 donor tapes:

- `BUY_SEED`: 2,330
- `BUY_PRODUCT`: 724
- `BUY_ANIMAL`: 159
- `BUY_LAND`: 26
- BUY rows at step >= 480: 929

The seed cash-path oracle returns exactly one candidate:

`TAPE 12 / STEP 284 / ROW 0 / BUY_SEED MELON 1`

There is **no later `PLANT MELON` at all** in tape 12, so the purchased seed cannot enter a crop/cash path.

## Exact-engine donor witness

Tape 12 vs tape 0, seed 0, seat 0:

- cash before step-284 market: `$11,021`
- the MELON seed buy executes: cash becomes `$10,941`
- MELON seeds: `0 -> 1`
- terminal MELON seeds: `1`
- baseline terminal reward: `$52,429`
- replacing only that row with `[]`: `$52,509`
- own delta: **+$80**
- rival delta: **$0**

A broader fixed-route donor differential ran 104 cells: all 13 donor opponents × seeds 0..3 × both seats. Every cell is exactly `+$80` own and `$0` rival.

## Current-native truth scope

The inherited current-native replay observes exactly **one** production cell: seat 0, seed 0, rival tape 0, through step 284. On the pinned production bytes that cell returns `SELL WHEAT 9`, not the exact donor witness `BUY_SEED MELON 1`; MELON seed stock remains zero.

That is useful negative evidence, but it is **not a global COLD census**. It neither searches both seats / multiple seeds / multiple opponents nor detects arbitrary current-native dead-seed purchases at other callbacks. Therefore the authoritative disposition is:

**ONE_CELL_DONOR_WITNESS_ABSENT / GENERAL CURRENT-NATIVE DEAD-SEED ENGAGEMENT UNMEASURED.**

No runtime guard is authorized from this package. If a later owner wants a global COLD statement, the next gate is an authenticated current-native census that applies the generic dead-seed cash-path theorem to returned actions across a declared panel rather than checking exact equality with one historical row.

## Reproduce

From this directory:

```sh
python -B -m unittest -v test_deadcap_oracle.py
python -O -B -m unittest -v test_deadcap_oracle.py
python -B -m unittest -v test_current_native_truth.py
python -O -B -m unittest -v test_current_native_truth.py
```

For the full 104-cell donor matrix, call `deadcap_oracle.result_bundle(..., full_matrix=True)` against the pinned donor tape and official engine.

Scope limit: this proves one historical seed dead-capex defect, its exact fixed-route economics, and one authenticated negative current-native cell. It does **not** prove global current-native COLD and does not authorize removing buys without a current returned-action cash-path certificate.
