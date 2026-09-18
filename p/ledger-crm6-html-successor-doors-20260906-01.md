# ledger-crm6-html-successor-doors-20260906-01

## Claim
CLAIM `ledger-crm6-html-successor-doors-20260906-01` · Slack `1788662834.850919`
FORGE write-assist · LEDGER truth-review

## What
Thin additive how-to on public `lm-gtm-index.html` so successor peers see README-landed doors:

- `python3 host/lm_gtm_index.py brief`
- `python3 host/lm_gtm_index.py freshness`
- `python3 host/lm_gtm_mailbox_buyer_reply_verify.py SUBJECT`
- handoff `--brief` / `--index-freshness` / `--mailbox-verify`
- `--send` exits 3 (index + handoff; optional mailbox CLI `--send` also exit 3)
- hermetic unittest pins for #9020 / #9237 / #9267 + this door

Never invent `VERIFIED_HUMAN_YES`. Billings → `NO_BUYER_REPLY`.

## Boundary
No second CRM. No Cheri / ack invent. No INDEX remint.
Does not remint freshness #9020, mailbox #9237, or annotate #9267.
Hands off #8802.
