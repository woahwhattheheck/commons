# KEEP vs SELL

Factory loop: generate → measure revenue signal → KEEP (internal) or SELL (packaged).

Vertical: Weekend yard-help route (Curbline Weekend instance, $100 shop tier)
Measured signal (date, what was searched, result): 2026-09-02 — no sale, no buyer, USD 0. Search space: `#business-packs`, `#build-demand`, `#sales`, the hub, and the keep-sell ledger `ground/BUSINESS_PACK_KEEP_SELL.json` (`packs: []`). Demand evidence for the pack buyer is SCOUT's $100 Tyler card, not a purchase. Candidate runbook cited, not taken: `revenue/pack_keep_sell_candidates/yard-card-route-20260902-01`.
Decision: UNDECIDED (Bryce decides; this seat does not rule)

## KEEP (internal) if

- [ ] dated revenue signal exists — none yet
- [x] repeats without a new invention each time — print cards, walk two hours, take the three published jobs; nothing new is invented per stop
- [ ] Bryce wants to operate it — not stated
- [ ] holding it is cheaper than packaging it — it is already packaged; holding costs nothing either way

## SELL (packaged) if

- [x] a buyer can run it from instructions.md without Bryce as operator — instructions.md carries print, walk, nine house-front signals, ten-stop route, phone, job, Sunday count
- [x] assets.md is complete — brand, cards, price sheet, invoice, route log, phone script, job checklist, paperwork, door, calendars
- [x] week1.md is complete — seven days named
- [x] support boundary is honest — see README.md: public Commons post or `mailto:tokenjunkielabs@gmail.com`; no calls, no yards done for the buyer, no house lists
- [x] marketing stays owner-owned (no ads setup bundled) — nothing in this pack sets up ads; the door carries no pixel
- [x] this sale is a distinct instance / fresh package (similar vertical/pattern allowed; not a copy-paste clone of a prior sale) — first shop-tier yard-help instance; `manifest.json` fingerprint; the next buyer gets a new name, door and re-cut instructions

Lane: Slack `#business-packs` `C0BU7JAPUH3`.
This decision is not a Commons admission condition.

Not recorded in `ground/BUSINESS_PACK_KEEP_SELL.json`: that ledger's test asserts `packs == []`; recording is the factory seat's or Bryce's move with `host/business_pack_keep_sell.py record`.
