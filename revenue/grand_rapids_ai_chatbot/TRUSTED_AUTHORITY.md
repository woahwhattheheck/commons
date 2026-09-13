# Trusted preflight authority — 920-45-269

Issues: `#13884`, `#13918`  
Original authority operation: `GRANDRAPIDS-PREFLIGHT-INDEPENDENT-AUTHORITY-ZLFW3H7-20260913`  
Release-subject repair: `GRANDRAPIDS-RELEASE-SUBJECT-BIND-ZPAF3N8-20260913`

## Why this exists

`submission_state.json` is a proposal-working document, not a trust root. A state author must not be able to make the proposal READY by writing plausible evidence strings. The preflight therefore treats every state PASS as a **claim** until it resolves against one separately retained, host-pinned current authority generation.

The authority boundary covers the exact solicitation, controlling packet digest, ordered addenda set, full canonical gate universe, typed evidence identities/digests, and an explicit `OWNER_RELEASE` record. Packet-local prose cannot create owner release.

## Production trust root

The production CLI accepts an authority-document path but **never accepts the current generation or current authority digest on the command line or in proposal state**. The validation host provisions:

- `GRAND_RAPIDS_PREFLIGHT_AUTHORITY_GENERATION` — the current positive integer generation.
- `GRAND_RAPIDS_PREFLIGHT_AUTHORITY_SHA256` — SHA-256 of the exact canonical current authority material.

The host-pinned digest makes the authority document immutable from the proposal state's perspective. The separately pinned generation+digest prevents replay of an older approved document and prevents a same-generation fork.

**Threat boundary:** an actor that can replace the validation process's host environment is the validation host, not an untrusted proposal-state author. Keep the current root outside the repository, checkout, proposal package, and submission bundle.

## Canonical authority material

The host digest covers exactly:

```json
{
  "schema_version": "grand-rapids-920-45-269-authority/v1",
  "solicitation_id": "920-45-269",
  "generation": 1,
  "packet_sha256": "<64 lowercase hex>",
  "addenda": [
    {"id": "addendum-1", "sha256": "<64 lowercase hex>"}
  ],
  "required_gates": ["<the exact built-in ordered gate universe>"],
  "evidence": [
    {
      "id": "ev:packet",
      "gate": "controlling_packet_acquired",
      "kind": "CONTROLLING_PACKET",
      "sha256": "<exact packet sha256>",
      "source_generation_sha256": "<digest of packet_sha256 + ordered addenda>"
    }
  ]
}
```

Every object has an exact key set. Generation uses a strict built-in integer (booleans are rejected). Digests are lowercase 64-hex. Addenda are strictly sorted with unique canonical IDs. Evidence IDs are unique and bounded. Each gate has one fixed evidence kind. Every evidence row must bind the same exact packet/addenda source-generation digest; changing packet or addenda invalidates stale evidence mechanically.

Both `CONTROLLING_PACKET` and `PACKET_SHA256_VERIFICATION` evidence digests must equal the exact current `packet_sha256`. A syntactically valid but unrelated verification digest is not evidence that the controlling packet was verified.

## Exact owner release subject

`OWNER_RELEASE` does not merely bind the packet/addenda generation. Its evidence `sha256` must equal `trusted_authority.release_subject_sha256(material)` for the authority generation being approved.

The release-subject digest is domain-separated by `grand-rapids-920-45-269-release-subject/v1` and canonically covers:

- the exact solicitation ID;
- the exact packet/addenda source-generation SHA-256;
- the canonical required gate universe excluding `owner_release_to_submit`; and
- **every non-OWNER_RELEASE evidence row**, projected as exact evidence ID, gate, kind, evidence SHA-256, and source-generation SHA-256, sorted by evidence ID.

OWNER_RELEASE rows themselves are excluded from that projection to avoid a circular self-digest. As a result, changing pricing, forms, references, certifications, narrative, security/acceptance evidence, evidence IDs, evidence membership, packet bytes, or addenda makes an earlier owner release stale. A new authority document must carry a newly computed release-subject digest only after the owner has reviewed that exact evidence subject.

## Rotation / anti-rollback procedure

When the controlling packet, any addendum, or any trusted non-release evidence changes:

1. Build a **new** authority material generation from retained bytes/evidence.
2. Increment `generation`.
3. Recompute the packet/addenda source-generation digest and bind every carried-forward evidence row to it only after re-verification.
4. Set both packet-custody and packet-verification evidence SHA-256 values to the exact current `packet_sha256`.
5. Compute `trusted_authority.release_subject_sha256(material)` and, only after owner review of that exact subject, bind `OWNER_RELEASE.sha256` to that digest.
6. Compute the canonical authority SHA-256 with `trusted_authority.authority_sha256(...)`.
7. Persist the exact authority document.
8. Atomically advance the validation host's pinned `GENERATION` + `AUTHORITY_SHA256` root.
9. Update proposal state to reference that exact generation+authority digest.

An old previously approved document will fail because its generation does not match the host root. A fork at the current generation will fail because its authority digest does not match the host root. A carried-forward OWNER_RELEASE fails earlier whenever its exact release subject has changed.

## State semantics

`submission_state.json` v2 contains:

```json
"authority": {
  "generation": null,
  "authority_sha256": null
}
```

until an authenticated authority exists.

A PASS gate lists only authority evidence IDs. Those IDs are not trusted by themselves; preflight resolves them from the host-pinned current authority and checks exact gate, type, digest generation, and state-to-authority binding.

Current repository state deliberately keeps every gate on HOLD because no controlling MITN packet/addenda or owner submit release is possessed.

## Authority ceiling

This mechanism proves only that a readiness claim is bound to the retained authority generation configured by the validation host. It provides **no** portal mutation, buyer contact, signature, submission, award, payment, accounting, cash, or revenue-recognition authority.
