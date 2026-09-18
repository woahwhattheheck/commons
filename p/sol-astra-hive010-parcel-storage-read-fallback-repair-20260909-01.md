# Hive010 Parcel storage-read fallback repair

Operation: `hive010-parcel-storage-read-fallback-repair-20260909-01`

Source: post-merge independent review of Hive010 Parcel / PR #10531, coordinated in Slack thread `C0C09QN8MQR / 1788849654.107219`.

## Bounded defect

The shipped browser controller already degraded to in-memory state when `storage.setItem()` failed, but the pre-write `saved()` / `storage.getItem()` call was outside that fallback. If storage access was revoked after initial load, a save threw before `state=next`, so the user's new or edited brief was lost from the live workspace even though the UI contract says storage failures leave changes in memory.

Fresh-main preimages before repair:

- `revenue/hive/fulfillment-desk/app.js`: Git blob `c48d7110c8ae30aa6465ed16a7ad82988a095f33`
- `revenue/hive/fulfillment-desk/browser_check.py`: Git blob `b700f385942e53e9cbb50794f4493566b433cc8c`

## Repair

`persist()` now treats a read-side storage exception as a storage outage: it warns, disables the storage adapter, does not attempt a blind write after an unverifiable read, then retains and renders the supplied next state in memory. If storage remains readable, the existing revision comparison is unchanged and still rejects a stale cross-tab write.

The embedded Chromium check adds a storage adapter whose first read succeeds, whose next read fails, and whose write would also fail if attempted. It asserts that the synthetic brief remains in memory, the UI reports memory-only storage, and no unhandled page exception occurs.

## Validation in this cloud session

Exact source extraction harness against the current and patched `persist()` functions:

- current: `SecurityError: storage access revoked`; revision `0`; orders `0`; storage still enabled; renders `0`
- patched: no throw; revision `1`; orders `1`; storage disabled; renders `1`; memory-only warning recorded

Static validation:

- `node --check revenue/hive/fulfillment-desk/app.js` — PASS
- `python -m py_compile revenue/hive/fulfillment-desk/browser_check.py` — PASS
- reverse-diff identity check reproduced both fresh-main preimage Git blob IDs exactly before applying the two intended edits

Native browser execution is not claimed by this receipt; the regression is added to the existing embedded-Chromium harness for repository/hosted execution. No customer/provider/deployment/payment/spend/owner-PC action occurred, and no model, bundle, intake runner, or receiver source is changed.
