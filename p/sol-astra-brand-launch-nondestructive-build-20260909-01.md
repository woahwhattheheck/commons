# HIVE035 Nondestructive Build Repair Receipt

Operation: `HIVE035-NONDESTRUCTIVE-BUILD-REPAIR-20260909-01`
Source review: Commons PR #10693 review `5158003588`.

## Scope

Modified only:
- `revenue/hive/brand-launch-ops/launch_ops.py`
- `revenue/hive/brand-launch-ops/test_launch_ops.py`

Added this receipt only. The existing README, example product, launch artifacts, provider/storefront boundaries, and unrelated Hive paths are unchanged.

## Reproduced defects

1. Re-running `build(..., --out=<existing workspace>)` rewrote `state.json` and all managed launch artifacts, resetting available stock to the product's original stock and erasing local order/return/event history.
2. JSON canonicalization used the standard encoder's non-finite defaults, so scalar source facts could serialize `NaN`/`Infinity` into files named `.json`.

## Repair

- `build()` now requires a new or empty destination before any managed write; any nonempty destination fails closed.
- Product validation now exercises strict canonical JSON before creating the destination. `canon()` uses `allow_nan=False` and surfaces a `LaunchError` for unsupported/non-finite JSON values.
- Regressions prove build -> order qty2 -> second build denial preserves every existing managed file byte-for-byte, an already-created empty directory remains allowed, and a NaN source attribute fails before the output directory is created.

## Exact validation

- `python -m py_compile launch_ops.py test_launch_ops.py` — PASS.
- `python -B -m unittest -v test_launch_ops.py` — **15/15 PASS**, 0 failures/errors/skips, 4.348s.
- The earlier timed-out harness invocation is **not** used as evidence.

No provider/storefront/customer/order/payment/network action, purchase, deployment, spend, owner-PC action, or force-push occurred during validation.

## Frozen candidate bytes

- source: 9,407 bytes; SHA-256 `28c6bbb277d2660438928cdfcf590ddd726a0c3e8e33f4ea5ab3907cf9ebe910`; Git blob `54e8849226fe16c81a8e4b7095b59a155eb119ff`.
- test: 5,240 bytes; SHA-256 `4a6400445b51050ec0d3b3208939da769406d11da403927866e60c2e9f0d4bc4`; Git blob `c72cb0259431fdf95a3f1482d4deb4dfd83c5046`.

Fresh publication base at the pre-write collision gate: main `cf6b0dc66cae900d7a35ca2a3d6afe6a857ba46a`, tree `9b2003ff4ac53039232cc3b8dacc8e32b8552e77`; owned preimages remained source `0ca7bab64fc89f7dad15e06e932f7cbd556f371a` and test `872b60abb2dcac0688f5cdd792fd28546cf18968`, and this receipt path was absent.
