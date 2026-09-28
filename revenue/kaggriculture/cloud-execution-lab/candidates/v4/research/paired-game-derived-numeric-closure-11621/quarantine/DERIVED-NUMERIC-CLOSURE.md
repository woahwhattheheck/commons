# Derived numeric closure

Operation: `titan-v3-paired-game-derived-numeric-closure-20260909-sol-cipher-02`

Base: PR #11597 head `3816ed79509f3fe529834008acfb765fc1ec8f43`.

## Boundary

PR #11597 already owns immutable input snapshots, strict schema typing, and
integer-to-float overflow. This successor does not rewrite those controls. It
closes the remaining arithmetic seam after individually finite terminal scores
have been accepted.

## Predecessor failures

The predecessor can still exit 1 without a report when:

1. two finite terminal scores subtract to an infinite game margin;
2. finite baseline and candidate scores subtract to an infinite own/rival delta;
3. finite game margins subtract to an infinite margin delta;
4. finite per-cell deltas overflow `statistics.fmean` in a two-seat pair,
   opponent/seat stratum, or aggregate;
5. finite values overflow the even-cardinality median calculation.

The first four paths have direct CLI regressions. Summary helpers also enforce
finite medians so no derived non-finite value can reach policy comparison or
JSON serialization.

## Repair

- finite-check baseline and candidate margins before result classification;
- finite-check own, rival, and margin deltas at their cell boundary;
- compute W/T/L from the checked margins rather than recomputing unchecked
  subtraction;
- normalize mean and median overflow/non-finite results to `GateError`;
- label pair, opponent, seat, and aggregate failures with their exact stratum.

No clipping, saturation, alternate arithmetic, score semantic change, policy
relaxation, controller/runtime/archive/default mutation, game execution, or
provider spend is introduced. Extreme evidence is rejected as `INVALID`.

## Verification contract

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  python3 -m unittest -v \
  test_validation.py test_policy_cli.py test_derived_numeric_closure.py

Expected: 31 tests, OK

python3 -m compileall -q .
Expected: PASS
```

Each new test invokes the real CLI and requires exit 2 plus a persisted,
machine-readable `INVALID` report.
