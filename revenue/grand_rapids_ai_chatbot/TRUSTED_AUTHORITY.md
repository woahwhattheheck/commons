# Trusted preflight authority — 920-45-269

Original authority repair: `GRANDRAPIDS-PREFLIGHT-INDEPENDENT-AUTHORITY-ZLFW3H7-20260913`  
Post-merge release binding: `GRANDRAPIDS-PREFLIGHT-RELEASE-SUBJECT-BIND-ZESR4V6-20260913`  
Issues: `#13884`, `#13918`

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

Authority schema v2 uses exact keys. A normal evidence row is:

```json
{
  "id": "ev:pricing",
  "gate": "pricing_form_complete",
  "kind": "PRICING_FORM",
  "sha256": "<64 lowercase hex>",
  "source_generation_sha256": "<digest of packet_sha256 + ordered addenda>"
}
```

The authority envelope is:

```json
{
  "schema_version": "grand-rapids-920-45-269-authority/v2",
  "solicitation_id": "920-45-269",
  "generation": 1,
  "packet_sha256": "<64 lowercase hex>",
  "addenda": [
    {"id": "addendum-1", "sha256": "<64 lowercase hex>"}
  ],
  "required_gates": ["<the exact built-in ordered gate universe>"],
  "evidence": ["<typed evidence rows>"]
}
```

Generation uses a strict built-in integer (booleans are rejected). Digests are lowercase 64-hex. Addenda are strictly sorted with unique canonical IDs. Evidence IDs are unique and bounded. Each gate has one fixed evidence kind. Every evidence row binds the same exact packet/addenda source-generation digest; changing packet or addenda invalidates stale evidence mechanically.

Both `controlling_packet_acquired` and `packet_sha256_verified` must carry the **exact current `packet_sha256`** as their evidence digest. A syntactically valid but unrelated verification digest is rejected.

## Owner release is an exact release-subject approval

`OWNER_RELEASE` has one extra required field:

```json
{
  "id": "ev:owner-release",
  "gate": "owner_release_to_submit",
  "kind": "OWNER_RELEASE",
  "sha256": "<digest of the retained owner-decision artifact>",
  "source_generation_sha256": "<current packet/addenda generation digest>",
  "release_subject_sha256": "<exact release-subject digest>"
}
```

The release subject is deterministic and excludes `OWNER_RELEASE` itself to avoid a circular digest. It binds:

- release-subject schema and solicitation;
- current authority `generation`;
- current packet/addenda source-generation digest;
- the canonical required-gate universe; and
- the exact sorted projection of **every non-release evidence row** (`id`, `gate`, `kind`, `sha256`, and `source_generation_sha256`).

Therefore an owner release cannot be carried forward after changing pricing, forms, references, certifications, technical narrative, acceptance evidence, packet/addenda, evidence IDs, evidence kinds, or any other non-release readiness evidence. The new authority generation must contain a newly bound owner release for the new exact subject.

`trusted_authority.release_subject_sha256(...)` computes the subject to sign/record in the owner-release authority row. It does not grant release by itself.

## Rotation / anti-rollback procedure

When the controlling packet, any addendum, or any trusted evidence changes:

1. Build a **new** authority material generation from retained bytes/evidence.
2. Increment `generation`.
3. Recompute the packet/addenda source-generation digest.
4. Rebuild/re-verify the non-release evidence rows against the new generation.
5. Compute the new `release_subject_sha256` over the exact non-release authority projection.
6. Obtain/retain an owner-release decision bound to that exact release subject; do **not** copy the prior release row forward.
7. Compute the canonical authority SHA-256 with `trusted_authority.authority_sha256(...)`.
8. Persist the exact authority document.
9. Atomically advance the validation host's pinned `GENERATION` + `AUTHORITY_SHA256` root.
10. Update proposal state to reference that exact generation+authority digest.

An old authority document fails because its generation does not match the host root. A same-generation fork fails because its authority digest does not match the host root. An old owner release inside a newly pinned authority fails because its release-subject digest no longer matches.

## State semantics

`submission_state.json` keeps its authority fields null until an authenticated authority exists. A PASS gate lists only authority evidence IDs. Those IDs are not trusted by themselves; preflight resolves them from the host-pinned current authority and checks exact gate, type, packet/addenda generation, and state-to-authority binding.

Current repository state deliberately keeps every gate on HOLD because no controlling MITN packet/addenda or owner submit release is possessed.

## Authority ceiling

This mechanism proves only that a readiness claim is bound to the retained authority generation configured by the validation host and that owner release approves the exact non-release authority subject. It provides **no** portal mutation, buyer contact, signature, submission, award, payment, accounting, cash, or revenue-recognition authority.
