# SOL-ATLAS — Essco/Transcat calibration cutover reconciliation receipt

Demand: `essco-transcat-calibration-cutover-lims-01`
Source thread: Slack `#build-demand` parent `1788151314.259709`
Route: `1788877707.096439`
Claim: `1788877930.116259`

## Scope

NEW only:

- `revenue/production-lims/essco-transcat-calibration-cutover/README.md`
- `revenue/production-lims/essco-transcat-calibration-cutover/essco_transcat_cutover.py`
- `revenue/production-lims/essco-transcat-calibration-cutover/test_essco_transcat_cutover.py`
- `revenue/production-lims/essco-transcat-calibration-cutover/fixtures/essco_transcat_500_histories.json`
- `revenue/production-lims/essco-transcat-calibration-cutover/fixtures/manifest.json`
- `p/sol-essco-transcat-calibration-cutover-lims-20260908-01.md`

Final fresh publication base before Git Data composition:
`a7c513777072fa4993983dce25fb6a02911eb180`
tree `0b8ecbc4721488a77a9a8810cdb8ca1a3eb37419`.

Fresh collision audit: `revenue/production-lims` now contains one concurrent peer directory, `mccreath-field-sample-coa`, which is preserved unchanged. Exact `revenue/production-lims/essco-transcat-calibration-cutover` is absent (HTTP 404), and this exact `p/` receipt path is absent (HTTP 404). An immediately preceding source-thread read contained only the route plus this lane's claim; a later retry was Slack-rate-limited and did not alter ownership. No earlier hidden claimant surfaced before source writes.

## Frozen synthetic acceptance

The fixture stores a compact deterministic generation recipe and deterministically materializes each into the full frozen synthetic calibration history before validation. The signed manifest binds the raw fixture and complete expanded-record set.

- histories: **500**
- CLEAN: **400**
- HOLD: **100**
- HOLD distribution:
  - `DUPLICATE_ASSET_ID`: 15
  - `CUSTOMER_SITE_MISMATCH`: 15
  - `OUT_OF_SCOPE_PROCEDURE`: 14
  - `MISSING_AS_FOUND`: 14
  - `CERTIFICATE_VERSION_CONFLICT`: 14
  - `COURIER_CUSTODY_BREAK`: 14
  - `LEGACY_NEW_SYSTEM_MISMATCH`: 14
- automatic release: **0**
- clean rows: **QA_REQUIRED**
- fixture SHA-256: `daba9caee1ee285820ba381a5fa62897d4d1cb703d17f03dcfb595eb2d254568`
- expanded-record-set SHA-256: `a6b37eef17e8424f4d1bb49118a7b574bd4a07f18e5054e986daf46b9fe79765`
- manifest signature: `ed190e587a078bad95ed8c64673d8592b5f032989d128cbb542f341a4843aaaf`
- deterministic outcome SHA-256: `ca3ec8193bce4b52d3ffacdbe0f71156c2ab90ee4726a8bb7b2b70024b753912`

## Test receipt

Executed from the authored directory with CPython stdlib only:

`python -m unittest -v test_essco_transcat_cutover.py`

Result: **7/7 PASS**, 0 failures, 0 errors, 0 skips, 0.106s.

Also executed:

`python -m py_compile essco_transcat_cutover.py test_essco_transcat_cutover.py`

Result: PASS.

The suite proves exact 400/100 replay, exact truth-set HOLD codes, clean mapping exactly once end-to-end, field/unit/uncertainty/procedure/certificate-hash preservation, zero cross-customer asset/certificate ownership, deterministic rerun, exact rollback, authoritative-state non-mutation, manifest/record tamper rejection, and disabled automatic release.

## Pre-publication file SHA-256

- README: `c14f4e075393cfd300f01bf26fc179a8a963f1171bcb538d333d752a99cacfe0`
- module: `b3167a9a8e05d742ce218e34d028d687c6661cfd8820c9aa11b78a7f1231ee26`
- test: `d39a70be6e1d77cd752655e367d4f0848c11fc843bb54d488691102338b42459`
- fixture: `daba9caee1ee285820ba381a5fa62897d4d1cb703d17f03dcfb595eb2d254568`
- manifest: `f1e8c3804dc3ab6a9f780045d49c59da2b532e68330b74aa431dcfa8a54a561f`

## Safety boundary

Synthetic fixtures and read-only shadow state only. No live Essco, EsscoNet, Transcat, MET/CAL, courier, customer, provider, certificate-release, payment, or spend mutation. Existing systems remain authoritative. Human QA alone controls any real release. No force-push.
