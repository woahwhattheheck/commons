# E08 event-horizon ablation — submitted V3.1 vs V4 causal screen

This is an evidence-only V5 carrier for one V4-only semantic family. It does not change current runtime defaults, `TITAN-CONFIG.json`, release pointers, archives, or Kaggle submission.

## Why this exists

Exact submitted V3.1 source `a90d888f03987ef0b35cfd20ec3519c6144db08a` uses the inherited fixed SELL lookahead: `min(now + HORIZON, terminal, day_end)`, then clamps at the first unresolved controller checkpoint. Exact submitted V4 source `4af1113154e78c662780e6658cd920daac7902e3` includes E08 event-aware horizon extension (`event_aware_horizon`, represented shed-load events, and per-product event dates). The original E08 integration thread explicitly closed source/package tests but reported zero new complete official-engine games and no playing-strength claim.

`ablate_e08.py` authenticates exact submitted-V4 `frozen_selected.py` by Git blob `fc7baf5c179818a55037f6a61d92984d81d1a21c`, then rewrites only the E08 transform wiring back to the submitted-V3.1 fixed-window/date behavior. Later V4 seller mechanics remain intact, including funded-minimum policy, same-turn acquisition funding, E05 joint SELL composition, seller acceptance rules, and ordinary sale materialization.

The treatment intentionally leaves the E08 helper definitions present but unreachable from `FrozenSelected.transform`. This keeps the causal patch small: the experiment asks whether *using* E08 changed strength, not whether deleting dead helper text changes packaging.

## Source contracts

```bash
cd revenue/kaggriculture/cloud-execution-lab/candidates/v5/e08-event-horizon-ablation
python -B -m py_compile ablate_e08.py test_ablate_e08.py
python -B -m unittest -v test_ablate_e08.py
python -O -B -m unittest -v test_ablate_e08.py
```

The tests fetch the exact V3.1/V4 historical seller bytes from Git history, authenticate both Git blobs, compile the deterministic treatment source, prove the E08 calls are absent from the transformed seller path, prove later V4 seller mechanisms remain present, and cover the old eight-turn/checkpoint/day/terminal boundaries.

## Next evidence gate

Use exact submitted V4 archive SHA256 `4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b` as CTRL. Materialize an ABLATE arm that changes only `frozen_selected.py` to the deterministic output of `ablate_e08.py`; authenticate all unchanged members. First run direct just-outside-horizon/service and represented-shed-load engagement witnesses, then matched Apex/Arlene seeds in both seats. Record first trace divergence plus terminal own/rival/margin. A useful result feeds the single staged V5; this carrier itself authorizes no runtime/default promotion.
