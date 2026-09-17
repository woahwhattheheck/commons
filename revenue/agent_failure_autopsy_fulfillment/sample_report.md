# Agent Failure Autopsy fulfillment queue

Schema: `agent-autopsy-fulfillment-report/v1`  
Packet receipt: `076d3b12250a48e3720fc64c1d53e25e026914a7da530b15d32ea4bc1c2a9f19`  
Price: **$29 USD per existing canonical checkout**  
Payment truth: this layer records operator-asserted provider-receipt state; it does not authenticate Stripe or move funds.

## Queue

- `SYNTHETIC-UNPAID-001` — **HOLD_PAYMENT_UNVERIFIED** — `80c2c5e72517e7074b39774dd45a385bb318e7592795a35d16399fb3eae8ae4b`

## Case details

### SYNTHETIC-UNPAID-001
- state: `HOLD_PAYMENT_UNVERIFIED`
- payment: `UNVERIFIED`
- evidence: 1 item(s) / 1200 byte(s)
- refund satisfied: `false`
- reason(s): operator must verify the existing checkout receipt before analysis starts

## Authority ceiling

This artifact cannot send email, contact a buyer, capture/refund payment, claim cash received, recognize revenue, or accept an upsell. Those authorities are all false in the verified packet.
