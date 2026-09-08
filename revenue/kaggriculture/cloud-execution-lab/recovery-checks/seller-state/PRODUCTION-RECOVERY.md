# Completed frozen-seller recovery after a selected-action deadline

This change preserves only the last **completed** frozen-seller state when a later
complete parent selection becomes the timer-owned fallback before its seller
transform can finish. It does not serialize an interrupted seller computation.

The checkpoint contains `planned`, `pending`, `previous`, and
`observed_harvests`. On the next fresh initialization it is restored only when a
selected fallback armed recovery, then the skipped public observation is passed
to the unchanged seller observer exactly once and becomes `previous`.

No checkpoint is consumed after an interrupted producer, a first-call selected
cancellation without a prior completed action, a foreign `DeadlineExceeded`,
ordered mode, or terminal-history mode. Route recovery remains the existing
separate mechanism.

## Source-bound result

The unchanged PR10365 checker reproduced the current `f623c088...` defect:
step-450 fallback and route were equal, but sales at 451 and 453 disappeared.
With the candidate runtime, transform-entry, post-observer, and transform-return
cancellations at step 450 all preserve complete action and seller-state
continuity through step 718. The step-447 interrupted-replanning negative retains
its differences at 449 and 453, proving the patch does not commit unreturned
seller planning.

Three uninjected fresh-process pairs execute 718 calls per actor. All 2,154
original/candidate action pairs and all tracked seller-state pairs match exactly.
The alternating timings are retained only as a regression screen; no performance
or deployment-latency claim is made.

Six new focused methods and 25 existing worker, entry-clock, module, route, seed,
and history methods pass. Full report identities and exact source/package pins
are in `PRODUCTION-RECOVERY.json`. The retained workload is one own-observation
stream, not a game, natural timeout, strength sample, or engine replay.
