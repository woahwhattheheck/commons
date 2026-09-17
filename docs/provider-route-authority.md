# Provider-route authority control

This package turns an evidence packet into one deterministic, fail-closed outbound decision. It **does not send anything** and grants no buyer, provider, payment, or revenue authority.

The operating problem is simple: coordination state can say a route is clear while the mailbox already contains a provider SENT receipt, delivery-status notification, or human reply. A second writer that trusts only Slack can duplicate contact or start route-spraying. This compiler gives provider/mailbox evidence priority over stale intent.

## Decision states

| State | Meaning |
| --- | --- |
| `ALLOW_ONE_SEND` | One exact `org × route × purpose` attempt is permitted by the compiled evidence. Recompile immediately after the attempt or any new event. |
| `HARD_DNR` | The exact subject was provider-SENT. Wait for a genuine event. |
| `DEAD_ROUTE` | The route hard-bounced. A bounce is **not** permission to choose another address. |
| `HOLD_UNKNOWN` | Evidence is incomplete, delivery is uncertain, another purpose/route is already active, or the org-level route-spray guard is engaged. |
| `INBOUND_ONLY` | A genuine human reply/rejection exists for the organization; automated follow-up authority stops. |

## Precedence

1. Any same-organization human reply/rejection → `INBOUND_ONLY`.
2. Any hard bounce on the exact route (even for another purpose) → `DEAD_ROUTE`.
3. Two or more distinct hard-bounced routes for the organization → `HOLD_UNKNOWN` / route-spray guard.
4. Soft bounce/provider timeout on the route → `HOLD_UNKNOWN`.
5. Provider SENT on the exact route and purpose → `HARD_DNR`.
6. Provider SENT on the same route for another purpose → `HOLD_UNKNOWN`.
7. Provider SENT on another route for the same organization → `HOLD_UNKNOWN` rather than silent fanout.
8. Only after all provider/mailbox holds are absent may current `SLACK_TAKE + ROUTE_VERIFIED + MUSE_CLEAR` produce `ALLOW_ONE_SEND`.

`MUSE_CLEAR` and `ROUTE_VERIFIED` must be at or after the exact subject's `SLACK_TAKE`. A newer Muse event cannot override provider truth.

## Evidence model

Each event binds:

- immutable `event_id`;
- event `kind` and its mandatory source class (`SLACK`, `MUSE`, `PUBLIC_EVIDENCE`, `PROVIDER`, or `MAILBOX`);
- timezone-aware timestamp;
- organization, purpose, route type, and route;
- an append-only evidence reference.

The parser rejects duplicate JSON keys, floats, duplicate event IDs, source/kind forgery, malformed emails, naive timestamps, and unexpected fields. Input events are canonicalized before SHA-256 receipt hashing, so packet order cannot change the decision or digest.

## CLI

```bash
python -m revenue.provider_route_authority.cli compile INPUT.json > RECEIPT.json
python -m revenue.provider_route_authority.cli verify INPUT.json RECEIPT.json
```

Only a compiled `ALLOW_ONE_SEND` is positive authority, and it is deliberately narrow: one exact attempt. The caller must append the resulting provider/mailbox event and recompile before considering any additional action.

## Synthetic route-spray example

`revenue/provider_route_authority/fixtures/two-hard-bounces.json` contains two different hard-bounced mailboxes for one synthetic organization plus otherwise-valid coordination gates. It compiles to `HOLD_UNKNOWN` with `ROUTE_SPRAY_GUARD`, proving that two transport failures cannot be transformed into permission to try a third address.
