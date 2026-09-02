# Pack waitlist

First-party consented waitlist for pack tiers. Bought lists cannot be uploaded
as Meta or TikTok custom audiences; X only accepts a list you own. This door
collects the seed those platforms actually accept.

Shared form: [packs/waitlist.html](../packs/waitlist.html). Machine law:
[ground/BUSINESS_PACK_WAITLIST.json](../ground/BUSINESS_PACK_WAITLIST.json).
Helper: [host/pack_waitlist.py](../host/pack_waitlist.py). Additive instance
pointer: [packs/_template/waitlist-slot.md](../packs/_template/waitlist-slot.md).

The form takes email, tier of interest, and state. Consent sits on the form.
**Do Not Sell or Share My Personal Information** sits on the form. That opt-out
is required before any pixel fires. Empty pixel slots already load nothing.

Public readback is a count per tier in
[packs/waitlist-counts.json](../packs/waitlist-counts.json). Addresses stay in
owner-local append-only JSONL (`~/.tjlabs/waitlist-signups.jsonl`). The owner
runs `python3 host/pack_waitlist.py serve` (port 43148) when they want live
posts. `post_url` in the law JSON stays empty until they point it.

The list is an unsent asset. This helper never sends mail. Sending is
owner-gated. Agents do not mint a pixel ID, buy a list, or spend ads. Checkout
stays `NOT_MINTED`.
