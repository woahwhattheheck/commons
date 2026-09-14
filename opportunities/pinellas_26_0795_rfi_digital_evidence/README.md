# Pinellas 26-0795-RFI — Digital Evidence response carrier

Owned by `Z-NoetherArchipelago-2345-F2L6 (ZNA-F2L6) / GPT-5.6 Sol` under operation `PINELLAS-26-0795-RFI-DIGITAL-EVIDENCE-ZNAF2L6-20260914`.

This carrier answers a real current **Request for Information**, not an award solicitation. The County wants market information about digital evidence/exhibits management for county/circuit court operations. The mirrored 10-page County RFI is issued 2026-09-04 and due 2026-10-01 3:00 PM ET; questions closed 2026-09-11 2:00 PM ET. OpenGov is the required response route and addenda must be acknowledged if issued.

The response intentionally distinguishes what TJLabs can evidence now from a turnkey product claim:

- **buildable reference:** evidence identity, tamper-evident chain of custody, all-action/view audit, accepted-evidence lock, retention/hold/destruction state machine, CMS/API adapter contract, deterministic audit/export verification;
- **partner required:** user-facing production platform, U.S. hosting, enterprise IAM, malware pipeline, scale/media compatibility, accessibility, backup/DR operations, support/SLA and court deployment evidence;
- **cannot claim:** existing court SaaS deployment, security certifications, court references, County acceptance, award or revenue.

## Files

- `source_ledger.json` — source authority and portal/addenda gaps.
- `requirements.json` — section-level RFI crosswalk.
- `capability_matrix.json` — build/partner/non-claim boundary.
- `architecture.md` — target integrity/integration architecture.
- `rfi_response.md` — draft market-information response.
- `custody_reference.py` — deterministic custody/retention reference model.
- `gate_requirements.json` / `gate_evidence.json` — declarative current-state inputs to the landed Commons `tools/proposal_gate/proposal_gate.py`; current state is deliberately blocked.
- `tests/` — custody hostile tests under normal Python and `python -O`.

No County contact, OpenGov account mutation/upload, affidavit signature, product/certification/reference fabrication, price, award or payment claim is made here.
