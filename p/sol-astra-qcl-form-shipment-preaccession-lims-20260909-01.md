# SOL-ASTRA — QCL form/shipment pre-accession LIMS

Demand: `qcl-form-shipment-preaccession-lims-01`  
State: `TESTED / SYNTHETIC_DEIDENTIFIED_BUILD_AND_VERIFY`  
Date: 2026-09-09

## Delivered

Deterministic stdlib-only normalization of synthetic PDF/Word/email/shipment inputs into PRODUCT / RAW_MATERIAL / STABILITY pre-accession routes, with exact per-field source-document hashes and coordinates retained.

Frozen truth set: **200 = 160 READY / 40 HOLD**:
- 7 `QUOTE_MISSING_OR_CONFLICT`
- 7 `PO_MISSING_OR_CONFLICT`
- 7 `METHOD_MISSING_OR_CONFLICT`
- 7 `LOT_MISSING_OR_CONFLICT`
- 6 `SAMPLE_QUANTITY_MISSING_OR_CONFLICT`
- 6 `STORAGE_MISSING_OR_CONFLICT`

Held rows create zero accession/workflow/test/report state. READY rows enter exactly one intended workflow, preserve normalized/source provenance, and stage reports for named-human review only. Full replay adds zero accessions, workflows, test jobs, staged reports, holds, or events; authoritative state remains unchanged.

## Frozen evidence

Fixture SHA-256: `4ce6ccec57c446266869325973234ac458663f7d1d3657dc24ac66b51ac46d00`  
Expanded 200-record SHA-256: `5e3d25009c59703718c07a7d702ecc1f3a276f5681ef31416c319a6b443fba78`  
Manifest content-envelope signature: `1f201b1db55f0cae1dc76f9588193e369b34aa766f95f664f5fbd602492d28e5`

## Verification

- `python -m unittest -v test_qcl_preaccession.py` → **9/9 PASS**
- `python -m py_compile qcl_preaccession.py test_qcl_preaccession.py` → **PASS**
- exact 160/40 truth set and per-code distribution
- held-no-testing invariant
- per-field source-document hash/coordinates
- idempotent full replay
- manifest/record/PHI-shaped-field tamper rejection
- named-human-only release / automatic release denial

## Boundaries

Synthetic/deidentified fixtures and simulated/read-only shadow only. No real records, production/provider/customer writes, external sends, outreach, spend, automatic release, or secrets.
