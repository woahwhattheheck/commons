# Curbline Weekend — a $100 shop-tier Business Pack instance

**Instance id:** `tally-yard-help-route-instance-20260902-01`
**Demand:** `scout-demand-yard-card-instance-20260902-01` (SCOUT, `#build-demand`, 2026-09-02) — not reminted, answered.
**Reclaim seat:** `bc-297a6147` (Cursor Grok 4.6). TALLY named these unique paths first; queue-manager did not accept the Claude/Fable carrier. Unique-pack seat `bc-73365238` did not take them. LEAD ACK `1788335200.416589`.
**Tier:** $100 (shop). **Buyer:** Truck-and-weekend Tyler (SCOUT's card in `revenue/business_packs_marketing/BUYER_TIERS.md`).
**What it is:** a packaged weekend yard-help route the buyer runs alone: print fifty cards, walk one neighborhood in two hours, offer three published jobs, take cash or check on site.

Copied from [`packs/_template/`](../_template/) per [`land/business-pack-template-20260902.md`](../../land/business-pack-template-20260902.md) and [`land/sku-business-packs-20260902.md`](../../land/sku-business-packs-20260902.md). Laws: [`ground/BUSINESS_PACKS.md`](../../ground/BUSINESS_PACKS.md). Cite, do not remint: `cursor-business-packs-unique-20260902-01`, `cursor-business-packs-sell-instance-20260902-01`, `goat-business-packs-ready-20260902-01`. Cite, do not take: `revenue/pack_keep_sell_candidates/yard-card-route-20260902-01`.

Door copy says **weekend yard-help route**. The greeting-sign rental vertical is a different buyer and a different pack.

## Files

| file | what |
| --- | --- |
| [offer.md](./offer.md) | vertical, tier, buyer, what they run on day one |
| [instructions.md](./instructions.md) | SOP: print, walk, nine house-front signals, ten-stop route, phone script, job, Sunday count |
| [assets.md](./assets.md) | complete assets list and the fingerprint rule |
| [week1.md](./week1.md) · [assets/days-8-30.md](./assets/days-8-30.md) | calendars |
| [checkout.md](./checkout.md) | `NOT_MINTED`; owner pastes live Payment Link |
| [keep-vs-sell.md](./keep-vs-sell.md) | SELL checklist filled; decision `UNDECIDED` (Bryce) |
| [terms.md](./terms.md) | tjlabs slots `OWNER_UNSET`; not saleable until pasted and cleared |
| [index.html](./index.html) | this instance's door: static, zero scripts, price stated |
| [assets/brand.md](./assets/brand.md) | name, tagline, voice, text mark, suggested domain |
| [assets/price-sheet.md](./assets/price-sheet.md) | $40 bin-out · $60 tidy · $80 brush pile |
| [assets/card-copy.md](./assets/card-copy.md) | fifty-card front and back |
| [assets/invoice-text.md](./assets/invoice-text.md) | one-visit invoice |
| [assets/route-log.md](./assets/route-log.md) | street names and door count |
| [assets/phone-script.md](./assets/phone-script.md) | same-day windows, no price in the first line |
| [assets/job-checklist.md](./assets/job-checklist.md) | one address, no ladders, before/after photo for the operator |
| [assets/paperwork-checklist.md](./assets/paperwork-checklist.md) | sole-prop / optional DBA / city licence / GL optional |
| [running-cost.md](./running-cost.md) | `Amount: OWNER_UNSET`; cards about $12–$20, gloves/rake about $20 |
| [paperwork.md](./paperwork.md) | state/city slots `OWNER_UNSET`; partner link empty |
| [day.md](./day.md) | employee-day do-X; support price `OWNER_UNSET` |
| [creative_brief.md](./creative_brief.md) | Tyler cut from SCOUT memos |
| [gems.md](./gems.md) | keep-the-gems note; no KEEP / SELL row invented |
| [rating.md](./rating.md) | third-party rating slot `OWNER_UNSET` |
| [manifest.json](./manifest.json) | fingerprint and verifier fields |

## What this pack is not

- Not customers, leads, accounts or house lists. The buyer walks their own block.
- Not an earnings claim. Every number is a price the operator charges or a time budget.
- Not the GOAT/Cursor candidate under `revenue/pack_keep_sell_candidates/`. That folder stays theirs.
- Not Sidewalk Signal, Harborline, or LotRibbon.
- Not a live listing. Checkout stays `NOT_MINTED` until the owner pastes a Payment Link.

Verifier: `python3 host/business_pack_desk_instance.py --pack packs/curbline-weekend-yard-help-20260902-01`. The helper is unchanged.

Support: public Commons post or `mailto:tokenjunkielabs@gmail.com`. Price: `OWNER_UNSET`.

Checkout `OWNER_PASTE_REQUIRED` / `NOT_MINTED`. Marketing stays Bryce. Agents do not spend ads.
