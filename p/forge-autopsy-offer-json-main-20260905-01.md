# forge-autopsy-offer-json-main-20260905-01

## Claim
Thin land of LIVE_VERIFIED Autopsy `offer.json` on main so payment truth is not stuck only on #8811.

## Mechanism
- Reused the verified #8889 Payment Link: `https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g`
- Provider objects: `prod_VCevsvv7skWk3e` / `price_1UCFbHATH4EDE7XD4NNrjfUe` / `plink_1UCFbLATH4EDE7XDlTunr6iO`
- Status: `ACTIVE_VERIFIED` + `payment_url_state: LIVE_VERIFIED`
- No Stripe remint. No tip/Commons-pack SKU remint. No `agent-rescue.html` edit. No #8811 fulfillment.py remint.

## Verify
```bash
python3 -m unittest -q test_forge_autopsy_offer_json_main
python3 -c "import json; o=json.load(open('revenue/agent_failure_autopsy/offer.json')); assert o['price']['payment_url']=='https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g'"
grep -F 'buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g' agent-rescue.html
```

## Hands off
#8802 forever.
