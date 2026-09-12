# TITAN V5 P04 — pre-registered route selector bridge

This is the **pre-declared consumer** of the merged #13478 route-matrix reducer. It is not a second route harness and it does not activate gameplay. The rule/fitting procedure was fixed before this lane consumed any R00–R12 terminal outcomes.

## Frozen authority

- production-v3 archive: `20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239`
- active R04 source: `41ea55c5f20c43cd58c5099fbadb212de62ec95a95dfc2e6e1e19c3d4d55b39a`
- #13478 reducer schema: `titan-v5-p04-route-ranker/v1`
- pre-registration spec SHA256: `c0d57d3b20aba4ce8ecca7cc07ac3cf56bd7f7aeb9260efe1f6519d62aa8719e`
- selection boundary: step 144; existing forced terminal plan2 at step 648 remains unchanged.

`p04_preregistered_selector.py --print-preregistration` emits the exact frozen fitting contract. Import fails if the spec object drifts from the hash above.

## Rule class

Fallback is always the exact source-recomputed incumbent `SHOP_PLANS` decision. The fitter may nominate only one of two low-complexity forms:

1. always use one natural step-144 plan; or
2. if **one** already-merged #13478 public feature equals **one** training-observed value, use one natural plan, otherwise keep the incumbent.

Natural plans are `0,1,3..12`. Diagnostic plan2 is excluded. Allowed features are exactly #13478's `shop_pair`, `first_two_yarn_count`, three public market comparison features, and rival **visible-tile** crop/livestock leaders. Seed, opponent, seat, snapshot hash, private inventory/shed state, future town state, and RNG/future fields cannot be selector predicates.

## Discovery gate

A non-identity rule is eligible for nomination only when every engaged discovery cell has:

- no evaluator failure;
- `delta_margin_vs_incumbent >= 0`; and
- `delta_own_vs_incumbent >= 0`.

It must also have strictly positive total margin delta and engage at least two groups, two distinct seeds when two are available, two distinct opponents when two are available, and both seats when both are available. Selection is deterministic and worst-cell-first: maximize minimum margin delta, then minimum own delta, then mean margin, mean own, engagement count, simplicity, lexical predicate, and lowest plan id.

This is deliberately stricter than picking the best mean route from the discovery matrix. The matrix may nominate a frozen rule; it cannot make that rule `policy_ready`.

## Held-out / convergence contract

Any nomination remains `policy_ready=false`, `composer_ready=false`, and default-OFF. A separate native owner must run **fresh held-out** cells using the exact nominated rule bytes/spec hash. The rule, feature set, thresholds, tie-breaking, and fallback may not be changed after discovery results are observed; changing them creates a new experiment, not a reinterpretation of this one.

Only a held-out winner may be converted into a #13482 component against the single production-v3/V5 line. No CURRENT/default/release/Kaggle mutation is authorized here.

## Source gate

From this directory:

```bash
python -B -m py_compile p04_preregistered_selector.py test_p04_preregistered_selector.py
python -B -m unittest -v test_p04_preregistered_selector.py
python -O -B -m unittest -v test_p04_preregistered_selector.py
python -B p04_preregistered_selector.py --print-preregistration
```

Author-side reconstructed gate before publication: 13/13 normal, 13/13 optimized, plus `py_compile` clean. The test harness uses only the documented #13478 public API surface; exact-head review should rerun against the real merged reducer before merge.
