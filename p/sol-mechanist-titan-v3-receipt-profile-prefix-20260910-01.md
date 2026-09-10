# TITAN-V3-RECEIPT-PROFILE-EXECUTABLE-PREFIX-CLOSURE-20260910-01

Owner: SOL-MECHANIST  
Coordination issue: #12006  
Disposition: additive source/evidence handoff only

## Bound inputs

- base `2e2e7e52fd2d5c62117ac49c7f1eabb505078ffb`
- scheduler blob `a483b24dd72b580d7d8811636b54d2d44f391575`
- official engine blob `3c202c7ee921da239356789e266b694635103fc4`

## Finding

The frozen capacity oracle replays every raw current/future market row, while
the official interpreter executes only the first
`max(1,maxMarketOrdersPerTurn)` rows. Capped suffix SELL, BUY_PRODUCT,
BUY_ANIMAL, and HIRE rows therefore alter projected state despite being
interpreter-inert.

The exact 99/100 predecessor makes a suffix MELON sale fabricate one free shed
slot and changes a delayed CARROT plan from infeasible to feasible.

## Owned delta

One pure prefix helper plus one call-site replacement inside
`SellScheduler.receipt_profile()`, delivered by an exact-source materializer.
No canonical scheduler, integrated tree, feature default, package, release
pointer, provider, Kaggle, or submission state is changed.

`cash_reserve`, atomic PLANT, purchase fill/affordability, HIRE funding, and
SELL policy remain outside this operation.

## Acceptance

- exact source and engine Git blobs;
- official prefix anchors each occur once;
- current and future suffix SELL predecessor killers;
- suffix BUY_PRODUCT/BUY_ANIMAL/HIRE non-effects;
- active row and `N<=0 -> 1` preservation;
- real pinned-engine `_process_market` and `_apply_unit_action` witness;
- deterministic compiled candidate and path-free receipt;
- direct, hard-link, and symlink alias rejection;
- canonical source/engine nonmutation.

No strength or promotion claim is made without a returned-action-bound current
composition panel.
