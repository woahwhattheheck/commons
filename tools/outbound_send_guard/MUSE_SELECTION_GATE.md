# Muse publication selection gate

`muse_selection_gate.py` binds one internal Muse arbitration decision to the exact outbound publication candidate that requested it. It composes with the existing outbound-send guard and connector-native v3 proof-of-possession lease; it does not replace either one.

The problem is a fleet race: two workers can independently pass ordinary relationship checks and reach the same prospect + offer + route within seconds. A human-readable Slack convention such as “ask Muse first” is useful, but it is not enough for a provider boundary unless the selected worker, exact candidate generation, exact lease public identity, and exact arbiter event can be checked mechanically.

## Authority ceiling

A `SELECTED` receipt is **selection evidence only**. It always contains:

```json
{
  "requires_current_worker_lease_possession": true,
  "requires_fresh_provider_preflight": true,
  "side_effects_authorized": false
}
```

Immediately before an email/contact-form/direct-message/provider mutation, the caller still must independently:

1. validate the current relationship / route / cooldown / DNR / content policy gates;
2. validate the exact public outbound v3 lease receipt bound into this candidate;
3. re-read the live v3 lease branch/parent/metadata and call `connector_capability_lease.verify_possession(...)` with the privately retained current-worker capability;
4. re-run the provider/mailbox preflight required by the sending adapter; and
5. perform at most the one provider mutation authorized by the surrounding owner/application policy.

The raw outbound lease capability must never be placed in Slack, GitHub, candidate JSON, snapshot JSON, Muse messages, provider metadata, or this gate's receipt.

## Candidate identity

The strict input schema is `muse-publication-candidate/v1`.

The privacy-preserving `publication_key` hashes only the collision domain:

- `buyer_scope_sha256`
- `recipient_fingerprint`
- `offer_scope`
- `route_kind`

It intentionally excludes worker identity and message wording. Two workers pursuing the same buyer/recipient/offer/route therefore collide even if they drafted different text.

The separate `candidate_digest` hashes the entire normalized candidate, including:

- `candidate_id`
- `worker_id`
- exact `message_sha256`
- request time
- exact public v3 lease identity (`claimant`, `claim_id`, `lease_ref`, capability commitment, receipt digest)

The v3 lease claimant must equal the candidate worker. Only the commitment to the private capability is public; the capability itself is never accepted by this gate.

## Muse DM snapshot

The adapter supplies one complete `muse-publication-arbitration-snapshot/v1` for the exact Muse DM conversation. It contains:

- exact `conversation_id` and `arbiter_user_id`;
- `coverage_started_at` and `captured_at`;
- `complete=true` only after the relevant DM history window was fully read; and
- normalized events with canonical Slack message timestamps, sender user IDs, event type, publication key, candidate digest, candidate ID, and worker ID.

Supported event types are `CANDIDATE`, `SELECTED`, `NOT_SELECTED`, and `CANCELLED`.

Decision events are authoritative only when they come from the configured Muse arbiter user ID. Conflicting reuse of one Slack message ID, partial history, wrong conversation/arbiter identity, stale/future snapshots, event chronology violations, multiple distinct winners, selection expiry, or a later exact cancellation all fail closed.

Defaults are deliberately short-lived:

- snapshot freshness: 120 seconds;
- future clock skew: 30 seconds;
- request-to-decision latency limit: 600 seconds;
- selection TTL: 600 seconds.

A downstream adapter may use stricter values, but should not extend them casually.

## Structured Slack wire format

Human prose may accompany these records, but adapters should retain the machine record exactly. The examples below contain no raw recipient identity and no raw lease capability.

Candidate request:

```text
MUSE_PUBLICATION_CANDIDATE_V1 {"candidate_digest":"<sha256>","candidate_id":"<opaque-id>","publication_key":"<sha256>","worker_id":"<swarm-id>"}
```

Muse selection:

```text
MUSE_PUBLICATION_DECISION_V1 {"candidate_digest":"<sha256>","candidate_id":"<opaque-id>","decision":"SELECTED","publication_key":"<sha256>","worker_id":"<swarm-id>"}
```

Muse rejection or revocation uses the same fields with `decision` equal to `NOT_SELECTED` or `CANCELLED`.

The Slack adapter—not free-form model interpretation—must map the exact Slack event metadata into the snapshot. A missing or malformed machine record is `HOLD`, not an invitation to infer intent from nearby prose.

## Decisions

- `SELECTED`: exactly this candidate is the current unexpired winner and the snapshot is otherwise coherent.
- `NOT_SELECTED`: another candidate won, or Muse explicitly rejected/cancelled this exact candidate.
- `HOLD`: evidence is incomplete, stale, conflicting, malformed, ambiguous, or has no arbiter decision.

For `SELECTED`, `selection_binding_sha256` commits to the publication key, exact candidate digest/ID/worker, Muse conversation + arbiter, exact selection message ID/time, and the public lease-binding digest. `verify_receipt()` recomputes this binding as well as the outer receipt digest. `verify_selected_binding(candidate, receipt)` additionally proves the selected receipt is for the supplied exact candidate.

## CLI

```bash
python -m tools.outbound_send_guard.muse_selection_gate \
  --candidate candidate.json \
  --snapshot muse-snapshot.json \
  --conversation-id D0C1U7TUZEC \
  --arbiter-user-id U0C0TKRTQHZ \
  --out muse-selection-receipt.json
```

Exit codes:

- `0` — `SELECTED`
- `3` — `NOT_SELECTED`
- `4` — `HOLD`
- `2` — invalid input or output-publication failure

`--out` is create-exclusive; an existing path is never overwritten.

## Regression gate

```bash
python -m py_compile \
  tools/outbound_send_guard/muse_selection_gate.py \
  tools/outbound_send_guard/test_muse_selection_gate.py
python -m unittest -v tools.outbound_send_guard.test_muse_selection_gate
python -O -m unittest -v tools.outbound_send_guard.test_muse_selection_gate
```

The focused hostile suite covers copied-winner replay, same-opportunity publication-key collision across workers and wording, multiple winners, non-arbiter decisions, wrong conversation, partial/stale/future snapshots, decision latency and TTL expiry, later cancellation, conflicting Slack message-ID reuse, canonical Slack event IDs, duplicate JSON keys, unknown fields, lease-claimant mismatch, receipt tampering, candidate rebinding, forged inner selection binding with a recomputed outer digest, and CLI execution.
