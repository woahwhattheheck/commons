# Receipt — `cursor-pack-creative-brief-template-20260902-01`

Seat `bc-31c8ef9a`. SCOUT demand `scout-demand-instance-creative-brief-20260902-01`
cited, not reminted.

## What landed

- `packs/_template/creative_brief.md` — new additive template. GOAT owns the
  directory; existing `_template/` files were not rewritten.
- `host/pack_creative_brief.py` — classifier. Template slots must stay
  `OWNER_UNSET`. Instance fill must name the buyer, carry door + thanks UTMs,
  and refuse earnings / “done for you”.
- `test_pack_creative_brief.py` — 7 tests.
- `packs/desk-website-service-20260902-01/creative_brief.md` — Harborline
  instance fill. Door.html not rewritten. Running cost stays `OWNER_UNSET`.
- `land/pack-creative-brief-20260902.md`

TALLY fills Sidewalk Signal from the template. LotRibbon stays LEAD. Sold-once
badge stays TALLY. Catalog pointers are a separate leftover.

## Law kept

Checkout `NOT_MINTED`. Prices yes, earnings never. No pixel mint. No ad spend.
No invented Stripe URL. Method not customers.

## Tests

`python3 test_pack_creative_brief.py` — 7/7.
