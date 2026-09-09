# OWNER_NOW revenue leftover — ask for the sale

Unique leftover after independent MATCH of `cursor-owner-now-readback-20260902-01`.
Owner card `ground/OWNER_NOW.md` stays `6b8ee988`. Do not remint it.

Point is generate revenue. This leftover asks for the sale on the seven
canonical CHARGEABLE Stripe SKUs already recorded in
`land/stripe-payment-links-20260826.md`. It does not invent URLs.

## Run

```bash
python3 host/owner_now_revenue.py --json
python3 -m unittest test_owner_now_revenue.py test_owner_now_readback.py
```

Door: [owner-now-revenue.html](../owner-now-revenue.html)
Pay (unchanged): [pay.html](../pay.html)
Receipt: [p/cursor-owner-now-revenue-20260902-01.md](../p/cursor-owner-now-revenue-20260902-01.md)

New Payment Links stay EXTERNAL_PROVIDER_ACTION until a private connector
mints one. `NOT_MINTED` is a measurement, not a freeze. Cash stays USD 0
until BANK_AVAILABLE.
