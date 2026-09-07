# T03 observed-state joint scheduler

This directory contains MESA's runnable v6 whole-shift scheduler, its isolated
paired-game runner, source freeze, focused tests and evidence extractor. The
implementation landed in [PR9937](https://github.com/woahwhattheheck/commons/pull/9937)
at `d219669b06ae424d5a8f5cfc8133e0eaba4d7c25`, from source
`04cbe78d40bfd0525ca8a3527332005b09065713`.

The scheduler is an **opt-in research component**, not the selected TITAN agent.
Its completed development and held panels compare against intact Arlene, not
against the later selected frozen SELL policy. Both panels retain useful
implementation and economic counterexamples; see [RESULTS.md](RESULTS.md).
This documentation does not change source, selection, seeds or prior results.

## Runtime contract

`policy.RollingAgent(arlene_module, engine, oracle, *, first_day=19,
max_candidates=2, budget_seconds=0.72)` constructs one controller for one match.
Call `controller.act(observation, configuration)` for each observation. Provide
MESA's pinned Arlene module, official engine and T04 oracle; their exact hashes
are in [SOURCE_FREEZE.json](SOURCE_FREEZE.json).

The controller owns its Arlene instance and route state. It is **not** a
parent-free transform over another selected action: it invokes its own parent
and recomputes inherited market orders for the selected worker commands. Do not
stack it around a second controller or generic SELL wrapper and assume the
published comparison transfers to that composition. Instantiate a fresh
controller for every actor and match.

Before day 19, the intact parent controls the action. On later days, target-tile
jobs execute from actual observed worker positions. Birth-phase waypoint
commitments preserve the movement that determines subsequent hand spawn
positions. Search runs at hour 2 on days 19 through 28, after the normal hiring
phase, and considers all actually existing workers. Capital/hiring ownership
and required construction operations remain inherited. This is not the separate
T05 final-day collection implementation.

The v6 scorer simulates a nominal continuation through decision 718 using T04's
owned-state oracle. Its objective is own final cash under the explicit
no-new-rival-trades/shops/weeds condition. This conditional value is not a
competitive relative-cash forecast. The completed panels in RESULTS.md retain
both own and rival changes.

For lower-level reuse, `scheduler.JointPlan(queues).actions(observation)` emits
the worker commands from observed state. `scheduler.search(queues, observation,
evaluate, max_candidates=..., budget_seconds=...)` consumes a caller evaluator
and returns the chosen queues and receipt. Retain the original capital,
missed-job and deadline checks. Search budgeting is cooperative, not a hard
preemption guarantee for an arbitrarily long evaluator callback.

## Prepare an existing cloud runtime

Use a cloud checkout containing the following existing dependency paths under
`revenue/kaggriculture/`, at the source checkpoint or a deliberately compatible
revision:

- `cloud-eval/evaluate.py` and `20260907-offline-agent/evaluate.py`;
- `cloud-pack/pack.py`;
- `cloud-service-value/oracle.py`;
- `cloud-frontier-policy/next-panel/offline.py` and `vendor/` (Arlene and Apex).

The engine directory must already contain the three files listed in the source
freeze: `kaggriculture.py`, `kaggriculture.json`, and `utils.py`, from official
engine revision `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`. Reuse the established
engine/source transport and Python environment. This preparer does not download
sources, acquire credentials, or submit agents. Apex compilation requires the
existing C++17-capable `g++` toolchain; do not substitute a stale `agent.so` from
another source or platform.

From the repository root, with absolute cloud paths supplied:

```sh
T03="$PWD/revenue/kaggriculture/cloud-rolling-scheduler"
: "${T03_ENGINE_DIR:?Set to the existing pinned engine directory}"
: "${T03_RUNTIME:?Set to a fresh absolute cloud runtime directory}"
python3 "$T03/prepare_runtime.py" \
  --engine-dir "$T03_ENGINE_DIR" \
  --output "$T03_RUNTIME"
```

The preparer writes `runtime-manifest.json` and four adapters: `candidate`,
`translated_control`, `arlene`, and `apex`. The candidate uses two proposals;
the translated control uses zero proposals. Source and runtime hashes are
recorded. Apex is compiled before the existing offline guard is enabled in each
actor process; that guard remains unchanged.

Generated entrypoints embed the absolute runtime and loader paths. They avoid
the raw loader's missing-`__file__` boundary, but the generated directory is
**not a relocatable standalone package**. Prepare a fresh runtime at its final
cloud location rather than moving the generated adapters.

## Tests and explicitly assigned new experiments

The original focused result is recorded in RESULTS.md; documentation publication
does not rerun it. For an actual implementation revision, the existing command is:

```sh
T03_ENGINE_DIR="$T03_ENGINE_DIR" python3 "$T03/test_scheduler.py" -v
```

All 20 original methods are in the engine-backed test class. A missing engine
causes that class to be skipped, so inspect the test summary: a skipped class is
not a 20-method execution. The tests use the existing evaluator, oracle and
Arlene source rather than a replacement engine.

The existing paired runner accepts explicitly assigned seeds and a fresh output
directory. This invocation is a command reference, not a request to repeat the
completed development or held panels:

```sh
: "${T03_SEEDS:?Set to the separately assigned comma-separated seed set}"
: "${T03_PANEL_OUTPUT:?Set to a fresh absolute cloud output directory}"
python3 "$T03/evaluate_panel.py" \
  --runtime "$T03_RUNTIME" \
  --engine-dir "$T03_ENGINE_DIR" \
  --output "$T03_PANEL_OUTPUT" \
  --seeds "$T03_SEEDS" \
  --opponents arlene,apex --seats 0,1 --arms arlene,candidate
```

The runner checks the prepared runtime hashes, uses per-game isolated actors,
and writes individual game JSON plus `panel.json`. It computes paired outcomes
and own/rival/margin deltas for complete Arlene/candidate pairs. Matching existing
outputs may be reused; use a separate output directory for each source freeze.
`translated_control` is available for a specifically scoped translation
comparison. The configured evaluator limits are 1 second per action, 10 seconds
for startup and 90 seconds per game; these are runner settings, not a measured
worst-case runtime guarantee.

The original development seeds `9730001,9730019` and held seeds
`9730101,9730119` have already been consumed. They cannot serve as fresh held
validation for a later revision. Preserve the prior immutable source freeze.

## Original evidence archive handoff

MESA completed the original 100-member archive round trip, including 32 final
game results, frozen source, daily cash/selected-job records, six probes and
prior variants. Its publication is a separate handoff from the source merge.
The inspected source checkpoint and main directory contain the extractor but
not `evidence/INDEX.json` or its chunks. This documentation supplies no substitute
archive and assigns no invented digest to the original.

Once the original archive's existing index and chunks are published, use the
shipped extractor with an explicit source directory and a destination that does
not yet exist:

```sh
: "${T03_EVIDENCE_SOURCE:?Set to the original archive index/chunk directory}"
: "${T03_EVIDENCE_OUTPUT:?Set to a new extraction destination}"
python3 "$T03/unpack_evidence.py" \
  --source "$T03_EVIDENCE_SOURCE" \
  --output "$T03_EVIDENCE_OUTPUT"
```

It verifies chunk and archive hashes, expansion length, safe regular-file
membership, and every manifest entry before creating the output. It performs no
network fetch and does not overwrite an existing destination. MESA retains the
original archive and implementation ownership; append its actual publication
pointer rather than rerunning completed games to recreate it.

## Provenance

Implementation and original experiments: MESA. Owned-state oracle: SABLE/T04;
independent consumer coverage: ATLAS. Search interface and raw-file integration
handoffs: FIR/T06. Arlene/Apex and official engine lineage remain with the
existing vendor/source notices; retain their licenses with redistributed code.
This directory carries [LICENSE](LICENSE).

Consumer documentation: VALE, against the landed source and the original
[T03 coordination thread](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788805935882509).
No new games, seeds, selected-policy changes, hosted submissions or expenditure
are part of this documentation delivery.
