# SHARP RTU-vial replay payload-binding repair

Operation: `sharp-6818-replay-payload-binding-20260909-02`
Demand: `sharp-rtu-vial-isolator-lineage-lims-01`
Original landed PR: `#6818`
Independent review blocker consumed: `5157898344`
Prior repair handoff/release: Slack `C0BU51F1PL3 / 1788976217.103259`
Takeover coordination claim: Slack `C0BU51F1PL3 / 1788976368.154589`
Demand-thread claim: Slack `C0BTRNE6Y58 / 1788976376.100929`

## Scope

Only:
- modified `sharp_rtu_vial_isolator_lineage.py`
- modified `test_sharp_rtu_vial_isolator_lineage.py`
- this new receipt

No live LIMS, isolator, lyophilizer, provider, customer, GMP/compliance/clinical/public-health decision, outreach, spend, owner-PC action, force-push, or history rewrite.

## Reproduced blocker

The existing `ingest_row()` normalized `row_id` and, if that id already belonged to a job, immediately emitted `REPLAY_NOOP` and returned the prior accession/submission. It did not bind the first-seen row id to the canonical payload. A later row could therefore retain the same `row_id` while changing sponsor/material/batch/method/result/QC content and still be treated as an exact replay.

## Repair

- Compute `row_payload_hash = sha256_hex(row)` immediately after normalized `row_id`.
- When an existing job has the same row id, compare its stored `row_payload_hash` before any event or return.
- A mismatch raises `ValueError("ROW_ID_PAYLOAD_MISMATCH")` before journal mutation.
- An exact payload hash retains the existing `REPLAY_NOOP` behavior.
- Persist `row_payload_hash` on the first-created job record.
- Add a regression that mutates sponsor, material, batch, method version, result, and QC content under the same row id; every mismatch must raise and leave the complete journal unchanged, while exact replay still returns `REPLAY_NOOP`.

## Frozen preimages and candidate bytes

Fresh composition preimage used for candidate diff audit:
- main `d3e796a630d5130366358c197609b2cf6e042aa5`
- tree `d554e1833ce4604878e7a7f4c90d7964b0da8cde`
- source preimage `a47a2f406623700745a295e2d48656cb1f8bd4fd`
- test preimage `eacfd84d31ea7c287293ca4a54a39229aad3dffd`
- this receipt path was absent (404)

Candidate Git blobs:
- source `f43e2c21c650c8a4643302c86977fb1e2b483c57`
- test `993638e40fcf2681f6c25672298d07dbbf5dcf60`

A connector-side immutable candidate commit `ccd2a11ef10891e37569aa1eaecdcf853c3095ca` was compared directly to that fresh main. GitHub reports exactly two code paths changed: source **+4/-0** and test **+26/-0**. This proves the full-file reconstruction preserved every unrelated byte/line and added only the payload binding plus focused regression.

## Validation boundary

This cloud runtime did not have a Commons checkout and direct raw GitHub materialization was unavailable, so this receipt does **not** claim a local full-suite PASS. The final PR is to be inspected for exact three-path diff and its GitHub Actions/check state read explicitly before merge. Any hosted results are reported separately in the merge/Slack receipt rather than backfilled here.

The frozen acceptance contract remains 120 synthetic records => 90 READY / 30 HOLD, 100 jobs, zero intake-hold scheduling, no held staging/release, deterministic lineage hashes, exact replay no added jobs, named-human-only release, simulated interfaces, zero production writes and zero compliance decisions. This repair changes replay identity binding only; it does not alter the fixture, route catalog, evidence pack schema, golden audit/evidence digests, or production boundary.