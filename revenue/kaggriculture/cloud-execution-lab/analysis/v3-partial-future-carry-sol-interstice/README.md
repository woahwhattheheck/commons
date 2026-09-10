# SOL-INTERSTICE — Titan V3 partial-future carry repair

## Decision

Do not promote frozen V2 or the strict forced-feasibility ablation from this lane alone. Run the closure-bound three-arm panel and require the causal, economic, outcome, stratum, and clustered-support admission gate.

## Source theorem

The frozen V2 scheduler can represent either:

1. carry all remaining stock beyond the short horizon, or
2. schedule all remaining stock into a future tranche (plus three full-liquidation split shapes).

It cannot represent “sell only enough later to make room, then carry the rest.” On public replay episode `107130860`, seed `539131249`, that missing middle is live:

- observation step `639`: `24 STRAWBERRY` in the shed;
- exact projected day-end total without sale: `113` units;
- pinned feasibility guard: `total - sold <= shedCapacity - 1`, so minimum sale is `14` units;
- frozen V2 plan: `[(639, 0), (645, 24)]`;
- successor plan: `[(639, 0), (645, 14)]`, retaining `10` units as continuation carry;
- emitted action at step `645`: `SELL STRAWBERRY 24` → `SELL STRAWBERRY 14`.

The repair also consumes scheduled tranches exactly once. Without that lifecycle rule, a partial tranche remains in `self.planned` and can be offered again on the next observation.

## Behavior boundary

The candidate changes `scheduler.py` only in a temporary copied closure. Frozen V2 is never modified. It:

- keeps forced-feasibility admission and priority;
- adds at most one minimum-feasible partial-future candidate per future date, only when the reference is infeasible and only at `minimum_now`;
- treats the full executable predicate as arbitrary and scans bounded integer quantities rather than assuming monotonicity;
- explicitly prefers less liquidation only when an infeasible-reference repair has the same modeled key;
- retires past/due scheduled rows before replanning;
- publishes selected sold/carry quantities in diagnostics.

## Evidence

`step-639-decision-capsule.json` is a compact source contract bound to:

- Slack file `F0C0KEQ5MFY` (`107130860.json.gz`);
- replay gzip SHA-256 `9337c7c734eff0804400f732d48c155dedb6d6f12b3afdefbc620f78fdfc686b`;
- frozen V2 scheduler blob `7c068b7078c3d7c09bb3836590ad42b0af934cdf`;
- parent exact-screen head `1d87e934f713b6bafd267be7bc1c8e2f95bd9207` and run `34410859768`.

Local replay probing is observation-tape analysis. It proves the policy seam and first changed action, not downstream counterfactual score after divergence.

## Economic-admission closure

Independent exact-packet review found four predecessor-killing false advances in the original classifier (counterexample receipt SHA-256 `9cfb87b9ad05f3e0a64da38f94f0644447116ddc63abb1bfe5d4240286d51a90`): sixteen control wins could become repair losses; repair could displace an action/trace/score-identical strict arm; one activated positive cell could launder fifteen inert cells; and positive own cash could hide a negative global or opponent-by-seat margin.

`economic_admission.py` now fails closed unless action identity implies trace and terminal-world identity and trace identity implies terminal-world identity. Admission requires a realized tested-action change, positive mean and nonnegative median own cash, no negative own-cash cell, nonnegative global and every opponent-by-seat own/margin mean, zero new losses and lost wins, and positive evidence in at least five paired opponent-seed blocks spanning both opponents and at least three seeds. The one-sided opponent-seed sign tail must be at most `0.05`. Repair can displace strict only when the same full gate passes for repair versus strict.

## Run

```bash
python -B -m unittest -v \
  test_materialize.py \
  test_mechanism.py \
  test_bind_execution.py \
  test_compare_three_arm.py \
  test_economic_admission.py
```

The 41 local contracts cover exact patch cardinality, the predecessor-killing decision capsule, one-shot scheduled tranches, three closure-verifying entrypoints, and fail-closed report classification. The workflow then materializes and binds three exact closures:

- `control`: frozen V2;
- `strict`: SOL-KEEL’s forced-feasibility rejection;
- `repair`: this minimum-capacity liquidation successor.

It runs the same opponents, seeds, seats, evaluator, timeouts, and parser for every arm. The classifier also requires exact engine, loader, opponent, wrapper, invocation, trace, bank, and both-actor execution custody. `economic_admission.py` exits zero only when repair passes every causal economic-admission check against control. The report separately identifies whether strict rejection remains preferred or repair has independently earned displacement authority.

## Non-claims

This lane does not establish Kaggle leaderboard gain, hosted scoring parity, or submission authority. It supplies a predecessor-killing mechanism contract and the exact experiment required to decide between V2, strict rejection, and the carry repair.
