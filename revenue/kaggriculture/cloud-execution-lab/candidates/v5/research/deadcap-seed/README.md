# V5 DEADCAP — current-native dead-seed convergence

Status: **candidate/proof surface only; default OFF; current-route engagement must be measured before any production hook.**

This is the V5 continuation of the merged ASTRA-DEADCAP research package (`candidates/v4/research/terminal-dead-capex`, #12932/#12958). It does not remint the historical theorem and does not generalize it to hires, land, animals, or products.

## Narrow invariant

The pinned engine (`reference/engine/kaggriculture.py`, Git blob `3c202c7ee921da239356789e266b694635103fc4`) executes unit actions before market orders. A `BUY_SEED` on callback `t` therefore cannot fund a `PLANT` on callback `t`.

`deadcap_seed.py` may replace one executable `BUY_SEED <crop> <n>` row with `[]` only when all of the following are explicit:

1. the candidate is exactly enabled;
2. the supplied route family is declared complete for this decision;
3. no dynamic unit rewriter can synthesize a future `PLANT`; and
4. **every supplied authored route has zero `PLANT <crop>` actions after the current callback.**

The route set is intentionally an over-approximation: treating every canonical route as still reachable can miss opportunities, but cannot certify a dead seed merely because one current branch lacks a consumer.

The replacement is `[]`, not deletion. This preserves market row index and engine prefix-cap topology. BUY_SEED also does not alter public market inventory, so the certified mutation removes only our private cash-to-seed transfer. Malformed route evidence, malformed actions, bad market limits, type-aliased activation, or active dynamic unit rewriters all fail to identity.

## Current route census

`scan_current_routes.py` loads the exact canonical `reference/next-panel/vendor/arlene.py::routes()` bytes from the checkout, hashes them, and scans only engine-executable BUY_SEED rows in the effective market prefix. A reported row is a static authored opportunity only; it is **not** proof that the current runtime returns that row after FrozenSelected/seed-budget/funding transforms.

Run from this directory:

```sh
python -B scan_current_routes.py
```

If the census is nonzero, the next gate is a matched current-runtime engagement trace: control versus this transform on identical observation callbacks, with the canonical V5 candidate identity (`v5c:`) and policy-engagement fingerprint attached. If the current runtime never returns a certified row, release this lane as COLD and do not add a runtime feature.

## Focused contracts

```sh
python -B -m unittest -v test_deadcap_seed.py
python -O -B -m unittest -v test_deadcap_seed.py
```

The tests pin engine quantity coercion (`int()`), list-only BUY_SEED grammar, the engine market-cap floor `max(1, int(...))`, same-callback unit-before-market ordering, all-route conservatism, exact slot preservation, caller isolation, and fail-closed activation.
