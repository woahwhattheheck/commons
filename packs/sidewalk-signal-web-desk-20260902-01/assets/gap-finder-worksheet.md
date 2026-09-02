# Gap-finder worksheet — nine signals and a ten-row sheet

Print this or copy it into a spreadsheet. One row per business. Ten rows is
one Saturday morning: about three minutes per site check plus the lookups.

You are looking for **observable** gaps: things anyone can see on the
business's own public pages today. You never submit their forms, never
create accounts, never scrape personal data, and never contact anyone
twice. Public business routes only.

## The nine signals

Each signal names what to check, what counts, and which offer it maps to.
The examples are the kinds of gaps a verified local-business sweep found
across auto repair, HVAC, roofing, lawn care, cleaning, bakeries, coffee,
restaurants, boutiques, spas, law offices and guesthouses on 2026-09-01.
No business from that sweep is included here; you find your own.

| # | Signal | How to check (under 3 minutes) | Counts when | Maps to |
| --- | --- | --- | --- | --- |
| S1 | **Primary action broken** | On your phone, tap the main call to action ("Get a quote", "Contact", "Book"). Do not submit. | An error message ("something went wrong", "form unavailable"), a form with no fields, or fields with no labels. | #2 or #4 |
| S2 | **"Coming soon" promise** | Search the page text for "coming soon", "under construction", "call to book". | Online booking, scheduling or a store is promised but not delivered while services and prices are already published. | #3 or #4 |
| S3 | **Phone-only conversion** | Look at what "Schedule" / "Order" / "Book" actually does. | It is only a `tel:` link. No form, no booking, no request flow. | #2 or #3 |
| S4 | **Dated build** | Read the footer year; resize the browser narrow; look for the last dated testimonial or award; right-click a form field, Inspect, look for `<label>`. | Footer year five or more years old; fixed-width layout with no `viewport` meta; testimonials or awards that stop years ago; unnamed form fields. | #2 |
| S5 | **No first-party site** | Search the exact business name plus city. | Top results are Facebook, Instagram, Yelp, Waze or an aggregator, and no owned domain appears; or the only "menu" is an unclaimed aggregator page with stale text. | #1 or #2 |
| S6 | **Site down or broken hosting** | Load the site twice, a minute apart. | 5xx error, connection refused, expired certificate, expired domain, parked page. | #2 |
| S7 | **Third-party detour** | Follow "shop" / "order" / "menu". | Shoppers are sent to a marketplace or a delivery app while the site says "new online store coming soon" or has no first-party catalog. | #3 |
| S8 | **Trust breaks** | Click "Reviews", "About", every nav item, every button. | Review link returns 404; a preview or staging URL appears in navigation; an empty reviews block; a dead `#` link; an expired offer still live. | #2 |
| S9 | **Manual custom-order flow** | Find how a custom order or reservation is placed. | Published rules exist (lead times, sizes, party size, dates) but the flow is "call or email us" or a generic contact form with none of those fields. | #4 |

One signal is enough for a row. Two or more make a stronger first sentence.

## Where the rows come from

- Google Maps category search in your zip code: auto repair, HVAC, roofing, lawn care, cleaning services, bakeries, coffee, restaurants with rotating menus, boutiques, salons and spas, yoga studios, small law and accounting practices, independent motels and guesthouses.
- Your city's published license rosters (many cities post HVAC, plumbing and contractor license lists with the license holder's name).
- Better Business Bureau profiles (principal and customer-contact names are public).
- Chamber of Commerce and Alignable directories.
- Nextdoor recommendation threads (read only; do not post there).

## Decision-maker and route (public only)

For each row you need one named person and one public business route:

1. The site's About or Team page.
2. The BBB profile's principal contact.
3. A published business e-mail on the site (a person's name beside it is best).
4. The business's public phone.
5. LinkedIn company page → owner, or the owner's own profile if it names the business.

If you cannot find a named person through public business pages, leave the
row in the sheet with `route: NONE` and move on. Do not guess an e-mail
address pattern.

## The sheet

| Business | Category | City / zip | First-party domain | Signal(s) | Exact evidence (quote or URL) | Date checked | Decision maker | Public route | Offer | Contacted before? | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | | | | | | | | | | no | |
| 2 | | | | | | | | | | no | |
| 3 | | | | | | | | | | no | |
| 4 | | | | | | | | | | no | |
| 5 | | | | | | | | | | no | |
| 6 | | | | | | | | | | no | |
| 7 | | | | | | | | | | no | |
| 8 | | | | | | | | | | no | |
| 9 | | | | | | | | | | no | |
| 10 | | | | | | | | | | no | |

Status values: `FOUND` → `SENT` → `REPLIED` → `YES` / `NO` / `NO_REPLY` → `INTAKE` → `BUILDING` → `LAUNCHED`.

## Evidence rules

- Write down the exact words or the exact URL. "Form is currently unavailable" is evidence; "site looks bad" is not.
- Record the date. Sites change; your first sentence must be true on the day you send it.
- A single guest review or complaint is one person's report, not a finding. Do not repeat it to the owner.
- Never describe a business as failing, embarrassing, or losing money. You saw one thing; you can fix that thing.
