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
owns reply classification. Reference observed 2026-08-27:
<https://explee.com/>.

It does not replace `revenue/production_survival`, the canonical commerce
catalog, Airtable CRM, Apollo receipts, or `host/swarm_mail.py`. It composes
them. The checked-in cohort intentionally demonstrates three truthful states:

- AnythingLLM is `HOLD_DO_NOT_RESEND` from canonical receipts;
- Metaforms is `HOLD_OCCUPIED` because another Commons lane already staged it;
- SigNoz is `RESEARCH_REQUIRED` until a relevant owner and first-party route
  are identified.

No checked-in candidate is silently promoted into contact. A prospect becomes
`READY_TO_DRAFT` only when it has an exact first-party quote with production
pain, a relevant owner role, a verified route, a binary proof hypothesis, no
disqualifier, no occupied lane, and no canonical do-not-resend collision. The
generated message quotes the prospect's own words, names one existing offer,
links one measured proof, asks one narrow question, and includes a visible
opt-out. The planner still performs zero transport actions.

Run the measured cohort:

```sh
python3 host/smart_outreach.py validate
python3 host/smart_outreach.py plan
```

Private drafts can later enter Swarm Mail's existing exact-once and suppression
path. Replies remain owned by the production-survival reply intake. This planner
does not open a second CRM, transport, inbox, SKU, or cash ledger.
