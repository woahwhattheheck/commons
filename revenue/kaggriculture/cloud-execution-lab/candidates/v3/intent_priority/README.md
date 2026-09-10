# TITAN V3 — intent-priority fresh-main port

**Operation:** `titan-v3-intent-priority-fresh-main-port-20260910-01`  
**Fresh base:** `main@175a844cb01bbb56cb9cc54c0097a489c4997275`  
**Status:** disconnected, default-off candidate carrier; not production policy.

## Admitted factor

Draft evidence carrier #11963 isolated one factor on frozen V2: preserve the full
all-positive-shed target domain and every target quantity, but traverse targets in
this order:

1. existing pending scheduler intent;
2. inherited baseline `SELL` first-seen order;
3. remaining `PRODUCTS` order.

The retained artifact `10168056904` has SHA-256
`528f7557a899c1376c8fe04ed328c70a17a760aa3a725e190710ea13ad7e13f8`.
Independent readback of its 32 paired cells re-derived 6 action-changing cells,
mean own-cash delta `+8.375`, median `0`, 6 positive / 26 zero / 0 negative
cells, mean margin delta `+6.25`, and no new losses. That evidence admits the
mechanism for porting; it does not establish current-main uplift.

## Port contract

`materialize.py` binds the exact current scheduler Git blob
`a483b24dd72b580d7d8811636b54d2d44f391575`, replaces exactly one expression in
a separate output file, compiles the result, and emits a receipt. It fails closed
for source drift, seam multiplicity, output/source aliasing, or readback mismatch.

The committed tree does not import or invoke the candidate. Canonical `main.py`,
`scheduler.py`, `TITAN-CONFIG.json`, the selected archive and pointers remain
unchanged. Therefore all-off behavior is byte identity, not an inferred runtime
claim.

Nine contracts prove:

- target membership and quantities equal the current `PRODUCTS`-ordered control;
- pending then baseline then remaining ordering;
- unknown and zero-stock keys cannot expand the domain;
- no-intent ordering equals current `PRODUCTS` order;
- exact current-source binding and one-output-file materialization;
- source nonmutation, compile success, admission-artifact custody and fail-closed
  drift/alias handling.

## Advance gate

This carrier may advance to a fresh current-control execution panel only. That
panel must materialize independent control/candidate arenas, bind candidate-side
returned-action digests before interpretation, cover both seats and retained
opponents/seeds, and require nonzero activation, positive mean own-cash delta,
nonnegative median, zero negative paired cells and no negative opponent×seat
mean. Until such a retained receipt exists, do not enable the factor, rebuild the
canonical archive, mutate provider/Kaggle state, or claim leaderboard uplift.
