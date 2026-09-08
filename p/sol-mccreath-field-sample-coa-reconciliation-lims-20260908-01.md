# SOL-MCCREATH — field-sample-to-CoA reconciliation LIMS

Task: `mccreath-field-sample-coa-reconciliation-lims-01`
Buyer pair: Lisa Longacre / McCreath Laboratories
State at source publication: TESTED / synthetic BUILD-AND-VERIFY

## Owned paths

- `revenue/production-lims/mccreath-field-sample-coa/README.md`
- `revenue/production-lims/mccreath-field-sample-coa/field_sample_coa.py`
- `revenue/production-lims/mccreath-field-sample-coa/test_field_sample_coa.py`
- `revenue/production-lims/mccreath-field-sample-coa/fixtures/mccreath_100_jobs.json`
- `revenue/production-lims/mccreath-field-sample-coa/fixtures/manifest.json`
- `p/sol-mccreath-field-sample-coa-reconciliation-lims-20260908-01.md`

All six paths are additive and isolated. No shared runtime, board, catalog, provider, customer, or production-LIMS path is owned by this lane.

## Frozen synthetic fixture

- Rows: 100
- Fixture SHA-256: `b6d732ed06587b2cf14888909888b86bf0a0ab3ac87a637990d1efcc20772a10`
- Truth set: 75 READY; 10 `CUSTODY_WEIGHT_CONFLICT`; 5 `DUPLICATE_CONTAINER`; 5 `FORM_PACKAGE_MISMATCH`; 5 `CONTRACT_SPEC_MISMATCH`.
- Every READY job has exactly one accession, preparation split, analytical result, and staged CoA.
- Every HOLD job creates none of those work objects.
- Result identity binds analyte, method, method version, value, unit, rounding, and synthetic source hash.
- Final CoAs remain `STAGED_HUMAN_REVIEW`; release requires both a non-empty named reviewer and approval ID.

## Acceptance evidence

Commands executed on the frozen bytes:

`python3 -m py_compile field_sample_coa.py test_field_sample_coa.py`

`python3 test_field_sample_coa.py`

Result: **12/12 PASS**; 0 failures; 0 errors.

`python3 field_sample_coa.py --fixture fixtures/mccreath_100_jobs.json --manifest fixtures/manifest.json --verify`

Verifier result:

- rows = 100
- READY = 75
- HOLD = 25
- hold counts = 10 / 5 / 5 / 5 exactly as the truth set
- accessions = 75
- splits = 75; orphan splits = 0
- results = 75
- staged CoAs = 75
- event ledger entries = 325
- ledger SHA-256 = `3ffd8cd46323306fb897f781535eb9e4bf622b5f6f4765d9d017a21e528e29b2`
- full-fixture replay = 100/100 idempotent
- replay delta = 0 accessions / 0 splits / 0 results / 0 CoAs / 0 holds / 0 events

## Boundaries

Synthetic fixtures and simulated/read-only adapters only. This implementation makes no laboratory, regulatory, contractual, certification, or compliance disposition. It performs no production LIMS/customer/provider write, no outreach, no prospect-facing demo, no automatic CoA release, and no payment or spend action.

Publication commit/PR/merge identifiers are intentionally not embedded here because that would require a recursive receipt-only follow-up commit. The authoritative connector publication and merged-byte readback identifiers are posted in the source Slack thread after the single atomic source publication.
