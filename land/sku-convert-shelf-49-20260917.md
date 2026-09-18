# Land — sku-convert-shelf-49-20260917

- work_order: WO-CONVERT-SHELF-49
- cite: anvil-convert-shelf-49-20260917-01
- pack: packs/convert-shelf-49-20260917-01/
- door: packs/convert-shelf-49-20260917-01/door.html
- engine: host/convert_shelf_pack.py
- test: test_anvil_convert_shelf_49_20260917_01.py
- contract: revenue/convert_shelf_49/contract.json
- checkout: NOT_MINTED (Stripe ask if no PL; mailto tokenjunkielabs@gmail.com)
- cash_usd: 0
- buyer: none
- bryce_as_buyer: false
- invented_stripe: false
- autopsy_sold: false
- sample: hermetic canary — `python3 host/convert_shelf_pack.py --canary --json`
  renders sample/context.json → sample/shelf.rendered.html, zero placeholders,
  splice href byte-exact.
- boundary: buyer's EXISTING checkout URL only; never mint; Autopsy SCRAPPED.
- Tip KEEP · #8802 off
