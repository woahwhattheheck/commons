# SOL-ASTRA — UNR biobank courier-to-freezer custody LIMS

Demand: `unr-biobank-courier-custody-lims-01`  
State: `TESTED / SYNTHETIC_DEIDENTIFIED_BUILD_AND_VERIFY`  
Date: 2026-09-09

## Delivered

A deterministic, stdlib-only, fully synthetic/deidentified, read-only custody shadow for study/IRB/MTA reference → courier/package custody → receipt/temperature → deidentification → specimen/aliquot genealogy → freezer position → named-human-controlled research-use authorization.

Frozen truth set: **120 shipments = 90 READY_FOR_STORAGE / 30 HOLD**.

HOLD distribution:
- `IRB_MTA_REFERENCE_INVALID`: 8
- `CUSTODY_TEMPERATURE_FAIL`: 6
- `DUPLICATE_BARCODE`: 6
- `SPECIMEN_MANIFEST_MISMATCH`: 5
- `UNAPPROVED_TRANSPORT_ROUTE`: 5

Held shipments create zero specimens, aliquots, or positions. Each READY shipment creates one parent specimen, two aliquots, and three unique freezer coordinates. Source/courier/custody/temperature/position SHA-256 lineage is exact. All READY specimens and aliquots remain research-unavailable until a non-empty named human reviewer authorizes research use. Automatic release raises. A full second replay adds **0 specimens / 0 aliquots / 0 positions / 0 holds / 0 events**, and authoritative state remains unchanged.

## Frozen evidence

Fixture SHA-256: `3c9a5e3ec64fd7d26bf6fc1f1168b4fe962ec8589b2e681362e775ef26fed360`  
Expanded 120-record SHA-256: `7aea13dd195585087e686216defb56395170729cf59501ba1ab1d3c406f1694f`  
Manifest content-envelope signature: `c50b31526f037a2e365d66ed4556ceec0a481dfcb02ce75ed5004a17014618d9`

## Verification

- `python -m unittest -v test_unr_biobank_custody.py` → **9/9 PASS**
- `python -m py_compile unr_biobank_custody.py test_unr_biobank_custody.py` → **PASS**
- Manifest and record tamper rejection → covered
- Forbidden PHI-shaped fixture-key rejection → covered
- Duplicate-barcode no-storage invariant → covered
- Named-human-only research-use authorization / automatic-release denial → covered

## Boundaries

Synthetic/deidentified fixtures and simulated/read-only shadow state only. No PHI, clinical interpretation, diagnostic release, patient-facing action, provider/state-system/customer write, external send, automatic research release, spend, or secrets. Real-record use is outside this build.
