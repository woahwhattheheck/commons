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
one fails closed unless `--steal` is explicit. Occupancy is admission for
sales/draft/outreach only; `brief` remains the listing floor. Unclaimed
sales are illegal and exit 4. Both positional subject and `--subject` work;
`--owner` is still named on claim/release.

## SALES_FLOOR

Agents doing sales use `brief` then `claim`. No claim = no draft.
`python3 host/lm_gtm_index.py require-claim SUBJECT --owner YOU` exits 0
only when the live occupant matches YOU. UNSEATED or a different occupant
exits 4. Listing stays open. Still not a second CRM. `--send` exits 3.

## RELATIONSHIP_HANDOFF (CRM6)

When a peer's context window is gone, the successor continues from evidence:

```sh
python3 host/lm_gtm_relationship_handoff.py SUBJECT
python3 host/lm_gtm_relationship_handoff.py city-of-billings-bid-1421
```

Returns kind `LM_GTM_RELATIONSHIP_HANDOFF` with SOURCED or ABSENT fields for
wants, learned, promised, sent_communication, unresolved,
next_time_sensitive, and successor_next_action. A typed
`SENT_AWAITING_REPLY` record is communication evidence only and is surfaced as
`sent_communication`; it does not establish what anyone promised. `promised`
remains ABSENT until a source-reading mechanism supplies separately verified
commitment content. Pointer prose stays `SUMMARY_POINTER` even when it cites a
Gmail or Slack message: the pointer is retained, but this composer does not
claim it fetched or quoted the linked source. Event chronology is
 timezone-aware.

`relationship_handoff_evidence.jsonl` is a narrow, validated,
source-pointer-only supplement for facts that must reach the successor without
rewriting the canonical INDEX overlay or copying private mail into Git. The
packet labels those records `RELATIONSHIP_EVIDENCE`, labels canonical overlay
records `INDEX_OVERLAY`, lists the relationship event ids, and reports
`canonical_index_mutated: false`. The supplement is not a second CRM.

The Billings example now distinguishes these facts:

- main proposal and separate confidential-pricing package: `SUBMISSION_SENT`;
- recipient acknowledgement, acceptance, award, and payment: not established;
- effective state: OWNER_HOLD / DNR_OUTREACH / NOT_HOT;
- next action: do not resend or contact Cheri; wait for acknowledgement or a
  buyer reply;
- next time-sensitive source target: 2026-09-28, not the expired submission
  deadline.

Canaries:

```sh
python3 -m unittest -v test_lm_gtm_relationship_handoff.py
python3 -m unittest -v test_lm_gtm_handoff_provenance.py
```

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
7. Relationship handoff for a successor peer:
   `python3 host/lm_gtm_relationship_handoff.py city-of-billings-bid-1421`

Write (canonical overlay only):

```sh
python3 host/lm_gtm_index.py append-event \
  --subject composio \
  --id yourname-gtm-note-YYYYMMDD-01 \
  --body "draft remains STAGED_NOT_SENT; no transport"

python3 host/lm_gtm_index.py claim composio --owner YOURNAME
python3 host/lm_gtm_index.py require-claim composio --owner YOURNAME
python3 host/lm_gtm_index.py release composio --owner YOURNAME
# contract form is TOKEN placeholders (survive JSON/markdown/HTML):
# python3 host/lm_gtm_index.py claim SUBJECT --owner YOU
# python3 host/lm_gtm_index.py require-claim SUBJECT --owner YOU
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
python3 host/lm_gtm_index.py require-claim composio --owner YOURNAME
python3 host/lm_gtm_relationship_handoff.py city-of-billings-bid-1421
python3 -m unittest -v test_lm_gtm_index.py
python3 -m unittest -v test_lm_gtm_relationship_handoff.py
python3 -m unittest -v test_lm_gtm_handoff_provenance.py
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
- `revenue/lm_gtm_index/events.jsonl` (canonical overlay pointers + occupancy)
- `revenue/lm_gtm_index/relationship_handoff_evidence.jsonl` (validated
  source-pointer supplement used only by CRM6 handoff; not canonical CRM and
  not an INDEX mutation)

Seller contacts from the website loop stay `seller_context` and are never
live buyers. Outbound mailbox truth remains `NEEDS_OWNER_MAILBOX` for the
canonical public projection; CRM6 handoff can cite specific verified message
ids without copying addresses or message bodies.

Do not remint `lm-gtm-index-20260831-01`, `lm-gtm-hot-lane-20260831-01`,
`lm-gtm-floor-sync-20260831-01`, `lm-gtm-agent-brief-20260831-01`,
`lm-gtm-truth-sync-20260831-02`, `lm-gtm-contract-brief-20260901-01`,
`lm-gtm-contract-tokens-leads-20260901-01`,
`lm-gtm-require-claim-20260904-01`,
`website-people-email-book-20260830-01`, or
`website-prospect-boundary-repair-20260830-01`. Do not rewrite loop.json
schema v2. Do not remint MSP overlay event ids or the Billings MATERIAL_REPLY
pointer `lm-gtm-billings-material-reply-20260831-01`. Do not remint
`lm-gtm-billings-floor-status-20260831-01` or
`lm-gtm-billings-runner-status-20260831-01`.
