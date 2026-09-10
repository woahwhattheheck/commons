# SOL-RECONCILE — E11 pending-target reconciliation

Operation: `TITAN-V3-E11-PENDING-TARGET-RECONCILIATION-20260910-01`

Exact input: Slack file `F0C0JPCAAQP`, `v3_candidates_657b3d9c.tar.gz`, 27,500 bytes,
SHA-256 `f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728`.

## Lineage

This is a V3 composition regression against the queue/checkpoint coupling requirement already
established during review of GitHub PR #11460. Review `3390668066` identified that E11 queue
edits and persistent pending state had to move and roll back together; follow-up review
`3391105708` recorded that blocker as closed in the earlier carrier. The current packet places
E11 before pending accounting, but still feeds that accounting the pre-edit `targets` map. This
carrier credits that prior finding and supplies the missing target reconciliation plus a direct
predecessor-killing witness.

## Defect

The predecessor inserts E11 before seller pending bookkeeping but preserves the old local
`targets` map. When E11 blanks a SELL row in the emitted queue, the later
`for item,q in targets.items()` loop can still commit that absent sale into seller state.
The two-turn fixture demonstrates the divergence: turn one returns an empty WHEAT slot but
leaves WHEAT pending for turn two.

## Repair

`_v3_e11_before_pending` now returns `(action, frozenset(deferred_items))`. Both carried
seller anchors remove only those item keys from their local target map before pending
bookkeeping. The hook stages the candidate action, history, report, and deferred set before
committing any of them. An exception at any point returns the original action plus an empty
set, so the action and checkpoint cannot split.

The E11 trigger, threshold, lookback, future-absorption rule, queue indexes, quantities,
nondeferred targets, and all disabled/no-op behavior are unchanged.

## Evidence

The same 11-test harness run against the exact predecessor exits 1 with seven failures.
Applied to this repair, it exits 0 with 11/11 passing. It covers both seller variants,
duplicate same-item rows, nonmatching items, disabled/no-op/error paths, stale-state
immunity, a post-transform transactional failure, exact source anchors, and the two-turn
phantom-commit witness.

Apply with `patch -p1 < e11-pending-reconciliation.patch` at the exact packet root, then run:

```text
python -m unittest -v overlay/checks/test_v3_e11_pending_reconciliation.py
```

This packet does not modify canonical/package/pointer/provider/Kaggle/submission state and
makes no playing-strength claim. Current-head integration belongs to the one-tree publisher.
