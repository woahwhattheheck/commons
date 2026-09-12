# ASTRA-DEADCAP — terminal acquisition cash-path oracle

Status: **donor defect proven; current-native engagement COLD; evidence-only.**

This package lives inside the one canonical TITAN V4 research tree. It does not add a controller, feature key, runtime hook, default, archive, or Kaggle change.

## The invariant

The official engine awards terminal reward as player cash. A purchase is therefore strictly dominated by keeping its spend when the purchased asset has no causally reachable path to later cash.

DEADCAP is deliberately conservative. The first certified subfamily is seeds only: a seed purchase is called dead only when even a generous authored-route over-approximation cannot find a later `PLANT <crop>` followed, after the crop's official first-yield age, by any later `SELL <crop>`. HARVEST/DROP feasibility is not required by the oracle, so uncertainty biases toward **REFUSE**, not toward deleting a purchase.

HIRE is explicitly out of scope. Product/animal/land rows are counted for the broad census but are not certified dead by this first package.

## Exact source custody

- donor `r01_tapes.py`: 32,955 bytes, Git blob `a43289b9cc5e34a2481fddf652762a7d92f427ef`, SHA256 `4a60e775e52905048257aff4871a11c5ba49de6ba464177ed6ae4d9bd3120e18`
- official engine: Git blob `3c202c7ee921da239356789e266b694635103fc4`
- authenticated foundation artifact: `10175943272`, archive SHA256 `b567942e4fb4e0571ebf9f8eaaf143d4a9156df3289f09a98db37823ef4d68d9`
- current production pins during the audit: `main.py` `4a8cf7bc...`, `titan_runtime.py` `6d9720f4...`, config `3a3bef83...`

The foundation runtime preimage is `b952c9c2...`. Current `titan_runtime.py` differs by commit `682ad628...`, whose reviewed repair only rebinds cache hits into `sys.modules`; that commit explicitly leaves gameplay selection/defaults unchanged.

## Census

Across the exact 13 × 719 donor tapes:

- `BUY_SEED`: 2,330
- `BUY_PRODUCT`: 724
- `BUY_ANIMAL`: 159
- `BUY_LAND`: 26
- BUY rows at step >= 480: 929

The seed cash-path oracle returns exactly one candidate:

`TAPE 12 / STEP 284 / ROW 0 / BUY_SEED MELON 1`

There is **no later `PLANT MELON` at all** in tape 12, so the purchased seed cannot enter a crop/cash path.

## Exact-engine witness

Tape 12 vs tape 0, seed 0, seat 0:

- cash before step-284 market: `$11,021`
- the MELON seed buy executes: cash becomes `$10,941`
- MELON seeds: `0 -> 1`
- terminal MELON seeds: `1`
- baseline terminal reward: `$52,429`
- replacing only that row with `[]`: `$52,509`
- own delta: **+$80**
- rival delta: **$0**

A broader fixed-route differential ran 104 cells: all 13 donor opponents × seeds 0..3 × both seats. Every cell is exactly `+$80` own and `$0` rival.

## Current-native disposition

The production agent on authenticated artifact `10175943272`, replayed to the same boundary against tape 0 seed 0, does **not** emit the donor row. At step 284 its returned market is `SELL WHEAT 9`; MELON seed stock remains zero. The current runtime's only post-foundation byte change is the loader-cache namespace repair above, not gameplay.

Therefore: **COLD / NO RUNTIME GUARD.** Landing a DELETE/PASS transform would duplicate behavior current native already achieves and would add unnecessary policy surface. This package instead keeps the historical defect and exact cash-path regression executable so a future route/controller change cannot silently reintroduce it.

## Reproduce

From this directory:

```sh
python -B -m unittest -v test_deadcap_oracle.py
python -O -B -m unittest -v test_deadcap_oracle.py
```

For the full 104-cell matrix, call `deadcap_oracle.result_bundle(..., full_matrix=True)` against the pinned donor tape and official engine.

Scope limit: this proves one seed dead-capex witness and the current COLD engagement state. It is not a general proof that all late purchases are dead and it does not authorize removing buys without the cash-path certificate.
