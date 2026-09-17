# Relationship Contact Guard

`relationship_contact_guard` is a **coordination diagnostic**, not an outbound sender and not an authorization surface.

It closes a fleet-level anti-spam gap that exact-recipient single-writer locks cannot close by themselves: two workers may hold different operation keys or routes for the same organization/opportunity and each can appear locally clean while still hitting one hot relationship too close together.

## What it binds

A packet contains one proposed contact and an ordered retained event history. The guard binds canonical counterparty, opportunity, route, purpose, process-owned evaluation time, provider message/thread identifiers, human response scope, and event chronology. It emits canonical JSON plus a SHA-256 semantic receipt and verifies by exact deterministic recompile.

The compiler detects, among other cases:

- same counterparty contacted recently through a different route or operation key;
- same opportunity/purpose contacted within a longer pursuit window;
- exact route/purpose provider-SENT with no later resolving event (`HOLD_EXACT_DNR`);
- a route with a retained hard-bounce (`HOLD_DEAD_ROUTE`) without converting that transport failure into organization rejection;
- explicit human negative/opt-out at route-purpose or whole-counterparty scope;
- a genuine retained human reply, which converts the lane to inbound review rather than fresh outbound;
- future-dated, reordered, duplicate, orphaned, cross-counterparty, noncanonical, or malformed evidence.

Callers may lengthen cooldowns but cannot weaken the code-owned floors: six hours for counterparty contact and 72 hours for same-opportunity/same-purpose pursuit contact.

## Truth boundary

Every artifact hard-codes these to false:

- `send_authorized`
- `muse_authorized`
- `provider_send_proven`
- `buyer_acceptance_proven`
- `contract_proven`
- `payment_proven`
- `cash_proven`
- `revenue_recognized`

`NO_CONFLICT_FOUND` means only **no conflict was found in the supplied retained packet**. This compiler neither proves the packet complete nor authenticates provider state. Before external mutation, the executor still needs a fresh Slack + provider census and the session-bound Muse lease/consume/GO protocol from the atomic OneWriter successor. A HOLD here cannot be overridden by treating another coordination receipt as send authority.

## CLI

```bash
python tools/relationship_contact_guard/guard.py compile packet.json artifact.json
python tools/relationship_contact_guard/guard.py verify packet.json artifact.json
```

The packet shape is intentionally small:

```json
{
  "candidate": {
    "counterparty_id": "example.com",
    "opportunity_id": "example-rfp-1",
    "route": "sales@example.com",
    "purpose": "paid-qa-workshare",
    "now": "2026-09-17T19:00:00Z"
  },
  "events": []
}
```

Provider sends require `provider_message_id`. Bounces and human responses must reference an earlier retained provider send through `in_reply_to_message_id`. Human negative events additionally bind `scope` as either `ROUTE_PURPOSE` or `COUNTERPARTY`.

## Proof

The retained root test exercises strict JSON ingress, receipt exact-recompile, cross-route and cross-key collisions, route-scoped bounces, human-negative scopes/reopen, provider response lineage, packet-transplant rejection, Unicode/noncanonical identifiers, cooldown-floor protection, future/reordered/duplicate evidence, and the hard false authority ceiling under normal Python and real `python -O`.
