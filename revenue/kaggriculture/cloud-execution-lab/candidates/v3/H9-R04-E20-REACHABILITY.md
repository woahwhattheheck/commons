# H9 — R04 E20 HIRE-guard reachability

Status: **experiment / evaluator arm only**. No default, package, or Kaggle submission change.

## Source-grounded gap

V3 already ships `overlay/e20_hire_guard.py`. E20 is deliberately narrow: when observed crop demand is below `e20_min_unwatered_crops` (default 3), it permits only the remaining daily HIRE allowance up to `e20_max_hires_per_day` (default 3). Excess HIRE rows are replaced with `[]` at the same literal queue indices. When crop demand is high enough, the action is untouched.

The canonical controller invokes E20 in `TitanAgent._v3_post`. R04 is a whole-route delegate and returns before `_v3_post`, so enabling the shipped package key does not affect live R04 play.

H9 does **not** change E20's classifier, thresholds, or queue semantics. `experiments/h9_r04_e20_hire_guard.py` reuses `apply_hire_guard` unchanged and wraps the *final* installed R04 callable.

## Why final-action placement

R04 constructs and then postprocesses its market queue before returning it to the engine. E20's semantic-safety contract is about literal final queue indices, so H9 judges that final action. If an excess HIRE at index `i` is suppressed, index `i` becomes `[]`; no later row shifts and no R04 SELL/BUY row is re-ordered.

Disabled H9 returns the exact parent output object.

## Independence from H5

H5 owns any new capital-ROI policy. H9 is only a reachability/evidence lane for a feature already present in V3. It does not generalize or tune hiring policy. If H5 changes HIRE selection, composition must be reviewed by H5 before any production wiring.

## Required evidence before production wiring

1. Focused H9 contract checks green.
2. Run exact H9 against exact V3.1 on the same 41-live-game pinned-opponent panel.
3. Report paired competitive margin `ΔM = Δown - Δrival`, `telemetry.changed`, `telemetry.dropped_hire_rows`, reason counts, and every negative cell.
4. Inspect every activation for whether the suppressed HIRE was actually redundant/low-demand in the recorded public state. A positive mean alone is insufficient if a small number of large wins hide harmful activations.
5. Reject or narrow the arm if it suppresses productive expansion/hiring in any recurrent loss archetype.
6. Only after positive evidence: production wiring must be reconciled with H5 ownership and deterministic V3 package manifests; this experiment intentionally stays outside `overlay/**`.

## Bench hook

```python
from h9_r04_e20_hire_guard import install as install_h9

candidate = install_h9(exact_v31_r04_callable, enabled=True)
```

The returned callable exposes `.telemetry` with calls, changed-action count, total dropped HIRE rows, and reason counts.
