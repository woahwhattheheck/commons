# SOL-VECTOR: FrozenSelected atomic-PLANT projection audit

`FrozenSelected._funding_trace()` and `represented_shed_event()` replay future
unit rows by calling `_apply_unit_action()` one actor at a time. The official
interpreter first counts every same-crop `PLANT` request. If demand exceeds
available seeds, all requests for that crop become `PASS`.

This directory does not claim a stronger agent. It supplies three admission
layers:

1. exact source SHA-256 identities for the imported runtime, mechanics, official
   engine, and route bundle;
2. a complete four-route census of repeated same-crop `PLANT` rows; and
3. a minimized downstream certificate where sequential projection changes an
   actual `BUY_ANIMAL` fill while the official atomic projection preserves it.

The downstream witness is intentionally stronger than a tile-only mismatch:
one seed and two `PLANT WHEAT` requests are followed by `BUILD_PASTURE`,
`PLACE COW`, and a capacity-bound animal purchase. Sequential projection plants
one crop, blocks the build, drops the cow into a 99/100 shed, and rejects the
purchase. Official atomic projection plants neither, builds and places the cow,
and admits the purchase.

## Run

```bash
cd revenue/kaggriculture/cloud-execution-lab
python analysis/v3-frozen-atomic-projection-sol-vector/test_audit.py
python analysis/v3-frozen-atomic-projection-sol-vector/audit.py \
  --output analysis/v3-frozen-atomic-projection-sol-vector/REPORT.json
```

`DORMANT` means the exact current route bank contains no repeated same-crop
plant row. `ROUTE_RISK` means the necessary route pattern exists but still
requires observation-bound activation before any candidate or game spend.
`INVALID` means the exact current helper no longer reproduces the witness.

No canonical runtime/config/archive/pointer/provider/Kaggle mutation is
authorized by this audit. No score claim is made.
