# SOL-PRO — executable frozen cross-product slot reservation

- Operation: `TITAN-V3-CROSS-PRODUCT-SLOT-EXECUTABLE-FROZEN-PORT-20260910-01`
- Slack claim: `1789079883.383819`
- Exact parent/donor: #12100 @ `47aa401c647f330cdd7acae31515e1351f557fad`
- Canonical runtime/config/source/archive/pointers: untouched
- Games/provider/Kaggle/promotion/merge: untouched

## Closure

The reviewed #12100 helper cannot affect selected V3 by itself: the package
selects `consumer=frozen`, and `FrozenSelected.transform()` owns a copied
product-local `feasible(plan)` predicate. The underscore donor helper is also
excluded by `from scheduler import *`.

This additive stack authenticates and materializes the exact #12100 scheduler
postimage, then connects the one copied frozen predicate to
`scheduling._planned_slot_reservations`. The helper remains single-sourced.

The retained causal probe constructs the exact selected consumer through
`TitanAgent` and reproduces the nine-row predecessor: MILK is admitted and
marked chosen, CARROT consumes row ten, and MILK disappears from the returned
market. The repaired postimage rejects that MILK plan before selection. Two-free
row and inherited-MILK controls remain admitted and emitted; overdue future and
malformed-ledger controls fail closed.

T08 owns one-tree adoption and any official game/promotion disposition.
