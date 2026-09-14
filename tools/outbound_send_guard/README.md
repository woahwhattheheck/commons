# Outbound send guard

`tools/outbound_send_guard` is a **read-only, offline authority gate** for parallel sales/email workers.
It exists because a workspace-only search can say “no send receipt” while the mailbox already contains a provider-SENT message to the buyer. A second worker must not turn that visibility gap into duplicate outreach.

The guard does not search Gmail or Slack and cannot send email. An adapter/operator supplies two bounded JSON inputs:

- an `outbound-send-intent/v1` describing one intended email route + offer;
- an `outbound-send-evidence/v1` snapshot from a complete bidirectional mailbox query and complete Slack receipt query.

It emits `outbound-send-guard-receipt/v2` with one decision:

- `ALLOW_NEW` — complete/fresh evidence contains no same-offer send and no outbound inside the configured cross-offer cooldown;
- `REPLY_ONLY` — a recipient inbound is newer than the latest outbound; the receipt returns the exact inbound provider message id, but does **not** authorize a net-new thread;
- `HOLD` — evidence is incomplete, stale, future-dated, contradictory, or another outbound is still inside the cross-offer cooldown;
- `DO_NOT_RESEND` — a hard DNR exists or the exact offer has already been sent without a newer inbound.

The receipt always sets `side_effects_authorized=false`. A sender must make its own explicit mutation call only after separately consuming an acceptable decision.

## Safety / authority rules

1. Mailbox and Slack lookups must both be marked complete. Rate limits or partial pagination are `HOLD`, never “not found.”
2. Provider-SENT evidence is authoritative even when Slack has no send receipt.
3. Exact-offer outbound evidence never ages out by itself. A newer inbound changes the lane to `REPLY_ONLY`, not `ALLOW_NEW`.
4. Unknown/different prior outreach enforces a configurable route-level cooldown (default 30 days).
5. `hard_dnr` is terminal. There is deliberately no automatic “release DNR” event.
6. Duplicate provider/event identifiers with conflicting facts make authority `unknown` and `HOLD`.
7. Email identity is case-folded but plus tags are **not** stripped or guessed equivalent.
8. Input JSON is strict: duplicate keys, non-finite numbers, coercive booleans/integers, unknown fields, naive timestamps and malformed addresses fail closed.
9. CLI output cannot alias either evidence input and is published with same-directory stage + `fsync` + `os.replace`.
10. Receipt integrity and source-byte custody are distinct claims; neither authenticates the external provenance of supplied evidence.

## Source custody in receipt v2

Receipt v2 makes the input binding explicit under `payload.source`.

For parsed-object callers:

```python
receipt = guard.evaluate(intent_obj, evidence_obj)
```

The public object API accepts no source-digest override arguments. It derives canonical JSON object digests itself and reports:

```json
{
  "custody_mode": "canonical_objects",
  "intent_object_sha256": "...",
  "evidence_object_sha256": "...",
  "byte_custody": null
}
```

This proves receipt integrity against the supplied parsed objects. It does **not** claim which file bytes produced them.

For callers that need exact consumed-byte custody:

```python
receipt = guard.evaluate_bytes(intent_bytes, evidence_bytes)
```

`evaluate_bytes()` requires actual `bytes`, strict-parses those exact byte strings, then hashes those same bytes internally. The receipt reports `custody_mode="exact_consumed_bytes"` plus exact SHA-256 values under `source.byte_custody`. The internal path re-parses custody bytes and compares canonical JSON bytes, so Python scalar aliases such as `True == 1`, `False == 0`, or `1 == 1.0` cannot substitute a type-different source.

Whitespace/key-order-equivalent JSON can therefore have the same canonical object digest and different raw-byte digests. That distinction is intentional.

For compatibility, `payload.evidence.intent_sha256` and `payload.evidence.evidence_sha256` remain present in v2, but they are now **always aliases of the canonical object digests**. Exact raw-byte hashes exist only under `payload.source.byte_custody`; callers must not treat the compatibility fields as raw-file hashes.

The CLI reads each input once and routes those bytes through `evaluate_bytes()`. There is no caller-precomputed SHA override path.

These hashes are local integrity/custody evidence, not an external attestation. A self-consistent receipt does not prove that the mailbox/Slack snapshot was independently trustworthy or that the files came from a particular provider.

## Minimal example

```json
{
  "schema_version": "outbound-send-intent/v1",
  "intent_id": "intent-001",
  "recipient": "buyer@example.com",
  "offer_id": "fixed-proof-001",
  "requested_at": "2026-09-13T07:20:00Z",
  "route_kind": "email"
}
```

The evidence envelope has:

- `generated_at`;
- `mailbox.complete`, `mailbox.query_id`, `mailbox.messages[]`;
- `slack.complete`, `slack.query_id`, `slack.events[]`;
- optional strict policy integers for cooldown/freshness/skew.

Each mailbox row is metadata-only: `message_id`, `direction`, `counterparty`, `observed_at`, optional `offer_id`. The guard does not require or persist email bodies. Slack rows use `event_id`, `kind` (`lead`, `sent`, `hard_dnr`), `recipient`, `observed_at`, optional `offer_id` and optional `provider_message_id`.

Run:

```bash
python -m tools.outbound_send_guard.guard --intent intent.json --evidence evidence.json --out receipt.json
```

Exit codes are deliberately semantic: `0 ALLOW_NEW`, `3 REPLY_ONLY`, `4 HOLD`, `5 DO_NOT_RESEND`, `2 invalid input/publication failure`.

## Regression gate

```bash
python -m py_compile \
  tools/outbound_send_guard/guard.py \
  tools/outbound_send_guard/test_guard.py \
  tools/outbound_send_guard/test_guard_source_custody.py
python -m unittest -v \
  tools.outbound_send_guard.test_guard \
  tools.outbound_send_guard.test_guard_source_custody \
  tools.outbound_send_guard.test_buyer_scope \
  tools.outbound_send_guard.test_buyer_scope_custody_escape
python -O -m unittest -v \
  tools.outbound_send_guard.test_guard \
  tools.outbound_send_guard.test_guard_source_custody \
  tools.outbound_send_guard.test_buyer_scope \
  tools.outbound_send_guard.test_buyer_scope_custody_escape
```

The hostile suite includes the live failure shape that motivated this gate: no Slack send receipt, but a provider-SENT Gmail message for the buyer. That shape must never return `ALLOW_NEW`. Source-custody hostiles also cover caller digest overrides, mismatched raw bytes, duplicate/non-finite JSON, whitespace-equivalent raw sources, strict byte types and JSON scalar-type aliases.
