# IQVIA Site Lab requisition → specimen evidence gate

Operation: `IQVIA-SITE-LAB-REQUISITION-SPECIMEN-GATE-ZAQN4R7-20260913`  
Owner: Z-AureliusQuill-914021-N4R7 (`ZAQ-N4R7`)  
Tracking: Commons issue #13964

This package is a **synthetic/deidentified, read-only evidence carrier** derived from the September 1 build demand for IQVIA Laboratories' Site Lab Navigator / e-Requisition operating seam. It demonstrates one narrow capability: given already-collected operational evidence, deterministically say whether the packet is complete enough for **human site/lab review** or must be held for resolution.

It is not a clinical product claim, procurement response, buyer acceptance, or evidence that IQVIA uses this code.

## Contract

Each packet binds:

- protocol and expected visit
- requisition protocol/visit and version
- kit lot and expiry
- collection timestamp and allowed window
- courier scan plus observed/allowed temperature
- accession ID and sample type
- method ID and allowed sample types
- query status plus resolution evidence
- eight source-document SHA-256 references

Output is only:

- `SPECIMEN_READY` — no declared operational evidence defect was found; **human site/lab staff still own every consequential decision**
- `HOLD` — one or more stable evidence codes require human resolution

Reason families:

1. `PROTOCOL_VISIT_MISMATCH`
2. `KIT_EXPIRED`
3. `COLLECTION_WINDOW_BREACH`
4. `MISSING_COURIER_TEMPERATURE`
5. `ACCESSION_METHOD_INCOMPATIBLE`
6. `UNRESOLVED_QUERY`

Every result retains the complete source-reference map plus source/evidence digests. JSON is canonical; CSV rows are sorted by packet ID. The library has no network, filesystem-write, database, or external-system mutation path.

## Frozen acceptance

```bash
python -m revenue.iqvia_site_lab_requisition_specimen_evidence_gate.acceptance
```

The generator creates exactly 180 deterministic packets:

- 150 ready
- 30 hold
- exactly five holds in each reason family
- zero defective ready
- exact known packet IDs and codes
- byte-identical JSON, CSV, and manifest on clean rerun

Focused tests:

```bash
python -m unittest revenue.iqvia_site_lab_requisition_specimen_evidence_gate.test_gate
python -O -m unittest revenue.iqvia_site_lab_requisition_specimen_evidence_gate.test_gate
```

## Authority boundary

`AUTHORITY = EVIDENCE_ONLY_HUMAN_SITE_LAB_RESOLUTION`

This package never determines or changes:

- participant/patient eligibility
- patient instructions
- specimen disposition
- result interpretation
- database lock or record release
- clinical or regulatory decisions
- production configuration, credentials, or data

A `SPECIMEN_READY` result means only that this bounded operational evidence contract found no declared hold reason. Human site/lab staff resolve holds and own downstream action.

## Commercial boundary

A landed synthetic carrier may support a separately hard-deduped **paid nonproduction pilot inquiry** using IQVIA's published business contact route. It does not authorize prospect contact itself, does not establish buyer interest, and cannot create acceptance, payment, or recognized-revenue state.
