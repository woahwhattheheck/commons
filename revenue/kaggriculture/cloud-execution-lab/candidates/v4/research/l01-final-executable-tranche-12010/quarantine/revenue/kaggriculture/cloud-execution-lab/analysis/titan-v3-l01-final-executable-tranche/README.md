# TITAN V3 L01 final-executable tranche repair

Operation: `TITAN-V3-L01-FINAL-EXECUTABLE-TRANCHE-20260910-01`

## Finding

The authenticated one-tree handoff `F0C0JPCAAQP` (`v3_candidates_657b3d9c.tar.gz`, SHA-256 `f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728`) contains an off-by-one lifecycle gate in `overlay/l01_mechanics.py`:

```python
FINAL_EXECUTABLE_STEP = 718
...
if day < TRANCHE_DAY_FROM or step >= FINAL_EXECUTABLE_STEP:
    return action
```

That predicate treats observation step 718 as terminal. In a 720-state Kaggriculture episode, state 0 is the initial observation and the remaining 719 states are produced by 719 agent actions. The last agent input is therefore `episodeSteps - 2`, or step 718 under the default configuration. State 719 is the produced terminal state.

The source-bound replay receipt in `REPLAY-107213024-BOUNDARY.json` proves the distinction on public episode `107213024`:

- input state/index and observation step: `718`;
- produced state/index and observation step: `719`;
- status: `ACTIVE -> DONE`;
- Otter Vibe cash: `117176 -> 122100` (`+4924`);
- the action stored in state 719 dropped and sold exactly `CARROT 60`, `WHEAT 31`, `WOOL 4`, `EGG 1`, and `FERTILIZER 2` from the actor inventories visible at input step 718.

This matters specifically to L01 because its tranche runs after `_finish_production` and reads `selected_post_units`: final-turn `DROP` inventory is available to the seller at this seam. Returning identity at step 718 suppresses the existing L01 mechanism on the only action that can realize that inventory.

## Repair

`one-tree-l01-final-executable.patch` makes one bounded mechanism repair:

1. derive the final executable input as `episodeSteps - 2`;
2. allow the unchanged L01 tranche on that input;
3. quarantine only later/post-action indices;
4. pass `episodeSteps` from `TitanAgent._v3_post_final`;
5. fail closed on explicit malformed or impossible episode lengths.

It does **not** change product selection, WHEAT/CARROT tranche sizes, queue packing, the ten-order cap, route tapes, feature defaults, or any other V3 lane. It is not a new T01 terminal-liquidation policy.

## Evidence

Run:

```bash
python -m unittest -v test_carrier.py
```

Result: `22/22 PASS`.

The contracts prove:

- the exact handoff predecessor returns identity at step 718;
- the repaired source activates at step 718 and returns identity at step 719;
- a configurable 12-state episode activates at step 10 and not step 11;
- malformed episode lengths fail closed;
- all sampled pre-boundary outputs and activation counts match the predecessor;
- policy constants and all non-lifecycle functions are byte-identical;
- feature-off, early-day, no-inventory, input-nonmutation, existing-order, and ten-row cap behavior are preserved;
- the patch owns exactly five one-tree source/documentation paths;
- the replay boundary receipt is pinned to gzip SHA-256 `1494f55bad971d957a29f398a35a9ef51ad5c431288b989a3f0b1fb032d3e8c6` and reconstructs the exact same-turn DROP/SELL ledger.

The patch also applies cleanly to the authenticated handoff and produces all five `PIN.json` postimage hashes exactly.

## Consumption boundary

This is an additive exact-source repair/evidence carrier. The one-tree owner should:

```bash
git apply --check one-tree-l01-final-executable.patch
git apply one-tree-l01-final-executable.patch
python -m unittest -v revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/checks/test_v3_l01.py
python revenue/kaggriculture/cloud-execution-lab/candidates/v3/build_v3.py --check
```

Then regenerate the integrated archive and its file/hash receipts from the repaired source. Do not hand-edit the generated `FILES.json` or release pointer.

## Claim boundary

This carrier claims source custody, replay lifecycle evidence, patch applicability, and focused contracts only. It makes no gameplay-strength, hosted-panel, promotion, archive, release, provider, Kaggle, or submission claim.
