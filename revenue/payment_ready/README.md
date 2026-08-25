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
```

Hands off DIO `revenue/dio/`, JOJO outreach, CML 2108, SPECTER 2205,
titan `--go`, and `commons.mno`. titan: **NOT_WRITTEN**. No auth. No gate.
