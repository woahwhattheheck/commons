# LLM-native GTM index

One index-first compose/query layer over GTM ledgers Commons already has.
Humans keep the existing UIs. Agents load one INDEX, list live next-actions,
open an existing prospect by reference, and append an overlay event. This is
not a second CRM and not a new contact book.

Canonical CRM remains Airtable `JOJO Revenue Recovery CRM / Revenue Pipeline`.
Private routes stay off git. Public cash stays USD 0 unless a named payment
evidence URL already exists in a source ledger.

## Cross-harness contract

Read (any harness with git):

1. Load [`INDEX.jsonl`](./INDEX.jsonl). First line is `LM_GTM_INDEX_HEADER`.
   Every later line is one `LM_GTM_INDEX_ROW` pointing at existing files.
2. List live next-actions: rows with `"live": true`, or
   `python3 host/lm_gtm_index.py next`.
3. Open one existing subject by id:
   `python3 host/lm_gtm_index.py show composio`
   (also `signoz`, `metaforms`, `anythingllm-mintplex`, or any other INDEX id).
   `metaforms` hydrates `route.kind: EXISTING_CRM_RECORD` /
   `airtable:recWHbHxQoQfGhS0q` from `loop.json`. Emails stay in the source
   ledgers; the INDEX does not copy them.

Write (overlay only):

```sh
python3 host/lm_gtm_index.py append-event \
  --subject composio \
  --id yourname-gtm-note-YYYYMMDD-01 \
  --body "draft remains STAGED_NOT_SENT; no transport"
```

The event appends to [`events.jsonl`](./events.jsonl) and cites an existing
subject id. Unknown ids are refused. Event-id remint is refused. Seller
fixture contacts cannot receive overlay events. No `crm/`, `people/`,
`contacts/`, or `sales/` tree is created.

`--send` exits 3. This composer never transports mail.

```sh
python3 host/lm_gtm_index.py validate
python3 host/lm_gtm_index.py write-index
python3 host/lm_gtm_index.py next
python3 host/lm_gtm_index.py show metaforms
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

Seller contacts from the website loop stay `seller_context` and are never
live buyers. Outbound mailbox truth remains `NEEDS_OWNER_MAILBOX`.

Do not remint `website-people-email-book-20260830-01` or
`website-prospect-boundary-repair-20260830-01`. Do not rewrite loop.json
schema v2.
