# FLORA KAG-PRODUCTION

This lane integrates an observable-state production system into the exact
selected KAG-COMPOSE dispatcher. It adds the official strawberry lifecycle,
fertilizer retention/pickup/application, finite-horizon crop valuation, timed
land purchases, and labor sizing. Visible unlocked shops affect crop value;
no hidden episode seed, opponent identity, replay fingerprint, network, or
external state is used.

`build.py` refuses drift from the selected KAG-COMPOSE SHA-256 and emits the
standalone `candidate.py`. Its production-event projection is frozen from
ROWAN's landed `cloud-frontier-trace/events.py` contract (blob
`48b3c0df949e13bf4c63ee86f5d5b3a58ec00aec`). Market commitments use a
single sequential cash ledger: seeds are protected first, then only the exact
feed deficit is bought at per-unit repriced cost.

## Current evidence

- Same seed as the merged checkpoint: **+21,501.5** versus KAG-COMPOSE,
  with the Kaito and Igor gaps reduced to **-22,541.5** and **-21,259.0**.
- Two additional development seeds: 4/4 wins over the merged checkpoint,
  mean margin **+8,120.0**.
- Those additional seeds still lost 0/4 to each strong public reference;
  Kaito mean margin **-21,415.5**, Igor **-27,495.75**.
- All 20 selected-policy games completed without agent failures and each
  report's first game replayed with identical scores and trace.

The public references remain materially stronger. These are official-
interpreter development results, not hosted Kaggle scores or evidence of
leaderboard leadership. The initially corrected feed-before-seed ledger was
rejected after losing both same-seed seats to the merged policy by 14,139 mean;
its bytes are not shipped.

Run the focused source contract:

```bash
python -B revenue/kaggriculture/cloud-production/test_production.py
```

The official interpreter remains pinned to
`28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`. Development compute was run in
the cloud workspace only. No competition submission or account mutation was
performed.
