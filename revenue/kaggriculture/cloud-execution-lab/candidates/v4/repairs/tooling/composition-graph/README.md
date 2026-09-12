# TITAN V4 composition graph (ASTRA-LOOM)

This tooling is a **fail-closed control plane for the one canonical V4 workspace**. It does not create another V4, materialize production, enable feature keys, rebuild the archive, or submit to Kaggle.

`INTEGRATION.json` remains the custody/evidence ledger. `COMPOSITION.json` answers a different question: *given authenticated transform packages, in what exact order may they be applied to the same current source surfaces without silently consuming stale bytes?*

## Contract

A component is one of:

- `compose`: eligible for the deterministic plan, but not thereby runtime-promoted.
- `blocked`: known package whose prerequisites/economic/custody gate is not satisfied.
- `evidence_only`: preserved evidence that is not executable composition input.

Every active transform names a logical `surface`, an exact `input_identity`, and an exact `output_identity`. Relations (`requires`, `before`, `after`, `conflicts`) are component IDs. The validator rejects unknown relations, active dependencies on blocked/evidence components, active conflicts, cycles, unordered writes to the same surface, stale predecessor identities, duplicate output identities, missing package/entrypoint paths, and strict-discovery entrypoints not registered in the manifest.

The initial graph deliberately stays small. It registers only packages whose source/output status is explicit enough to avoid guessing. Current-ABI fast-tape-clone is the first composable edge; D4 strawberry timing is deliberately blocked because its own manifest requires a fresh reachability/economic gate and prohibits stale V4 wiring.

## Run

From `candidates/v4`:

```sh
python check_composition_graph.py --json
python -m unittest repairs/tooling/composition-graph/test_composition_graph.py
python -O -m unittest repairs/tooling/composition-graph/test_composition_graph.py
```

A zero exit means the declared graph is internally composable. It does **not** mean the components are production-promoted or that every landed repair has been registered. Strict discovery only covers the entrypoint patterns explicitly listed in `COMPOSITION.json`; extend those patterns and register/justify newly discovered composers as the native integration surface broadens.

## Adding a component

1. Authenticate the exact current input and generated output identities.
2. Add the package and executable entrypoint paths relative to this V4 root.
3. Declare every touched logical surface.
4. Declare ordering/dependency/conflict edges instead of relying on Slack chronology.
5. Use `blocked` rather than inventing an identity, predecessor, or authorization.
6. Run the validator and both normal/optimized focused suites before handing the plan to the existing native composer.

LOOM intentionally does not own claim-liveness (LANTERN), custody semantics (LEDGER), optimizer logic (WEAVE), or final native materialization. It only makes cross-package composition order mechanically reviewable.
