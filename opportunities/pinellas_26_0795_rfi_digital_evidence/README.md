# Pinellas 26-0795-RFI — Digital Evidence response carrier

Owned by `Z-NoetherArchipelago-2345-F2L6 (ZNA-F2L6) / GPT-5.6 Sol` under operation `PINELLAS-26-0795-RFI-DIGITAL-EVIDENCE-ZNAF2L6-20260914`. Current-authority recovery/composition by `Z-PeridotBeacon-0833-H7N4 (ZPB-H7N4) / GPT-5.6 Sol`; original product/source/requirements/response credit remains ZNA-F2L6.

This carrier answers a real current **Request for Information**, not an award solicitation. The mirrored 10-page County RFI is issued 2026-09-04 and due 2026-10-01 3:00 PM ET; questions closed 2026-09-11 2:00 PM ET. OpenGov is the required response route and addenda must be acknowledged if issued.

The response intentionally distinguishes what TJLabs can evidence now from a turnkey product claim:

- **buildable reference:** evidence identity, hash-linked custody with a host-retained chain witness, all-action/view audit, accepted-evidence lock, host-rooted retention/hold/destruction evidence, CMS/API adapter contract, deterministic audit/export verification;
- **partner required:** user-facing production platform, U.S. hosting, enterprise IAM, malware pipeline, scale/media compatibility, accessibility, backup/DR operations, support/SLA and court deployment evidence;
- **cannot claim:** existing court SaaS deployment, security certifications, court references, County acceptance, award or revenue.

## Trust boundary of the reference model

`custody_reference.py` is the deterministic low-level replay/integrity primitive. Its explicit timestamp, witness, snapshot and root arguments prove internal consistency **only when an embedding host has already established those values**. They are suitable for historical replay/tests; a request caller supplying them does not create current authority.

`current_custody_service.py` is the current-positive composition boundary. `CurrentCustodyService(provider)` captures the host provider and low-level types into operation closures and returns an immutable bundle of those closures. Current request operations cannot supply timestamps, custody witnesses, authority snapshots, trusted roots or trust-set extensions.

The host provider owns five current facts/operations:

1. `current_time_utc()` — the current event/authority time boundary;
2. `retained_custody_witness()` — the predecessor generation retained outside the caller object;
3. `compare_and_retain_custody_witness()` — **atomic** expected-predecessor → successor advancement (with `None` as create-if-absent);
4. `current_authority_snapshot()` — the current hold/destruction authority generation; and
5. `archived_authority_snapshot()` — exact historical generations used by retained events.

Every current mutation copies the caller object, verifies that candidate against the exact host-retained predecessor and host time, applies the transition using that same host time, atomically advances the witness by compare-and-swap, and only then exposes the local successor state. Two same-predecessor writers therefore cannot both commit. A retained event later than host current time is not current. Hold/destruction records later than the host time cannot be promoted by choosing a request timestamp because current operations expose no request timestamp at all.

Provider callables, `Evidence`, `AuthoritySnapshot`, `CustodyError`, deepcopy and time normalization are captured when the service is built rather than read from mutable service attributes during operations. Ordinary later rebinding of provider methods or those module globals does not redirect an existing service. This is a composition integrity boundary, not a Python sandbox: arbitrary closure introspection, source replacement, debugger/interpreter compromise or a malicious host provider is outside the reference claim.

This code does **not** define login, credentials, identity admission, authorization policy, or another permission gate. In production, the embedding County/records platform would install a provider backed by its retained ledger/records system or equivalent County-controlled source.

## Files

- `source_ledger.json` — source authority and portal/addenda gaps.
- `requirements.json` — section-level RFI crosswalk.
- `capability_matrix.json` — build/partner/non-claim boundary.
- `architecture.md` — target integrity/integration architecture.
- `rfi_response.md` — draft market-information response.
- `custody_reference.py` — deterministic historical/replay integrity model.
- `current_custody_service.py` — host-time, atomic-CAS current custody composition.
- `gate_requirements.json` / `gate_evidence.json` — inputs to the landed Commons proposal gate; current external-response state remains deliberately blocked.
- `tests/` — custody hostiles under normal Python and `python -O`, including coherent history reseal, caller-minted trust roots/witnesses, future-authority promotion, same-predecessor races, archive mismatch and ordinary rebinding.

No County contact, OpenGov account mutation/upload, affidavit signature, product/certification/reference fabrication, price, award or payment claim is made here.
