# Assets list

Vertical: Weekend yard-help route (Curbline Weekend instance)
Every asset the buyer needs to run this pack:

- [x] name / brand — `assets/brand.md` (name, tagline, voice, text mark, colors, suggested domain with availability UNMEASURED)
- [x] templates — `assets/price-sheet.md` (three jobs), `assets/invoice-text.md` (one visit), `assets/card-copy.md` (fifty cards)
- [x] scripts or forms — `assets/phone-script.md`, `assets/route-log.md`, `assets/job-checklist.md`
- [x] public doors (optional) — `index.html` (this instance's door; static, no scripts, price stated, checkout placeholder)
- [x] calendars — `week1.md`, `assets/days-8-30.md`
- [x] paperwork — `assets/paperwork-checklist.md` (sole prop, optional DBA, city licence, sales-tax check, optional GL, invoice; checklist, not filing)
- [x] running cost — `running-cost.md` (shared slot, `Amount: OWNER_UNSET`; itemized typical ranges)
- [x] paperwork slot — `paperwork.md` (template shape; Do X lines filled; `State` / `City` / `Status` `OWNER_UNSET`; partner link empty)
- [x] employee day — `day.md` (onboarding, training, daily and weekly do-X list; support price `OWNER_UNSET`)
- [x] terms — `terms.md` (TokenJunkie Labs slots `OWNER_UNSET`, `HOLD_COUNSEL`)
- [x] data — none shipped. The buyer walks their own block. No house list.

Missing a required asset means the pack is not SELL-ready. All required
assets above are present in this directory.

Do not attach secrets, live processor payloads, or `.mno` files.

## Fingerprint

`manifest.json` records the SHA-256 of every file under `assets/`, of
`instructions.md`, and of the two calendars, plus the brand and checkout
tokens. `host/business_pack_desk_instance.py` recomputes them and runs
`host/business_pack_unique.py` so a second sale of identical bytes is
`CLONE_STAMP`. Similar vertical/pattern is allowed. This instance is not
a clone of the GOAT candidate, Sidewalk Signal, Harborline, or LotRibbon.

Cite, do not take: `revenue/pack_keep_sell_candidates/yard-card-route-20260902-01`.
