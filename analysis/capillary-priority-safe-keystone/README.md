# KEYSTONE — Capillary same-turn priority-safe successor

Operation: `titan-v3-capillary-priority-safe-20260909-keystone-01`

## Score-facing defect

The closed Capillary compiler moved an already-planned day-zero expensive seed buy into the first blank active market slot immediately before each plant. A blank slot is not necessarily an execution-safe slot. When an inherited market row follows that blank, the new seed purchase executes first and can consume cash or capacity needed by an inherited `HIRE`, `BUY_LAND`, `BUY_PRODUCT`, `BUY_ANIMAL`, or sale. Route topology, actor bytes, seed totals, and inactive suffix checks do not detect that loss.

## Candidate theorem

For every injected `BUY_SEED` row in every changed route and step:

1. every inherited nonblank active market row remains byte-exact at its original index;
2. the injected slot is strictly greater than the final inherited nonblank active slot;
3. no inactive-suffix row changes;
4. any route/group lacking trailing active capacity is rejected; and
5. any priority rejection or post-compile audit defect rolls the complete route map back to exact control bytes.

The exact historical compiler executes in a private module graph. Only that private module's placement primitive is replaced, so the public predecessor module and canonical runtime remain untouched.

## Executable carrier repair

`CapillaryTitanAgent` verifies and unwraps exactly one installed `SpatialTempo` closure, deep-copies the inherited shared route bank, and reinstalls the same wrapper once over the private map before compilation. This avoids both known bad states: rebinding after capture (candidate erased on first action) and mutating the module-global scheduler routes (cross-instance contamination).

`capillary_main.py` executes canonical `main.py` privately per evaluator load and reuses its exact `_new_instance` code object with an isolated import view that substitutes only `TitanAgent`. The live `titan_runtime.TitanAgent` is never patched, and canonical deadline, fallback, reconstruction, finalization, early-capital, and final-pressure control flow remains authoritative.

## Gates

The hosted workflow runs the original 36 compiler/replay tests, the seven lifecycle/carrier tests, and new predecessor-discriminating tests covering:

- interior-hole predecessor behavior versus trailing-slot successor behavior;
- full-prefix rejection and whole-map atomic rollback;
- malformed target quantities;
- private compiler and canonical-module registry isolation;
- exact current four-route activation; and
- an exact repository-engine witness where predecessor slot-0 seed spend makes an inherited `BUY_LAND` fail, while successor tail placement preserves the land fill.

This is an isolated causal candidate, not a leaderboard or score claim. Official matched games remain gated on a green exact-head source/execution receipt.
