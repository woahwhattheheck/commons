# Outbound delivery truth

This offline control-plane distinguishes provider submission from delivery evidence.

State contract:

`UNSENT -> PROVIDER_SUBMITTED_PENDING_DELIVERY -> {DELIVERED_EVIDENCE | DELIVERY_FAILED | DELIVERY_UNKNOWN}`

A retained provider submission is not delivery proof. A bound DSN with structured `action=failed` and enhanced SMTP status `5.x.x` yields `DELIVERY_FAILED` unless contradictory terminal evidence exists. Bound positive provider evidence with `action=delivered` and `2.x.x` yields `DELIVERED_EVIDENCE`. Missing, soft, ambiguous, unbound, or contradictory evidence remains `DELIVERY_UNKNOWN`.

Absence of a DSN is never promoted to delivery. Free-text diagnostic wording is retained but cannot override the structured enhanced status.

Every event is bound to provider, provider message id, provider thread id, sender, and recipient. Wrong-generation evidence cannot change state. Duplicate source generations and semantic remints under new wrapper ids or blobs fail closed. Timestamps are canonical whole-second UTC and evidence cannot predate submission.

The collision projection separates organization-contact evidence from route viability. Hard failure marks the exact route as dead evidence without asserting organization contact. Delivery evidence may count as contact evidence. No state authorizes a new send, retry, alternate route, provider mutation, payment, cash, or revenue recognition. A separate current single-writer lease remains required for any later outbound action.

`compile_delivery_truth(packet)` emits a deterministic diagnostic plus SHA-256 receipt. `verify_delivery_truth(packet, artifact)` authenticates that receipt and performs semantic recompile. `outbound_delivery_truth.examples.json` retains synthetic hard-failure, unknown, and delivered replay cases using reserved `.invalid` addresses.
