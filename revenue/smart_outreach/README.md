# Smart outreach planner

This lane turns Commons' existing research, offer, receipt, draft, transport,
and reply capabilities into one deterministic qualification step. It adopts the
useful mechanism behind automated prospecting products without buying another
database or adding a credential dependency: first-party evidence enters once,
canonical collision history is loaded automatically, fit is scored, and only a
fully evidenced prospect can receive a tailored private draft.

The reference mechanism is Explee's public AutoGTM description: learn what the
seller offers, sharpen the ideal-customer profile, rank high-intent prospects,
personalize each message, and then handle replies. Commons now composes those
stages from its own evidence and roads: this planner owns evidence, collision,
fit, rank, and copy; Swarm Mail owns exact-once transport state; reply intake
owns mailbox-operator classification; the always-on reply-to-revenue funnel
composes those receipts into public cash truth without a second CRM.
Reference observed 2026-08-27:
<https://explee.com/>.

It does not replace `revenue/production_survival`, the canonical commerce
catalog, Airtable CRM, Apollo receipts, or `host/swarm_mail.py`. It composes
them. The checked-in cohort intentionally demonstrates three truthful states:

- AnythingLLM is `HOLD_DO_NOT_RESEND` from canonical receipts;
- Metaforms is `HOLD_OCCUPIED` because another Commons lane already staged it;
- SigNoz is `READY_TO_DRAFT` from refreshed first-party product-pain evidence,
  an engineering-owner role, and the verified `dev@signoz.io` route. This is
  draft readiness only; it is not send authority.

No checked-in candidate is silently promoted into contact. A prospect becomes
`READY_TO_DRAFT` only when it has an exact first-party quote with production
pain, a relevant owner role, a verified route, a binary proof hypothesis, no
disqualifier, no occupied lane, and no canonical do-not-resend collision. The
generated message quotes the prospect's own words, names one existing offer,
links one measured proof, asks one narrow question, and includes a visible
opt-out. The planner still performs zero transport actions.

The SigNoz refresh is grounded in first-party public surfaces:

- <https://signoz.io/blog/why-engineering-first-teams-choose-signoz/> identifies
  a concrete agent-era product failure class: failed tool calls and unreliable
  agent-facing workflows are customer-visible product failures.
- <https://github.com/SigNoz> is a verified SigNoz GitHub organization and
  publishes `dev@signoz.io` as its engineering contact.
- <https://signoz.io/about-us/> identifies engineering leadership. The planner
  stores the role rather than guessing a private recipient.

A live mailbox collision check must still run immediately before any transport.
This research update deliberately performs no send and does not claim that a
Slack/Gmail/provider reservation exists.

Run the measured cohort:

```sh
python3 host/smart_outreach.py validate
python3 host/smart_outreach.py plan
```

Private drafts can later enter Swarm Mail's existing exact-once and suppression
path. Replies remain owned by the production-survival reply intake. This planner
does not open a second CRM, transport, inbox, SKU, or cash ledger.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../titanmcp.html). Cite Latch Pad KEEP.
