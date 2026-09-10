# TITAN V3 cross-product SELL-slot active-consumer closure

Operation: `TITAN-V3-CROSS-PRODUCT-SLOT-ACTIVE-CONSUMER-CLOSURE-20260910-01`

Slack claim: `1789080124.806719`

Exact base: `fcaba636557a112ac091ca9018bf0d4a689bf3cd`

Reviewed donor: draft PR #12100 at `47aa401c647f330cdd7acae31515e1351f557fad`.

## Why this successor exists

PR #12100 proves the shared market-row reservation theorem against
`scheduler.py`, but the configured V3 path defaults to `Features.consumer =
'frozen'`. `TitanAgent._initialize()` imports root `frozen_selected.py` and
constructs `FrozenSelected`; that class carries a copied product-local
`feasible(plan)` closure. The scheduler-only donor therefore cannot alter the
returned action of the active consumer.

The active predecessor can promise the final queue slot twice. With nine
inherited rows under a ten-row cap, a due CARROT excess row is already retained
in `self.planned`. MILK is evaluated independently, sees one apparently free
row, and is marked chosen. Final settlement appends products alphabetically:
CARROT consumes row ten and MILK is silently omitted. Optimizer diagnostics and
mutated future-plan state no longer describe the returned action.

## Closure

The materialized active postimage performs two related repairs:

1. Before a product-local plan uses an appended SELL row, reserve one shared row
   for each other product whose retained scheduler-owned excess is due by that
   date. Current rows reserve only when executable stock still exceeds inherited
   matching SELL capacity. Future and already-overdue retained rows reserve until
   cleanup retires them. Same-product replacement is excluded, multiple tranches
   of one product consume one row, and malformed internal ledgers fail closed.
2. After final materialization and same-turn funding reorder, certify that every
   selected due-now quantity is actually present in the returned market queue.
   A missing or malformed emission restores the incumbent `current` and
   `self.planned`, removes the detached `chosen` certificate, rematerializes the
   incumbent action, and records a bounded `selection_emission` fallback report.

## Executable witness

`active_witness.py` loads both the exact predecessor and materialized successor.
It injects each as the module selected by a real
`TitanAgent(Features(consumer='frozen'))` initialization, while replacing only
unrelated seed-budget and spatial services with inert controls. It then executes
`FrozenSelected.transform()` through that selected instance.

The deterministic witness requires all three discriminators:

- predecessor: MILK is `chosen`, but only CARROT is emitted;
- successor: the shared reservation rejects MILK before selection; and
- emission custody: under a deliberate post-selection emitter fault, the
  successor removes `chosen`, restores incumbent plan state, and returns only
  the incumbent CARROT row.

The exact-source materializer binds Git blobs for `frozen_selected.py`,
`scheduler.py`, `selected_sell_core.py`, and `titan_runtime.py`; verifies the
runtime import/constructor anchors; requires unique AST-parseable preimages; and
emits deterministic postimage and receipt hashes.

## Boundary

This is an additive direct-source carrier and executable proof. It does not
change the canonical runtime, configuration, archive, pointer, replay bank,
provider state, Kaggle state, merge state, or promotion decision. It consumes
#12100's reviewed theorem and leaves normalized excess-plan representation and
expired-plan cleanup under their existing owners. T08 retains one-tree
composition, complete-game evaluation, merge, publication, and submission.
