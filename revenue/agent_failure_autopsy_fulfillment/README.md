# Agent Failure Autopsy — deterministic fulfillment spine

This package lowers the marginal fulfillment cost of the **existing** `$29 / one business day` Agent Failure Autopsy. It does not create a new product or checkout. The canonical purchase surface remains `agent-rescue.html` and its existing Stripe link.

## Money truth

A buyer-facing page, intake brief, queue row, Git commit, or packet is **not** payment. `payment.state=VERIFIED_PAID` is an operator assertion made only after the operator has read back a provider receipt. This package does not authenticate Stripe, capture money, issue refunds, send email, contact buyers, recognize revenue, or accept an upsell. Those authority flags are hard-false in every verified packet.

## Workflow

1. Buyer purchases through the existing checkout and sends only sanitized, in-cap evidence using the published handoff.
2. Operator verifies the provider receipt outside this package and records only a receipt SHA-256 plus `VERIFIED_PAID`; raw payment data is not stored here.
3. Operator enters the sanitized case fields and digest-only evidence metadata.
4. `core.py compile` creates an exclusive output directory containing `packet.json` and `report.md`.
5. Queue state is derived, never caller-selected:
   - `HOLD_PAYMENT_UNVERIFIED`
   - `HOLD_INTAKE_INCOMPLETE`
   - `READY_FOR_ANALYSIS`
   - `REFUND_REQUIRED`
   - `DELIVERED`
6. Completed delivery or refund requires an explicit operator receipt digest; neither is inferred from intent or checkout. Once a refund is satisfied by provider `REFUNDED` state or a refund-receipt digest, the case remains in packet history but is removed from the active work queue.
7. For a later larger engagement, use the existing `$12k GGUF` / `$30k White Box` pages. This package cannot claim that a buyer accepted either offer.

## Strict ingress

Input is strict JSON: duplicate keys and non-finite constants fail closed; exact keys/types are required; bool/int aliases are rejected; evidence is digest-only metadata; obvious email, URL, phone and credential/token shapes are refused from sanitized text; case refs are bounded opaque identifiers. Max one batch is 100 cases; each case allows at most 10 evidence items and 25 MB cumulative raw-byte metadata, matching the public intake cap.

## CLI

```bash
python revenue/agent_failure_autopsy_fulfillment/core.py compile \
  revenue/agent_failure_autopsy_fulfillment/sample_input.json \
  /tmp/autopsy-output
python revenue/agent_failure_autopsy_fulfillment/core.py verify \
  /tmp/autopsy-output/packet.json
```

Publication is create-exclusive: the output directory must not already exist.

## Sample

`sample_input.json`, `sample_packet.json`, and `sample_report.md` are synthetic. The sample is deliberately **UNVERIFIED / unpaid**, so it cannot be reused as proof of a sale or cash receipt.
