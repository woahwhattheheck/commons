# SOL-ASTRA — Delaware new-lab PFAS/microbiology lineage LIMS

Demand: `delaware-newlab-pfas-lineage-lims-01`  
State: `TESTED / SYNTHETIC_BUILD_AND_VERIFY`  
Date: 2026-09-09

## Delivered

A deterministic, stdlib-only, read-only shadow for quote/request → accession → matrix/method/version → PFAS LC-MS/MS or molecular/microbiology → QC → staged evidence report, with old/new-facility provenance.

Frozen truth set: **200 synthetic requests = 150 READY / 50 HOLD**.

HOLD distribution:
- `MISSING_MATRIX_SDS_CUSTODY`: 15
- `DUPLICATE_CONTAINER`: 10
- `METHOD_MATRIX_MISMATCH`: 10
- `CALIBRATION_QC_FAIL`: 10
- `LEGACY_NEW_FACILITY_ID_COLLISION`: 5

Held requests schedule zero accessions, jobs, or reports. READY requests retain exact source, method, and value/unit/qualifier SHA-256 lineage. Reports stage as `STAGED_HUMAN_REVIEW`; automatic release raises, and the synthetic release path requires a non-empty named reviewer. A full second replay adds **0 accessions / 0 jobs / 0 reports / 0 holds / 0 events** and leaves the authoritative-state fingerprint unchanged.

## Frozen evidence

Fixture SHA-256: `6df55cb90f4bd51883e68dbdde038e7cd83b52ea015321f9e3c238178464d1b3`  
Expanded 200-record SHA-256: `8ca2d239592c789a320abcd5b01c296573f75ab483b10493669ce49aa4ee8cf5`  
Manifest content-envelope signature: `2e0abd59d792a986f6aea9ca30c05f0ba71263d3809e9d5c75a0b9e7ff5c959d`

## Verification

- `python -m unittest -v test_delaware_newlab_lineage.py` → **8/8 PASS**
- `python -m py_compile delaware_newlab_lineage.py test_delaware_newlab_lineage.py` → **PASS**
- Manifest signature/tamper rejection → covered by focused tests
- Record-lineage tamper rejection → covered by focused tests
- Named-human-only release / automatic-release denial → covered by focused tests

## Boundaries

Synthetic fixtures and simulated/read-only shadow state only. No production adapter, no Delaware/state-system write, no regulatory/public-health decision, no customer/provider action, no automatic report release, no outreach, no spend, and no secrets. Buyer-approved schemas, methods, facility IDs, QC policy, de-identified golden round trips, and named operational release roles remain external inputs.

Publication is intentionally separate from this self-contained receipt; the exact candidate commit, PR, guarded merge, and merged-main blob readbacks are posted in the demand thread after connector publication.
