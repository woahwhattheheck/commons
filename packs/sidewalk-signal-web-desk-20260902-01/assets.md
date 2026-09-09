# Assets list

Vertical: Local-business website service (Sidewalk Signal instance)
Every asset the buyer needs to run this pack:

- [x] name / brand — `assets/brand.md` (name, tagline, voice, text mark, colors, suggested domain with availability UNMEASURED)
- [x] templates — `assets/price-sheet.md` (four offers and launch acceptance), `assets/contract-placeholder.md` (scope skeleton with OWNER / COUNSEL markers), `assets/delivery-checklist.md` (intake packet, seven-day plan, handoff packet)
- [x] scripts or forms — `assets/outreach-script.md` (e-mail, follow-ups, DM, voicemail, walk-in, the two-step start, reply handling), `assets/gap-finder-worksheet.md` (nine signals and the ten-row sheet)
- [x] public doors (optional) — `index.html` (this instance's door; static, no scripts, price stated, checkout placeholder)
- [x] calendars — `week1.md`, `assets/days-8-30.md`
- [x] paperwork — `assets/paperwork-checklist.md` (legal form, DBA, EIN, local licence, sales-tax check, bank, payment rail, insurance, contract review, W-9, taxes, commercial e-mail rules, door privacy line, client-owned accounts, records; checklist and links, not filing)
- [x] running cost — `running-cost.md` (shared slot, `Amount: OWNER_UNSET`; itemized typical ranges the runbook states)
- [x] paperwork slot — `paperwork.md` (template shape; Do X lines filled; `State` / `City` / `Status` `OWNER_UNSET`; partner link empty)
- [x] employee day — `day.md` (onboarding, training, daily and weekly do-X list; support price `OWNER_UNSET`)
- [x] rating slot — `rating.md` (badge, report, partner, bulk price all `OWNER_UNSET`)
- [x] waitlist — reached through the peer catalog pointer to the shared `packs/waitlist.html`; nothing on this door
- [x] sold-once badge — rendered into `index.html` by the verifier from `manifest.json` `sold_once`; anchor line slot `OWNER_UNSET`
- [x] terms — `terms.md` (TokenJunkie Labs slots `OWNER_UNSET`, `HOLD_COUNSEL`)
- [x] data (license + provenance, or UNMEASURED) — `assets/showcase-manifest.json`: the two demo attachments (`SMB-Website-Showcase.pdf` 1,099,041 B and `SMB-Workflow-App-Showcase.mp4` 661,524 B) are delivered by the owner at sale from private `smb-showcase-inventory` main `0d91231e`; the manifest carries their SHA-256 so the buyer can verify the bytes. Demo-use license while operating this instance. No other data ships; the buyer finds their own businesses.

Missing a required asset means the pack is not SELL-ready. All required
assets above are present in this directory except the two demo files, which
are owner-delivered by design (sellable product artifacts stay off public
commons).

Do not attach secrets, live processor payloads, or `.mno` files.

## Fingerprint

`manifest.json` records the SHA-256 of every file under `assets/`, of
`instructions.md`, and of the two calendars, plus the brand and checkout
tokens. `host/business_pack_desk_instance.py` recomputes them and runs
`host/business_pack_unique.py` so a second sale of identical bytes is
`CLONE_STAMP`, not `UNIQUE`. Refresh after any edit:

```text
python3 host/business_pack_desk_instance.py --write
python3 host/business_pack_desk_instance.py
```
