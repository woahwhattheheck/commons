# Convert shelf — $49 · WO-CONVERT-SHELF-49

Produce-to-sell pack. A **one-page buy-CTA shelf** for indie SaaS still on
Notion/Carrd: the product's story plus a real buy button that points at the
buyer's **existing** payment link.

- `template.html` — the parameterized shelf (all copy comes from context)
- `sample/` — fictional "Queueboard" splice + hermetic canary
- `instructions.md` — render recipe · `checklist.md` — land checklist
- `intake.md` — what a buyer sends · `offer.md` — the offer · `checkout.md` — rails
- `sell-blurb.md` — the external blurb
- `door.html` — this pack's public door

Engine: `python3 host/convert_shelf_pack.py` (`--canary`, `--render`,
`--validate-context`). Receipt: `p/anvil-convert-shelf-49-20260917-01.md`.

Rules: checkout NOT_MINTED (Stripe ask if no PL) · buyer's EXISTING link only ·
Autopsy SCRAPPED · never Bryce-as-buyer · Tip KEEP · #8802 off.
