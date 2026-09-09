# sextant-buy-what-we-have-20260904-01 — the receive side of a pack sale, landed

Seat: SEXTANT (Claude Fable 5.1, Claude Code desktop app, owner PC, 2026-09-04 evening).
Lane: Astra's commercial lane "let someone buy what we already have" (hub `C0BU51F1PL3`
p1788567980525579), under Bryce's direction that this run is about revenue. Claim
p1788568046566709. This is the Commons pointer; the detailed receipt with every measurement lives
in the private store repository.

## Where the work lives

Private `woahwhattheheck/pack-market`, main `fd812c5871e6551e17367ee96992d839836028c2` after
PRs #2, #3, #4, #5, #6 (all merged, every landed blob read back against the tested bytes).
Detailed receipt: `p/sextant-buy-what-we-have-20260904-01.md` in that repository.

## What a buyer can receive now

- All four packs have a buyer-clean delivery cut: Sidewalk Signal (`PK-DESK-0001`, $250),
  Harborline Local Sites (`PK-DESK-0002`, $250), Curbline Weekend (`PK-SHOP-0001`, $250),
  LotRibbon Greetings (`PK-PLANT-0001`, $1,000). Each cut drops the factory's internal files and
  words, keeps the operating files, and adds a client-facing door the buyer hosts.
- One command builds the bundle a buyer receives (zip with a delivery note listing every file's
  sha256, a manifest with source pins and per-file provenance), refusing on any drift from the
  pinned sources or any factory word. One command records the sale in the store's books and marks
  a sold-once pack sold. One command does both and writes the delivery mail text.
- A one-page offer sheet per pack, generated from the catalog and the policies, with the Buy
  button only when a real Stripe-hosted link exists.
- The Stripe link lands in the store with one command that accepts Stripe hosts only and probes
  the page live; `status` is the chargeable gate.

## Measured

- Tests 38/38 on the store's fulfillment and link tools; existing smokes still pass.
- No PK-* Payment Link exists; the store is NOT CHARGEABLE 0/4. This seat has no Stripe road.
- `tokenjunkielabs@gmail.com` is the Stripe account's notification address (Stripe mail present,
  no payment mail, matching zero completed sessions): a sale surfaces as mail a seat can read.
- The 9/3 `sku-commons-pack-20260903` link is a $299 product named "Commons pack" with no
  description as a buyer sees it; not the same offer as any pack.
- The pack sources vendored from commons `packs/**` carried OWNER_UNSET / NOT_MINTED / HOLD_COUNSEL
  / "owner pastes" in 16 / 21 / 22 / 19 files; those words are retired in `ground/OWNER_NOW.md` and
  are not delivered.

## Open, and who holds it

- The Payment Link mint for each pack (spec in the hub, 20:47 and 21:15 EDT): a seat with the
  Token Junkie Labs Stripe session.
- A public landing URL for the offer (the Payment Link page itself serves): owner or marketing.
- Shipping operations for the two physical packs (starter inventory, printed cards): owner ops.
- The agreement numbers (TJLabs percentage, ownership fraction): Bryce's open question.

No buyer contacted. No cash claimed. Commons `packs/**` and every peer path untouched.

## Update 2026-09-05 02:55Z — LotRibbon Greetings withdrawn by owner ruling

Bryce, in-session to this seat: the lawn-greeting business is not something we sell; the idea
itself is out, not just this instance. Recorded as a mechanism on pack-market main
`9dbc0d632e4c1c9d55f423b3b47cc762a0a664d6` (PR #8): `data/withdrawn.json` lists `PK-PLANT-0001`;
the shelf hides it, the offer sheet skips it, the bundle builder and the sale command refuse it,
the chargeable gate counts three packs. Files stay in the repository. The shelf is Sidewalk Signal,
Harborline Local Sites and Curbline Weekend, all $250, all deliverable; every one still waits on
the Payment Link mint.
