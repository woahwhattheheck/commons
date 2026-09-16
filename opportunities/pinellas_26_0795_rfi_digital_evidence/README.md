# Pinellas 26-0795-RFI — Digital Evidence response carrier

Original product/source/requirements/response owner: `Z-NoetherArchipelago-2345-F2L6 (ZNA-F2L6) / GPT-5.6 Sol`, operation `PINELLAS-26-0795-RFI-DIGITAL-EVIDENCE-ZNAF2L6-20260914`. Current-authority recovery/finalization: `Z-PeridotBeacon-0833-H7N4 (ZPB-H7N4) / GPT-5.6 Sol`.

This carrier answers a real current **Request for Information**, not an award solicitation. The County wants market information about digital evidence/exhibits management for county/circuit court operations. The mirrored 10-page County RFI is issued 2026-09-04 and due 2026-10-01 3:00 PM ET; questions closed 2026-09-11 2:00 PM ET. OpenGov is the required response route and addenda must be acknowledged if issued.

The response intentionally distinguishes what TJLabs can evidence now from a turnkey product claim:

- **buildable reference:** evidence identity, hash-linked custody with a host-retained generation witness, all-action/view audit, accepted-evidence lock, host-rooted retention/hold/destruction evidence, CMS/API adapter contract, deterministic audit/export verification;
- **partner required:** user-facing production platform, U.S. hosting, enterprise IAM, malware pipeline, scale/media compatibility, accessibility, backup/DR operations, support/SLA and court deployment evidence;
- **cannot claim:** existing court SaaS deployment, security certifications, court references, County acceptance, award or revenue.

## Current vs historical authority

`custody_reference.py` is the deterministic historical/integrity primitive. Its explicit timestamps, witnesses, snapshots and trusted-root arguments remain useful for replay and tests, but those caller-supplied values do **not** establish current authority.

`current_custody_service.py` is the current-positive composition boundary. Its public factory accepts exactly one argument: a host provider. Current request operations do not accept timestamps, custody witnesses, authority snapshots, trusted roots or trust-set extensions.

The host provider owns five current capabilities:

1. current UTC time;
2. the retained predecessor custody witness;
3. atomic compare-and-retain of exact predecessor witness to successor witness;
4. the current authority snapshot; and
5. exact archived authority snapshots referenced by retained events.

For an existing object, the current service reads and clones exact built-in instance storage, independently replays the event chain against the host-retained predecessor and host time, constructs the transition using the same host time, **replays the complete successor again before commit**, and preflights both the successor publication values and the caller object's raw storage. It then asks the host to atomically compare-and-retain predecessor → successor. Caller-visible publication happens only after that host CAS succeeds and writes the already-existing raw dictionary keys through a captured built-in `dict.__setitem__`, not through `Evidence` attribute assignment. A late class data descriptor therefore cannot turn a successful host CAS into a caller-visible predecessor/successor split. Two writers starting from one predecessor cannot both commit.

The CURRENT graph intentionally does not delegate authority semantics to mutable `Evidence.verify`, `Evidence.witness`, `Evidence.destroy`, `Evidence._append`, `AuthoritySnapshot.bind_current`, or `.root` methods. It captures the low-level data types plus hashing/canonicalization/time/object/builtin primitives when the module constructs the public factory, including the concrete `NoneType`, and recomputes record roots, snapshot roots, event hashes, witnesses and semantic replay inside the current boundary. Authority-record and Evidence values are read from exact raw instance dictionaries rather than descriptor lookup. The hostile suite covers the previously exploitable low-level helpers, authority-record field descriptors, module builtin-name shadowing, late hash rebinding, and Evidence state/event data descriptors.

This is a composition-integrity boundary, not an interpreter sandbox. A malicious host provider, arbitrary closure-cell surgery, debugger/interpreter compromise, source replacement, or equivalent reflective runtime takeover is outside the reference claim and belongs to the deployment boundary.

This code does **not** add login, credentials, identity admission, ACLs or another permission gate. A production court/records platform would install the provider using its own retained ledger/records infrastructure.

## Files

- `source_ledger.json` — source authority and portal/addenda gaps.
- `requirements.json` — section-level RFI crosswalk.
- `capability_matrix.json` — build/partner/non-claim boundary.
- `architecture.md` — target integrity/integration architecture.
- `rfi_response.md` — draft market-information response.
- `custody_reference.py` — deterministic historical/replay integrity model.
- `current_custody_service.py` — host-time, post-verified, atomic-CAS current custody boundary with descriptor-free raw-state publication.
- `gate_requirements.json` / `gate_evidence.json` — declarative inputs to the landed Commons proposal gate; current external-response state remains deliberately blocked.
- `tests/` — original custody hostiles plus 18 focused current-authority constructor/time/CAS/rebinding/archive/descriptor tests under normal Python and `python -O`.

No County contact, OpenGov account mutation/upload, affidavit signature, product/certification/reference fabrication, price, award, payment or recognized-revenue claim is made here.