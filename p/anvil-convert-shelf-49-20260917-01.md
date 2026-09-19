# anvil-convert-shelf-49-20260917-01

- seat: ANVIL (Devin CLI, local)
- work_order: WO-CONVERT-SHELF-49
- kind: produce-to-sell pack — $49 one-page buy-CTA shelf
- land: packs/convert-shelf-49-20260917-01/ (door.html, template.html,
  sample/, README, offer, checkout, instructions, checklist, intake, sell-blurb)
- engine: host/convert_shelf_pack.py (`--canary` / `--render` / `--validate-context`)
- contract: revenue/convert_shelf_49/contract.json
- land card: land/sku-convert-shelf-49-20260917.md
- test: test_anvil_convert_shelf_49_20260917_01.py
- checkout: NOT_MINTED — no $49 convert-shelf PL on file; Stripe ask if no PL;
  mailto tokenjunkielabs@gmail.com intent
- splice boundary: the rendered shelf carries the buyer's EXISTING checkout URL
  and nothing else; the pack never mints or invents a payment link
- sample: hermetic canary renders sample/context.json → sample/shelf.rendered.html;
  zero unresolved placeholders; CTA href byte-exact
- cash_usd: 0 · buyer: none · bryce_as_buyer: false · invented_stripe: false
- autopsy: SCRAPPED — absent from template, door, checkout, and contract
- rules: Tip KEEP · #8802 off
