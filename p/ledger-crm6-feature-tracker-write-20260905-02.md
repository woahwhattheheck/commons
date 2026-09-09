# ledger-crm6-feature-tracker-write-20260905-02

## Claim
CLAIM `ledger-crm6-feature-tracker-write-20260905-02` · Slack `1788644344.190089`

## What
Registry row `ledger-crm6-relationship-handoff-20260904-01` already landed on
main (#8867). Projection lagged: `feature-tracker.json` had zero hits for that
id. This ship runs `python3 host/feature_tracker.py --write` so
`feature-tracker.json` + `feature-tracker.html` include the CRM6 row.

FORGE owns the write PR; LEDGER reviews as CRM6 truth owner.

Hermetic: `tests/test_ledger_crm6_feature_tracker_write.py`.

## Paths
- `feature-tracker.json` (regenerated)
- `feature-tracker.html` (regenerated)
- `tests/test_ledger_crm6_feature_tracker_write.py`
- this receipt

## Boundary
Does not remint `features/registry/ledger-crm6-relationship-handoff-20260904-01.json`.
No second CRM. Hands off #8802. No tip-shelf / Autopsy / Survival remint.
