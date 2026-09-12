# TITAN V4 cross-ledger coherence audit

This package is a **read-only** control-plane audit for the sole canonical TITAN V4 tree. It does not register components, order transforms, rewrite either ledger, execute gameplay, promote defaults, assemble a runtime, or authorize a merge.

## Why it exists

`INTEGRATION.json` and `COMPOSITION.json` already have separate fail-closed validators, but those validators intentionally own different questions. That leaves one dangerous split-brain class: both documents can be individually valid while a component is marked `compose` in the composition graph without any exact landed custody path in the integration ledger, or while an integration row with explicit composition metadata disagrees with the graph.

`check_cross_ledger.py` binds `CANONICAL.json`, `INTEGRATION.json`, and `COMPOSITION.json` together without changing their ownership boundaries.

## Contract

The audit requires the three documents to agree on the canonical branch/workspace and requires production coordinates shared by CANONICAL/INTEGRATION to agree. It then applies two asymmetric rules:

- A `compose` component must have an exact `INTEGRATION.json` landed row whose `repair_path` equals the component `package`. Missing exact custody is a hard error.
- A `blocked` or `evidence_only` component with no exact landed `repair_path` is only a warning unless an integration row explicitly declares composition metadata for that package. This avoids laundering source custody while also avoiding false claims that every research blocker is already a landed runtime component.

When a landed row explicitly supplies `composition_state` (and optionally `composition_intake_pr`), that row must resolve to exactly one component by exact package path and its state must match the graph. Duplicate repair paths, duplicate component packages, unsafe paths, malformed/duplicate-key JSON, canonical-coordinate drift, and an exact negative/parked package marked `compose` all fail closed.

The result carries an explicit no-authority policy: no merge/close, ledger rewrite, composition mutation, runtime promotion, or economic decision is authorized by this checker.

## Current live diagnostic that motivated the lane

The initial capture found one gap. A fresh-main recheck at `main@ef0a2f297f2ca3ec4b7e3053db58b7ef82ac2eaf` widened it in the expected direction: `COMPOSITION.json` Git blob `a9bba310e2b0f71f429513cd79966c12b3ba9b4f` now marks `funding-capacity-stack` (`repairs/performance/funding-replay`), `scoped-construction` (`repairs/performance`), and `projection-state-clone` (`repairs/performance/projection-state-clone`) as `compose` after authenticated LOOM composition work, while the current integration ledger still has no exact landed `repair_path` for those packages. By contrast, fast-tape has an exact path match and row-shed's explicit `blocked` composition state matches the graph.

That snapshot is evidence, not an eternal assertion: `main` moves quickly. Re-run against fresh main before relying on the diagnosis. The checker is intentionally **not** wired as a required CI gate in this package; until the ledger owner and LOOM reconcile any live errors, a non-zero audit result is useful coordination evidence rather than a reason to fork or silently rewrite either authority.

## Run

From this directory:

```bash
python -B -m unittest -v test_check_cross_ledger.py
python -O -B -m unittest -v test_check_cross_ledger.py
python -m py_compile check_cross_ledger.py test_check_cross_ledger.py
```

From anywhere, audit the repository's canonical V4 root:

```bash
python -B revenue/kaggriculture/cloud-execution-lab/candidates/v4/research/cross-ledger-coherence/check_cross_ledger.py --pretty
```

Exit status is `0` only when there are no hard cross-ledger errors. Warnings remain visible in the JSON result.
