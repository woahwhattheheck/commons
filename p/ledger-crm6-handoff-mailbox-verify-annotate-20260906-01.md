# ledger-crm6-handoff-mailbox-verify-annotate-20260906-01

## Claim
CLAIM `ledger-crm6-handoff-mailbox-verify-annotate-20260906-01` · Slack `1788659069.785529`
FORGE write · LEDGER review

## What
Optional handoff annotate mirroring `--index-freshness`:

```sh
python3 host/lm_gtm_relationship_handoff.py city-of-billings-bid-1421 --mailbox-verify
```

Stamps `mailbox_verify` from the landed hermetic pin (#9237). Billings →
`NO_BUYER_REPLY`. `verified_human_yes` is always false; invent attempts fail
closed to UNKNOWN. Missing fixtures become UNKNOWN while the packet remains
usable.

Registry: `revenue/lm_gtm_index/mailbox_buyer_reply_registry.json` records the
landed mailbox claim id / PR / merge SHA.

README documents the flag and that `--send` exits 3 on handoff (no transport).

## Boundary
No second CRM. No Cheri / ack invent. No INDEX remint.
Does not remint mailbox verify #9237 or freshness #9020.
Hands off #8802.
