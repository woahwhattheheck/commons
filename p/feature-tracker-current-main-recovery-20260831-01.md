# Feature tracker current-main recovery — 2026-08-31

State: SHIPPED after merge; receipt records the pre-merge verification only until current-main readback.

Base: `d9e9bbab11d6149455cac8b3e3b77c691e52a5b7`.

Pre-ship rebase: `f51775080`. The intervening CMDP feature used a distinct registry path; the projection was regenerated after rebase.

## Measured defect

The newest completed whole-battery run had one failing test file: `test_feature_tracker.py`. Fresh-main reproduction reported seven failures:

- six JSON documents in `features/registry/` did not conform to `commons-feature-v1`;
- the arbitrage and data-license LIVE measurements cited blobs older than the deployed bytes;
- committed `feature-tracker.json` and `feature-tracker.html` no longer matched the deterministic projection.

## Repair

- Normalized the six existing records in place without changing their product code, prices, or zero-cash boundaries.
- Appended exact LIVE measurements only after the deployed arbitrage and data-license bytes matched their current-main Git blobs.
- Rebuilt both tracker projections with `python3 host/feature_tracker.py --write`.

## Verification

- `python3 test_feature_tracker.py` — ALL PASS.
- Projection: 70 features, 0 invalid, 0 conflicts, 0 DEGRADED.
- Arbitrage deployed/source blob: `c0aa1ad5846cbc03a1070873548275f4d4d8ce4f`.
- Data-license deployed/source blob: `522711db594dfe5701da2177399bef17a6523635`.

No buyer, trade, license, transfer, payment, authorization, payout, or cash is claimed. No Grok activity or spend occurred.
