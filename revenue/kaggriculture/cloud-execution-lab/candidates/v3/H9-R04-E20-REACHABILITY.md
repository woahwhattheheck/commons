# H9 — R04 E20 HIRE-guard reachability

Status: **experiment / evaluator arm only**. No default, package, or Kaggle submission change.

## Source-grounded gap

V3 already ships `overlay/e20_hire_guard.py`. E20 is deliberately narrow: when observed crop demand is below `e20_min_unwatered_crops` (default 3), it permits only the remaining daily HIRE allowance up to `e20_max_hires_per_day` (default 3). Excess HIRE rows are replaced with `[]` at the same literal queue indices. When crop demand is high enough, the action is untouched.

The canonical controller invokes E20 in `TitanAgent._v3_post`. R04 is a whole-route delegate and returns before `_v3_post`, so enabling the shipped package key does not affect live R04 play.

H9 does **not** change E20's classifier, thresholds, or queue semantics. `experiments/h9_r04_e20_hire_guard.py` reuses `apply_hire_guard` unchanged and wraps the *final* installed R04 callable.

## Why final-action placement is testable but not automatically production-safe

R04 constructs and then postprocesses its market queue before returning it to the engine. E20's local row-safety contract is about literal final queue indices, so H9 judges that final action. If an excess HIRE at index `i` is suppressed, index `i` becomes `[]`; no later row shifts and no R04 SELL/BUY row is re-ordered.

Independent exact-head review identified the important composition predecessor: stateful R04 layers can commit a coherent investment *before* H9 sees the final action. In particular, V219 can request land + tomato seed + HIRE rows on day 18 while recording pending/committed intent. H9 may then blank one or more coupled HIRE rows while the BUY_LAND/BUY_SEED rows remain executable. V219 detects missing workers on the next callback rather than inventing actor indices, so this is not a state-corruption finding; it is a **stranded-capital / broken-investment-coherence** risk.

Therefore `telemetry.changed` and `telemetry.dropped_hire_rows` are proposal/edit counts only. They must not be reported as realized worker reductions or as safe activations.

Disabled H9 returns the exact parent output object.

## Activation evidence added after review

Every changed H9 action now appends a record to `telemetry.activation_trace` containing:

- player, step, and day,
- all original HIRE row indices,
- the HIRE indices E20 blanked,
- any same-action `BUY_LAND`, `BUY_SEED`, `BUY_PRODUCT`, or `BUY_ANIMAL` rows,
- own observed hand count before the edited action,
- available published R04 V219/V233 hire-shortfall counters before the edit, and
- on the next later callback: observed hand count/delta plus V219/V233 hire-shortfall deltas.

`coupled_investment_activations`, `settled_activations`, `unresolved_on_reset`, and aggregate V219/V233 shortfall deltas are also exposed. If an alternate harness callable does not share R04 module globals, those report snapshots fail soft to zero; the per-action coupled-purchase trace still remains available.

The next-observation hand delta is **not** a counterfactual baseline. The paired evaluator must compare the exact H9 cell to exact V3.1 because a parent HIRE can independently no-op for cash/other engine reasons.

## Independence from H5

H5 owns any new capital-ROI policy. H9 is only a reachability/evidence lane for a feature already present in V3. It does not generalize or tune hiring policy. If H5 changes HIRE selection, composition must be reviewed by H5 before any production wiring.

## Required evidence before production wiring

1. Focused H9 contract checks green, including the V219 day-18 coupled-capital predecessor and next-observation settlement trace.
2. Run exact H9 against exact V3.1 on the same 41-live-game pinned-opponent panel.
3. Report paired competitive margin `ΔM = Δown - Δrival`, `changed`, `dropped_hire_rows`, `coupled_investment_activations`, reason counts, and every negative cell.
4. Publish every activation trace: step/day, original/dropped HIRE indices, coupled investment rows, next-observation hand delta, and V219/V233 hire-shortfall deltas when available.
5. **Any coupled-purchase activation that strands capital is a production HOLD even if aggregate mean ΔM is positive.** Positive mean alone is insufficient.
6. Distinguish proposal edits from realized hand-count differences by comparing the paired H9 and exact-V3.1 trajectories/callbacks. Do not infer a worker reduction solely from `changed`.
7. Reject or narrow the arm if it suppresses productive expansion/hiring in any recurrent loss archetype.
8. Only after positive, activation-safe evidence: production wiring must be reconciled with H5 ownership and deterministic V3 package manifests; this experiment intentionally stays outside `overlay/**`.

## Bench hook

```python
from h9_r04_e20_hire_guard import install as install_h9

candidate = install_h9(exact_v31_r04_callable, enabled=True)
```

The returned callable exposes `.telemetry` with edit counts, coupled-investment activation traces, next-callback hand evidence, and available R04 hire-shortfall deltas.
