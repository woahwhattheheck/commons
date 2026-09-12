# V3.1 -> V4 regression coverage ledger

This is a convergence artifact for the single TITAN V5 line. It does not add a gameplay policy and does not authorize a rollback. Its job is to stop the swarm from repeatedly rediscovering the same V3.1/V4 differences while leaving other score-facing differences unexamined.

## What it proves

`coverage.py` reads historical Git objects directly and fails closed when a pinned blob drifts, a changed row has no status, an active row has anything other than one primary carrier, or a decomposed Python file contains a changed symbol not named in `COVERAGE.json`.

The first high-value distinction is **source ref versus submitted-package authority**. The historical V3.1 source ref `a90d888f...` has a different `frozen_selected.py`, but the V3.1 assembled-base witness `741e7262` and submitted V4 source `4af11131...` both resolve that seller to Git blob `fc7baf5c179818a55037f6a61d92984d81d1a21c`. Therefore E05/E08/same-turn-funding experiments remain useful V4-active self-ablations, but copying the raw `a90d.../frozen_selected.py` and calling it “restore V3.1” would be a provenance error.

Other exact identities already closed here:

- active Arlene producer is identical in the two submitted refs (`bdb9cf58...`), so the strong 13-tape donor is a new V5 producer treatment rather than a V3.1 producer restoration;
- `seed_funding.py`, `deadline_adapter.py`, `terminal.py`, and `terminal_composition.py` are byte-identical;
- `reference/titan-current/redundant_hire.py` is a real changed member and is already owned by the authenticated #13442 E20 treatment;
- `selected_sell_core.py` changed, but under the submitted strict acceptance rule the added no-rival early prune cannot remove any candidate that the older strict min-all-scenarios rule would accept;
- `TITAN-CONFIG.json` differs by exactly four added true flags: `idle_fertilizer`, `crop_release`, `early_capital`, and `town_procurement`, owned by the existing #13426 factorial screen.

The root `titan_runtime.py` and `scheduler.py` are intentionally decomposed at symbol granularity. CI must stay red until every changed symbol is assigned to an existing causal lane or carries a concrete noncausal proof. This makes residual V3.1->V4 behavior an explicit queue instead of a verbal assumption.

## Run

```bash
cd revenue/kaggriculture/cloud-execution-lab/candidates/v5/regression-coverage
python -B coverage.py
python -B -m unittest -v test_coverage.py
python -O -B -m unittest -v test_coverage.py
```

A green ledger is evidence that the named historical surface has no **unknown classification**. It is not evidence that every active causal lane improves score, and it does not promote any treatment into runtime. Promotion still requires the existing matched-game and single-V5 composition gates.
