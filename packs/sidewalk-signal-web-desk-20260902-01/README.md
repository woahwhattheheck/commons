# Sidewalk Signal — a $200 desk-tier Business Pack instance

**Instance id:** `tally-desk-website-service-pack-20260902-01`
**Demand:** `scout-demand-desk-website-service-pack-20260902-01` (SCOUT, `#build-demand`, 2026-09-02) — not reminted, answered.
**Tier:** $200 (desk). **Buyer:** Laptop Lena / Desk Dan (SCOUT's card in `revenue/business_packs_marketing/BUYER_TIERS.md`).
**What it is:** a packaged local-business website service the buyer runs alone from a laptop: find businesses in their own zip code whose sites show one of nine observable gaps, sell them a finished site at a published price, deliver in seven days after intake, hand over everything.

Copied from [`packs/_template/`](../_template/) per [`land/business-pack-template-20260902.md`](../../land/business-pack-template-20260902.md) and [`land/sku-business-packs-20260902.md`](../../land/sku-business-packs-20260902.md). Laws: [`ground/BUSINESS_PACKS.md`](../../ground/BUSINESS_PACKS.md). Cite, do not remint: `cursor-business-packs-unique-20260902-01`, `cursor-business-packs-sell-instance-20260902-01`, `goat-business-packs-ready-20260902-01`.

## Files

| file | what |
| --- | --- |
| [offer.md](./offer.md) | vertical, tier, buyer, what they run on day one, what they keep and do not get |
| [instructions.md](./instructions.md) | the SOP: start, the nine-signal gap finder (find ten businesses), daily loop, weekly loop, stop, revenue signal |
| [assets.md](./assets.md) | complete assets list and the fingerprint rule |
| [week1.md](./week1.md) · [assets/days-8-30.md](./assets/days-8-30.md) | calendars |
| [checkout.md](./checkout.md) | `NOT_MINTED`; owner pastes live Payment Link; after-payment redirect to `packs/thanks.html` |
| [keep-vs-sell.md](./keep-vs-sell.md) | SELL checklist filled; decision `UNDECIDED` (Bryce) |
| [terms.md](./terms.md) | TokenJunkie Labs profit-share percent and partial-ownership fraction, both `OWNER_UNSET`; `counsel_cleared: false`; not saleable until set and cleared (`ground/TJLABS_PACK_TERMS.md`) |
| [index.html](./index.html) | this instance's door: static, zero scripts, price stated, checkout placeholder |
| [assets/brand.md](./assets/brand.md) | name, tagline, voice, text mark, colors, suggested domain (availability UNMEASURED) |
| [assets/price-sheet.md](./assets/price-sheet.md) | the four offers the operator charges: $1,500 · $2,500 · $4,000 · from $6,000, and the launch acceptance list |
| [assets/gap-finder-worksheet.md](./assets/gap-finder-worksheet.md) | nine signals, sources, name-and-route rules, ten-row sheet |
| [assets/outreach-script.md](./assets/outreach-script.md) | the sales law and the scripts: e-mail, follow-ups, DM, voicemail, walk-in, two-step start |
| [assets/delivery-checklist.md](./assets/delivery-checklist.md) | intake packet, seven-day plan, launch acceptance, handoff |
| [assets/contract-placeholder.md](./assets/contract-placeholder.md) | scope skeleton with `[OWNER]` / `[COUNSEL]` markers |
| [assets/showcase-manifest.json](./assets/showcase-manifest.json) | the two demo attachments by name, bytes and SHA-256; owner-delivered at sale, not in this repository |
| [assets/paperwork-checklist.md](./assets/paperwork-checklist.md) | the required paperwork for a one-person US website service (legal form, DBA, EIN, licence, sales tax, bank, insurance, contract, W-9, taxes, e-mail rules, records) with where to check; checklists and templates, never filing for the buyer (Bryce, hub 2026-09-02 01:43 EDT) |
| [running-cost.md](./running-cost.md) | the shared running-cost slot (`Amount: OWNER_UNSET`, owner pastes) with the itemized typical ranges the runbook states (SCOUT running-cost rule) |
| [paperwork.md](./paperwork.md) | the shared paperwork slot in the template's shape: every Do X line filled for this vertical, `State` / `City` and every `Status` `OWNER_UNSET`, formation-partner link empty, never-on-the-door lines kept |
| [day.md](./day.md) | employee-day do-X list: onboarding, training, daily and weekly tasks; support subscription price `OWNER_UNSET` (Bryce, hub `1788327136.593709`) |
| [manifest.json](./manifest.json) | machine record: instance fields, per-file hashes, fingerprint, verdicts |

## What this pack is not

- Not customers, leads, accounts or locations. The buyer finds their own businesses with the method. This keeps the pack outside the FTC Business Opportunity Rule's customer-provision prong (16 CFR 437.1); see `revenue/business_packs_marketing/LAW_AND_POLICY_FLAGS.md`.
- Not an earnings claim. Every number is a price the operator charges or a time budget. `host/business_pack_unique.py classify_copy` runs over every file.
- Not a franchise, and the word is not used in the buyer-facing files.
- Not a live listing. `checkout.md` is `NOT_MINTED` until the owner pastes a Payment Link; the door shows a `mailto:` fallback until then.
- Not an ad. Marketing stays with Bryce. The door carries no pixel; the after-payment redirect is the shared `packs/thanks.html`.

## Verify

From the repository root:

```text
python3 host/business_pack_desk_instance.py
python3 -m unittest test_business_pack_desk_instance -v
```

The helper recomputes every hash in `manifest.json`, builds the instance
fingerprint with `host/business_pack_unique.py` (`assets`, `brand`,
`checkout`, `instructions`, `ops`), checks the sell-instance rule (brand plus
door), scans every file for earnings claims, invented Stripe URLs and
lottery language, and checks the door for scripts. `--write` refreshes the
manifest after an edit. Exit 1 on any error. It is not a Commons gate.

## Uniqueness

This is the first instance of this vertical. A second sale must be a fresh
package: new name, new door, re-cut instructions, its own checkout. The
manifest fingerprint makes a byte-identical second sale show as
`CLONE_STAMP`. Similar vertical and pattern are allowed; copy-paste is not.

## Support boundary

Included: the files above and the two demo attachments delivered by the
owner. Buyer questions after a sale: public Commons post or
`mailto:tokenjunkielabs@gmail.com`. Not included: ads setup, a marketing
agent, building the client's site for the buyer, leads, invented checkout
URLs, device or `commons.mno` actuation, or closing the Commons door.

## Owner decisions open

KEEP or SELL · Payment Link · refund policy on the door · the two
terms-of-service slots in `terms.md` (profit-share percent and
partial-ownership fraction, both `OWNER_UNSET`) plus counsel clearance, per
`ground/TJLABS_PACK_TERMS.md` · whether this instance is a nuts mix-in and
its value range.

Open door. No login. Possessing the Commons link is enough to read and post.
