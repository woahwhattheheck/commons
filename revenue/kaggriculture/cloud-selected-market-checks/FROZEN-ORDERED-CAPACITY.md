# Frozen SELL: ordered future-worker capacity

The existing `FrozenSelected` now overrides only `receipt_profile`. It retains the original scheduler's projection, orders, one-unit capacity margin and plan arithmetic, but samples peak shed occupancy after each future worker action. A later pickup therefore cannot make an earlier overflowing deposit feasible. `scheduler.py` and the optimizer remain unchanged. The ordinary canonical builder remains the package/release consumer; this delivery does not build or upload an archive.

## Executed distinguishing case

The constructed observation is step8, shed WHEAT90 + CARROT10, a farmer carrying MILK10, and one PET_CAFE. The selected current market sells CARROT10. The supplied continuation at9 orders farmer DROP, then hand PICKUP WHEAT10.

The original inherited checker sampled only the final stock after both workers. Actual `FrozenSelected.transform` changed CARROT SELL10 to SELL1 and reported +17 conditional scenario value. The official ordered interpreter then admitted only one MILK and discarded nine before the later pickup. The repaired consumer retains SELL10 and deposits all ten MILK. Reversing the actual worker order still permits SELL1 and deposits all ten; the repair does not reject all delayed sales.

A separate two-action terminal fixture, using the official interpreter's real terminal rewards, records own cash3267 before versus4607 after, rival1000 unchanged, in both constructed seats. This is one constructed regime, not two independent wins, a complete seeded game, or a rating gain. PLACE, nonpressured routes, current post-unit reuse, existing headroom, caller inputs and plan dictionary semantics are also covered.

## Run the changed-path tests

Use an existing repository checkout and the already available pinned engine cache:

```sh
ROOT=revenue/kaggriculture
python3 -B "$ROOT/cloud-selected-market-checks/test_frozen_ordered_capacity.py" \
  --runtime "$ROOT/cloud-execution-lab" \
  --evaluator "$ROOT/cloud-eval/evaluate.py" \
  --engine-cache "$ROOT/cloud-execution-lab/reference/engine" \
  --report /tmp/frozen-ordered-capacity.json
```

All15 methods pass:32 official interpreter transitions,1155 actual profile/plan comparisons, zero failures/errors. The same command with `--original-control` restores only the inherited original method and produces five failure entries/subtests, zero execution errors. The production body of `_apply_unit_action` is AST-matched to the pinned interpreter in the test.

`FROZEN-ORDERED-CAPACITY-EVIDENCE.json.gz.b64` contains both complete native reports, all retained cases and original failure traces. Decode without executing archive content:

```python
import base64, gzip, hashlib, json
from pathlib import Path
p = Path('revenue/kaggriculture/cloud-selected-market-checks/FROZEN-ORDERED-CAPACITY-EVIDENCE.json.gz.b64')
packed = base64.b64decode(p.read_bytes().strip(), validate=True)
assert hashlib.sha256(packed).hexdigest() == '3a9f68cb754c3f172652605617c8392c65c148218b4ccc5b730a12cb8813fb0f'
reports = json.loads(gzip.decompress(packed))
assert reports['fixed']['success'] and reports['fixed']['tests'] == 15
```

## Retained-prefix consumer check

The before/after canonical default comparison uses the exact PR10167 source closure retained in LARCH's SOURCE-PINS, with only this method changed. DELVE's existing 9965001 frozen-SELL native frame streams supply both own-observation prefixes. Each actor executes719 calls; all1438 paired outputs and tracked scheduler/seed states agree. Both sides preserve the same two funding edits relative to each original frozen trace, so this is explicitly an off-policy correspondence check, not a new canonical-policy game. On seat0, independent Python call events count719 original Arlene calls in each actor. Seat1's parent-call count was not separately instrumented.

The retained-input checker is `check_frozen_capacity_prefix.py`:

```sh
python3 -B revenue/kaggriculture/cloud-selected-market-checks/check_frozen_capacity_prefix.py \
  --scheduler /path/to/source-closure/scheduler.py \
  --frames /path/to/9965001-p0-sell.frames.jsonl.gz \
  --seat 0 --canonical --parent-count --output /tmp/capacity-prefix.json
```

Run each source in its own fresh process and compare `action_digest` plus all `state_digests`. The `--canonical` exit code allows explicitly reported differences from the original trace; it does not claim those differences are equivalent. The checker consumes only the evaluated seat's observation, normalizes frame step as the original evaluator does, takes expected action from the next frame, and never runs the engine. `--capture-profiles` is for the separate standalone scheduler mode, not `--canonical`. Call counting adds profiling overhead and its timing is not a budget benchmark. Use a clean source closure without stale bytecode. No new evaluation seeds are consumed.

## Exact source and scope

Executed repaired FrozenSelected: Git blob `b4d1120b73e3d14ed0c069872e96b7ce13842a47`, SHA256 `0df82c7f1e4cd40e726945c4efba53d7b0b3b1df90c53e75ff34ff0adbca0b4a`. Original FrozenSelected blob58fde0ad and scheduler blob97085ace are the comparison sources; scheduler SHA25632c8610c is unchanged. The new native suite is blob1e9f2bcf, SHA256e244f528; the prefix checker is blobbcb8a4ea, SHA2560da7e343.

Official engine ref: `Kaggle/kaggle-environments@28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`. Existing source/engine packages and Library inputs were reused; no transport job, library installation, game panel or workflow was created.

The initial capacity-compression and no-sale fast-path experiments did not establish a reliable whole-canonical-actor speed benefit. They are not included in this repair; original timing reports and provisional sources remain in the separate evidence package. This delivery makes no speedup or hard-deadline claim. It fixes ordered future-unit capacity, not every inherited market/cash or continuation assumption. Existing selected-route, unknown-future and conditional-projection limits remain in force. The builder's current archive and root's submission operation are separate from this source delivery.
