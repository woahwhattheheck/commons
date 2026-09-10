# TITAN V3 P07 — exact pair-atomic joint actor integration

Operation: `TITAN-V3-P07-JOINT-ACTOR-INTEGRATION-20260910-01`

This additive candidate repairs four concrete defects in the earlier P07 lane:

1. the September 9 candidate completed 384 official games with exact score
   identity but accepted **zero live swaps**, while its no-op telemetry sampled
   only hour 23;
2. its continuation plans entered canonical `SpatialTempo.finish`, whose normal
   contract accepts actors independently, so a late one-sided unit rewrite could
   retain half of a nominally atomic exchange;
3. its blanket current-market veto excluded a source-proven reachable boundary:
   all actors already present execute before current-row `HIRE` appends a new
   hand; and
4. merely hiding that HIRE from a unit-only simulator is unsound across a
   multi-step horizon. HIRE spawn observes the changed current positions, and
   the appended actor participates from the next turn onward.

## One owned mechanism

P07 does not invent a route, buy an actor, repair a HIRE shortfall, reorder
same-turn local operations, or edit market orders. After the existing
SpatialTempo transform, it enumerates a bounded family of already-existing
actor pairs and same-day horizons. Every first-stage proposal is delegated to
merged `joint_assignment.propose_pair_swap`, which requires:

- empty starting cargo for both actors;
- complete `PICKUP -> service -> DROP` bundles;
- inherited event steps and each actor's original continuation endpoint;
- no future market row, checkpoint, hour-23 reset, partial pickup, event no-op,
  or unsupported action;
- fewer total travel moves; and
- exact equality of final public farm and private inventory/shed state under
  sequential unit mechanics.

The adapter additionally rejects current route/action mismatch, actors already
owned by spatial/crop/stock continuations, and ambiguous top-ranked proposals.

## Current-HIRE theorem plus full replay

`p07_current_hire.py` consumes SOL-CROSSWIND PR #11975 only for the exact
interpreter-order theorem: pre-action actors execute before market processing.
It admits only an exact active-prefix queue of `None`, `[]`, and `["HIRE"]`,
freezes the pre-action actor count, preserves the complete market queue and any
bounded current new-actor action tail, and leaves every future market row as a
hard boundary.

That theorem is followed by a second certificate before publication. The
adapter replays baseline and candidate through the entire proposed horizon with:

- official actor order and atomic PLANT-demand handling;
- exact current HIRE cost/spawn/appended-inventory mechanics;
- dynamically increased actor count on later turns;
- unchanged future actions for every non-pair and newly appended actor; and
- exact final farm/private equality.

A spawn, resource, tile, inventory, or new-actor interaction mismatch restores
all original route row objects and pre-proposal SpatialTempo state. The
provisional exact-unit trace line is withheld until this second certificate
resolves, so a replay rollback is emitted once as a rejection and
can never be counted as an activation.

## Pair-atomic publication

All changed rows and both plan dictionaries are built before shared state is
mutated. Three boundaries then enforce custody:

- `guard_returned` keeps both candidate current actions or restores both exact
  pre-P07 actions;
- a current-HIRE proposal also binds the complete final returned market queue,
  so a later consumer cannot keep the pair after changing its replay premise;
- `finish` verifies that the committed continuation contains both pair members
  or neither. A defensive backstop removes a hypothetical half commit while
  preserving unrelated actors' commits.

Reconstruction reuses canonical `_initialize`; the hook is installed on every
replacement SpatialTempo controller. Canonical `main.py`, `TITAN-CONFIG.json`,
source/archive manifests, release pointers, and submitted artifacts are
unchanged. The future one-tree key is `p07_joint_actor` and is default-off; only
`candidate.py` enables it for this development screen.

## Evidence gate

The path-scoped workflow runs **24** focused atomicity, dynamic-HIRE, source-
binding, rollback-accounting, and fail-closed contracts. It hashes the complete
execution closure, including extracted `mechanics.py` and the pinned official
engine, then executes a paired official-engine census against Arlene and
submitted V1 on fixed seeds and both candidate seats. The evaluator hashes all
719 candidate-seat actions immediately before interpretation and logs every
candidate step.

A result can advance only when a replay-certified pair is proposed and
committed, a pre-interpreter action sequence changes, every score change is
action-bound, no half commit is observed, mean own cash and margin are positive,
and every opponent/seat own-cash stratum is nonnegative. Dormancy, replay
rollback, or regression is an explicit rejection, not a strength or leaderboard
claim.

No provider call, paid compute, Kaggle upload, canonical promotion, or
submission is performed by this branch.
