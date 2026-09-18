# MVTL NEMAGENE pairing + release build receipt

Demand: `mvtl-nemagene-pairing-release-lims-01`
Buyer pairing: Minnesota Valley Testing Laboratories / Jerry Balbach
Date: 2026-09-09

## Scope

Additive synthetic/read-only incumbent-LIMS shadow that binds NEMAGENE SCN add-on jobs/results to their original soil/fertility accession, validates deterministic receipt/SLA evidence, preserves result/source lineage, and stages combined reports for named-human review. No biological or diagnostic interpretation is performed.

## Frozen acceptance

- `python -m unittest -v test_mvtl_nemagene_pairing.py` — **10/10 PASS**.
- `python -m py_compile mvtl_nemagene_pairing.py test_mvtl_nemagene_pairing.py` — **PASS**.
- `python mvtl_nemagene_pairing.py` — **PASS**.
- Exactly **500** synthetic soil orders: **400 valid / 100 HOLD**.
- Exactly **250** valid fertility+SCN orders; the remaining 150 valid orders are fertility-only.
- Frozen HOLD truth set: 25 each `DUPLICATE_BARCODE`, `MISSING_ID`, `ADDON_SAMPLE_MISMATCH`, `DIVERGENT_RECEIPT`.
- Every valid order creates one accession and one staged unsent combined report; every valid SCN add-on creates one SCN job/result binding to the same original sample/fertility accession.
- Exactly 250 unique SCN result IDs; zero orphan or duplicate SCN results.
- Signed receipt dates map exactly to the fixture's deterministic two-business-day SLA dates.
- Every combined report carries fertility/SCN result digests, source hash, SCN lineage hash when applicable, and a deterministic combined-result digest.
- Full same-ledger replay reports 500 idempotent records and adds zero accessions/SCN jobs/reports/holds/events; state and combined-manifest hashes are unchanged.
- Named-human release is copy-only and unsent; reserved/one-token identities fail; automatic release is disabled.
- Read-only authoritative mock snapshot fingerprint: `ee4789fb0be2dec7c3fb76e9c019e7731f3fd956b15569802cc5933046822cbf`.

## Frozen hashes

- Fixture SHA-256: `77c8db0014946b581bd7aa7a0f0fac707ead2c29f709e83f0033ce3713eaf0f6`
- Expanded 500-record SHA-256: `1e3d4ef14641aef0ca1869d6b79153cf5b565e7d2405aef0ea1c54f559fa5c4d`
- Manifest envelope signature: `259e6a426274e3a0a22f8411673848c9c3e445edc00d20d52f7d1e46944f3b8f`
- Shadow state SHA-256: `fea2f471f49ad74955e1e3cfe489e6db3367e4ea4be3caa114a0abf5b77b3785`
- Combined-manifest SHA-256: `5e0659bceffe128524245b4718d22443fd733be5f5b496a728359fb1127b5fe9`

## Boundary

Synthetic/deidentified fixture and read-only mock incumbent-LIMS state only. The SLA rule is a fixture assertion pending buyer/vendor golden validation. No live LIMS/state/provider/customer write, biological/diagnostic interpretation, report send, outreach, spend, autonomous release, or owner-PC action.
