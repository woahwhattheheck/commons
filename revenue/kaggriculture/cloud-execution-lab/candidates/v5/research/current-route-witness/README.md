# Current route witness — committed producer authority, one immutable tape capture

This V5 provenance helper closes the future-route seam shared by recovered V3.1 selected-action transforms. B5/JIT needs the exact **step+1** authored action; H4/market recovery needs a bounded ordered future window. Those consumers must not call a second producer, reconstruct a legacy R04 tape, or perform repeated live reads that can mix route snapshots.

The trust root is the route that actually committed with the selected action, **not** raw `controller.cur`. TitanAgent may already have a later/interrupted proposal in `cur`, so callers must pass the completed producer route identity from TitanAgent / the entrypoint route receipt:

```python
window = bind_current_route_window(
    controller,
    observation,
    completed_route_id=completed_route_id,
    lookahead=8,
)
```

`bind_current_route_window` captures and canonicalizes exactly `controller.R[completed_route_id]` once, rebinds that same authorized route after capture, and publishes an immutable envelope containing:

- schema `titan-v5-current-route-window-v2` and source authority `committed_producer_route.R[route_id]`;
- concrete controller type plus the explicitly authorized `route_id`;
- public `current_step/current_index`, current worker cardinality and route length;
- SHA-256 over the full captured authorized route snapshot;
- an ordered bounded future window (maximum 72 rows) with exact authored step, per-row worker cardinality, detached action bytes and action SHA-256;
- a window digest over schema/source/route identity plus ordered row receipts.

Raw `controller.cur` is deliberately ignored for authority. If selected action A committed and `cur` has already moved to a valid proposal B, the witness captures A or fails closed; it never silently publishes B. Omitting or supplying a malformed/missing completed route identity fails closed. The v2 schema prevents v1 receipts—whose source semantics trusted `R[cur]`—from replaying as v2 authority.

The full-route digest deliberately binds bytes outside a small requested window: a consumer cannot claim an H1/H8 witness from a route whose remaining snapshot was not serializable/authenticated. Returned actions are reconstructed from canonical JSON, so later controller/tape mutation cannot change an already-published witness.

`bind_current_route(..., completed_route_id=...)` derives the strict step+1 B5 view from an H1 capture. It additionally requires the next authored row to have the exact currently represented worker cardinality. `bind_b5_kwargs` emits only `next_authored` + `next_authored_step` for `B5CurrentABI.transform`. Wider consumers use the same `CurrentRouteWindow`; no feature-local tape oracle is needed.

The helper never calls `controller.act`, changes `cur`, edits route bytes, selects a policy, or imports gameplay code. It fails closed on malformed actor identity, non-plain clock values, invalid private worker cardinality, missing/replaced/drifting authorized routes, non-JSON route bytes, malformed authored actions, route exhaustion, invalid authority, or invalid lookahead.

This is source/evidence plumbing only. It does not change runtime defaults, `TITAN-CONFIG.json`, archive pointers, release authority, or Kaggle submission. The intended one-V5 composition is: current producer commits selected action + route receipt -> one immutable committed-route capture -> recovered selected-action transforms -> existing matched-economics/composition/release gates.

Focused contracts:

```bash
python -B -m py_compile current_route_witness.py test_current_route_witness.py
python -B -m unittest -v test_current_route_witness.py
python -O -B -m unittest -v test_current_route_witness.py
```
