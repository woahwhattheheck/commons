# SOL-SUTURE — TITAN V2 forced-feasibility carrier wiring receipt

- Operation: `titan-v2-forced-feasibility-carrier-wiring-20260909-01`
- Parent PR: `#11799`
- Exact parent head: `95b6a5b20976d2391b05746f8029a8d89a530c43`
- Branch: `sol-suture/titan-v2-forced-feasibility-carrier-wiring-20260909-01`
- Slack claim: `#titan-v25-sim-runs`, message `1788990358.743979`

## Blocking predecessor

The parent head contains closure-verifying arm wrappers in `bind_execution.py`
and a candidate-only pre-interpreter action digest in
`materialize_evaluator.py`, but its hosted workflow does not invoke either
module. It still executes the two identical 66-byte `candidate.py` aliases
through the unpatched evaluator and classifies the reports with only the
materialization receipt. Merely adding the repair modules therefore did not
repair the experiment executed by CI.

## Repair

This child:

1. Materializes the exact patched evaluator and records
   `EVALUATOR-MATERIALIZATION.json`.
2. Builds distinct control and ablation closure-verifying entry wrappers and
   records `EXECUTION-BINDING.json`.
3. Executes both arms through those wrappers and the patched evaluator.
4. Classifies only after binding the reports to observed wrapper, evaluator,
   engine, loader, opponent, source, ablation, and receipt bytes.
5. Requires the literal four-seed × two-opponent × two-seat grid, distinct
   invocation IDs, 720 configured steps / 719 returned candidate actions,
   exact limits/RNG/runtime identity, and atomic final reports.
6. Uses only the candidate-seat pre-interpreter returned-action digest for
   activation; the whole-game digest remains diagnostic evidence.
7. Re-inventories both bound payloads, source trees, wrappers, and evaluator
   after the panels, rejecting post-materialization drift.
8. Adds an opponent×seat non-regression gate so aggregate upside cannot hide a
   systematic regression in one seat.

## Changed paths

- `.github/workflows/titan-v2-forced-feasibility-ablation-sol-keel.yml`
- `revenue/kaggriculture/cloud-execution-lab/analysis/v2-forced-feasibility-ablation-sol-keel/compare_bound.py`
- `revenue/kaggriculture/cloud-execution-lab/analysis/v2-forced-feasibility-ablation-sol-keel/test_carrier_wiring.py`
- `p/sol-suture-titan-v2-forced-feasibility-carrier-wiring-20260909-01.md`

## Local evidence

- Focused predecessor-discriminating contracts: `9/9 PASS`
- `py_compile`: `PASS`
- Workflow YAML parse: `PASS`
- Comparator Git blob: `f13c068cf227bf88a8bee2ad407943ec7dc252bf`
- Contract-test Git blob: `649ffc2c006f6e74dcb9907061b7c9d93338846c`
- Workflow Git blob: `560760ed3a87a0c81d4213d11d9342468ecf466d`

The focused tests reject: disconnected repair modules, unpinned/uncompiled
carrier files, a truncated grid, Boolean seats, aggregate upside with a
negative opponent×seat stratum, evaluator tampering, and bound-payload
mutation after play. They also retain a positive exact-grid/upside witness.

## Boundary

No frozen V1/V2 scheduler or candidate, canonical TITAN package, gameplay
policy, runtime configuration, archive, pointer, provider state, Kaggle state,
submission, or spend is changed. This repair makes the offline causal screen
admissible; it does not itself claim leaderboard strength, promotion, or a
score improvement.
