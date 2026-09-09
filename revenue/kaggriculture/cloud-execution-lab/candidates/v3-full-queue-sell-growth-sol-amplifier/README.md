# TITAN V3 saturated-queue same-product SELL expansion — SOL-AMPLIFIER

Operation: `titan-v3-full-queue-same-product-sell-growth-20260909-sol-amplifier-01`

## Source-proven regression

Submitted V1 could replace its first inherited SELL row for a selected product
with the full current scheduled quantity. Submitted V2 added index-preserving
materialization, but also capped every inherited SELL row to its original
quantity and rejected `q > offered` whenever the raw market list had reached the
per-turn order limit. Current V3's actual selected consumer retains both halves
in `frozen_selected.py`.

That combination treats quantity and position capacity as the same resource. A
10-row queue that already contains `SELL CARROT 1` can execute `SELL CARROT 5`
in exactly that row without adding or moving an order, yet current V3 forbids
the planner from selecting it and forbids the emitter from materializing it.
The lost four units can be lost same-turn cash, especially before inherited
fixed acquisitions.

## One-factor boundary

`growth_patch.py` reuses the exact canonical `FrozenSelected.transform` code
object with a private globals table. Only its `optimize_lot` and
`materialize_sales` global lookups are replaced:

* the capacity callback may relax `q > offered` only when the list length is
  exactly the configured maximum and a positive same-product SELL row already
  exists;
* the emitter adds only the selected excess to that first row, preserving every
  existing row quantity, unrelated row, list length, and index;
* queues below the cap, queues above the cap, blank-only opportunities, new
  products, receipt/capacity failures, and all unrelated plans delegate to the
  canonical functions.

The canonical instance's exact `_initialize` code object is also reused with a
function-private builtins table. Its sole import override returns a private view
of `frozen_selected` containing the candidate class. Neither the canonical
module binding nor `sys.modules` is changed, even transiently. The resulting
consumer owns a private transform function; sibling controls and future plain
constructions remain untouched. Canonical `main.py::agent`, its whole-call
timer, fallback, reconstruction, production guards, funding reorder, final
pressure, and release files are unchanged.

## Gates

Focused tests include the predecessor-failing 10-row witness, absent-row and
receipt-failure rejections, below-cap parity, overlong-queue containment,
duplicate-row/index preservation, stock clipping, private-global isolation,
private-import reconstruction, exception containment, no module-cache mutation, and source custody. The
path-scoped workflow also verifies the canonical release build, then runs an
identical-cell official-engine baseline/candidate screen against submitted V1,
Arlene, Apex, and Public BT12 in both seats. Own cash is primary; a green
workflow is not a leaderboard claim, and retained JSON/markdown is the verdict.
