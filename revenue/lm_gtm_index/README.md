# LLM-native GTM index

One index-first compose/query layer over GTM ledgers Commons already has.
Humans keep the existing UIs. Agents load one INDEX, run `brief` for compact
HOT next-actions, open an existing prospect by reference, and append an overlay
event. This is not a second CRM and not a new contact book.

Canonical CRM remains Airtable `JOJO Revenue Recovery CRM / Revenue Pipeline`.
Private routes stay off git. Public cash stays USD 0 unless a named payment
evidence URL already exists in a source ledger.

Floor command is now `python3 host/lm_gtm_index.py brief` — compact JSONL
(header + HOT rows). Header includes `occupied` (live rows whose owner
is not UNSEATED), `composed_at`, `mailbox` only while still
`NEEDS_OWNER_MAILBOX`, and a one-line `stale_warning` when the overlay
is older than 12h. Compact rows omit `owner` when UNSEATED and omit
`dnr` when false; keep `dnr: true` on sent/bounced and keep `owner`
when actually claimed. `sent` is HARD_DO_NOT_RESEND, including bounced
DNR with decision `BOUNCED`.
`hot` remains the full-row actionable subset: it excludes seller context,
the research universe, mailbox manifests, DNR / HOLD_DO_NOT_RESEND /
HOLD_DO_NOT_CONTACT, OWNER_HOLD, SENT/AWAITING_REPLY with
HARD_DO_NOT_RESEND, bounced DNR, and HOLD_BUILD_AND_VERIFY unless a
MATERIAL_REPLY reopened them. Rank: material_reply > sent_awaiting_reply >
ready_to_draft > verified_lead_unsent. City of Billings Bid 1421 is
OWNER_HOLD, not hot.

`python3 host/lm_gtm_index.py hold` lists HOLD_BUILD_AND_VERIFY rows. Those
are live and queryable, not hot, and PRE-SALE TRANSPORT NONE.

Occupancy (`claim` / `release`) writes an overlay event onto the INDEX `owner`
field. It does not rewrite `loop.json`. A second occupancy on a seated live
one fails closed unless `--steal` is explicit. That is collision-avoidance
for two harnesses hitting the same live one, not an admission gate. Both
positional subject and `--subject` work; `--owner` is required.

## Cross-harness contract

Read (any harness with git):

1. Load [`INDEX.jsonl`](./INDEX.jsonl). First line is `LM_GTM_INDEX_HEADER`.
   Every later line is one `LM_GTM_INDEX_ROW` pointing at existing files.
2. List all live next-actions: rows with `"live": true`, or
   `python3 host/lm_gtm_index.py next`.
3. Compact HOT (agent floor):
   `python3 host/lm_gtm_index.py brief`
4. HARD_DO_NOT_RESEND:
   `python3 host/lm_gtm_index.py sent`
5. Full-row actionable live ones:
   `python3 host/lm_gtm_index.py hot`
6. Open one existing subject by id (compact; `--sources` hydrates ledgers):
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

python3 host/lm_gtm_index.py claim composio --owner YOURNAME
python3 host/lm_gtm_index.py release composio --owner YOURNAME
# contract form is TOKEN placeholders (survive JSON/markdown/HTML):
# python3 host/lm_gtm_index.py claim SUBJECT --owner YOU
# equivalent flag form:
python3 host/lm_gtm_index.py claim --subject composio --owner YOURNAME
# second occupancy fails closed unless:
python3 host/lm_gtm_index.py claim composio --owner OTHER --steal
```

Pointer overlay events may introduce INDEX rows by reference (Slack ts, Gmail
id, Airtable rec). HOLD_BUILD_AND_VERIFY pointers are org + person + Slack ts
only. STATUS refreshes `next_action` / `source_paths` / `due` / `decision` /
`dnr` on an existing live subject and cannot mint a contact. Unknown
NOTE/STATUS ids are refused. Event-id remint is refused. Seller fixture
contacts cannot receive overlay events. No `crm/`, `people/`, `contacts/`, or
`sales/` tree is created.

`--send` exits 3. This composer never transports mail.

```sh
python3 host/lm_gtm_index.py validate
python3 host/lm_gtm_index.py write-index
python3 host/lm_gtm_index.py brief
python3 host/lm_gtm_index.py sent
python3 host/lm_gtm_index.py next
python3 host/lm_gtm_index.py hot
python3 host/lm_gtm_index.py hold
python3 host/lm_gtm_index.py show city-of-billings-bid-1421
python3 host/lm_gtm_index.py show composio --sources
python3 host/lm_gtm_index.py claim composio --owner YOURNAME
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

Do not remint `lm-gtm-index-20260831-01`, `lm-gtm-hot-lane-20260831-01`,
`lm-gtm-floor-sync-20260831-01`, `lm-gtm-agent-brief-20260831-01`,
`lm-gtm-truth-sync-20260831-02`, `lm-gtm-contract-brief-20260901-01`,
`lm-gtm-contract-tokens-leads-20260901-01`,
`website-people-email-book-20260830-01`, or
`website-prospect-boundary-repair-20260830-01`. Do not rewrite loop.json
schema v2. Do not remint MSP overlay event ids or the Billings MATERIAL_REPLY
pointer `lm-gtm-billings-material-reply-20260831-01`. Do not remint
`lm-gtm-billings-floor-status-20260831-01` or
`lm-gtm-billings-runner-status-20260831-01`.
