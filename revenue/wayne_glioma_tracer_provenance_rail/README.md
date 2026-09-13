# Glioma PET Tracer-to-Map Provenance Rail — delivery core

This directory is an **offline synthetic acceptance core** for the commercial offer sent on 2026-09-13. It is not buyer acceptance, clinical software, an IND/NIH submission, a production imaging integration, a tracer-release system, or evidence that the $325,000 implementation has been contracted.

## What the core proves

`rail.py` reconciles pseudonymous study identities across released tracer batches and resynthesis lineage, recorded administered-dose events, PET/CT acquisitions and retries, versioned segmentations, versioned quantitative maps, and downstream handoffs. It emits a deterministic custody manifest, exact lineage rows, explicit quarantine records for ambiguous/cross-subject links, and a content-addressed offline receipt.

The core is deliberately fail closed on malformed schemas, conflicting event identifiers, invalid timestamps/hashes, broken batch-resynthesis chains, duplicate entity identities, non-contiguous segmentation/map versions, and forged parent versions. Exact byte-identical event retries are collapsed. Cross-subject or non-released-batch relationships are **not** joined into clinical lineage; they are quarantined with a named human-review owner.

`acceptance.py` deterministically generates 100 synthetic episodes with released tracer batches, resynthesis, delayed and failed/retried scans, revised segmentations/maps, handoffs, exact retries, and three deliberately cross-subject map attempts. Acceptance requires all 100 valid episode lineages to remain intact, zero cross-subject associations in accepted lineage, every deliberate ambiguity quarantined, and byte-identical manifests across clean replays.

## Clinical/privacy authority boundary

All clinical authority flags are hard-coded false. This package does **not** diagnose, classify recurrence, recommend treatment, decide/administer dose, release tracer batches, approve a clinical handoff, or contact a patient. PHI-shaped fields are rejected recursively; the acceptance generator uses synthetic opaque IDs only. Real PHI, DICOM/PACS/RIS, radiopharmacy/QC systems, scanner integrations, image/model artifacts, institutional identity/RBAC, retention rules, signing keys, validation, and clinical approvals remain outside this package.

The commercial email described a “signed custody ledger.” This package intentionally does **not** fake an institutional digital signature: `PACKAGE_MANIFEST.json` records `cryptographic_signature_implemented=false`. It provides deterministic SHA-256 content-addressed receipts only; institution-controlled signing is a later integration requirement.

## Run

```bash
python3 -m unittest revenue/wayne_glioma_tracer_provenance_rail/test_rail.py -v
python3 -O -m unittest revenue/wayne_glioma_tracer_provenance_rail/test_rail.py -v
python3 revenue/wayne_glioma_tracer_provenance_rail/acceptance.py --episodes 100 --output /tmp/wayne-acceptance.json
python3 revenue/wayne_glioma_tracer_provenance_rail/rail.py build /tmp/wayne-acceptance.json --manifest /tmp/wayne-manifest.json --receipt /tmp/wayne-receipt.json
python3 revenue/wayne_glioma_tracer_provenance_rail/rail.py verify /tmp/wayne-manifest.json /tmp/wayne-receipt.json
```
