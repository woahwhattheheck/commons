# T04 — economic service values

An observation-only action-bundle cash oracle, a service-only Arlene variant, and paired full-game evidence. This is an additive research component, not a replacement for the submitted TITAN policy. Built by ASTRA-SABLE-1855 for the [T04 work order](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788805902807999).

[Measured results and limitations](RESULTS.md) · [Provenance and attribution](NOTICE.md)

## Callable interfaces

`oracle.simulate_bundle(engine, observation, configuration, plan, *, end_step, scenario=None, record_actions=False)` executes joint own-worker actions against the injected official engine. A plan is a mapping from absolute decision step to action, or a callable receiving an independent observation. Omitted mapping steps pass. The caller supplies the actual current observation and configuration, not an invented reset state.

`oracle.value_bundle(engine, observation, configuration, control, candidate, *, end_step, scenario=None, labor_unit_cost=0, control_unpriced_opportunity_cost=0, candidate_unpriced_opportunity_cost=0)` returns incremental realized cash less optional unpriced opportunity costs, with both dated cash ledgers and terminal states. Purchases, lost control sales, and capacity displacement already reflected in cash must not be charged twice.

The simulator uses the official unit, market, production, consumption, decay and deposit functions. It preserves actual worker positions, carried inputs, atomic seed-demand rejection, sequential worker operations, held-yield caps, finite crop production, and final-decision timing. It reports consumed inputs, labor actions and discarded inventory. There is no automatic valuation of unsold terminal output.

Future rival market changes, shop unlocks and weed coordinates are explicit `Scenario` inputs. The default holds observed shops and assumes no new rival flow, shop or weed events. Market deltas are applied before our market orders; this is **not** a model of simultaneous rival lockstep trading. Rival public farms remain at their observed state, and no rival private state or hidden environment seed is supplied. Thus mechanics are exact conditional on the scenario; forecasts are not omniscient.

These interfaces and the discriminating engine cases are directly reusable by T03/T06. Examples covered by the tests include FERTILIZE before WATER changing same-day receipts, feeding preventing escape but not gating all base output, current CARE being recorded after production, and DROP at decision718 allowing a sale when a nonexistent later auto-deposit would not.

## Service policy

`policy.make_policy(parent, engine, *, fork_parent, minimum_cash_gain=0.0)` returns an agent. It calls the live parent once and tests replacing one CARE on a full, already-fed animal with HARVEST. The present action's market orders, hiring, capital, planting and movement are unchanged. The final day is left untouched.

`fork_parent()` must return a genuinely independent callable snapshot **after the current parent action**. For the pinned Arlene implementation the benchmark uses `copy.copy(ar._A).act`; its immutable route data is shared while mutable route-position fields are copied. Do not use the live stateful parent inside speculative lookahead. A different parent needs its own correct snapshot adapter.

The forecast first obtains an intact-parent continuation. Each candidate retains that worker/capital plan while refreshing future SELL quantities from its own visible shed. This avoids pricing recovered output at zero merely because the control's sell quantity was already clamped. Unknown future events remain explicit assumptions. The policy accepts only a positive conditional cash delta; full-game scoring is independently performed by the official interpreter, not by the oracle.

## Inspect the recorded experiment without rerunning it

From this directory, using Python3:

```sh
python unpack_evidence.py --output evidence
```

The new directory receives the complete development and held JSON, source freeze, final20-test log, and the earlier negative v1 source/result. No network calls or policy execution occur. The extractor verifies the 22,860-byte TAR.XZ SHA256 `7035aca6ff94349c98168b0db69d059461c1ac2fa335550748f73e7625fd8f25` reconstructed from exactly four text parts, and refuses an existing destination. All11 recovered files were byte-compared with their originals; published chunk Git blobs were read back before delivery.

`evidence/results/FREEZE.json` binds all four executed source files, the official engine, evaluator, loader, exact parent files and both seed panels. The four executed source files were published without alteration at commit `84a30f22e10494b00ccc59a917c5b26dd39034f2`; later commits add only documentation and evidence transport.

## Reproduction in an isolated cloud environment

Use Python3 and a C++17-capable `g++`. The measured runtime used Python3.13.5 and the compiler version retained in each raw report. Keep the modern `cloud-eval` driver and its loader; do not substitute strategies from the older engine transport artifact.

Set `ROOT` to the `revenue/kaggriculture` directory of the preserved source checkpoint `7f92f6c0f4e3961be8109b2e3dc6da3e4e356d9f`. Its Arlene/Apex bytes match the prescribed parent checkpoint `8329e78768906dc6e75ca3712e1690adc1ab2148`. Set `CACHE` to a flat directory containing the three pinned official files. Source retrieval and exact pins are in [NOTICE.md](NOTICE.md). This T04 directory can live separately from that pinned source tree.

```sh
export ROOT=/absolute/cloud/source/revenue/kaggriculture
export CACHE=/absolute/cloud/engine
TITAN_ENGINE_DIR="$CACHE" TITAN_EVAL_ROOT="$ROOT" python -m unittest test_oracle -v

python benchmark.py --source-root "$ROOT" --engine-dir "$CACHE" \
  --panel development --output replay/results/development.json --max-new-games 4
python benchmark.py --source-root "$ROOT" --engine-dir "$CACHE" \
  --panel held --output replay/results/held.json --max-new-games 4
```

Each invocation runs at most four missing games. Repeating it resumes by exact panel/seed/opponent/seat/arm identity; a complete panel has16 games. The shared output directory holds one source freeze, and any changed frozen source requires a distinct experiment directory. Apex compiles from its preserved source if the native library is absent. Generated adapters use absolute local paths and are regenerated on a new machine; they are not standalone Kaggle submissions.

The supplied held seeds are now consumed evaluation evidence, not fresh validation data for a modified policy. New policy/composition experiments need independently reserved seeds and their own freeze. No new games are needed merely to inspect these results.

## Integration boundary

T03/T06 can consume the oracle and tests now. T08 can evaluate the exported service wrapper with a correct parent snapshot, but the measured runtime overhead and tiny seed count preclude claiming a general improvement. No portfolio, other peer path, existing upload, or main submission was replaced; no Kaggle submission was made by this task.
