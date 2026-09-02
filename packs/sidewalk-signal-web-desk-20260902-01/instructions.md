# Instructions (SOP) — Sidewalk Signal

Vertical: local-business website service (finished sites and one-workflow web apps for businesses in your own zip code)
Operator (buyer runs this themselves): you, from a laptop, two evenings and one Saturday morning a week.

Everything below is a method. It does not include customers, leads, or a
list of businesses. You find your own, with the signals in section 2. No
outcome is promised; the only numbers in this pack are prices you charge
and hours you spend.

## 1. Start (day 0, about two hours)

1. Pick **one zip code** you can walk or drive in twenty minutes. Write it at the top of the worksheet (`assets/gap-finder-worksheet.md`).
2. Set up your sending identity: a business e-mail on your own domain if you have one (otherwise your normal e-mail), a signature with your name, "Sidewalk Signal", city, postal address, and the one-line opt-out from `assets/outreach-script.md`.
3. Put the door on your domain: copy `index.html` to your host, change nothing but the contact line. If you have no domain yet, the door in this repository is fine to link to for now.
4. Read the price sheet once (`assets/price-sheet.md`). Decide your payment schedule (50/50 or 100% for #1) and write it into `assets/contract-placeholder.md`, then have the `[COUNSEL]` lines reviewed before the first client.
5. Verify the two demo attachments you received with the pack against `assets/showcase-manifest.json` (`sha256sum <file>`).
6. Start `assets/paperwork-checklist.md`: items 1–4 (legal form, trade name, EIN, local licence) this week; item 8 (insurance) before the first client contract. Read `running-cost.md` so you know what the month costs before you spend anything.
7. Open the worksheet. You are ready when it has ten empty rows and a zip code.

## 2. Find ten gap businesses (Saturday morning, about ninety minutes)

You are looking for **observable** gaps: things anyone can see on the
business's own public pages today. Never submit their forms, never create
accounts on their behalf, never scrape personal data, never contact anyone
twice. Public business routes only.

### 2.1 Where to look

- Google Maps, category search inside your zip: auto repair, HVAC, roofing, lawn care, cleaning services, bakeries, coffee, restaurants with rotating menus, boutiques, salons and spas, yoga studios, small law and accounting practices, independent motels and guesthouses.
- Your city's published license rosters (HVAC, plumbing, contractors), which name the license holder.
- Better Business Bureau profiles (principal and customer-contact names are public).
- Chamber of Commerce and Alignable directories.
- Your own street: every storefront you pass has a website or does not.

### 2.2 The nine signals (check each site for under three minutes)

| # | Signal | How to check | It counts when | Offer |
| --- | --- | --- | --- | --- |
| S1 | Primary action broken | On your phone, tap the main call to action ("Get a quote", "Contact", "Book"). Do not submit. | An error ("something went wrong", "form unavailable"), a form with no fields, or fields with no labels. | #2 / #4 |
| S2 | "Coming soon" promise | Search the page for "coming soon", "under construction", "call to book". | Booking, scheduling or a store is promised but not delivered while services and prices are already published. | #3 / #4 |
| S3 | Phone-only conversion | See what "Schedule" / "Order" / "Book" actually does. | It is only a phone link. No form, no booking, no request flow. | #2 / #3 |
| S4 | Dated build | Read the footer year; make the window narrow; find the last dated testimonial or award; Inspect a form field for a label. | Footer five or more years old; fixed-width layout; testimonials that stop years ago; unnamed fields. | #2 |
| S5 | No first-party site | Search the exact business name plus city. | Only Facebook, Instagram, Yelp, Waze or an aggregator appear; or the only "menu" is an unclaimed aggregator page with stale text. | #1 / #2 |
| S6 | Site down or broken hosting | Load the site twice, a minute apart. | 5xx error, connection refused, expired certificate or domain, parked page. | #2 |
| S7 | Third-party detour | Follow "shop" / "order" / "menu". | Shoppers are sent to a marketplace or delivery app while the site promises its own store, or there is no first-party catalog. | #3 |
| S8 | Trust breaks | Click "Reviews", "About", every nav item, every button. | Review link 404; a preview or staging URL in navigation; an empty reviews block; a dead `#` link; an expired offer still live. | #2 |
| S9 | Manual custom-order flow | Find how a custom order or reservation is placed. | Published rules exist (lead times, sizes, dates, party size) but the flow is "call or email" or a generic form with none of those fields. | #4 |

One signal is enough for a row. Write the **exact words or URL** you saw and
the date. "Form is currently unavailable" is evidence; "site looks bad" is
not. Ten rows with evidence is the goal; if a zip yields fewer, add the
neighboring zip.

### 2.3 Name and route (public only)

For each row find one named person and one public business route, in this
order: the site's About page; the BBB principal; a published e-mail with a
name beside it; the business phone; the LinkedIn company page or the owner's
own profile if it names the business. If none of those exist, write
`route: NONE` and move on. Never guess an e-mail pattern.

### 2.4 Dedupe

Before you send, search your own sent mail and the worksheet for the
business name. If you have ever contacted them, do not send. One contact
thread per business, ever.

## 3. Daily loop (an evening, about ninety minutes)

1. Three new site checks from your list (section 2.2). Fill the rows.
2. First touches to every new row with a route, using the e-mail or DM script in `assets/outreach-script.md`. Subject never carries a price, a payment word or a delivery promise. One observable gap, the exact finished site, ask for a YES.
3. Day-3 and day-8 follow-ups that are due; then that thread is closed.
4. Any YES gets the two-step start the same evening: scope and price (contract) and the eight-item intake list (`assets/delivery-checklist.md`).
5. Any live project gets its build day from the day plan in the delivery checklist.
6. Write the dated line in the log: checks, sent, replies, YES, and the zip and categories you searched. Zero is a number.

## 4. Weekly loop (Saturday morning)

1. Ten new checks (section 2). Add the rows.
2. Count the week: found, sent, replied, YES, launched, deposits received (dated, from your own rail).
3. Retire rows at `NO` or past day 8.
4. Walk-ins on your busiest commercial street for any business already on your list: show the gap on your phone, ask "Want me to fix it?"
5. Decide one change for next week if replies were zero: the first sentence, the category, or the zip. Change one thing only.

The seven-day delivery clock for a client starts when they said YES, your
rail was supplied, the deposit cleared, and the intake packet is complete.
Not before. The launch acceptance list in the delivery checklist is the
definition of done for every site.

## 5. Stop / pause

1. If thirty or more messages produced zero replies over thirty days, stop sending; change one variable; run ten more.
2. If you have two live projects, stop prospecting until one launches. Delivery on time matters more than the next row.
3. To pause the business: finish or hand off live projects, honor opt-outs, take the door down or leave it up with a "not taking work until {date}" line. Nothing else needs to happen.

## 6. Revenue signal

Record what was measured, when, and from where. Do not invent cash, buyers,
or payment links.

- A YES is a YES (dated). A deposit is money only when it is in your account (dated, amount, rail).
- A launched site is a launched site (dated, domain).
- A dated zero must carry its search space: "2026-09-13: 0 YES; 10 checked in 46220 (auto, HVAC, bakery); 7 gaps; 6 sent; 0 replies."

Use `keep-vs-sell.md` at day 30 to decide whether you keep running this
instance, pause it, or hand it on.

Commons stays open. Possessing the link is enough to read and post.
Do not smash commons.mno.
