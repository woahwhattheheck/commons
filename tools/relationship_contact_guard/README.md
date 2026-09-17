# Relationship Contact Guard

`relationship_contact_guard` is a **coordination diagnostic**, not an outbound sender and not an authorization surface.

It closes a fleet-level anti-spam gap that exact-recipient single-writer locks cannot close by themselves: two workers may hold different operation keys or routes for the same organization/opportunity and each can appear locally clean while still hitting one hot relationship too close together.

## What it binds

A packet contains one proposed contact and an ordered retained event history. The guard binds canonical counterparty, opportunity, route, purpose, process-owned evaluation time, provider message/thread identifiers, human-response lineage, human-negative scope, explicit reopen target, and event chronology. It emits canonical JSON plus a SHA-256 semantic receipt.

The compiler detects, among other cases:

- same counterparty contacted recently through a different route or operation key;
- same opportunity/purpose contacted within a longer pursuit window;
- exact route/purpose provider-SENT with no later resolving event (`HOLD_EXACT_DNR`);
- a route with a retained hard-bounce (`HOLD_DEAD_ROUTE`) without converting that transport failure into organization rejection;
- explicit human negative/opt-out at route-purpose or whole-counterparty scope;
- a genuine retained human reply, which converts the lane to inbound review rather than fresh outbound;
- future-dated, reordered, duplicate, orphaned, cross-counterparty, noncanonical, or malformed evidence.

Callers may lengthen cooldowns but cannot weaken the code-owned floors: six hours for counterparty contact and 72 hours for same-opportunity/same-purpose pursuit contact.

## Response lineage and reopen semantics

A bounce or human response is accepted only when its `in_reply_to_message_id` refers to an earlier retained `PROVIDER_SENT` **and** its counterparty, opportunity, route, purpose, and optional provider thread exactly match that send. A response cannot be transplanted from another opportunity or route merely because a provider message id exists.

`HUMAN_REOPEN` is not a generic "relationship is clear" signal. It must carry:

- `in_reply_to_message_id`;
- `reopens_event_id` naming an earlier retained `HUMAN_NEGATIVE`;
- `scope` equal to that negative's scope;
- the exact counterparty/opportunity/route/purpose/message lineage of that negative.

Only that explicitly referenced negative is reopened. If multiple negatives are retained, every unreopened negative remains active; reopening a newer one cannot silently erase an older opt-out.

A retained hard bounce also remains transport-dead evidence even if later contradictory human-shaped evidence exists for the same send.

## Process-owned currentness

Packets do **not** carry a caller-controlled `now`. `compile_guard()` samples current UTC from the process and retains the exact whole-second `evaluated_at` in the artifact. This prevents a caller from aging recent contacts out of a cooldown by supplying a forged clock.

`verify_guard()` replays the artifact at its retained evaluation timestamp to prove artifact integrity, but first samples process UTC and rejects a future timestamp or an artifact older than the code-owned five-minute verification window. This prevents a caller from forging a far-future `CURRENT` time to age contacts out. Verification still does **not** establish that provider/Slack state is current or complete; `truth.verify_replay_establishes_currentness` is therefore always false.

## Truth boundary

Every artifact builds its authority map from source-literal false values. The exported `AUTHORITY` object is compatibility/documentation only and is not used to mint semantic output. Ordinary mutation or rebinding of that module attribute cannot widen compile or verify results.

These fields are always false:

- `send_authorized`
- `muse_authorized`
- `provider_send_proven`
- `buyer_acceptance_proven`
- `contract_proven`
- `payment_proven`
- `cash_proven`
- `revenue_recognized`

`NO_CONFLICT_FOUND` means only **no conflict was found in the supplied retained packet at the retained process-owned evaluation time**. This compiler neither proves the packet complete nor authenticates current provider state. Before external mutation, the executor still needs a fresh Slack + provider census and the session-bound Muse lease/consume/GO protocol. A HOLD here cannot be overridden by treating another coordination receipt as send authority.

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
    "purpose": "paid-qa-workshare"
  },
  "events": []
}
```

Provider sends require `provider_message_id`. Bounces and human responses must reference an earlier retained provider send through `in_reply_to_message_id`. Human negative events bind `scope` as either `ROUTE_PURPOSE` or `COUNTERPARTY`; reopen events additionally bind the exact prior negative through `reopens_event_id`.

## Proof

The retained root suite exercises strict JSON ingress, retained-time receipt replay, cross-route and cross-key collisions, route-scoped bounces, response opportunity/route/purpose/thread transplant rejection, exact negative-to-reopen binding, packet-transplant rejection, Unicode/noncanonical identifiers, cooldown-floor protection, future/reordered/duplicate evidence, CPython large-integer parser normalization, multiple-negative reopen isolation, hard-bounce precedence, future/stale verifier-time rejection, process-clock callback injection resistance, and source-literal hard-false authority under ordinary module rebinding. The same suite is required under normal Python and real `python -O`.
