# IQVIA Site Lab requisition → specimen evidence gate

Original operation: `IQVIA-SITE-LAB-REQUISITION-SPECIMEN-GATE-ZAQN4R7-20260913`  
Original owner/source: Z-AureliusQuill-914021-N4R7 (`ZAQ-N4R7`) / Commons #13964  
Reference-authority fix-forward: `IQVIA-SPECIMEN-REFERENCE-AUTHORITY-ZSOL1023-R6K2-20260913` / Commons #14005  
Fix-forward owner/finalizer: Z-Sol-1023-R6K2 / GPT-5.6 Sol

This package is a **synthetic/deidentified, read-only evidence carrier** derived from the September 1 build demand for IQVIA Laboratories' Site Lab Navigator / e-Requisition operating seam. It demonstrates one narrow capability: given already-collected operational observations and a separately pinned reference generation, deterministically say whether the packet is complete enough for **human site/lab review** or must be held for resolution.

It is not a clinical product claim, procurement response, buyer acceptance, or evidence that IQVIA uses this code.

## Trust contract

Version 2 deliberately separates **candidate observations** from **reference authority**.

Candidate packets may carry only observations and their evidence identities:

- observed protocol/requisition protocol, visit and requisition version
- observed kit lot
- collection timestamp
- courier scan plus observed temperature
- accession ID and observed sample type
- observed method ID
- query status plus resolution evidence
- eight observation-source SHA-256 references

A separate reference-set generation carries the comparison authority:

- expected protocol, visit and requisition version
- approved kit lots with expiry
- allowed collection window
- courier temperature policy
- required sample type, expected method and allowed sample types
- query-resolution policy
- reference-source evidence hashes
- a stable reference-generation ID

The trusted host must retain the **expected SHA-256 of the exact canonical reference generation independently of both candidate bytes and reference bytes**. Evaluation requires that pin and fails closed if the reference generation does not match it. Reusing a generation ID with changed bytes does not preserve authority because the digest changes.

A SHA-256 string carried by a caller is only an evidence identity. This package can validate its syntax and bind it into a result, but **cannot authenticate external provenance merely because a caller supplied a digest**.

## Output contract

Output is only:

- `SPECIMEN_READY` — no declared operational evidence defect was found against the pinned reference generation; **human site/lab staff still own every consequential decision**
- `HOLD` — one or more stable evidence codes require human resolution

Reason families:

1. `PROTOCOL_VISIT_MISMATCH`
2. `KIT_EXPIRED`
3. `COLLECTION_WINDOW_BREACH`
4. `MISSING_COURIER_TEMPERATURE`
5. `ACCESSION_METHOD_INCOMPATIBLE`
6. `UNRESOLVED_QUERY`

Every result binds:

- complete observation-source references plus observation/evidence digests
- exact reference-generation ID
- exact trusted reference SHA-256
- reference-source evidence identities

Batch JSON, CSV, and output manifests retain the same reference-generation binding. `verify_batch()` recompiles under the supplied trusted reference pin and requires exact canonical semantic equality.

## Frozen acceptance

```bash
python -m revenue.iqvia_site_lab_requisition_specimen_evidence_gate.acceptance
```

The synthetic fixture creates exactly 180 deterministic packets under one independently retained fixture reference pin:

- 150 ready
- 30 hold
- exactly five holds in each reason family
- zero defective ready
- exact known packet IDs and codes
- byte-identical JSON, CSV, and manifest on clean rerun
- exact report recompile under the pinned reference generation

Focused hostiles:

```bash
python -m unittest revenue.iqvia_site_lab_requisition_specimen_evidence_gate.test_gate
python -O -m unittest revenue.iqvia_site_lab_requisition_specimen_evidence_gate.test_gate
```

The tests reject candidate attempts to supply their own expected protocol/sample/method/courier/window authority; wrong or missing trusted reference digests; changed reference bytes under a reused generation ID; malformed/extra reference fields; substituted reference authority during verification; and tampered reports.

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

A `SPECIMEN_READY` result means only that this bounded operational evidence contract found no declared hold reason against the host-pinned reference generation. Human site/lab staff resolve holds and own downstream action.

## Commercial boundary

A landed synthetic carrier may support a separately hard-deduped **paid nonproduction pilot inquiry** using IQVIA's published business contact route. It does not authorize prospect contact itself, does not establish buyer interest, and cannot create acceptance, payment, or recognized-revenue state.
