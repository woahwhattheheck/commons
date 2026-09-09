# Waitlist slot — additive

Each sold instance door may carry the shared first-party waitlist. This is a
pointer, not a second list and not a send.

- Form: [`packs/waitlist.html`](../waitlist.html)
- Fields: email, tier of interest, state
- Consent at the form: what is collected; may be used to reach the person on
  X / TikTok / Meta; unsubscribe any time
- Link on the form: **Do Not Sell or Share My Personal Information**
  (required before any pixel fires; empty pixel slots already load nothing)
- Public readback: count per tier only. Addresses never go on the door.
- Storage: owner-local append-only JSONL (`~/.tjlabs/waitlist-signups.jsonl`).
  Do not copy `revenue/swarm_mail` or AgentMail engines into this pack.
- Zero sends. The list is an unsent asset. Sending is owner-gated.
- No auth. No Commons gate. No invented Stripe URL. No pixel ID. No ad spend.

Door line to paste:

> Join the pack waitlist: `packs/waitlist.html`

Do not put addresses, look-alike uploads, or a “we will email you” send on the
instance door.
