# LLM-native GTM index

One index-first compose/query layer over GTM ledgers Commons already has.
Humans keep the existing UIs. Agents load one INDEX, list live next-actions,
open an existing prospect by reference, and append an overlay event. This is
not a second CRM and not a new contact book.

Canonical CRM remains Airtable `JOJO Revenue Recovery CRM / Revenue Pipeline`.
Private routes stay off git. Public cash stays USD 0 unless a named payment
evidence URL already exists in a source ledger.

Hot lane (`python3 host/lm_gtm_index.py hot`) is the actionable subset: it
excludes seller context, the research universe, mailbox manifests, and DNR /
HOLD_DO_NOT_RESEND / HOLD_DO_NOT_CONTACT unless a MATERIAL_REPLY reopened
them. Rank: material_reply > sent_awaiting_reply > ready_to_draft >
verified_lead_unsent.

Occupancy (`claim` / `release`) writes an overlay event onto the INDEX `owner`
field. It does not rewrite `loop.json`. A second occupancy on a seated live
one fails closed unless `--steal` is explicit. That is collision-avoidance
for two harnesses hitting the same live one, not an admission gate.

## Cross-harness contract

Read (any harness with git):

1. Load [`INDEX.jsonl`](./INDEX.jsonl). First line is `LM_GTM_INDEX_HEADER`.
   Every later line is one `LM_GTM_INDEX_ROW` pointing at existing files.
2. List all live next-actions: rows with `"live": true`, or
   `python3 host/lm_gtm_index.py next`.
3. List only actionable live ones:
   `python3 host/lm_gtm_index.py hot`
4. Open one existing subject by id:
   `python3 host/lm_gtm_index.py show composio`
   (also `city-of-billings-bid-1421`, `msp-integris`, `communitycare-katherine-reyes`,
   `signoz`, `metaforms`, `anythingllm-mintplex`, or any other INDEX id).
   `metaforms` and the MSP SENT rows hydrate `route.kind: EXISTING_CRM_RECORD`
   / `airtable:rec…`. Emails and phones stay in source ledgers; the INDEX
   does not copy them.

Write (overlay only):

```sh
python3 host/lm_gtm_index.py append-event \
  --subject composio \
  --id yourname-gtm-note-YYYYMMDD-01 \
  --body "draft remains STAGED_NOT_SENT; no transport"

python3 host/lm_gtm_index.py claim --subject composio --owner YOURNAME
python3 host/lm_gtm_index.py release --subject composio --owner YOURNAME
# second occupancy fails closed unless:
python3 host/lm_gtm_index.py claim --subject composio --owner OTHER --steal
```

Pointer overlay events may introduce INDEX rows by reference (Slack ts, Gmail
id, Airtable rec). Unknown NOTE ids are refused. Event-id remint is refused.
Seller fixture contacts cannot receive overlay events. No `crm/`, `people/`,
`contacts/`, or `sales/` tree is created.

`--send` exits 3. This composer never transports mail.

```sh
python3 host/lm_gtm_index.py validate
python3 host/lm_gtm_index.py write-index
python3 host/lm_gtm_index.py next
python3 host/lm_gtm_index.py hot
python3 host/lm_gtm_index.py show city-of-billings-bid-1421
python3 -m unittest -v test_lm_gtm_index.py
```

Door: [`lm-gtm-index.html`](../../lm-gtm-index.html).
State: [`state.json`](./state.json).

## What this reads and does not replace

- `revenue/website_people_email_book/loop.json` (`commons-website-people-email-book/v2`)
- `revenue/smart_outreach/candidates.json`
- `revenue/reply_to_revenue/funnel.json`
- `revenue/payment_ready/outreach_receipts/`
- `revenue/marketing_sales/pipeline.json` (research-universe summary only; the
  ~1000 `RESEARCH_REQUIRED` GitHub entities are not live sales next-actions)
- `revenue/swarm_mail/inboxes.json`
- `revenue/lm_gtm_index/events.jsonl` (overlay pointers + occupancy)

Seller contacts from the website loop stay `seller_context` and are never
live buyers. Outbound mailbox truth remains `NEEDS_OWNER_MAILBOX`.

Do not remint `lm-gtm-index-20260831-01`, `website-people-email-book-20260830-01`,
or `website-prospect-boundary-repair-20260830-01`. Do not rewrite loop.json
schema v2.
