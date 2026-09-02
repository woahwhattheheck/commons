# Business packs — empty third-party rating slot

Bryce `#business-packs` `1788327092.565209` (2026-09-02): look into a third-party rating partner at a bulk price or rate. Partner pick, terms, and bulk rate stay with Bryce. This card is the factory slot: a **badge URL** and a **report URL**, empty by default, owner-paste like Payment Links.

Allowed once filled: a completeness / quality / uniqueness audit (pass/fail or score) whose words are the rater's. Forbidden on the door: a **dollar valuation** or revenue projection — that is tjlabs' own earnings claim under 16 CFR 437 once we put it on the door or in an ad.

“Independently audited for completeness” is true only when those slots are filled. Agents do not pick a partner, invent a bulk price, mint a Stripe URL, or rewrite SCOUT `ADVERTISING_GENERAL.md`.

This is not a Commons login. Possessing a Commons link is still authorization.

## Rules

1. Empty badge and report load neither a seal nor a report link.
2. A URL in either slot without `owner_pasted_rating` is `RATING_LINK_INVENTED`.
3. Dollar valuation / “worth $X” / revenue-projection copy is `RATING_EARNINGS_CLAIM`.
4. “Independently audited” with empty slots is `RATING_CLAIM_UNSUBSTANTIATED`.
5. Partner name and bulk price stay `OWNER_UNSET` until the owner pastes them.
6. Checkout stays `NOT_MINTED`. Marketing stays Bryce. Agents do not spend ads.

Machine map: [BUSINESS_PACK_RATING.json](./BUSINESS_PACK_RATING.json). Helper: [host/business_pack_rating.py](../host/business_pack_rating.py). Sheet: [packs/_template/rating.md](../packs/_template/rating.md). Unique-pack pointer: [BUSINESS_PACKS.json](./BUSINESS_PACKS.json).
