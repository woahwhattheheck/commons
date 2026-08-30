# Website → people → email → book

Explee-style auto-GTM loop as a Commons capability. The **seller website is the
seed**. Drop a public page, extract the product and ICP, qualify external people
who need it from the existing evidence-bound Smart Outreach catalog, draft
emails with a book-a-call CTA, and stage bookings.

Contacts published on the seller website are retained as `seller_contacts`
context and are never treated as prospects. External candidates keep their
first-party evidence, route state, collision receipts, and occupancy decision.
Only `READY_TO_DRAFT` prospects with a verified email route receive a staged
draft. This composes `host/smart_outreach.py` and its checked-in candidates;
it does not mint a second prospect source.

Owner ask: Slack `#commons` `1788068123.766099` (2026-08-30 01:35 ET) —
"Do what these guys are doing" + Explee auto-GTM screenshot. Receipt:
[`p/website-people-email-book-20260830-01.md`](../../p/website-people-email-book-20260830-01.md).
Public door: [`website-people-email-book.html`](../../website-people-email-book.html).

This does **not** remint:

- `revenue/smart_outreach` — composed evidence-bound discovery, qualification, and collision suppression
- `revenue/subzero_gtm` — SUBZERO SKU architecture; that leftover forbids outreach
- `host/swarm_mail.py` — later exact-once transport after an owner mailbox exists
- `revenue/reply_to_revenue` — inbound cash truth after replies exist

It composes with those roads. Live send is refused here (`--send` exits 3).
Calls booked stay `0` until an owner calendar actually records one. Emails
are never invented. Prospects without a verified first-party email route stay
undrafted.

## Commands

```sh
python3 host/website_people_email_book.py run
python3 host/website_people_email_book.py run --url https://example.com
python3 host/website_people_email_book.py validate
python3 -m unittest -v test_website_people_email_book.py
```

`--send` is illegal and exits 3. `--url https://...` fetches a public seller
page. `--prospects` and `--receipts` select the existing Smart Outreach inputs.
The default measured run uses `fixture_seller.html` plus the current checked-in
real prospect catalog. Current truth is four external prospects and one eligible
Composio draft. The need signal comes from Composio's first-party changelog and
the route from its first-party support page. The draft remains `STAGED_NOT_SENT`;
no booking or cash is claimed.
