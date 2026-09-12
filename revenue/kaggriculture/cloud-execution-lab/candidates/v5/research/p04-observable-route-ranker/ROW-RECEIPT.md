# TITAN V5 route-matrix row receipt

This is the **observation/receipt bridge** between the merged shared route carrier
(`#13475`) and the merged P04 reducer (`#13478`). It is not a second evaluator,
route-force harness, or runtime selector.

`route_matrix_row_receipt.py`:

- SHA-verifies the pinned official native evaluator (`e30b3108...`) and loader
  (`61093af2...`) before execution.
- Consumes a shared `build_route_matrix.py` manifest and accepts only the
  step-144 matrix (`selection_step=144`, one changed `r04_full_router.py`,
  production-v3 baseline `20f20116...`, router preimage `41ea55c5...`).
- Imports the pinned evaluator unchanged and calls its original `play()` exactly
  once. During that call it temporarily wraps `Actor.act` only to observe the
  candidate input at step 144, then delegates exactly once to the original
  method with the same observation/configuration/timeout.
- Immediately reduces that observation to P04's public contract: first two
  shops, public market prices/inventory, own cash/worker+animal+crop counts,
  rival visible animal+crop counts, and source-derived incumbent plan. Raw
  `private`, shed, farmer inventory, future town and RNG fields are never
  serialized.
- Requires a complete failure-free 719-decision / 720-episode-step game and
  emits terminal own/rival/margin directly from the pinned evaluator result.
- Runs the produced row back through `p04_route_ranker.normalize_row()` and
  SHA256-binds its canonical public snapshot.
- Publishes the JSONL row and a sidecar receipt create-exclusively as one owned
  pair. A pre-existing final or path alias fails before overwrite; partial
  publication rolls back only files reserved by this invocation.

The sidecar binds the route candidate archive, evaluator/loader/engine
authority, candidate/opponent entry fingerprints, seed/seat/RNG seed,
step-144 snapshot digest, full-game trace digest, and exact horizon. It records
`private_observation_persisted=false`.

## Example: R07

Use the canonical merged route carrier to materialize plan 7, then run one
native cell through the observer bridge:

```bash
python -B route_matrix_row_receipt.py \
  --evaluator /.../reference/evaluator/evaluate.py \
  --engine-dir /.../reference/engine \
  --loader /.../20260907-offline-agent/evaluate.py \
  --candidate /.../plan7-adapter.py::agent \
  --candidate-entry-sha256 <authenticated-adapter-sha256> \
  --route-manifest /.../plan7-manifest.json \
  --opponent-label apex_v7 \
  --opponent /.../opponents/apex_v7/adapter.py::agent \
  --opponent-entry-sha256 e7b78d4b9e2fc7a68528e45f876a68b50d364103ebd5bf5f2dbbf68770bf54f5 \
  --seed 1209131101 --seat 0 --plan-index 7 \
  --row-out /.../r07-s1209131101-apex-s0.jsonl \
  --receipt-out /.../r07-s1209131101-apex-s0.receipt.json
```

The resulting row is directly consumable by `p04_route_ranker.py` after all
R00-R12 rows for the same `(seed, opponent, seat)` have landed.

The route discovery matrix is research evidence only. P04 keeps
`policy_ready=false`; any runtime selector still needs a predeclared observable
rule and fresh held-out native games.
