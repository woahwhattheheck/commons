# ROUTEMOTION — source-bound fixed-tape motion census

This lane is **research-only and policy-inert**. It measures a narrow class of main-farmer locomotion rewrites in the canonical V4 fixed tapes under the exact official-engine and router semantics pinned by the census.

It does **not** create a worker planner, alter HIRE cadence, compete with LABORFLOW, or mutate runtime/default/archive/Kaggle bytes.

## The source theorem

The pinned official engine gives actor 0 an exact position with four directional movement operations. Movement only changes that position. At end of day actor 0 resets to the canonical shed-access spawn. The interpreter executes unit actions before market processing.

One market operation is special for this proof: `HIRE`. A successful HIRE calls `_spawn_hand()`, and spawn selection observes the current farmer/hand positions. Therefore a transient farmer detour can change later worker geometry if it crosses a HIRE.

`route_motion_census.py` distinguishes two different authorization classes:

1. **Individual boundary no-op.** An out-of-bounds movement is already an engine no-op and is individually equivalent to `PASS`.
2. **Atomic closed-loop rewrite.** A same-day actor-0 loop is jointly removable only when:
   - actor 0 returns to the exact starting tile;
   - every actor-0 row inside the loop is only MOVE or PASS;
   - no callback in the loop contains a HIRE market row; and
   - **every movement row in that listed closed interval is rewritten together**.

For case (2), no single row inherits the loop theorem. A two-row `EAST -> WEST` loop is the simplest predecessor: replacing either row alone leaves actor 0 displaced. Only the complete interval is source-equivalent to replacing its movement rows with `PASS`.

The census deliberately emits **non-overlapping atomic intervals** rather than every nested geometric loop. Downstream consumers must use `closed_hire_free_motion_loops[*].movement_rows` as indivisible rewrite groups. `individually_pass_equivalent_movement_rows` contains only true single-row boundary no-ops.

## Bound sources

At authoring time the tool pins:

- official engine Git blob `3c202c7ee921da239356789e266b694635103fc4`;
- canonical 13×719 tape bank Git blob `a43289b9cc5e34a2481fddf652762a7d92f427ef`;
- canonical R04 router Git blob `a3e2fe87c717d128e43c9b65bae2265f40d1d76d`.

It also requires exact engine/router semantic anchors and fails closed on source drift.

The effective route is reconstructed exactly as the live R04 router does:

- steps `0..143`: plan 0;
- steps `144..647`: selected plan;
- steps `648..718`: plan 2.

All 13 possible selected plans are censused.

## Run

From the repository root:

```bash
V4=revenue/kaggriculture/cloud-execution-lab/candidates/v4
python -B "$V4/research/route-motion/route_motion_census.py" \
  --output /tmp/titan-v4-route-motion.json

python -B -m unittest -q \
  "$V4/research/route-motion/test_route_motion_census.py"

python -O -B -m unittest -q \
  "$V4/research/route-motion/test_route_motion_census.py"
```

The v2 output reports per route:

- total authored actor-0 movement rows;
- market callbacks containing HIRE;
- individually PASS-equivalent out-of-bounds movement no-ops;
- closed hire-free movement intervals as atomic rewrite groups;
- the union of movement rows participating in those groups for census/counting only.

## Ownership / next gate

This packet is evidence for existing route/composition owners. LABORFLOW keeps generic productive hand assignment and redundant-HIRE economics. HERDSCALE keeps animal-throughput scaling. The canonical graph/postimage runner remains the only composition sink.

If the current tapes contain admitted rows, the next useful step is a **source-pinned tape transform plus current-native replay**, not a new scheduler. The transform must preserve the exact row multiset outside individually authorized boundary no-ops and complete atomic loop groups; it must never consume a strict subset of a loop group. Current-native both-seat economics must run before any activation claim.

If the census returns zero admitted rewrites, land that as useful negative evidence and do not invent a movement policy.

## Not claimed

- hand/worker path optimality;
- opportunity incidence after all current-native runtime repairs;
- economic or competitive uplift;
- runtime activation;
- default promotion;
- archive replacement;
- Kaggle submission.
