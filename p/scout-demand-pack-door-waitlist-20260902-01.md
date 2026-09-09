# scout-demand-pack-door-waitlist-20260902-01

SHIP shared first-party pack waitlist. SCOUT demand id not reminted.

Consumer: every pack tier's launch, and Bryce's future X / TikTok / Meta
look-alike seed. Bought lists cannot be that seed.

## Unique paths

- `packs/waitlist.html`
- `packs/waitlist-counts.json` (public counts; zero addresses)
- `packs/_template/waitlist-slot.md`
- `ground/BUSINESS_PACK_WAITLIST.json`
- `host/pack_waitlist.py`
- `test_pack_waitlist.py`
- `land/pack-waitlist-20260902.md`
- this receipt

## Acceptance

- Form posts (owner-local helper) and reads back a count per tier
- Addresses never appear in the public counts JSON or HTTP body
- Consent text at the form (collected fields; may reach on X / TikTok / Meta;
  unsubscribe any time)
- Opt-out link: Do Not Sell or Share My Personal Information
- CCPA opt-out blocks pixels for that email; empty pixel slots already load
  nothing
- Zero sends. List is an unsent asset. Sending is owner-gated
- No auth, no gate, no password field, no static third-party scripts
- Template slot so each instance door can carry the form
- Storage is owner-local JSONL. Did not steal `revenue/swarm_mail` or AgentMail

## Not this demand

Email send, list purchase, pixel ID, ad spend.

## Tests

`python3 test_pack_waitlist.py`
