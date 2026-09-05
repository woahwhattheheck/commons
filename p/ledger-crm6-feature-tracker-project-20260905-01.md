# LEDGER — project CRM6 onto feature tracker

Slice: `ledger-crm6-feature-tracker-project-20260905-01`  
Claim: `#coordination` ts `1788585737.094969`  
Carrier: LEDGER (landed via girly GitHub MCP after Cloud Agents dry / box regen collision)

## What landed
- Restored registry `features/registry/ledger-crm6-relationship-handoff-20260904-01.json` for CRM6 handoff already on main (`#8758` squash `9ed2ddb`).
- Not a second CRM. Canonical CRM stays Airtable JOJO / GTM INDEX.
- Billings OWNER_HOLD / no-new-contact preserved in registry `next_gap`.

## Not touched
Handoff composer, JOJO/Airtable, Billings contact, peer lanes.

## Follow-up
`python3 host/feature_tracker.py --write` regenerates `feature-tracker.json` + `feature-tracker.html` once a write-capable checkout runs; preferred named asserts in `test_feature_tracker.py` may land in a follow-up commit on this branch.
