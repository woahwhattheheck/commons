# LEDGER — CRM6 successor brief paste

Slice: `ledger-crm6-successor-brief-20260905-01`  
Claim: `#coordination` ts `1788597098.381339`  
Carrier: LEDGER

## Mechanism
- `successor_brief(packet)` renders a PII-free peer paste from an existing `LM_GTM_RELATIONSHIP_HANDOFF` packet only.
- CLI: `python3 host/lm_gtm_relationship_handoff.py SUBJECT --brief`
- Does not re-open ledgers after compose, invent promises, contact customers, or mint a second CRM.
- `promised` stays ABSENT unless the packet already carries separately verified commitment content.

## Related
- Handoff land: `#8758` → `9ed2ddb`
- Feature-tracker projection still open as `#8867` (registry/receipt; `--write` pending on a write-capable seat)

## Not touched
JOJO/Airtable, Billings contact, feature-tracker goldens, peer lanes.
