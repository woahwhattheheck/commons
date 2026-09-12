# TITAN V5 route-matrix row receipt

This is the **observation/receipt bridge** between the merged shared route carrier
(`#13475`) and the merged P04 reducer (`#13478`). It is not a second evaluator,
route-force harness, or runtime selector.

`route_matrix_row_receipt.py` is the fail-closed public facade. The already
reviewed row/snapshot logic is preserved byte-for-byte in
`_route_matrix_row_receipt_core.py`; `route_matrix_candidate_custody.py` adds the
candidate execution binding that the first revision lacked.

The bridge:

- SHA-verifies the pinned official native evaluator (`e30b3108...`) and engine
  loader (`61093af2...`) before execution.
- Consumes a shared `build_route_matrix.py` manifest and accepts only the
  step-144 matrix (`selection_step=144`, one changed `r04_full_router.py`,
  production-v3 baseline `20f20116...`, router preimage `41ea55c5...`).
- Requires both the route-candidate archive and its materialized root. It
  single-reads every materialized member, rejects symlinks/extras/missing files,
  and checks every SHA against `manifest.files`.
- Decodes the candidate tar through the exact SHA-pinned `build_delivery.members`
  parser used by the canonical route builder (`build_delivery.py` SHA256
  `29b9584e...`). That parser authenticates the archive SHA and rejects
  non-files, duplicate/noncanonical paths, traversal and backslashes. The bridge
  then requires the archive member SHA map to equal `manifest.files` **and** the
  decoded archive bytes to equal the captured executable root byte-for-byte.
  An archive-A/root-B pair therefore cannot authorize a row.
- Publishes those authenticated captured bytes into a private snapshot and
  executes that snapshot through the pinned Kaggle file-agent contract
  `cloud-pack/official.py` (SHA256 `65fe4058...`). This prevents a row from being
  mislabeled with one plan manifest while the evaluator actually executes a
  different extracted candidate tree.
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
- Re-authenticates the private candidate snapshot and official file-loader path
  after the game, runs the produced row through `p04_route_ranker.normalize_row()`,
  and SHA256-binds its canonical public snapshot.
- Publishes the JSONL row and sidecar receipt through the ONE merged V5 shared
  `selective-carrot/publication_custody.py` primitive (SHA256 `547e733b...`).
  Final paths are create-exclusive, all are reserved before payload writes,
  success re-authenticates pathname/payload identity, and rollback only removes
  this invocation's still-owned finals while reservation FDs remain live.

The sidecar binds the route candidate archive, full materialized-file manifest,
archive/root byte identity, evaluator/loader/engine authority, generated
private-snapshot adapter, pinned file-loader authority, opponent entry
fingerprint, seed/seat/RNG seed, step-144 snapshot digest, full-game trace
digest, and exact horizon. It records `private_observation_persisted=false`.

## Example: R07

```bash
python -B route_matrix_row_receipt.py \
  --evaluator /.../reference/evaluator/evaluate.py \
  --engine-dir /.../reference/engine \
  --loader /.../20260907-offline-agent/evaluate.py \
  --official-file-loader /.../cloud-pack/official.py \
  --candidate-root /.../plan7-payload \
  --candidate-archive /.../plan7.tar.gz \
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

This bridge upgrades **candidate** custody by executing an authenticated private
snapshot. It does not independently snapshot the opponent executable closure;
the native executor must continue to use the authenticated/owned opponent tree
required by the existing #13468 authority.

The route discovery matrix is research evidence only. P04 keeps
`policy_ready=false`; any runtime selector still needs a predeclared observable
rule and fresh held-out native games.
