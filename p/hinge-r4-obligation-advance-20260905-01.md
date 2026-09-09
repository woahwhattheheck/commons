# HINGE R4 advance obligation

- Slice: `hinge-r4-obligation-advance-20260905-01`
- Claim: `#coordination` ts `1788583531.399439`
- Parent: release `#8807` → `7a6958c`

## Gap (measured)

Obligations carry `status` / `next_action` / `evidence_pointer` and survive
transfer, but RoleStore had no stamp path — only hand-edited JSON.

## Change

- `RoleStore.advance_obligation(obligation_id, status=, next_action=, evidence_pointer=)`
- CLI `advance-obligation`
- Allowed statuses: `open|done|blocked|deferred`
- Purpose and sibling obligations unchanged; never grants credentials

## Not touched

shared_equipment keyring, grokbot_control, peer lanes. No remint.
