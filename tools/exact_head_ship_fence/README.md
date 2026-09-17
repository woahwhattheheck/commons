# Exact-head ship fence

`tools.exact_head_ship_fence` is a dependency-free, evidence-only compiler for the last GitHub handoff before a guarded merge. It exists because an apparently ready PR can become unsafe when the PR head moves, `main` moves, hosted checks are queued/cancelled/stale, or a review belongs to an older head.

The tool **does not query GitHub and does not authorize a merge**. It consumes a retained snapshot assembled from provider observations, validates the snapshot strictly, and emits exactly one deterministic verdict plus one deterministic next action. `READY_TO_MERGE_EVIDENCE` means only that the retained packet satisfies this v1 evidence policy; the next action is deliberately `MERGE_AFTER_LIVE_RECENSUS`, never `MERGE`.

## Verdicts

- `READY_TO_MERGE_EVIDENCE`
- `HOLD_HEAD_MOVED`
- `HOLD_BASE_MOVED`
- `HOLD_CI_UNKNOWN`
- `HOLD_CI_RED`
- `HOLD_REVIEW_STALE`
- `HOLD_TOPOLOGY_UNKNOWN`
- `HOLD_INCOMPLETE_EVIDENCE`

The only next actions are `MERGE_AFTER_LIVE_RECENSUS`, `REJOIN_CURRENT_MAIN`, `WAIT_FOR_CI`, `REPAIR_CI`, `REREVIEW_EXACT_HEAD`, `REFRESH_TOPOLOGY`, and `REFRESH_EVIDENCE`.

## Snapshot contract

The root packet binds:

- repository and base branch;
- expected PR head and currently observed PR head;
- construction parent and current literal base head;
- bounded provider-observation time, a snapshot-completeness flag, and explicit existence of the PR/base refs (dangling refs reject);
- candidate changed paths, intervening base-delta paths, evaluated base SHA, and explicit rejoin evidence;
- a closed check policy plus exact-head hosted check observations;
- a closed review policy plus review verdicts tied to exact commit SHAs.

Candidate/base paths are canonical sorted relative paths with optional Git blob SHA-1s. `snapshot_complete=false` is a first-class HOLD, not an invitation to guess. Provider facts remain caller-retained evidence; this package does not authenticate GitHub independently.

### Moving `main`

If `construction_parent != current_base_head`, the packet cannot pass merely because a human says the drift is harmless. V1 requires all of:

1. candidate paths known;
2. intervening base-delta paths known;
3. those sets are disjoint;
4. `rejoin_proven=true`;
5. `evaluated_base_sha == current_base_head`;
6. `rejoin_head_sha == current_pr_head`.

Disjoint-but-not-rejoined remains `HOLD_BASE_MOVED`. Path overlap remains `HOLD_BASE_MOVED` even after a claimed rejoin because this v1 fence intentionally refuses to infer semantic conflict resolution from a path overlap.

### Hosted checks

Required checks are green only when the exact current head has `status=COMPLETED` and `conclusion=SUCCESS`, or `SKIPPED` when that exact check policy explicitly sets `allow_skipped=true`.

`QUEUED`, `IN_PROGRESS`, `MISSING`, `CANCELLED`, `NEUTRAL`, and policy-unapproved `SKIPPED` are UNKNOWN. Missing required observations are UNKNOWN. `FAILURE`, `TIMED_OUT`, and `ACTION_REQUIRED` are RED. Optional checks are retained but do not block the v1 gate.

A check observation tied to another head is rejected as cross-head evidence rather than silently reused.

### Reviews

A review on head A never authorizes head B. The packet can require N exact-head PASS reviews. Stale-head reviews do not count. An exact-head STOP produces `HOLD_REVIEW_STALE` with reason `EXACT_HEAD_REVIEW_STOP`; this taxonomy intentionally uses the review hold class for both stale/missing positive review and a current STOP because v1 has no separate `HOLD_REVIEW_RED` state.

## Strict boundary

JSON ingestion rejects duplicate keys, floats/non-finite values, unsafe integers, invalid Unicode scalars, unknown fields, malformed SHAs, duplicate identities, impossible check state/conclusion pairs, future/stale observations, and non-plain Python container subclasses. Public current compilation captures its UTC clock at initialization; ordinary module-global rebinding cannot substitute a historical clock.

A report is self-hashed, but self-hashing is not semantic verification. `verify_current()` first exact-recompiles the complete report at its recorded evaluation second, then re-evaluates the source packet against current process UTC. A semantically modified-and-resealed report fails.

## CLI

Compile into a create-exclusive two-file bundle:

```bash
python -m tools.exact_head_ship_fence compile snapshot.json out/ship-fence
```

The output directory must not already exist. It contains canonical `report.json` and deterministic `report.md`.

Verify the source plus both projections:

```bash
python -m tools.exact_head_ship_fence verify snapshot.json out/ship-fence
```

Domain/input failures return exit code `2` without a traceback. Input leaves are opened as regular files with a final-component no-follow fence where the platform supports it.

For a fresh synthetic example that performs no provider call:

```bash
python -m tools.exact_head_ship_fence.demo
```

## Authority ceiling

Every report hard-codes false for merge, ref mutation, review mutation, provider mutation, outbound, spend, payment, and revenue-recognition authority. A READY report is evidence for a human/finalizer to run a **fresh live recensus**; it is never a capability or permission to mutate GitHub.

## Proof

Run the focused suite in normal and assertion-disabled interpreters:

```bash
python -m unittest -v tools.exact_head_ship_fence.test_fence
python -O -m unittest -v tools.exact_head_ship_fence.test_fence
python -m py_compile tools/exact_head_ship_fence/*.py
```

The suite retains clean-ready, moved-head, moved-base/rejoin, topology-unknown, queued/cancelled/skipped/red CI, stale/STOP review, incomplete snapshot, strict-JSON/runtime hostiles, cross-head transplant, receipt reseal, current-clock rebinding, and create-exclusive CLI cases.
