# ledger-crm6-mailbox-buyer-reply-verify-20260905-01

## Claim
CLAIM `ledger-crm6-mailbox-buyer-reply-verify-20260905-01` · Slack `1788653647.048429`
FORGE write · LEDGER review · girly GO

## What
Hermetic mailbox-only buyer-reply verify pin for CRM6.

```sh
python3 host/lm_gtm_mailbox_buyer_reply_verify.py city-of-billings-bid-1421
```

Status values:
- `NO_BUYER_REPLY` — outbound SENT anchors present; no inbound buyer mail in-thread after them
- `BUYER_REPLY_OBSERVED` — hermetic fixture includes inbound buyer mail after outbound

Billings committed fixture is outbound-only (`gmail:1a06e2cbaa802037`, `gmail:1a06e2cc33f8c7aa`) → `NO_BUYER_REPLY`. Ack remains unestablished.

Optional: `--pin-material-reply --organization NAME` appends a `MATERIAL_REPLY` pointer to `revenue/lm_gtm_index/relationship_handoff_evidence.jsonl` only when status is `BUYER_REPLY_OBSERVED`. Never mutates `INDEX.jsonl` / `events.jsonl`.

`verified_human_yes` is always `false` in this slice. Never invent `VERIFIED_HUMAN_YES`.

Live Gmail is optional later; this PR is hermetic fixtures + mechanism only.

## Paths
- `host/lm_gtm_mailbox_buyer_reply_verify.py`
- `revenue/lm_gtm_index/mailbox_buyer_reply_fixtures/`
- `tests/test_ledger_crm6_mailbox_buyer_reply_verify.py`
- this receipt

## Boundary
No Cheri contact. No resend. No second CRM. No INDEX remint.
Does not remint `ledger-crm6-relationship-handoff-20260904-01` or freshness gate.
Hands off #8802.
