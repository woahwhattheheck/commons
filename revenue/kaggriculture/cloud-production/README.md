# FLORA KAG-PRODUCTION

This lane integrates an observable-state production system into the exact
selected KAG-COMPOSE dispatcher. It adds the official strawberry lifecycle,
fertilizer retention/pickup/application, finite-horizon crop valuation, timed
land purchases, and labor sizing. Visible unlocked shops affect crop value;
no hidden episode seed, opponent identity, replay fingerprint, network, or
external state is used.

`build.py` refuses drift from the selected KAG-COMPOSE SHA-256 and emits the
standalone `candidate.py`. The initial development pilot used one new seed in
both seats against KAG-COMPOSE and the hash-pinned Kaito/Igor references. It is
an explicit-interpreter development result, not a hosted Kaggle score.

## Current evidence

- 2/2 wins against KAG-COMPOSE; mean margin **+9,793.5**.
- 0/2 against Kaito; mean margin **-41,809.0**.
- 0/2 against Igor; mean margin **-37,738.5**.
- The diagnostic match executed 33 plant, 365 water, 64 fertilize, 302 harvest,
  and 39 drop actions, reaching 79,866 terminal cash versus 70,135.
- The first report game replayed with identical scores and trace.

The public references remain materially stronger. This checkpoint proves that
the requested production loop is executable and improves the inherited policy
on the pilot; it does not establish leaderboard readiness or superiority.

Run the focused source contract:

```bash
python -B revenue/kaggriculture/cloud-production/test_production.py
```

The official interpreter remains pinned to
`28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`. Development compute was run in
the cloud workspace only. No competition submission or account mutation was
performed.

