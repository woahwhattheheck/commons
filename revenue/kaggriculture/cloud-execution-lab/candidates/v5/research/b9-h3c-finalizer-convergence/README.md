# TITAN V5 — B9 → H3c single-producer finalizer convergence

This is the integration carrier for the already-merged #13408 current-ABI
semantic authority. It does **not** create another B9/H3c implementation and it
does not touch production defaults, the CURRENT release pointer, or Kaggle.

## Why this seam

Submitted V3.1 wrapped the selected stack with B9 terminal fertilizer and then
H3c goose EOD rescue. Current V5 has the recovered B9/H3c semantics, but #13408
is source-only.

The stable current rendezvous is `TitanAgent._finish_production()` immediately
after `_early_capital_selected()` returns. `FinalPressureAgent` overrides that
method to own the late returned-action chain, so pressure/town and the incoming
overflow → EOD → row-shed serial finalizers remain **inside** the recovered
B9 → H3c pair. The call still lands before quadrant/spatial/history state
commits. This avoids another writer inside the hot `main.py` finalizer seam.

## What the composer proves

`compose_current_runtime.py` captures and Git-blob-authenticates:

- current `titan_runtime.py`, `TITAN-CONFIG.json`, and `build_integrated.py`;
- merged #13408 `outer_wrappers_current.py`;
- exact submitted-V3.1 B9 and H3c donor bytes already authenticated by #13408.

It then writes a scratch postimage only:

- exact-bool `terminal_fertilizer` and `goose_rescue` feature keys, both false;
- one adapter installation, with no producer/controller invocation;
- one B9 → H3c selected-action call after `_early_capital_selected()`;
- deadline/fallback identity;
- transactional B9 state rollback if a unit-action change cannot be rebound to
  a current post-unit snapshot;
- post-unit recomputation through current `scheduler.post_units` when B9/H3c
  changes farmer/hand actions;
- a finalizer checkpoint on the exact recovered returned action;
- exact canonical #13408 bytes mapped into the scratch release tree.

`B9-H3C-MATERIALIZATION.json` records all input/output Git blobs and explicitly
states `production_activation=false`.

## Run

From this directory:

```bash
python -B -m py_compile compose_current_runtime.py test_compose_current_runtime.py
python -B -m unittest -v test_compose_current_runtime.py
python -O -B -m unittest -v test_compose_current_runtime.py
python compose_current_runtime.py --out /tmp/titan-b9-h3c-postimage
```

The pull-request workflow checks out and asserts the exact PR head before the
normal/`-O`/compile gate.

## Promotion boundary

This carrier is additive evidence/tooling until the moving finalizer queue is
rejoined and the postimage is reviewed against that fresh current source. A
production materialization still requires current package tests and matched
engagement/economics. Historical V3.1 success is motivation, not a default-on
authorization.

No whole-route R04 transplant, no second producer, no sibling V5, no release
pointer mutation, and no Kaggle submission.
