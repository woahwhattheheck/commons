# V233/V234 six-sheep production recovery on the current V5 ABI

Research-only recovery of the submitted V3.1 V233/V234 production theorem. No runtime/default/config/CURRENT/archive/release/opponent/Kaggle activation occurs here.

## Why this lane exists

The exact V3.1→V4 Arlene comparison showed a large WOOL production gap while own wool receipts were nearly unchanged. V233 is the submitted six-sheep southeast-quadrant investment theorem; V234 is its bounded wheat/feed rescue. This carrier preserves that theorem but moves its route provenance onto current V5 authority.

Submitted authority remains commit `a90d888f03987ef0b35cfd20ec3519c6144db08a`, R03 blob `182e0b7b3f0cc1125967dc092b2c118601b19084`.

## One route authority, not another producer

`current_route_full_snapshot.py` is now a companion to the landed receipt-bound route witness, not a second route selector. `bind_current_full_route(...)` requires the exact immutable producer receipt:

```text
{route_step, last_step, player, route}
```

The receipt must authorize the current selected-action boundary exactly: `route_step == last_step == observation.step`, exact player equality, and the explicit committed route. Raw `controller.cur` is ignored. The helper captures `R[receipt.route]` once using canonical `_capture_route`, stores strict detached route JSON, and records route-step/last-step/player provenance.

A bounded `snapshot.window(lookahead)` reconstructs the landed `CurrentRouteWindow` v3 receipt byte-for-byte, including controller type, receipt fields, worker cardinality, route length/full route digest, requested lookahead and ordered row receipts. Non-finite route payloads fail closed.

## Public V233/V234 surface

`v233_v234_current.py` is retained as unchanged theorem mechanics. The authorizing current-V5 surface is `v233_v234_current_safe.V233V234SixSheepCurrentSafeABI`.

The safe adapter accepts only `CurrentFullRouteSnapshot` v2 with canonical route source and validates against the current observation:

- exact `route_step == last_step == current_step == current_index == observation.step`;
- exact receipt player;
- non-empty route id and route length beyond the current step;
- strict canonical route JSON and matching full-route SHA-256;
- a re-derived canonical v3 bounded window whose receipt matches the snapshot provenance.

Only after those checks does it build a private compatibility view for the unchanged submitted V233/V234 theorem. Missing, stale, cross-player, wrong-route or forged receipt fields therefore return the selected action unchanged.

## Preserved theorem

The donor logic remains default OFF and preserves submitted qualification, order/capacity/budget checks, physical confirmation, two-worker ownership, sheep lifecycle, observed-production credit, bounded wheat rescue and transactional retry contracts. It never calls or replaces the producer.

## Contracts

Exact-head CI on Python 3.11/3.12 compiles the canonical route witness, full snapshot helper, safe adapter and donor tests, then runs normal and `python -O` focused suites. Coverage proves:

- full snapshot receipt-window equivalence to canonical v3;
- detached route bytes and raw-`cur` rejection;
- stale/carried/cross-player/wrong-route and non-finite rejection;
- safe-surface forged route-step/last-step/player/route-id rejection;
- a real receipt-bound snapshot still drives the exact day-12 V233 request;
- the original V233/V234 gameplay theorem remains unchanged.

Fresh matched current-V5 engagement/economics are still required before any composition or promotion through the single V5 release gate.
