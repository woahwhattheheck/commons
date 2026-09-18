# Outbound delivery truth / DSN reconciliation

`coordination/outbound_delivery_truth.py` is an offline transport-truth compiler. It exists because a provider accepting a message into a local **Sent** surface is not proof that the recipient system accepted or delivered it.

This surface is deliberately separate from Muse / OneWriter. Send coordination answers which exact session may attempt one provider mutation; delivery truth answers what retained transport evidence says happened afterward. This module never sends, retries, selects another route, authenticates a provider, proves buyer action, or recognizes revenue.

## State model

- `UNSENT`: no provider submission or historical local-Sent record.
- `PROVIDER_SUBMITTED_PENDING_DELIVERY`: exact provider submission is retained, but no structured delivery evidence exists. This is not delivery.
- `DELIVERED_EVIDENCE`: an exact-bound DSN has `action=delivered`, 2xx SMTP, and 2.x.x enhanced status.
- `DELIVERY_FAILED`: an exact-bound DSN has `action=failed`, 5xx SMTP, and 5.x.x enhanced status.
- `DELIVERY_UNKNOWN`: historical Sent without later evidence, transient 4xx evidence, or contradictory terminal evidence.

Time passing and absence of a bounce never promote a message to delivered.

Historical local-Sent migrates to UNKNOWN when no later transport evidence is retained. If a later structured DSN binds the exact historical provider/message/thread/recipient generation, that same generation may reconcile to FAILED or DELIVERED_EVIDENCE. The old Sent row itself is never terminal proof.

## Evidence contract

Schema: `commons.outbound-delivery-evidence/v1`.

The immutable outbound descriptor binds `operation_key`, `organization_id`, `counterparty`, `route`, `purpose`, `provider`, `subject_sha256`, and `body_sha256`. Its normalized canonical digest must match `outbound_descriptor_sha256`.

A provider submission or historical Sent row binds exact provider message id, provider thread id, recipient, UTC-second submission time, and retained `source_ref` / `source_sha256`.

Only structured `kind=DSN` events are admitted as delivery evidence. Each event must bind the exact provider, message id, thread id, recipient, DSN final recipient, and DSN original message id. Free-text prose is retained only as diagnostic text and never parsed into authority.

Supported structured classes:

| action | SMTP | enhanced | result |
|---|---:|---:|---|
| `delivered` | 2xx | 2.x.x | delivered evidence |
| `delayed` | 4xx | 4.x.x | unknown |
| `failed` | 5xx | 5.x.x | failed |

Wrong-message, wrong-thread, wrong-recipient, pre-submission, duplicate-id, duplicate-source-generation, semantic-remint, and reordered-event inputs fail closed. Contradictory delivered+failed terminal evidence compiles to UNKNOWN.

## Collision/contact projection

The output separates route viability from organization contact history:

- hard failure => `DEAD_ROUTE` + `DEAD_ROUTE_NOT_CONTACTED`;
- delivered evidence => `DELIVERED_CONTACT` with successful-contact delta 1;
- pending/unknown => `UNCONFIRMED_CONTACT` with successful-contact delta 0;
- revenue activity delta is always 0;
- alternate-route contact authorization is always false.

A dead route does not prove the organization was contacted and does not authorize trying another route. A caller must return to its normal single-writer/collision/owner policy before any new provider action.

## Authority ceiling

Every compile and verify result hard-falses send, retry, alternate-route, provider-action, buyer-acceptance, contract, payment, cash, receivable, and revenue authority. Retained source hashes bind bytes; they do not authenticate the provider.

## Replay and verification

The compiler emits a deterministic receipt and `verify_report(packet, report)` recomputes the complete semantic result. Rehashing an altered report cannot make it valid.

The JSON boundary rejects duplicate keys, floats/non-finite values, oversized integers, lone surrogates, excessive nesting, unexpected fields, and non-canonical identifiers. Retained file reads use descriptor-bound regular-file and pre/post generation checks.

`coordination/outbound_delivery_truth_demo.json` retains three synthetic `example.invalid` cases: delivered, historical local-Sent unknown, and a 550 / 5.4.1 hard failure. No real recipient or provider credential is present.

## Verification commands

```bash
python -m py_compile coordination/outbound_delivery_truth.py test_outbound_delivery_truth.py
python -m unittest -v test_outbound_delivery_truth.py
python -O -m unittest -v test_outbound_delivery_truth.py
python coordination/outbound_delivery_truth.py compile --input packet.json > report.json
python coordination/outbound_delivery_truth.py verify --input packet.json --report report.json
```
