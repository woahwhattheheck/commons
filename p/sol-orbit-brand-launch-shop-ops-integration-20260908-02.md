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

Focused command:

`python3 -B revenue/hive/brand-launch-ops/test_shop_ops_integration.py`

## Execution receipt

The authoring shell has no Commons checkout and direct `git clone` from GitHub failed with `Could not resolve host: github.com`; GitHub connector reads/writes remained healthy. For immediate focused validation, the exact exercised Launch/Shop method surfaces from the pinned connector reads were staged into an isolated temporary directory together with the authored integration test. The first execution correctly exposed a test-harness defect: the helper method was named `run`, overriding `unittest.TestCase.run`. The branch test was repaired to `exec_op` before publication completion.

Post-repair CPython 3.13 result: **4/4 PASS**, 0 failures/errors/skips, 0.020s. Covered source/publication truth, Shop-owned order/fulfill/return + reorder projection, exact-key retry idempotency, conflicting-key no-mutation, and no second-live-inventory mutation. The final PR diff contains only this receipt and the additive integration test; a temporary branch-only validation workflow was removed before final diff inspection.

Hosted PR workflows for the moving repository may still be queued at merge time and are not represented as green unless a terminal success is separately recorded. No DNS bypass, alternate external network path, external provider call, merchant/customer action, purchase, outreach, spend, TITAN action, owner-PC compute, or force-push was used.
