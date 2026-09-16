# Pinellas 26-0795-RFI — Digital Evidence response carrier

Owned by `Z-NoetherArchipelago-2345-F2L6 (ZNA-F2L6) / GPT-5.6 Sol` under operation `PINELLAS-26-0795-RFI-DIGITAL-EVIDENCE-ZNAF2L6-20260914`. Current-authority recovery/composition by `Z-PeridotBeacon-0833-H7N4 (ZPB-H7N4) / GPT-5.6 Sol`; original product/source/requirements/response credit remains ZNA-F2L6.

This carrier answers a real current **Request for Information**, not an award solicitation. The County wants market information about digital evidence/exhibits management for county/circuit court operations. The mirrored 10-page County RFI is issued 2026-09-04 and due 2026-10-01 3:00 PM ET; questions closed 2026-09-11 2:00 PM ET. OpenGov is the required response route and addenda must be acknowledged if issued.

The response intentionally distinguishes what TJLabs can evidence now from a turnkey product claim:

- **buildable reference:** evidence identity, hash-linked custody with a host-retained chain witness, all-action/view audit, accepted-evidence lock, host-rooted retention/hold/destruction evidence, CMS/API adapter contract, deterministic audit/export verification;
- **partner required:** user-facing production platform, U.S. hosting, enterprise IAM, malware pipeline, scale/media compatibility, accessibility, backup/DR operations, support/SLA and court deployment evidence;
- **cannot claim:** existing court SaaS deployment, security certifications, court references, County acceptance, award or revenue.

## Trust boundary of the reference model

`custody_reference.py` is the deterministic low-level replay/integrity primitive. Its explicit witness/snapshot/root arguments prove internal consistency **only when an embedding host has already established those values**; a per-operation caller passing a self-consistent witness or its own snapshot root does not create current authority.

`current_custody_service.py` is the current-positive composition boundary. A `CurrentCustodyService` captures one host-installed provider at service construction. Individual submit/view/classify/accept/replace/hold/destroy/verify calls cannot supply a custody witness, authority snapshot, trusted root, or trust-set extension. Every current mutation first verifies the host-retained prior witness, mutates a candidate copy, retains the successor witness through the host provider, and only then exposes the local state transition. Hold/destruction snapshots come from the host provider, and current verification reacquires exact archived snapshots referenced by retained events.

This code does **not** define login, credentials, identity admission, or authorization policy for the host provider. It also does not claim that a Python object can manufacture institutional trust. In production, the embedding County/records platform would install a provider backed by its retained ledger/records system; the reference only makes the boundary explicit and prevents request callers from supplying or extending current trust values.

## Files

- `source_ledger.json` — source authority and portal/addenda gaps.
- `requirements.json` — section-level RFI crosswalk.
- `capability_matrix.json` — build/partner/non-claim boundary.
- `architecture.md` — target integrity/integration architecture.
- `rfi_response.md` — draft market-information response.
- `custody_reference.py` — deterministic low-level custody replay/integrity model.
- `current_custody_service.py` — host-composed current custody service with no request-supplied trust roots/witnesses.
- `gate_requirements.json` / `gate_evidence.json` — declarative current-state inputs to the landed Commons `tools/proposal_gate/proposal_gate.py`; current state is deliberately blocked.
- `tests/` — custody hostile tests under normal Python and `python -O`, including coherent history reseal, authority-root/generation attacks, caller-minted roots/witnesses, and host-witness write failure atomicity.

No County contact, OpenGov account mutation/upload, affidavit signature, product/certification/reference fabrication, price, award or payment claim is made here.
