# TITAN V3.1 H4 × horizon-10 interaction arm

Operation: `TITAN-V31-H13-H4-HORIZON10-INTERACTION-CARRIER-20260911-01`

This is an **experiment-only evaluator carrier**. It does not change `overlay/**`, V3 defaults,
canonical/package inputs, the evaluator, opponent bytes, provider state, or Kaggle state.

## Question

H13 measured a large positive change from `r04_sale_horizon=8` to `10`, including a clean
16/16 interaction screen after L3 was applied. H4 is independently positive and also changes
late strawberry reservation timing. Before H4 and horizon-10 are combined in a winning stack,
the pair needs an exact arm rather than an ad-hoc wrapper.

## Exact arm

The parent is the current H4 source head. `candidate.py` reuses that H4 module unchanged and
pins the live R04 tuple:

- `r04_sale_horizon`: **10** (control is 8)
- `r04_opening_roundtrip`: 0
- `r04_row_order`: true
- `r04_evening_flush`: true
- `r04_sale_fertilizer`: true
- `r04_cattle_early`: true
- `h4_strawberry_topup`: true

The focused test requires the control and candidate dictionaries to differ on exactly the
horizon key and verifies the resulting R04/H4 runtime globals. It snapshots and restores all
mutated globals so shared unittest discovery is not poisoned by importing the evaluator arm.

## Evidence boundary

This carrier proves source/config custody only. It makes **no economics or promotion claim**.
The next gate is paired official-interpreter execution of H4+h10 against the identical H4+h8
control, using the same exact candidate package lineage, seeds/seats, and opponent bytes.
Report paired competitive ΔM plus H4 activation/debt telemetry; a positive H13 result by itself
must not be counted as H4×h10 interaction evidence.

Focused local/CI command:

```bash
cd revenue/kaggriculture/cloud-execution-lab/candidates/v3/experiments/h4_horizon10
python -B -m unittest -v test_candidate.py
```
