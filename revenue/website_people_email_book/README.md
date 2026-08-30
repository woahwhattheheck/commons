# Website → people → email → book

Explee-style auto-GTM loop as a Commons capability. The **website is the seed**.
Drop a public page, extract the product and ICP, find people on that page who
need it, draft emails with a book-a-call CTA, and stage bookings.

Owner ask: Slack `#commons` `1788068123.766099` (2026-08-30 01:35 ET) —
"Do what these guys are doing" + Explee auto-GTM screenshot. Receipt:
[`p/website-people-email-book-20260830-01.md`](../../p/website-people-email-book-20260830-01.md).
Public door: [`website-people-email-book.html`](../../website-people-email-book.html).

This does **not** remint:

- `revenue/smart_outreach` — evidence-bound planner from checked-in candidates; zero transport; no website seed; no booking
- `revenue/subzero_gtm` — SUBZERO SKU architecture; that leftover forbids outreach
- `host/swarm_mail.py` — later exact-once transport after an owner mailbox exists
- `revenue/reply_to_revenue` — inbound cash truth after replies exist

It composes with those roads. Live send is refused here (`--send` exits 3).
Calls booked stay `0` until an owner calendar actually records one. Emails
are never invented. People without a `mailto:` on the page stay `UNVERIFIED`.

## Commands

```sh
python3 host/website_people_email_book.py run
python3 host/website_people_email_book.py validate
python3 -m unittest -v test_website_people_email_book.py
```

`--send` is illegal and exits 3. Optional `--url https://...` fetches a public
page (no auth). Default measured cohort is `fixture_seller.html`.
