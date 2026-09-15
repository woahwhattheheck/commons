# Intent receipt provenance boundary

This package deliberately separates **byte commitment** from **submission provenance**.

`facts.intent_receipt` is caller-owned evidence. Its `provider_event_sha256` can prove that
the caller is referring to one stable byte string, and `submitted_at` is parsed as a
strict UTC timestamp. Neither property authenticates a provider event, proves that OHSU
received or accepted an intent-to-bid message, or grants submission authority.

Therefore the source-bound compiler treats caller receipts as
`UNVERIFIED_CALLER_RECORD` evidence:

- before the confirmed intent deadline, qualification/route/owner-review facts determine
  the owner-review status; the caller receipt does not grant any external authority;
- at or after the confirmed intent deadline, a caller receipt cannot clear
  `HOLD_INTENT_DEADLINE`;
- a caller timestamp after the confirmed deadline remains
  `HOLD_INTENT_CHRONOLOGY`;
- a future trusted provider/harness attestation, if added, must be a separate authority
  boundary rather than another caller boolean, digest, path, or timestamp.

The executable module pins the reviewed predecessor bytes as a non-importable text donor,
checks their exact Git-blob identity, and applies the provenance repair with exact-once
source transforms before executing the integrated engine. The donor exists only to make
the predecessor and its historical receipt semantics mechanically reproducible in tests;
it is not a supported decision surface.

No code in this repair authorizes buyer/partner contact, intent submission, proposal
submission, contracting, payment, spend, award/cash assertions, or revenue recognition.
The existing $12,500 workshare remains `PROPOSED_NOT_ACCEPTED`.
