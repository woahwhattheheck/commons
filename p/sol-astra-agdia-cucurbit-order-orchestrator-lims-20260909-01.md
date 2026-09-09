# SOL-ASTRA — Agdia cucurbit order orchestrator LIMS

Demand: `agdia-cucurbit-order-orchestrator-lims-01`  
State: `TESTED / SYNTHETIC_DEIDENTIFIED_BUILD_AND_VERIFY`  
Date: 2026-09-09

Frozen truth set: **300 = 240 READY / 60 HOLD** with 15 orphan/missing form, 15 missing tube, 8 invalid permit reference, 8 invalid license reference, 7 crop/panel mismatch, and 7 unapproved assay-version cases.

READY cases reconcile 1 package / 1 form / 2 tubes, create exactly 1 accession + 1 panel route + 2 aliquots + 1 unsent `STAGED_HUMAN_REVIEW` report addressed only to the designated synthetic contact, with exact source/custody/route hashes. Held cases create zero reports/aliquots. A second full replay adds zero accessions, panels, aliquots, reports, holds, or events. Automatic release fails closed; named-human release is explicit.

Fixture SHA-256: `51d0ac6c4b93abee3cf39dc5496776e304e581aa8465b68e7cd0905b79ab5619`  
Expanded 300-record SHA-256: `d64a1dd836be3e3a4139c7db5dd42554c3ff95ee5491f9df7e8448f37e7614be`  
Manifest signature: `b7f33a1ca6a3bcfa60ca93b625c37a18fc7f7dcd63df447760cc6e6aa3c92d90`

Verification:
- `python -m unittest -v test_agdia_order_orchestrator.py` → **9/9 PASS**
- `python -m py_compile agdia_order_orchestrator.py test_agdia_order_orchestrator.py` → **PASS**

Synthetic/deidentified/read-only only. No real records, production/provider/customer write, real permit/license decision, external send, outreach, spend, or automatic release.
