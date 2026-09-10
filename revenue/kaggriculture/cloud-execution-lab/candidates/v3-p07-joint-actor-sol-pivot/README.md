# TITAN V3 P07 — exact pair-atomic joint actor integration

Operation: `TITAN-V3-P07-JOINT-ACTOR-INTEGRATION-20260910-01`

This additive candidate closes two gaps in the previous P07 runtime witness:

1. the September 9 candidate completed 384 official games with exact score
   identity but logged **zero live swaps**, and its no-op telemetry sampled only
   hour 23; and
2. its continuation plans entered canonical `SpatialTempo.finish`, whose normal
   contract accepts actors independently.  A later one-sided unit rewrite could
   therefore retain half of a nominally atomic route exchange.

## One owned mechanism

P07 does not invent a route, buy an actor, repair a HIRE shortfall, reorder
same-turn local operations, or touch market orders.  After the existing
SpatialTempo transform, it enumerates a bounded family of already-existing
actor pairs and same-day horizons.  Every proposal is delegated to the merged
`joint_assignment.propose_pair_swap` authority.  That authority requires:

- empty starting cargo for both actors;
- complete `PICKUP -> service -> DROP` bundles;
- inherited event steps and each actor's original continuation endpoint;
- no market row, checkpoint, hour-23 reset, partial pickup, event no-op, or
  unsupported action;
- fewer total travel moves; and
- exact equality of final public farm and private inventory/shed state under
  sequential official mechanics.

The adapter additionally rejects current route/action mismatch, actors already
owned by spatial/crop/stock continuations, and ambiguous top-ranked proposals.

## Pair-atomic publication

All changed rows and both plan dictionaries are built before shared state is
mutated.  Two later boundaries then enforce custody:

- `guard_returned` keeps both candidate current actions or restores both exact
  pre-P07 actions; one-sided interpreter exposure is impossible.
- `finish` verifies that the committed continuation contains both pair members
  or neither.  A defensive backstop removes a hypothetical half commit and
  restores the prior pair plans while retaining unrelated actors' commits.

Reconstruction reuses canonical `_initialize`; the hook is installed again on
the reconstructed SpatialTempo object.  Canonical `main.py`,
`TITAN-CONFIG.json`, source/archive manifests, release pointers, and submitted
artifacts are unchanged.  The future one-tree key is `p07_joint_actor` and is
default-off; only `candidate.py` enables it for this development screen.

## Evidence gate

The path-scoped workflow runs focused atomicity contracts, verifies the
canonical integrated build remains unchanged, and executes a paired
official-engine census against Arlene and submitted V1 on fixed seeds and both
candidate seats.  The evaluator hashes all 719 candidate-seat actions
immediately before interpretation.  P07 emits an append-only record for every
candidate step, not merely hour 23.

A result can advance only when a pair is proposed and committed, a
pre-interpreter action sequence changes, every score change is action-bound,
no half commit is observed, mean own cash and margin are positive, and every
opponent/seat own-cash stratum is nonnegative.  Otherwise the exact result is a
rejection, not a strength or leaderboard claim.

No provider call, paid compute, Kaggle upload, canonical promotion, or
submission is performed by this branch.
