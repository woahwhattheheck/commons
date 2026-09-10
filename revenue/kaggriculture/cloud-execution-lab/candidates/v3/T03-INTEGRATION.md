# T03 opening-script integration contract

Operation: `TITAN-V3-T03-OPENING-SCRIPT-SOLVENCY-20260910-01`  
Base handoff: Slack `F0C0JPCAAQP`, SHA-256 `f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728`.

This draft is stacked on the one-tree landing branch. It adds the independently testable lane source now and does **not** promote a gameplay variant. Apply the wiring below only after the base branch has materialized its 13-file V3 source.

## Runtime wiring

In `apply_v3.py` add package parameters:

```python
"opening_script_variant": "balanced",
"opening_cash_reserve": 350.0,
"opening_last_step": 47,
```

Add default-off `Features` fields:

```python
opening_script: bool = False
opening_script_variant: str = "balanced"
opening_cash_reserve: float = 350.0
opening_last_step: int = 47
```

Include `opening_script` in `_v3_active()` and `_v3_config()`. Carry the three parameters under `titan_v3.params`. In `_v3_post()`, before rival-model and hire-guard mutation:

```python
if v3.get("opening_script"):
    from opening_script import apply_opening_script
    output, report["opening_script"] = apply_opening_script(
        obs, output, params, enabled=True
    )
```

Add `opening_script: false` plus the three parameters to `TITAN-CONFIG.json`. Keep all-off behavior byte-identical to canonical.

## Admission boundary

Only `action["market"]` may change. Exact-step tapes are quoted in full before replacement. The gate checks market cardinality, fixed seed/animal/land costs, public `hires_today` with Fibonacci hire pricing, finite numeric state, and a cash reserve. It credits no uncertain same-turn SELL receipt and rejects nonlinear `BUY_PRODUCT` without the engine curve quote. Every rejection returns the inherited action object unchanged.

Historical arithmetic is executable evidence:

- `gemini_legacy`: $882, leaving $118 from $1,000; the reported $502 was wrong.
- `leader_legacy`: $1,507, exceeding $1,000 by $507; the reported $757 was wrong.
- `balanced`: $402, leaving $598. Planting remains canonical.
- `liquid`: $167, leaving $833. Planting remains canonical.

## Required gate before promotion

1. Run `build_v3.py`, then `build_v3.py --check`, refreshing `FILES.json` and manifest hashes.
2. Run the three `checks/test_v3_opening_*.py` suites in the materialized package; the two wiring checks must stop skipping and pass.
3. Prove all-off identity against canonical.
4. Panel `balanced` and `liquid` separately on matched seeds, seats, and opponents. Do not promote either without observed non-negative evidence.
