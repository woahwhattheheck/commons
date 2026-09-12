# TITAN V4 — represented-market executability salvage

Status: **PRESERVED DONOR CHAIN / CURRENT-ROOT DEFECT CONFIRMED / NOT YET PRODUCTION-PATCHED**

Canonical workspace: `revenue/kaggriculture/cloud-execution-lab/candidates/v4` on `main`.

This packet preserves a correctness family that was completed as separate V3 donors but was never consumed into the current V4 scheduler. It is deliberately recorded on the sole V4 integration line instead of creating another V4 branch.

## Current-root witness

Fresh audit of current production scheduler source found Git blob:

- `revenue/kaggriculture/cloud-execution-lab/scheduler.py`
- Git blob `a483b24dd72b580d7d8811636b54d2d44f391575`

`SellScheduler.receipt_profile()` still replays authored market intent as if it physically executed. In particular, after choosing the current/future market rows it still contains the equivalent of:

```python
elif o[0] in ('BUY_PRODUCT','BUY_ANIMAL') and len(o)>2:
    p['shed'][o[1]] = p['shed'].get(o[1], 0) + int(o[2])
elif o[0] == 'HIRE':
    f['hands'].append(m._spawn_hand(f, len(f['tiles'])))
    p['inventories'].append({})
```

Those projections do not establish official fill legality, available cash, shed capacity, sequential per-unit early stop, or HIRE affordability before mutating represented physical state. A represented purchase/HIRE can therefore manufacture goods or an actor that the official interpreter would reject, and that fabricated state can influence SELL feasibility/horizon decisions.

The already-preserved scheduler-prefix repair is necessary but not sufficient: slicing to the official executable raw prefix removes inert suffix rows, while **in-prefix** purchase/HIRE physical executability remains a separate seam.

## Exact donor chain to consume

Preserve the original ownership split and composition order; do not paste any stale whole-file postimage over V4.

1. **#12056 — raw executable-prefix inputs**
   - head `5d1b376d33858dd827e7e20051cc49648d313034`
   - removes out-of-prefix current/future market rows from represented-horizon inputs only;
   - explicitly does not prove purchase fills or in-prefix HIRE execution.

2. **#12110 — represented purchase executability / phantom-fill closure**
   - transport head `247fa31fd364f0819cb9956f93f3501fb5043461`
   - binds official interpreter blob `3c202c7ee921da239356789e266b694635103fc4`;
   - kills zero-cash `BUY_PRODUCT WHEAT`, illegal `BUY_PRODUCT CARROT`, zero-cash `BUY_ANIMAL GOOSE`, and full-shed animal phantom fills;
   - its own declared composition order is #12056 -> #12110 -> #12055 -> one shared official transition model.

3. **#12055 — in-prefix HIRE physical executability**
   - current exact head `cdd76008c34d27e84df315365200fdec26275ab6`;
   - proven-HIRE materializer blob `2b1f128d0d406e5ba5eac619817ae6e73e0a4edc`;
   - only spawns a represented hand when a conservative copied-cash lower bound proves the Fibonacci-scaled HIRE can execute;
   - ignores uncertain SELL credit and invalidates later-HIRE cash proof after unproven purchases.

The V3 donor family explicitly stopped short of claiming a complete two-player official-transition model. V4 consumption must retain that boundary rather than promoting any one donor as if it closed the entire scheduler.

## Relationship to current V4 scheduler-prefix work

Canonical main already preserves the current-root executable-prefix repair under `candidates/v4/repairs/gameplay/scheduler-prefix/` (main receipt commit `3cb388d0c989edc4a088e504054feac030af3b37`). That repair owns raw-prefix slicing for `cash_reserve()` / `receipt_profile()` only.

A separate current owner has also claimed the remaining uncapped `SellScheduler.act` baseline/reference/output consumers. Do not duplicate that action-prefix lane here.

This packet owns only the still-unconsumed **physical execution semantics inside the admitted represented prefix** and the exact historical donor provenance needed to build the current-root closure.

## Required current-root composition gate

Before production adoption, build one current-main source-bound repair that:

- composes after the raw-prefix helper rather than replacing it;
- models only official-executable `BUY_PRODUCT`, `BUY_ANIMAL`, and `HIRE` effects, including product legality, cash, price/fill sequencing, shed capacity, HIRE cost and actor creation;
- preserves inactive suffix bytes/indexes and does not compact queues;
- derives represented physical state from one bound prestate in official row order;
- fails closed on malformed/coerced values rather than manufacturing state;
- carries predecessor-killing witnesses from #12056/#12110/#12055;
- proves that any changed SELL decision is causally attributable to the corrected represented poststate;
- runs normal and `python -O` focused tests against exact current source + exact official engine bytes;
- remains source/test evidence until the then-current one-tree gameplay gate admits the composed repair.

## Explicit non-goals

- No feature/default flip.
- No legacy V3/V3.1/V4 ref movement.
- No execution of legacy `apply_v4.py` against current production.
- No duplicate scheduler-prefix or scheduler-action-prefix carrier.
- No claim that #12055's old `HOLD_FOR_PAIRED_PANEL` alone authorizes current V4 production.
- No Kaggle/provider/submission action.

This file exists so the exact correctness work cannot be lost again while the current-root implementation is recomposed safely on the single V4 line.
