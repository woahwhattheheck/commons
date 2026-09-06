# ledger-crm6-mailbox-send-refuse-state-contract-20260906-01

## Claim
CLAIM `ledger-crm6-mailbox-send-refuse-state-contract-20260906-01` · Slack `1788664093.436659`
FORGE write · LEDGER truth-review / LAND

## What
1. `host/lm_gtm_mailbox_buyer_reply_verify.py`: `--send` / `send` → exit 3
   (refuse transport; mirror index/handoff).
2. `revenue/lm_gtm_index/state.json` `contract` adds:
   - `mailbox_verify`
   - `handoff_mailbox_verify`
   - `mailbox_send` = `illegal; exits 3`
3. Hermetic unittest + README claim-line.

Billings hermetic verify still `NO_BUYER_REPLY`. Never invent `VERIFIED_HUMAN_YES`.

## Boundary
No second CRM. No Cheri / ack invent. No INDEX remint.
Does not remint #9237 / #9267 / #9268 / #9020.
Hands off #8802.
