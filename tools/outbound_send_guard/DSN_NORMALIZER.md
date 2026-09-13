# Delivery-status (DSN) normalizer

`dsn_normalizer.py` converts one raw RFC delivery-status notification into the
strict `dsn` event shape accepted by `route_lifecycle.py`.

It closes the collector boundary exposed by live Gmail/Googlemail failures:
`route_lifecycle.py` deliberately expects normalized evidence, while mailbox
records arrive as `multipart/report; report-type=delivery-status` messages with
per-message and per-recipient fields.

This normalizer is evidence-only. It never sends mail and every receipt sets
`side_effects_authorized=false`.

## Binding input

The raw MIME is paired with one explicit `outbound-dsn-binding/v1` object:

```json
{
  "schema_version": "outbound-dsn-binding/v1",
  "source_id": "dsn-provider-record-id",
  "provider_message_id": "original-provider-send-id",
  "original_rfc822_message_id": "<original-message-id@example>",
  "recipient": "buyer@example.com",
  "sent_at": "2026-09-13T09:26:31Z",
  "captured_at": "2026-09-13T09:27:00Z"
}
```

The binding separates provider identity from RFC message identity. The
normalizer never guesses a provider message id from the bounce.

## Fail-closed extraction contract

The raw message must:

- be at most 10 MiB and parse without MIME defects;
- be `multipart/report` with `report-type=delivery-status`;
- contain exactly one `message/delivery-status` part;
- bind the expected original RFC Message-ID through
  `X-Original-Message-ID`, `In-Reply-To`, or both; every present supported
  binding must agree;
- contain exactly one per-recipient block whose `Final-Recipient` matches the
  expected route (case-insensitive);
- use `rfc822` recipient addressing;
- carry `Action: failed` + `5.x.x`, or `Action: delayed` + `4.x.x`;
- carry `Diagnostic-Code: smtp; ...` with one unambiguous 4xx/5xx SMTP code
  whose class agrees with `Status`;
- have an outer `Date` between the original send and capture boundary.

A multi-recipient DSN is allowed only when the expected route matches exactly
one block. Other recipient blocks are not emitted. A duplicate target block,
missing target, conflicting original-message binding, malformed status,
multiple SMTP codes, unsupported diagnostic type, or boundary violation
fails closed.

The emitted event contains only:

- deterministic content-addressed `event_id`;
- `kind=dsn`;
- exact provider message id and normalized recipient;
- normalized observed timestamp;
- source record id + SHA-256 of the complete raw MIME;
- SMTP code and enhanced status.

Human-readable diagnostic prose, remote host text, and arbitrary DSN payload
content are intentionally not copied into authority evidence.

## Receipt

The `outbound-dsn-normalizer-receipt/v1` receipt binds the exact raw source
digest, exact binding digest, original-message binding sources, recipient block
cardinality, the normalized event and event digest, plus a final
content-addressed receipt digest. `verify_receipt()` checks the integrity and
the no-side-effects invariant.

The event can then be inserted into a complete
`outbound-route-lifecycle-evidence/v1` envelope and evaluated by the already
landed route-lifecycle authority. This adapter itself never returns
`BLOCK_ROUTE`, `HOLD_ROUTE`, or any send/resend permission.

## CLI

```bash
python -m tools.outbound_send_guard.dsn_normalizer \
  --raw-mime dsn.eml \
  --binding binding.json \
  --out dsn-receipt.json
```

Output publication is staged, fsynced, and atomically replaced.

## Regression gate

```bash
python -m py_compile \
  tools/outbound_send_guard/dsn_normalizer.py \
  tools/outbound_send_guard/test_dsn_normalizer.py

python -m unittest -v tools.outbound_send_guard.test_dsn_normalizer
python -O -m unittest -v tools.outbound_send_guard.test_dsn_normalizer
```

Coverage includes the observed Googlemail/Exchange `550 5.4.1` shape, unrelated
multi-recipient blocks, duplicate/missing target ambiguity, independent and
conflicting original-message bindings, 4xx delay handling, action/status/SMTP
class mismatches, missing/non-SMTP/multi-code diagnostics, capture-time bounds,
MIME/report-type rejection, strict binding schema, case-folded route matching,
stable identity/digests, receipt tampering, side-effect escalation, malformed
Message-ID/addressing, and raw-size bounds.
