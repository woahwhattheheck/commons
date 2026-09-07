# T05: final-day collection and delivery

A runnable observation-only overlay over **intact Arlene v14**. Default actions
through 697 are unchanged, including the final-day opening hire and input pickup.
From 698 through 718, all workers receive jointly reserved collection routes and
capacity-aware deposits, followed by sales of the actual projected shed contents.

The selected entry is `main.py:agent`, backed by a persistent `terminal.Planner`.
It is **not** the stateless `terminal.overlay` research variant: that earlier
variant lost development games. Do not substitute it when reproducing the result.

## Measured result

Development: 8 candidate wins versus control 4 wins / 4 ties. Held: 8 candidate
wins versus control 4 wins / 4 ties. Four ties became wins in each panel; Apex
results stayed unchanged. All 16 paired pre-698 state/action hashes matched.
Held mean own cash improvement was **168.25**, mean margin improvement **352.75**.
Maximum selected action across the two panels was **0.05524 seconds**.

**Attribution matters:** every paired sold-unit total was unchanged, and both
arms ended with no carried, shed, or on-tile held yield. This panel demonstrates
better delivery/sale timing, not additional harvest, lower stranded stock, or
proof of broad strategic strength. There was no observed DROP loss. These are
local official-interpreter results, not a Kaggle upload, rating, or cash receipt.
Full results, limitations and rejected variants are in [RESULTS.md](RESULTS.md).

## Mechanism and deployment interface

The planner turns the parent's already-known **own** route into jobs that must
exist in the observed farm. It preserves the parent's productive crop-treatment
order, removes needless motion, then performs bounded joint insertion and local
treatment improvement. It models travel, mature WATER gains, fertilizer use,
plant decay, collection and time to deliver. Capacity admission follows actual
worker order: a DROP is used only when the entire load fits; selective PLACE can
admit a valuable subset without erasing overflow. Pricing is a current-quote
heuristic, not future market knowledge or an optimal schedule guarantee.

All four shed access tiles and movement across LOCKED tiles are usable in the
pinned engine. Worker actions precede market processing; DROP on decision718 can
be sold that turn. A final automatic deposit is not a substitute. Nonproductive
CARE/FEED is omitted, but useful immediate WATER is retained. These rules are
covered by real-engine tests, not a mock transition implementation.

`main.py` loads the exact parent hash, retains its state, and passes its selected
own route tail to the persistent planner. No environment seed, rival future
actions, hidden shop draws, replay, network or engine import is used by the policy.
The native file loader supplies `configuration['__raw_path__']`; a normal Python
module import can use `__file__`. Use a fresh process/module per match.

For an explicit integration with an existing parent controller:

```python
from terminal import Planner
planner = Planner()  # once per actor/match
# Each turn, after updating the intact parent's state exactly once:
action = planner.act(observation, parent_action, configuration,
                     own_future_actions=selected_parent_route_tail)
```

The supplied tail must be that controller's own known planned actions, never
future rival or replay data. Without it, the planner uses a greedy fallback;
that is not the selected v3 comparison. The result is a **complete action**, with
both unit and market decisions. T08 must reconcile SELL stages and actual
post-deposit quantities explicitly rather than stacking full-action wrappers.
No combined-lane or alternative-parent benefit has been measured here.

## Sources and freeze

[Source pack](https://github.com/woahwhattheheck/commons/tree/8329e78768906dc6e75ca3712e1690adc1ab2148/revenue/kaggriculture/cloud-frontier-policy/next-panel):
`8329e78768906dc6e75ca3712e1690adc1ab2148`.
[Official engine](https://github.com/Kaggle/kaggle-environments/tree/28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c/kaggle_environments/envs/kaggriculture):
`28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`.
Arlene SHA256: `1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4`.

Runtime and measurement hashes were [frozen in Slack before held tests](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788809618102709).
[FREEZE.json](FREEZE.json) is that historical record; `held_started: false`
describes the freeze instant, not the current completed evaluation state.
Seeds: development 9750001/9750019, held 9750101/9750119. No collision appeared in
the downloaded source/results trees or separate GitHub searches; GitHub search
was incomplete, so this was a bounded check, not an exhaustive workspace claim.

## Reproduce in a cloud workspace

Use the existing source-pack evaluator and packer at the exact Commons pin above.
When replaying from a newer main, extract the pinned shared paths into a separate
cloud directory, then copy this T05 directory alongside them. Do not overwrite
peer work or create new owner-PC clones/caches. Required shared paths are
`revenue/kaggriculture/cloud-frontier-policy`, `cloud-pack`, `cloud-eval`, and
`20260907-offline-agent/evaluate.py`. The first path includes its existing export
and licensed Arlene/Apex sources. The existing offline engine loader verifies all
three official Git blobs; it does not silently replace missing source in offline mode.

From the repository root, with the verified three-file engine cache at `$ENGINE`:

```sh
P=revenue/kaggriculture/cloud-terminal-routing
python "$P/prepare.py" --runtime /tmp/t05-runtime
T05_ENGINE_DIR="$ENGINE" python -m unittest discover -s "$P" -p test_terminal.py -v
python -m py_compile "$P/main.py" "$P/terminal.py" "$P/measure.py" "$P/test_terminal.py"
python "$P/measure.py" --engine-dir "$ENGINE" --runtime /tmp/t05-runtime \
  --seeds 9750001 --opponents arlene --variant control --output /tmp/t05-control.json
python "$P/measure.py" --engine-dir "$ENGINE" --runtime /tmp/t05-runtime \
  --seeds 9750001 --opponents arlene --variant candidate --output /tmp/t05-candidate.json
```

Both seats are the default. Repeat per seed/opponent with distinct output names.
The preparer reuses the existing g++ Apex build and network-denied native actors;
requirements are Python 3.13, g++, and the source pack's existing Linux seccomp
library. It performs no download. For a fresh engine cache, the existing
`python revenue/kaggriculture/cloud-eval/evaluate.py --prepare-engine "$ENGINE"`
retrieves the three public pinned source files.
No hosted submission or new paid resource is used by these commands.

## Build and check the native package

```sh
python revenue/kaggriculture/cloud-pack/pack.py build \
  --spec "$P/export-spec.json" --output /tmp/t05-export
python revenue/kaggriculture/cloud-pack/pack.py verify --bundle /tmp/t05-export
python revenue/kaggriculture/cloud-pack/pack.py check \
  --bundle /tmp/t05-export --spec "$P/export-spec.json" --engine-dir "$ENGINE" \
  --opponent /tmp/t05-runtime/arlene-adapter.py --seed 9750001 \
  --output /tmp/t05-export-check
```

Executed export: **40,440 bytes**, SHA256
`4954c74023e06c34f5430a942898d691fe61afd77c1bd893d616c26ed3d3af9c`.
All source hashes and notices are in [export-spec.json](export-spec.json).
Native cold probes matched both seats. Four full packaging games (reference and
extracted export, both seats) had identical scores and full trace hashes;
maximum exported call was 0.06604 seconds. These packaging replays reuse a
development seed; they are not additional independent held evidence.

## Inspect the complete raw evidence

```sh
python "$P/evidence.py" --output /tmp/t05-evidence
```

The five binary parts under `evidence/` losslessly encode 29 files / 27,594,762
original bytes in 51,644 bytes. Repeated JSON subtrees are interned, then XZ
compressed. The decoder uses standard-library JSON, not pickle or execution;
every part and every restored file is checked against its exact SHA256 before
being written. All 29 restored files were byte-compared to their originals.

Restored material includes all 38 recorded experiment attempts (including two loader
failures and four rejected-policy losses), complete final-day observations and
actions, cash/unit/drop-loss measurements, raw actor timings, final states,
rejected source versions, the paired summary, the separate four-game native
export report, and test logs. Timing fields are measurements on this cloud host,
not byte-reproducible performance forecasts.

## Attribution and coordination

Apache-2.0; retain the source pack's LICENSE and Arlene/source notices when
redistributing the generated package. ASTRA-RELAY-CI authored the terminal
overlay, tests, measurement hooks and evidence codec. Arlene, Apex, the official
engine, the existing evaluator, native loader and packer retain their source
attribution. No peer-owned production path was changed.

[T05 assignment and running record](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788805899688949)
/ [session coordination](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788805274807649).
