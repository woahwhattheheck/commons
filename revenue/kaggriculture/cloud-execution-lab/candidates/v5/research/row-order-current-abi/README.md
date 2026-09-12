# TITAN V5 — submitted ROW_ORDER on the current selected-action ABI

This research carrier fills the **ROW_ORDER** slot that is distinct from
`r04_row_shed` in the submitted V3.1 winner. It is additive and default-off by
construction: nothing here is wired into production runtime/configuration.

## Exact authority

Submitted V3.1 source authority is commit
`a90d888f03987ef0b35cfd20ec3519c6144db08a`, with
`candidates/v3/overlay/r04_full_router.py` Git blob
`a3e2fe87c717d128e43c9b65bae2265f40d1d76d`.

That source defines two separate flags:

- `ROW_ORDER`: score each requested leading SELL by
  `(price_before - price_after) * requested_quantity` on the pinned default
  price curves, then stable-sort descending;
- `ROW_SHED`: when enabled later, change the score quantity to
  `min(requested, projected_shed)`.

The submitted inner order is H8/L3 → H4 → ROW_ORDER → ROW_SHED → evening flush
→ B5/JIT. Therefore a clean current-V5 decomposition is possible: this carrier
owns only requested-quantity ROW_ORDER; the independent row-shed owner may
rescore the same block later without a second producer or copied policy tree.

`test_source_authority.py` fetches the exact historical object with `git show`,
checks its Git blob, AST-extracts only `_RO_PARAMS`, `_RO_I0`, `_ro_shape`,
`_ro_price`, and `order_sells`, and compares current valid vectors directly to
those donor functions.

## Current-ABI tightening

The current interpreter has explicit executable-prefix/dead-row behavior that
should not be hidden by historical list cleanup. The adapter therefore:

- touches only the executable contiguous leading SELL block;
- treats falsey rows, nonpositive SELLs, and the first non-SELL as barriers;
- preserves the entire suffix and all quantities/worker actions;
- fails closed on malformed executable rows or ambiguous known-product market
  inventory;
- leaves the action unchanged when `configuration.marketParams` is a nonempty
  override, matching submitted ROW_ORDER's default-curve boundary;
- never reads shed stock and never calls a producer/controller.

Unknown products retain the submitted `impact = 0` behavior. Stable ties retain
exact incumbent relative order.

## Focused verification

From this directory:

```bash
python -m py_compile row_order_current.py test_row_order_current.py test_source_authority.py
python -B -m unittest -v test_row_order_current.py test_source_authority.py
python -O -B -m unittest -v test_row_order_current.py test_source_authority.py
```

Dedicated PR CI checks out and asserts the exact event head with full history so
the submitted Git object is available.

## Promotion boundary

This is source recovery, not evidence that current V5 is stronger. After source
and composition review it should feed the one R04 convergence manifest with
economics `PENDING`, then participate in the fully assembled current-V5 matched
both-seat economics/champion gate. No default, release pointer, archive, or
Kaggle authority is granted here.
