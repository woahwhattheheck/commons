# Trusted preflight authority — 920-45-269

Issue: `#13884` / `#13918`  
Operation: `GRANDRAPIDS-RELEASE-SUBJECT-BIND-ZPAF3N8-20260913`

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

The `controlling_packet_acquired` evidence digest must equal the exact `packet_sha256`. The `packet_sha256_verified` / `PACKET_SHA256_VERIFICATION` evidence digest must also equal that exact current `packet_sha256`; an unrelated 64-hex digest is rejected.

`owner_release_to_submit` accepts only an evidence row whose gate is exactly `owner_release_to_submit` and whose kind is exactly `OWNER_RELEASE`. That row's digest must equal the **release-subject digest**: SHA-256 of the exact solicitation id, the current packet/addenda source-generation digest, the canonical required-gate universe, and the complete non-release evidence projection (id/gate/kind/sha256/source_generation, sorted by id). Changing any non-release evidence id, digest, type, or gate, adding or removing a non-release row, or changing packet/addenda invalidates a carried-forward OWNER_RELEASE.

## Rotation / anti-rollback procedure

When the controlling packet, any addendum, or any trusted evidence changes:

1. Build a **new** authority material generation from retained bytes/evidence.
2. Increment `generation`.
3. Recompute the packet/addenda source-generation digest and bind every carried-forward evidence row to it only after re-verification.
4. Recompute the release-subject digest and bind `OWNER_RELEASE` to that exact digest.
5. Compute the canonical authority SHA-256 with `trusted_authority.authority_sha256(...)`.
6. Persist the exact authority document.
7. Atomically advance the validation host's pinned `GENERATION` + `AUTHORITY_SHA256` root.
8. Update proposal state to reference that exact generation+authority digest.

An old previously approved document will fail because its generation does not match the host root. A fork at the current generation will fail because its authority digest does not match the host root. A carried-forward OWNER_RELEASE after non-release evidence change will fail because it does not match the current release-subject digest.

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
