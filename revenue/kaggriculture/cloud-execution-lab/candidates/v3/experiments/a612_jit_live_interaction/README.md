# JIT PASS→FERTILIZE on shipped `a612` — interaction gate

This directory is **evidence only**. It is a direct child of merged canonical
`titan/v3.1-20260911@a6120d0ea1bdb75eb0da2239220efce551f624a6` and changes no
production overlay, package input, manifest, FILES receipt, default, evaluator,
opponent, submission, or Kaggle artifact.

## Why this gate exists

The reviewed JIT helper (`jit_pass_fertilize.py` Git blob
`6ef7ddcd9590e3cb3f55ceb708b8026235d59410`) previously produced a strong narrow
signal: exact-V3.1 10 positive / 6 zero / 0 negative, mean paired ΔM +41.0 on
seeds 2611151001..1008 both seats. The CARROT × JIT factorial was almost exactly
additive. Those receipts predate the merged `a612` package, which now ships H4
strawberry top-up plus rival-gated L3.

The missing question is therefore not another source rewrite. It is whether the
**exact same JIT helper** still activates and improves competitive margin when
composed after the exact shipped R04 action on `a612`.

## Composition under test

`baseline.py` installs the exact score-facing `a612` R04 tuple:

- sale horizon 8, opening round-trip 0;
- row order, evening flush, sale-fertilizer, cattle-early ON;
- kill-late-water and strawberry-endgame OFF;
- rival-gated no-late-sale-advance ON at step 648;
- H4 strawberry top-up ON.

`candidate.py` calls that exact parent first. It then supplies the reviewed JIT
helper with the current plan's **next raw authored R04 tape row**, matching the
prior execution theorem. The helper alone may turn a literal selected `PASS`
into `FERTILIZE`; it cannot alter a non-PASS row, route, purchase, hire, market
row, movement, or default.

This stage intentionally does not production-wire a new config key. Production
wiring is allowed only if the live interaction screen is positive.

## Cheap paired screen

Dedicated CI uses the pinned official interpreter and compares:

1. exact `a612` baseline vs exact `a612` baseline; and
2. JIT wrapper vs the same exact `a612` baseline,

on seeds `2611151001..2611151004`, both candidate seats, with first-cell
reproducibility recheck. Those seeds include three positive and one zero prior
JIT cells, so the panel is a cheap reachability/interaction discriminator.

The reducer reports every paired `Δown`, `Δrival`, and `ΔM` plus whether the full
action+bank trace changed. Disposition is fail-closed:

- zero trace deltas → reject as unreachable on live `a612`;
- any negative ΔM → hold interaction regression;
- nonpositive mean ΔM → hold;
- positive mean with no negative cells → **promising only**, advance to a
  materialized default-OFF package gate.

A trace delta is an activation proxy, not a production receipt. No result from
this PR authorizes default-true, merge, or Kaggle upload.
