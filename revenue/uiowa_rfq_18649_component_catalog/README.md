# UIOWA-101 — verified component entry-point catalog

This package answers a practical operator question: **what can I actually run from the published Iowa RFQ preparation repository, at which source revision, with what input/output contract?**

It does not infer readiness from folder names. Every entry is bound to a Git blob SHA. Runnable entries carry a command, working directory, source-contract markers, prerequisites, input/output description, and one synthetic/source-backed sample signal. Static/template/incomplete entries are deliberately separated.

## Files

- `component_catalog.json` — machine-readable catalog bound to snapshot `c853c1422fc3e34aabbb54fe205bd9ea5b48bf34`.
- `RUN_MENU.md` — linked operator menu.
- `verify_catalog.py` — stdlib verifier for byte drift, missing paths, command-contract drift, sample evidence, and incomplete-entry transitions.
- `test_verify_catalog.py` — regression tests proving drift and missing-entrypoint states fail closed.

## Use

```bash
cd revenue/uiowa_rfq_18649_component_catalog
python verify_catalog.py
python verify_catalog.py --json
python -m unittest -v test_verify_catalog.py
```

## Status semantics

- **working** — executable source exists at the recorded blob SHA; its advertised command was checked against the source contract and a sample signal is recorded.
- **static** — useful published data/interface contract, no executable entry point.
- **template** — useful worksheet/document bundle, no executable entry point.
- **incomplete** — documentation advertises or implies a runnable entry point that is absent/unusable in the snapshot.

“Working” here is not a claim that this catalog build independently executed every component. The `sample_result.basis` field distinguishes checked-in outputs, source contracts, provider readbacks, and published validation receipts. This avoids turning second-hand execution receipts into new claims.

## Snapshot discipline

The source snapshot is immutable on purpose. New swarm merges do not silently mutate catalog truth. If a source changes or an incomplete entry point lands, `verify_catalog.py` fails and the next operator creates a refreshed catalog revision.

## Boundaries

Everything is preparation/synthetic unless the underlying component states otherwise. No catalog result is a University of Iowa finding, compliance conclusion, release approval, or individual performance score.
