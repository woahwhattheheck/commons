# Outbound route lifecycle authority

`route_lifecycle.py` classifies **route-specific delivery evidence** after an outbound message was accepted by the sending provider. It closes a gap between “provider accepted the send” and “this address is safe to use again.”

The motivating live shape was a provider-SENT message followed by a delivery-status notification for the exact recipient and provider message: SMTP `550`, enhanced status `5.1.1`, `User Unknown`. Treating only the send receipt as evidence would suppress that distinction; treating the bounce as permission to contact another address would be equally unsafe.

This tool does neither. It emits one read-only receipt:

- `BLOCK_ROUTE`: exact route is suppressed. v1 grants this only for explicit complaint/unsubscribe evidence or DSN enhanced status `5.1.1` (bad destination mailbox).
- `HOLD_ROUTE`: retry is not authorized because the route has a temporary, non-allowlisted permanent, or internally conflicting delivery signal.
- `DELIVERED`: an explicit delivery event exists for the exact provider message and recipient.
- `UNCONFIRMED`: a complete lookup has no delivery/failure event for that exact message.

**No decision authorizes another send.** Every receipt has `same_route_resend_authorized=false`, `alternate_route_requires_independent_send_guard=true`, and `side_effects_authorized=false`. A different public/business route must independently pass the existing outbound-send guard and its complete mailbox+Slack evidence compiler.

## Evidence contract

Input schema: `outbound-route-lifecycle-evidence/v1`.

The envelope binds one exact send with `recipient`, `provider_message_id`, `sent_at`, a shared `as_of` boundary, `query_id`, `complete: true`, and `next_cursor: null`. Every event must bind that same recipient/message, fall between `sent_at` and `as_of`, and carry a `source_id` plus lowercase SHA-256 of the raw source record used by the collector.

Supported event kinds:

- `dsn`: must carry integer 4xx/5xx SMTP code and matching enhanced-status class;
- `delivered`;
- `complaint`;
- `unsubscribe`.

Exact duplicate event IDs collapse. Reuse of an event ID with changed facts fails closed. A delivery event coexisting with any failure/block signal becomes `HOLD_ROUTE/unknown`; the reducer does not guess which provider event is authoritative.

v1 intentionally hard-blocks only `5.1.1` among DSN codes. Other 5xx statuses (policy rejection, mailbox-full variants, etc.) are `HOLD_ROUTE`, because a permanent SMTP failure does not necessarily prove the address itself is dead. 4xx is also `HOLD_ROUTE`.

## CLI

```bash
python -m tools.outbound_send_guard.route_lifecycle \
  --evidence route-evidence.json \
  --out route-receipt.json
```

Exit codes: `0 DELIVERED`, `3 UNCONFIRMED`, `4 HOLD_ROUTE`, `5 BLOCK_ROUTE`, `2 invalid evidence/publication failure`.

The CLI rejects direct/hardlink/symlink input-output aliasing and atomically stages/fsyncs the receipt before replacement. Publication failure preserves any prior receipt.

## Regression gate

```bash
python -m py_compile tools/outbound_send_guard/route_lifecycle.py tools/outbound_send_guard/test_route_lifecycle.py
python -m unittest -v tools.outbound_send_guard.test_route_lifecycle
python -O -m unittest -v tools.outbound_send_guard.test_route_lifecycle
```
