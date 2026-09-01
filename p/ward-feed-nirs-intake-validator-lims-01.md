---
id: ward-feed-nirs-intake-validator-lims-01
title: Ward feed/forage → NIRS intake validator LIMS
agent: cursor-cloud-bc-b0829985-fd71-4a97-a50d-1b24540aea48
demand: ward-feed-nirs-intake-validator-lims-01
buyer: Ward Laboratories / Nikki Kuhr
gate: HOLD / BUILD-AND-VERIFY
cash_usd: 0
pre_sale_transport: NONE
---

# Ward feed/forage → NIRS intake validator

Shipped unique OPEN leftover from #build-demand (`Demand ID: ward-feed-nirs-intake-validator-lims-01`, Slack `1788150744.422929`).

## Product

Synthetic feed/forage form ingestion → bag-label reconcile → description→NIRS calibration → NIRS/wet-chem route → prep + time gates → worksheet only for READY → staged report → named-human release.

## Acceptance (locked)

| Metric | Value |
| --- | --- |
| Inputs | 400 |
| READY / accessioned | 320 |
| HOLD | 80 |
| NIRS routes | 240 |
| Wet-chem routes | 80 |
| Replay new accessions | 0 |
| Replay new worksheets | 0 |
| Autonomous release | denied |

HOLD mix: 14 missing ID, 14 missing analysis, 13 desc/calibration conflict, 13 duplicate bag, 13 insufficient prep, 13 time window.

## Commands

```bash
python3 ward_feed_nirs_intake_validator.py
python3 test_ward_feed_nirs_intake_validator.py
```

## Paths

- `ward_feed_nirs_intake_validator.py`
- `test_ward_feed_nirs_intake_validator.py`
- `ward-feed-nirs-intake-validator-lims.html`
- `revenue/ward_feed_nirs_intake_validator/`
- `features/registry/ward-feed-nirs-intake-validator-lims-01.json`

Adapters simulated/read-only. No outreach. No production writes. PRE-SALE TRANSPORT: NONE.
