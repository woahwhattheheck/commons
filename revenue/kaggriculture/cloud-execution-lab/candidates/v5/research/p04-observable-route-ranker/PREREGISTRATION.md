# TITAN V5 P04 — pre-registered route selector bridge

This is the **pre-declared consumer** of the merged #13478 route-matrix reducer. It is not a second route harness and it does not activate gameplay. The rule/fitting procedure was fixed before this lane consumed any R00–R12 terminal outcomes.

## Frozen authority

- production-v3 archive: `20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239`
- active R04 source: `41ea55c5f20c43cd58c5099fbadb212de62ec95a95dfc2e6e1e19c3d4d55b39a`
- #13478 reducer schema: `titan-v5-p04-route-ranker/v1`
- pre-registration rule-spec SHA256: `c0d57d3b20aba4ce8ecca7cc07ac3cf56bd7f7aeb9260efe1f6519d62aa8719e`
- pre-outcome discovery-universe SHA256: `3c393d57c4caae9c5ee3b4e6c1110220efbb556b48230ca209061b57a4119a66`
- discovery-universe source: #titan-kaggriculture `C0C0Z8AHGP2` message TS `1789253666.394169`, published before any R00–R12 terminal outcomes
- selection boundary: step 144; existing forced terminal plan2 at step 648 remains unchanged.

`p04_preregistered_selector.py --print-preregistration` emits both the exact frozen fitting contract and the pre-outcome experiment-universe commitment. Import fails if either commitment object drifts from its recorded hash.

## Pre-outcome universe binding

Independent review found that the first draft could accept a cherry-picked subset because its coverage floor was derived from whatever groups a caller supplied. The repair does **not** change the rule grammar, scoring thresholds, tie-breaking, or promotion boundary. Instead it binds discovery input to the route board that already existed before outcomes:

- seeds `1209131101` and `1209131102`;
- opponents `apex_v7` and `arlene_v14`;
- seats `0` and `1`;
- exact Cartesian product = eight `(seed, opponent, seat)` groups.

`validate_discovery_report()` now requires exact set equality with those eight keys after duplicate rejection. Missing groups, extra groups, substituted seeds/opponents/seats, or a two-positive-cell cherry-pick fail closed before any rule is enumerated or scored. This closes the subset-selection attack while preserving the original preregistered rule-spec SHA.

## Rule class

Fallback is always the exact source-recomputed incumbent `SHOP_PLANS` decision. The fitter may nominate only one of two low-complexity forms:

1. always use one natural step-144 plan; or
2. if **one** already-merged #13478 public feature equals **one** training-observed value, use one natural plan, otherwise keep the incumbent.

Natural plans are `0,1,3..12`. Diagnostic plan2 is excluded. Allowed features are exactly #13478's `shop_pair`, `first_two_yarn_count`, three public market comparison features, and rival **visible-tile** crop/livestock leaders. Seed, opponent, seat, snapshot hash, private inventory/shed state, future town state, and RNG/future fields cannot be selector predicates.

## Discovery gate

A non-identity rule is eligible for nomination only when every engaged discovery comparison has:

- **both** the selected candidate row and its incumbent-control row free of evaluator failures;
- `delta_margin_vs_incumbent >= 0`; and
- `delta_own_vs_incumbent >= 0`.

Failure accounting is explicit: the receipt separately records candidate-failure groups and incumbent-control-failure groups, while `failure_groups` counts any invalid comparison. This prevents a clean candidate from being certified against a failed incumbent control.

The rule must also have strictly positive total margin delta and engage at least two groups, two distinct seeds, two distinct opponents, and both seats. Selection is deterministic and worst-cell-first: maximize minimum margin delta, then minimum own delta, then mean margin, mean own, engagement count, simplicity, lexical predicate, and lowest plan id.

This is deliberately stricter than picking the best mean route from the discovery matrix. The matrix may nominate a frozen rule; it cannot make that rule `policy_ready`.

## Held-out / convergence contract

Any nomination remains `policy_ready=false`, `composer_ready=false`, and default-OFF. A separate native owner must run **fresh held-out** cells using the exact nominated rule bytes/spec hash/universe hash. The rule, feature set, thresholds, tie-breaking, and fallback may not be changed after discovery results are observed; changing them creates a new experiment, not a reinterpretation of this one.

Only a held-out winner may be converted into a staging component against the single production-v3/V5 line. No CURRENT/default/release/Kaggle mutation is authorized here.

## Source gate

From this directory:

```bash
python -B -m py_compile p04_preregistered_selector.py test_p04_preregistered_selector.py
python -B -m unittest -v test_p04_preregistered_selector.py
python -O -B -m unittest -v test_p04_preregistered_selector.py
python -B p04_preregistered_selector.py --print-preregistration
```

Author-side reconstructed exact-API gate after both review hardenings: 16/16 normal, 16/16 optimized, plus `py_compile` clean. Hostiles include the two-positive-group subset attack, an unexpected extra-group substitution, and a clean positive candidate compared against a failed incumbent control. Independent exact-head repo execution remains the final source gate before merge.
