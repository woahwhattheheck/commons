---
from: CODEX
id: website-prospect-boundary-repair-20260830-01
kind: SHIP_RECEIPT
status: BUILT_AND_TESTED
source: slack:1788068123.766099
trigger: slack:1788095635.373319
---

# Website loop: external-prospect boundary repaired

The Explee screenshot's measured contract is seller website → people who need
the product → email draft → booking CTA. The first landed implementation instead
treated people published on the seller's own page as buyers and drafted pitches
back to them.

This repair composes the seller website with the existing evidence-bound Smart
Outreach catalog and receipt collision index. Seller-page people remain visible
as `seller_contacts` context but can never become outreach targets. External
prospects retain first-party source evidence, route state, occupancy, and
collision receipts. Only a `READY_TO_DRAFT` external prospect with one verified
email route receives a staged draft. No transport or live booking is claimed.

Measured default readback at `2026-08-30T13:14:08Z`: 1 seller website, 4 seller
contacts observed, 3 external prospects evaluated, 0 eligible drafts, 0 sent,
0 booked, USD 0. The zero-draft result is current collision/route truth, not a
mock: a qualified external-catalog canary produces one evidence-bound draft,
while a same-domain seller canary is held.

Verification:

```sh
python3 -m unittest -v test_website_people_email_book.py test_smart_outreach.py
python3 host/website_people_email_book.py validate
node --check website-people-email-book.js
python3 open_door_guard.py --diff HEAD^ HEAD
```
