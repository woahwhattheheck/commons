# SHARP intake-HOLD row payload binding repair

Operation: `sharp-intake-hold-row-payload-binding-20260909-01`
Demand: `sharp-rtu-vial-isolator-lineage-lims-01`
Consumes: independent review blocker `5158091536` on merged PR `#11251`
Slack claim: `C0BTRNE6Y58 / 1788998882.518399`
Claim path correction: `C0BTRNE6Y58 / 1788999008.474189`

## Scope

Only:
- modified root `sharp_rtu_vial_isolator_lineage.py`
- modified root `test_sharp_rtu_vial_isolator_lineage.py`
- this new receipt

No fixture, route catalog, provider/customer interface, GMP/compliance decision, outreach, spend, owner-PC action, force-push, or history rewrite.

## Reproduced defect

PR #11251 bound a `row_id` to its canonical payload only after a job existed. Intake HOLDs return through `_hold()` before creating any job, so a first-seen held row could later reuse the same `row_id` with changed payload and be reclassified as a new schedulable record.

Concrete frozen-fixture reproducer: `SHP-MV02` / `R099` first arrives as `FILL_WEIGHT` with blank `method_version`, producing unscheduled `MISSING_METHOD_VERSION`. Reusing `R099` with `FW-6R-v2` changes the payload and was not stopped by the job-only binding.

## Repair

- `empty_journal()` now owns an immutable `row_payload_hashes` mapping.
- `ingest_row()` computes canonical `sha256_hex(row)` and rejects a known same-`row_id` hash mismatch before classification, events, holds, jobs, or other journal mutation.
- First-seen rows are bound only after classification/computation has successfully reached a normal effect boundary: immediately before an intake HOLD, accession replay event, or new job insertion.
- Existing job-level `row_payload_hash` verification remains as defense in depth.
- Exact intake-HOLD replay remains a duplicate/no-add HOLD; changed held→corrected payload raises `ROW_ID_PAYLOAD_MISMATCH` with byte-equivalent journal state before/after.
- Full frozen fixture regression now proves all 120 successfully processed row IDs are bound.

The new mapping is journal custody state only. It is not added to the established audit or evidence-pack projections, so frozen audit/evidence digest semantics are intentionally unchanged.

## Frozen preimages / candidate blobs

Composition base: `d905579f624020b379b947cff6b60fabf0d3a243`
Base tree: `77aa05ed1faa7c5cd80cb8e644a66cced3ac652e`
Source preimage: `f43e2c21c650c8a4643302c86977fb1e2b483c57`
Test preimage: `993638e40fcf2681f6c25672298d07dbbf5dcf60`
Receipt preimage: absent (404)
Candidate source blob: `5920a5ce83de9e40293a4901b47ae63997db9bce`
Candidate test blob: `4051c05ca971e047a3051a342f8460fb57562897`

## Validation boundary

This receipt does not backfill a local PASS claim. Exact candidate publication is followed by PR-diff inspection and connector-native GitHub Actions/status reads. Any hosted PASS/FAIL receipt and merge/readback identity is reported in the PR/Slack terminal receipt.

Frozen business acceptance remains: 120 synthetic inputs → 90 READY / 30 HOLD, 100 jobs, 90 staged packs, 20 intake HOLDs schedule zero line jobs, held rows do not stage/release, replay adds zero jobs/holds, audit SHA-256 `d248f9b13cdc38c76d1be2e4d8c2d753a77aa1d3f8efc7fcf6bc30cf7e0c95a8`, evidence digest `d255a5866b7d1a34c697a2f653d56e9c95fc98a271e2da5f7290c623e324ca01`, simulated interfaces, production writes 0, compliance decisions 0.
