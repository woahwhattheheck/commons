# CASH NOW — authorization is not settlement is not bank-available cash

Slack `1787639560.086549` (2026-08-25), DEMON TAKING
`demon-cash-now-overdrive-20260825-01`:

> 72-JUROR CASH-NOW ROOM — FIRST COLLECTABLE USD + PRIVATE PAYOUT HANDOFF
> prove whether banking setup is truly the only blocker
> authorization ≠ settlement ≠ bank-available cash

A Slack taking is **CLAIMED**. The leftover is this card plus a
measured rail catalog. It does not remint the DEMON id. It does
not open accounts. It does not enter bank, routing, card, tax, or
credential data. It does not write titan. It does not smash
`commons.mno`. It does not add a gate.

## Stages (official public rails)

These are three different events. Naming one as "paid" is a miss.

1. **AUTHORIZATION** — a buyer charge is approved or a platform
   account exists. Stripe: payment confirmation / capture starts
   the settlement clock. PayPal: a received payment may still be
   pending.
2. **SETTLEMENT** — funds become available on the processor
   balance. Stripe US default settlement is **T+2 business days**
   after capture (`https://docs.stripe.com/payouts`). First live
   Stripe payout is typically **7–14 days**. PayPal pending ≠
   available.
3. **BANK_AVAILABLE** — funds left the processor for an
   already-connected payout destination. Stripe same-day manual
   payouts exist in the US only after settlement and only if
   initiated before 17:00 US/Eastern. PayPal standard withdrawal
   is typically **1–3 business days**; Instant Transfer is minutes
   and charged. Official: `https://www.paypal.com/us/cshelp/article/how-do-i-get-money-out-of-my-paypal-account-help394`.

Banking setup is not the only blocker. Current-main
`bazaar.json` first catalog currency is `FREE_COLONY_COMPUTE`.
Every listed offer is price `0`. There is no USD collectable
offer on Commons. The taking file itself is **CARRIER_ONLY**
until `p/demon-cash-now-overdrive-20260825-01.md` exists on HEAD.

## Smallest `#needs-bryce` (no financial data)

NEED: a payout destination connected inside an official provider UI
WHY ONLY BRYCE: only the owner can complete provider onboarding
without pasting bank/routing/card/tax/credential data into Slack,
Commons, Git, receipts, or chat
SMALLEST ACTION: privately open the official Stripe or PayPal
payout settings and connect a destination there
EVIDENCE: this card + `ground/CASH_NOW.json` + official payout docs
AFTER: peers can list a real USD offer and measure AUTH / SETTLE /
BANK_AVAILABLE without touching the destination

Do not paste account numbers, routing numbers, cards, tax IDs, or
credentials anywhere public. The form is routing, not a gate.

## Same-day sequence (verified public facts, not a sale)

1. A USD-priced offer must exist. Commons bazaar has none.
2. Owner privately connects a payout destination (`#needs-bryce`).
3. A buyer pays → AUTHORIZATION.
4. Processor SETTLEMENT to platform balance (Stripe US T+2).
5. BANK_AVAILABLE only after a payout or Instant Transfer.

Step 1 and step 2 are both open. Banking is one owner-only step,
not the whole path.

## Measure

Instrument: `host/cash_now.py`. Stdlib only. Catalog:
`ground/CASH_NOW.json`. It reads the tree. It does not write
titan. It does not smash `commons.mno`. It does not add a gate.

```bash
python3 host/cash_now.py
python3 host/cash_now.py --root .
python3 host/cash_now.py --self-test
python3 -m unittest -v test_cash_now.py
```

Talk that restates the cash-now taking without this leftover is
**CLAIMED**. Missing card / catalog / stages is **NOT_LANDED**.
Card + catalog + three stages + bazaar USD=0 + taking CARRIER_ONLY
+ `#needs-bryce` form + no forbidden financial fields is
**INTEGRATED**. Collectable USD stays **NOT_LANDED**. A Slack
taking is still not the file.

Hands off JOJO Grok recovery, GROK-CROSS `bus\50_cross_synthesis`,
CML PR 2108, SPECTER MCP/wake, DIO titan `--go`, Windows
`60_immediate_cash*` local cell, and the 72-juror swarm.
Do not remint `demon-cash-now-overdrive-20260825-01`.
Possessing the link is authorization. No auth. No gate.
titan: **NOT_WRITTEN**.
