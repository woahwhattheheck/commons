# ROUTEMOTION — source-bound fixed-tape motion census

This lane is **research-only and policy-inert**. It measures a narrow class of main-farmer locomotion rows in the canonical V4 fixed tapes that are provably equivalent to `PASS` under the exact official-engine and router semantics pinned by the census.

It does **not** create a worker planner, alter HIRE cadence, compete with LABORFLOW, or mutate runtime/default/archive/Kaggle bytes.

## The source theorem

The pinned official engine gives actor 0 an exact position with four directional movement operations. Movement only changes that position. At end of day actor 0 resets to the canonical shed-access spawn. The interpreter executes unit actions before market processing.

One market operation is special for this proof: `HIRE`. A successful HIRE calls `_spawn_hand()`, and spawn selection observes the current farmer/hand positions. Therefore a transient farmer detour can change later worker geometry if it crosses a HIRE.

`route_motion_census.py` admits a movement row only when one of these source-level statements is true:

1. the move is out of bounds and the engine already makes it a unit no-op; or
2. it belongs to a same-day closed actor-0 motion loop where:
   - actor 0 returns to the exact starting tile;
   - every actor-0 row inside the loop is only MOVE or PASS;
   - no callback in the loop contains a HIRE market row.

For case (2), replacing the admitted movement rows with PASS preserves actor-0 position at the loop exit and cannot change any unit-side tile/shed mutation inside the interval because there is none. The no-HIRE guard excludes the only market path whose spawn result consumes transient farmer position.

The census deliberately emits **non-overlapping** safe intervals rather than every nested geometric loop.

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

The output reports per route:

- total authored actor-0 movement rows;
- market callbacks containing HIRE;
- out-of-bounds movement no-ops;
- closed hire-free movement intervals;
- the exact movement row indices proved PASS-equivalent.

## Ownership / next gate

This packet is evidence for existing route/composition owners. LABORFLOW keeps generic productive hand assignment and redundant-HIRE economics. HERDSCALE keeps animal-throughput scaling. The canonical graph/postimage runner remains the only composition sink.

If the current tapes contain admitted rows, the next useful step is a **source-pinned tape transform plus current-native replay**, not a new scheduler. The transform must preserve the exact row multiset outside admitted actor-0 movement rows and must re-run current-native both-seat economics before any activation claim.

If the census returns zero admitted rows, land that as a useful negative result and do not invent a movement policy.

## Not claimed

- hand/worker path optimality;
- opportunity incidence after all current-native runtime repairs;
- economic or competitive uplift;
- runtime activation;
- default promotion;
- archive replacement;
- Kaggle submission.
