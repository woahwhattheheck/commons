# Current route witness — one producer, one immutable authored-tape capture

This V5 provenance helper closes the future-route seam shared by recovered V3.1 selected-action transforms. B5/JIT needs the exact **step+1** authored action; H4/market recovery needs a bounded ordered future window. Those consumers must not call a second producer, reconstruct a legacy R04 tape, or perform repeated live reads that can mix route snapshots.

## Committed producer authority

The v2 witness does **not** trust `controller.cur` as a route-selection authority. The current runtime deliberately commits a route only after `production.act()` has returned a complete selected action; an interrupted producer may leave a different proposal in `controller.cur`. Callers must therefore pass `completed_route_id` from the producer's committed selected-action receipt (for `TitanAgent`, `_completed_route` after the producer transaction commits, or the stronger entrypoint route receipt when available).

`bind_current_route_window(controller, observation, completed_route_id=..., lookahead=N)` captures and canonicalizes `controller.R[completed_route_id]` once. Live `controller.cur` is checked only as a fail-closed consistency condition: if it differs from the committed route, the helper emits no witness rather than silently switching authority. The capture is rebound before publication and emits an immutable envelope containing:

- source authority `installed_controller.R[completed_route_id]` and concrete controller type;
- the explicit committed `route_id`, public `current_step/current_index`, current worker cardinality and route length;
- a SHA-256 over the full captured route snapshot;
- an ordered bounded future window (maximum 72 rows) with exact authored step, per-row worker cardinality, detached action bytes and action SHA-256;
- a window digest over route authority, route identity and ordered row receipts.

The full-route digest deliberately binds bytes outside a small requested window: a consumer cannot claim an H1/H8 witness from a route whose remaining snapshot was not serializable/authenticated. Returned actions are reconstructed from canonical JSON, so later controller/tape mutation cannot change an already-published witness.

`bind_current_route(controller, observation, completed_route_id=...)` derives the strict step+1 B5 view from an H1 capture. It additionally requires the next authored row to have the exact currently represented worker cardinality. `bind_b5_kwargs(..., completed_route_id=...)` emits only `next_authored` + `next_authored_step` for `B5CurrentABI.transform`. Wider consumers use the same `CurrentRouteWindow`; no feature-local tape oracle is needed.

The helper never calls `controller.act`, changes `cur`, edits route bytes, selects a policy, or imports gameplay code. It fails closed on missing/malformed committed route identity, a live `cur`/committed-route mismatch, malformed actor identity, non-plain clock values, invalid private worker cardinality, missing/replaced/drifting routes, non-JSON route bytes, malformed authored actions, route exhaustion, or invalid lookahead.

This is source/evidence plumbing only. It does not change runtime defaults, `TITAN-CONFIG.json`, archive pointers, release authority, or Kaggle submission. The intended composition remains one V5 line: current controller -> one committed selected action + route receipt -> one immutable current-route capture -> recovered selected-action transforms -> existing matched-economics/composition/release gates.

Focused contracts:

```bash
python -B -m py_compile current_route_witness.py test_current_route_witness.py
python -B -m unittest -v test_current_route_witness.py
python -O -B -m unittest -v test_current_route_witness.py
```
