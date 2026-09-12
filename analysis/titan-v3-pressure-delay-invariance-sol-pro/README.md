# TITAN V3 pressure-delay invariance carrier

Claim: `TITAN-V3-PRESSURE-DELAY-INVARIANCE-CERTIFICATE-20260910-01`

This is an additive semantic successor to the strict-pressure experiment at
`dfef8e57289b59c68bd45eb8f3fdd8ec610e0892`. It changes no canonical runtime,
configuration, archive, package pointer, provider state, Kaggle state, or
submission. It runs no score panel and makes no promotion claim.

## Why this carrier exists

The reviewed parent proposal stably places positive same-sized proxy scores
before proxy-zero SELL lots. The proxy-zero class is not a safety certificate on
the official rounded market curves.

Pinned predecessor:

- engine blob: `3c202c7ee921da239356789e266b694635103fc4`
- public inventory: `TOMATO=9999`, `MILK=9999`
- parent: `SELL TOMATO 1`, then `SELL MILK 1`
- rival: `SELL TOMATO 2`, then blank
- proxy scores: TOMATO `0`, MILK `+9`
- parent cash: own `229`, rival `117`
- unsafe proxy partition: own `226`, rival `120`
- effect: own `-3`, margin `-6`

PR #12047 independently binds that witness to the official `_process_market`
surface and provides the exhaustive evidence oracle. This carrier consumes that
oracle as specification and adds the missing pressure-aware production primitive.
It does not copy or replace the audit packet.

## Contract

A pressure-positive lot can cross an earlier non-positive lot only when the
earlier lot's own receipt is invariant for every feasible integer stock delay
through the public rival bound. The implementation:

1. computes the lot's stock in the parent order, excluding hidden rival supply;
2. adds any deterministic same-product quantity that a promoted lot to its right
   could place ahead of it;
3. validates every canonical quote in the complete resulting window as a strict
   integer, at least one dollar, and nonincreasing;
4. compares the lot receipt at delay zero with the receipt at the maximum delay;
5. treats endpoint equality as a certificate only after step 3.

For a validated nonincreasing quote curve, the sale receipt `R(d)` is itself
nonincreasing in delay. Consequently
`R(0) >= R(d) >= R(max_delay)` for every integer `d` in the window, so endpoint
equality proves exact equality at every intermediate delay. The committed tests
also compare this optimized predicate against an exhaustive all-delay oracle on
2,160 small monotone curves.

Every failed or unavailable premise is fail-closed. A malformed SELL row,
missing/nonfinite pressure, bool-as-number, missing/invalid inventory, invalid
bound, callback exception, noninteger quote, quote below the engine floor, or
nonmonotone quote window is an ordering barrier. Positive and demotable classes
are stable, and a barrier prevents every later positive lot from crossing it.
Rows are not mutated and their original objects are retained.

## Exact files

- production primitive:
  `revenue/kaggriculture/cloud-opponent-league/lark-responsive/pressure_delay_invariance.py`
- official-engine and adversarial contracts:
  `revenue/kaggriculture/cloud-opponent-league/lark-responsive/test_pressure_delay_invariance.py`
- immutable source receipt: `SOURCE.json`
- exact-head workflow: `.github/workflows/titan-pressure-delay-invariance-sol-pro.yml`

The workflow requires the exact parent as an ancestor, pins the mechanics blob,
rejects every out-of-scope changed path, parses both Python files without writing
bytecode, runs all contracts with pipe failure enabled, emits a deterministic
receipt under `$RUNNER_TEMP`, hashes all retained evidence, and proves the
checkout remains clean.

## Intended adapter seam

The existing factor already computes `pressure_by_product` and receives the
public inventory plus a canonical `price_by_stock(product, stock)` callback. A
current-source materializer can call:

```python
result = certified_pressure_partition(
    actions,
    pressure_by_product=pressure,
    inventory=state["market"]["inventory"],
    max_rival_units=config["shedCapacity"],
    price_by_stock=price_by_stock,
)
actions = list(result.actions)
```

Integration must bind the exact runtime state/configuration shape rather than
copy this illustrative lookup literally. The public bound must be an externally
validated engine value; the candidate must not choose its own smaller bound.

## Deliberate limit

The theorem is only about the demoted lot's **own receipt** under the declared
stock-delay envelope. It does not prove that the pressure score is a good signal,
that the promoted lot improves, that rival receipts cannot improve, or that the
head-to-head margin is nonnegative. Those are separate official-engine panel and
admission questions. Any integration that names this full bilateral strict
dominance would overclaim the carrier.

The next legitimate score step is therefore a current-source, action-bound
control-versus-certified-pressure panel using the same opponent/seed/seat cells
as the parent factor, followed by opponent-by-seat own/margin and lost-win gates.
