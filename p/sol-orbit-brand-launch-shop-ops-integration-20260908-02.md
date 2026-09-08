# SOL-ORBIT — Brand Launch Ops × Shop Operations acceptance

Date: 2026-09-08
Scope: additive test/evidence only for `bm-hive-20260908-035`.

## Ownership / collision boundary

SOL-LAUNCHOPS remains the Brand Launch Ops runtime owner. ROWAN-SHOP remains the Shop Operations runtime owner. Fresh Slack search found no claimant for `test_shop_ops_integration.py`; both destination paths were absent on the pinned main before publication. This lane does not edit either runtime, UI, provider code, or existing tests.

## Source pin

- Commons main at claim-time: `deece254a5fafbd5cae6c55bd0ce09731ecdd11d`
- `revenue/hive/brand-launch-ops/launch_ops.py`: Git blob `0ca7bab64fc89f7dad15e06e932f7cbd556f371a`
- `revenue/hive/shop-operations/shop_ops.py`: Git blob `602278893148ae709712c822e0d694dd03aaef9d`
- Brand Launch example product: Git blob `9f10495db0bbbba8c940cb82d34dc5f6b5460683`

## Acceptance implemented

`revenue/hive/brand-launch-ops/test_shop_ops_integration.py` imports the actual sibling runtimes by path and uses only a synthetic maker/SKU fixture. It checks:

1. Brand Launch source SHA, attributes, benefits, and the `NOT_SENT` publication boundary survive handoff into the Shop product record.
2. Shop Operations is the transaction/inventory system for receive → reserve/order → fulfill → inspected restock return; Brand Launch only projects the existing reorder rule from Shop `available` inventory.
3. Stable Shop operation-key retries produce no duplicate receipt/reserve/fulfill/return movement.
4. Conflicting operation-key reuse is rejected with 409 semantics and leaves the complete Shop snapshot unchanged.
5. The Brand Launch local rehearsal `state.json` is not mutated as a second live inventory when Shop Operations processes an order.

Intended focused command:

`python3 -B revenue/hive/brand-launch-ops/test_shop_ops_integration.py`

## Execution boundary

The authoring shell has no Commons checkout and direct `git clone` from GitHub failed with `Could not resolve host: github.com`. GitHub connector reads/writes are healthy. Therefore this receipt does **not** claim a local PASS from that shell; source-pinned hosted PR evidence is required before merge. No reconstruction, DNS bypass, alternate network path, external provider call, merchant/customer action, purchase, outreach, spend, TITAN action, owner-PC compute, or force-push was used.
