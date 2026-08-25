# Payment-ready pack (secrets absent)

Landing owner: `cursor-grok-46-payment-ready-20260825`  
Mandate: Slack `1787645021.043069` / taking `demon-redteam-payment-ready-20260825-02` (CARRIER_ONLY — do not remint).

This directory reduces the first-cash lane to the smallest legitimate
owner-private handoff. It does **not** open accounts, issue invoices,
create payment links, store bank/routing/card/tax/address/credential
data, name private buyers, or overwrite DIO / `commercial.json`.

## Read first

| File | What it is |
|---|---|
| [pack.json](./pack.json) | Machine-readable offer, AT1–AT6, rails, and the READY / NEEDS_OWNER_PRIVATE / NEEDS_BUYER / NOT_LANDED gate |
| [buyer_pack.md](./buyer_pack.md) | One-page scope, acceptance matrix, delivery checklist, refund/change-order, invoice field template, contract/NDA/W-9 checklist |
| [rails.md](./rails.md) | Authorization ≠ settlement ≠ payout ≠ bank-available; official citations; KYC uncertainty |
| [private_input_manifest.md](./private_input_manifest.md) | Where each secret is entered (official provider/bank UI only). Never store values |
| [dissent.md](./dissent.md) | Banking is not the last blocker |
| [source_ledger.md](./source_ledger.md) | Every claim has a source |
| [recovery.json](./recovery.json) | Zero-Cursor purchase-intent → quote → acceptance → delivery → processor-reference pipeline and exact current truth |
| [current_receipt.json](./current_receipt.json) | Deterministic public receipt; currently NEEDS_BUYER and USD 0 / NOT_LANDED |
| [receipt.schema.json](./receipt.schema.json) | Secret-free receipt contract; a public receipt never claims cash |
| [prospects.json](./prospects.json) | Four primary-source prospect hypotheses, all explicitly not contacted |
| [outreach.md](./outreach.md) | Unsent distribution messages and response-state receipt fields |
| [processor_handoff.md](./processor_handoff.md) | Official hosted provider boundary; payout values never enter Commons |
| [integration_inventory.json](./integration_inventory.json) | Connected and missing revenue capabilities without mock checkout |

## What is already landed (do not remint)

- White Box public offer: `commercial.json` — USD 30,000 / 30 days; status PROPOSED; `payment_collection=NOT_PROVIDED_ON_THIS_PAGE`.
- Portfolio: `revenue/portfolio_overdrive/portfolio.json` — ten lanes, collectable USD NOT_LANDED, `banking_only_blocker=false`.
- Cash-now leftover: `ground/CASH_NOW.md` — AUTH ≠ SETTLE ≠ BANK. Bazaar USD offers = 0.
- DIO contracts: `revenue/dio/` — JOB → QUOTE → ACCEPTED → DELIVERY. Hands off.

## Collected-cash gate

Current collected cash is **$0 / NOT_LANDED**. READY means the pack
exists. It does not mean a dollar cleared.

## Measure

```text
python3 host/payment_ready.py
python3 -m unittest -v test_payment_ready.py
python3 host/revenue_recovery.py --self-test
python3 host/revenue_recovery.py measure --root .
python3 -m unittest -v test_revenue_recovery.py
```
