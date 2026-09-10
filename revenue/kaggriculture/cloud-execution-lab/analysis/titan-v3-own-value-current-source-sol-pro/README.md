# TITAN V3 own-value objective — current-source integration

Operation: `TITAN-V3-OWN-VALUE-CURRENT-SOURCE-INTEGRATION-20260910-01`

This carrier ports the action-active SELL factor admitted by PR #11965 into the current editable source seam. It is deliberately a one-factor change:

```diff
-return own_cash + carry - other_cash, own_cash, other_cash, remaining
+return own_cash + carry,              own_cash, other_cash, remaining
```

The first tuple field is the optimizer ranking objective. The other fields remain realized own receipts, modeled rival receipts, and unsold units. Candidate enumeration, market pricing and floor admission, rival scenarios, queue feasibility, continuation receipts, materialization, and acceptance rules are unchanged.

## Exact binding

- integration base: `main@21011846096daad1dd487df0efedf209303c1cb5`
- predecessor `selected_sell_core.py` blob: `f23d3a8b5ee5e82029026e7f8f44eb36c143a5a3`
- integrated `selected_sell_core.py` blob: `368c21384b85b4dba39971cb8a51b6942d10acc7`
- evidence source: PR #11965 exact head `b6b9a8a4ca26152bbfe1a3833380ca885e5c4cae`
- authoritative evidence run: `34521455981`
- independent intake review: `5171602997`

The inherited current-package panel was action-active in all 32 tested cells and reported mean/median own-cash deltas of `+159.25/+118.5`, total own cash `+5096`, mean margin `+530.96875`, `31W/1L -> 32W/0L`, zero new losses, zero lost wins, and nonnegative opponent-by-seat gates. That panel is development intake evidence, not a disjoint promotion holdout.

## Fail-closed contracts

`verify_current_source.py` parses the real source and requires:

1. exactly one top-level `MarketPath` and one `MarketPath.score`;
2. the exact reviewed method signature and `terminal=False` default;
3. a four-field return tuple whose objective is structurally `own_cash + carry`;
4. unchanged diagnostic tuple fields;
5. objective dependencies limited to `own_cash` and `carry`;
6. a live optimizer consumption surface rather than a dead descriptive edit.

`test_current_source.py` kills the predecessor rival-subtraction objective, tuple/signature/duplicate-seam drift, and executes the integrated method against rival-invariance, continuation-value, terminal-boundary, and decision-inversion witnesses.

Run without gameplay:

```bash
CASE=revenue/kaggriculture/cloud-execution-lab/analysis/titan-v3-own-value-current-source-sol-pro
LAB=revenue/kaggriculture/cloud-execution-lab
python "$CASE/verify_current_source.py" --source "$LAB/selected_sell_core.py"
python -m unittest -v "$CASE/test_current_source.py"
```

## Integration boundary

This branch does **not** rebuild or repoint the canonical archive/source manifest, spend holdout seeds, mutate provider or Kaggle state, submit a notebook, or authorize promotion. The one-tree owner should compose this exact source factor with other admitted factors, then the archive custodian should rebuild from that reviewed source tree. A genuinely disjoint stronger-opponent holdout remains required before submission selection.
