# Current route witness — one producer, one immutable authored-tape capture

This V5 provenance helper closes the future-route seam shared by recovered V3.1 selected-action transforms. B5/JIT needs the exact **step+1** authored action; H4/market recovery needs a bounded ordered future window. Those consumers must not call a second producer, reconstruct a legacy R04 tape, or perform repeated live reads that can mix route snapshots.

`bind_current_route_window(controller, observation, lookahead=N)` reads only the already-installed controller's `cur` and `R`. It captures and canonicalizes the selected `R[cur]` once, rebinds the route after capture, and publishes an immutable envelope containing:

- source authority `installed_controller.R[cur]` and concrete controller type;
- `route_id`, public `current_step/current_index`, current worker cardinality and route length;
- a SHA-256 over the full captured route snapshot;
- an ordered bounded future window (maximum 72 rows) with exact authored step, per-row worker cardinality, detached action bytes and action SHA-256;
- a window digest over route identity plus ordered row receipts.

The full-route digest deliberately binds bytes outside a small requested window: a consumer cannot claim an H1/H8 witness from a route whose remaining snapshot was not serializable/authenticated. Returned actions are reconstructed from canonical JSON, so later controller/tape mutation cannot change an already-published witness.

`bind_current_route(controller, observation)` derives the strict step+1 B5 view from an H1 capture. It additionally requires the next authored row to have the exact currently represented worker cardinality. `bind_b5_kwargs` emits only `next_authored` + `next_authored_step` for `B5CurrentABI.transform`. Wider consumers use the same `CurrentRouteWindow`; no feature-local tape oracle is needed.

The helper never calls `controller.act`, changes `cur`, edits route bytes, selects a policy, or imports gameplay code. It fails closed on malformed actor identity, non-plain clock values, invalid private worker cardinality, missing/replaced/drifting routes, non-JSON route bytes, malformed authored actions, route exhaustion, or invalid lookahead.

This is source/evidence plumbing only. It does not change runtime defaults, `TITAN-CONFIG.json`, archive pointers, release authority, or Kaggle submission. The intended composition remains one V5 line: current controller -> one selected action -> one immutable current-route capture -> recovered selected-action transforms -> existing matched-economics/composition/release gates.

Focused contracts:

```bash
python -B -m py_compile current_route_witness.py test_current_route_witness.py
python -B -m unittest -v test_current_route_witness.py
python -O -B -m unittest -v test_current_route_witness.py
```
