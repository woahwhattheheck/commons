# KEEP vs SELL

Factory loop: generate → measure revenue signal → KEEP (internal) or SELL (packaged).

Vertical: Local-business website service (Sidewalk Signal instance, $200 desk tier)
Measured signal (date, what was searched, result): 2026-09-02 — no sale, no buyer, USD 0. Search space: `#business-packs`, `#build-demand`, `#sales`, `#leads`, the hub, and the keep-sell ledger `ground/BUSINESS_PACK_KEEP_SELL.json` (`packs: []`). Demand evidence for the buyer's *customers* exists (the 9/1 `#leads` sweep found 14 local businesses with observable site gaps in one evening; the `#sales` price sheet is posted). Demand evidence for the *pack buyer* is SCOUT's tier research, not a purchase.
Decision: UNDECIDED (Bryce decides; this seat does not rule)

## KEEP (internal) if

- [ ] dated revenue signal exists — none yet
- [x] repeats without a new invention each time — the loop is checks → sends → YES → build; nothing new is invented per client
- [ ] Bryce wants to operate it — not stated
- [ ] holding it is cheaper than packaging it — it is already packaged; holding costs nothing either way

## SELL (packaged) if

- [x] a buyer can run it from instructions.md without Bryce as operator — instructions.md carries the full nine-signal method, the daily and weekly loops, stop rules and the revenue-signal rule
- [x] assets.md is complete — brand, price sheet, scripts, worksheet, delivery checklist, contract placeholder, door, calendars, demo-attachment manifest
- [x] week1.md is complete — seven days named
- [x] support boundary is honest — see README.md: public Commons post or `mailto:tokenjunkielabs@gmail.com`; no calls, no builds done for the buyer, no leads
- [x] marketing stays owner-owned (no ads setup bundled) — nothing in this pack sets up ads; the door carries no pixel
- [x] this sale is a distinct instance / fresh package (similar vertical/pattern allowed; not a copy-paste clone of a prior sale) — first instance of this vertical; `manifest.json` fingerprint; the next buyer gets a new name, door and re-cut instructions

Lane: Slack `#business-packs` `C0BU7JAPUH3`.
This decision is not a Commons admission condition.

Not recorded in `ground/BUSINESS_PACK_KEEP_SELL.json`: that ledger's test asserts `packs == []`; recording is the factory seat's or Bryce's move with `host/business_pack_keep_sell.py record`.
