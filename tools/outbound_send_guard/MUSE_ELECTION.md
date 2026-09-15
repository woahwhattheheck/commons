# Muse outbound election receipt v1

The fleet already has buyer-scope dedupe, provider-capability leases, turn-generation leases, and owner-policy gates. Those primitives do not answer a different coordination question: **which one of many near-simultaneous seats is allowed to carry one exact outbound candidate forward?**

The owner-designated arbiter is the Muse assistant in Slack. Before an email-like prospect publication, a claimant sends Muse an exact election request and may treat the election prerequisite as satisfied only when fresh connector readback shows that Muse selected that same claimant for that same candidate.

`muse_election.py` makes that process deterministic and fail-closed. It is not a sender and it does not authenticate Slack by itself.

## Pinned route

v1 pins the observed workspace route used by the fleet:

- Muse Slack user: `U0C0TKRTQHZ`
- Muse DM conversation: `D0C1U7TUZEC`
- response deadline: 10 minutes after request construction
- selected-receipt freshness: 10 minutes after Muse's response

A route/identity change requires a code review and versioned policy update; callers may not override these values at runtime.

## Exact candidate

An election candidate binds six fields:

- `buyer_scope_sha256`
- `offer_scope_sha256`
- `intent_sha256`
- `body_sha256`
- `claimant`
- `operation_id`

Changing the body, offer, buyer, intent, claimant, or operation produces a different candidate digest. A selection for one digest cannot be composed with another candidate.

## Protocol

Prepare a request:

```bash
python -m tools.outbound_send_guard.muse_election prepare \
  --buyer-scope-sha256 "$BUYER_SHA" \
  --offer-scope-sha256 "$OFFER_SHA" \
  --intent-sha256 "$INTENT_SHA" \
  --body-sha256 "$BODY_SHA" \
  --claimant Z-Anvil \
  --operation-id COMMONS-MUSE-OUTBOUND-ELECTION-ZANV-20260914 \
  --request-id zanv-20260914-0001 \
  --requested-at 2026-09-15T00:30:00Z
```

Send the emitted `message` **unchanged** to the pinned Muse DM. It instructs Muse to reply exactly:

```text
SELECTED <request_id> <candidate_sha256>
```

or:

```text
NOT_SELECTED <request_id> <candidate_sha256>
```

Then reacquire the DM through the trusted Slack connector and construct an evidence object from the actual request and response messages:

```json
{
  "channel_id": "D0C1U7TUZEC",
  "request_message_ts": "1789432201.000001",
  "request_author_user_id": "U0CLAIMANT",
  "request_text": "<exact emitted message>",
  "response_message_ts": "1789432240.000001",
  "response_author_user_id": "U0C0TKRTQHZ",
  "response_text": "SELECTED zanv-20260914-0001 <candidate_sha256>"
}
```

Compile only with a complete prior-election ledger for this publication path:

```bash
python -m tools.outbound_send_guard.muse_election compile \
  --request request.json \
  --evidence evidence.json \
  --prior-ledger prior-election-receipts.json \
  --ledger-complete \
  --observed-at 2026-09-15T00:31:00Z
```

## Fail-closed holds

A receipt is `HOLD` when any of these are true, among others:

- Muse says `NOT_SELECTED` or does not use the exact response binding;
- wrong DM or wrong responder identity;
- response appears self-authored;
- request text differs from the compiled request;
- request/response ordering is impossible;
- Muse responds after the ten-minute election window;
- selected evidence is stale at compilation time;
- response echoes another request id or candidate digest;
- the prior-election ledger is incomplete/invalid;
- the same request, response, or evidence was already consumed by a prior receipt.

Malformed/tampered request artifacts are invalid and raise instead of degrading into an apparent policy decision.

## Authority ceiling

A valid `MUSE_SELECTED` receipt means only:

> fresh trusted-adapter evidence shows the pinned Muse identity selected this exact candidate, and the supplied complete prior-election ledger does not show this election evidence already consumed.

It **does not** mean:

- an email was sent;
- a recipient consented;
- an owner-policy decision was satisfied;
- buyer/contact dedupe is complete;
- provider capability is held;
- a payment or reply exists.

Both `external_send_authorized` and `side_effects_authorized` are always `false`. The sender must still satisfy the existing buyer/contact census, owner-policy gates when applicable, provider/turn lease, and fresh transport-side checks.

## Trust boundary

This module cannot cryptographically prove that an arbitrary Python dictionary came from Slack. The integration boundary is therefore explicit: `evidence` must be constructed from live Slack connector readback by a trusted adapter. The compiler's job is to bind that readback to the exact election candidate, make stale/cross-candidate/replayed evidence fail closed, and emit a tamper-verifiable receipt.
