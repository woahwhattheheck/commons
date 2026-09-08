# Full-support final-pivot arithmetic budget

## Change

`full_support.py::_solve_normalized` already checked `max_bits` before each
simplex pivot. A final pivot could increase a numerator or denominator beyond
the declared bit budget and also remove the last negative reduced cost. The next
loop iteration then exited through the optimality condition before checking the
oversized tableau. Consumers could therefore receive `status="optimal"` and a
selectable exact strategy even though the bounded arithmetic contract had been
exhausted.

The runtime now repeats the same existing `too_big` check immediately after a
completed pivot. A hit returns the established `bit_limit` result: unchanged
baseline weights, an independently verifiable upper-bound witness, `exact=false`,
and the actual completed pivot count. It does not return a partially optimized
action. The simplex, pivot ordering, table/cache identity, certificates, default
budgets, selector APIs and zero-baseline policy are otherwise unchanged.

This check necessarily observes the first over-budget arithmetic result; it does
not make Python's exact `Fraction` operation preemptible or provide a wall-clock
deadline. `max_bits` remains a bound on retained arithmetic state, as documented
by the existing solver.

## Executed evidence

The retained cloud packet tested the original main runtime Git blob
`7f7e2e9d62a655e24219490e9c54ab23019f1520` and the one-boundary repair.

- 21 focused methods pass on the repaired runtime; the original fails 8.
- 222 deterministic old/new finite-table comparisons were executed.
- 213 comparisons are byte-equivalent in their returned result.
- 9 deliberately low-budget cases change only at the exhausted final-pivot
  boundary: original `optimal` becomes repaired `bit_limit` with baseline
  selection and a valid bound certificate.
- 72 default-budget comparisons are identical.
- The existing T15/PRISM consumer classes preserve their complete supplied
  fallback and perform no draw for the repaired limit result.

The repository regression independently constructs a final-pivot discriminator
from a bounded deterministic corpus rather than trusting the production status.
It verifies that the tableau is within 16 bits before the last pivot, exceeds 16
bits after that pivot, and has no remaining entering variable. This makes the
old optimality-before-budget ordering fail directly without hard-coding a
solver-produced label.

These are component and consumer-contract tests, not engine games, policy gains,
probability calibration or leaderboard evidence. No selected policy, receipt
scenario, controller, seed panel or frozen result changes.

## Reproduce

From the repository root:

```sh
python -B -m unittest \
  revenue.kaggriculture.cloud-full-support.test_final_pivot_budget
```

The directory name contains a hyphen, so ordinary discovery is also supported:

```sh
python -B -m unittest discover \
  -s revenue/kaggriculture/cloud-full-support \
  -p 'test_final_pivot_budget.py' -v
```

For downstream behavior, pass the returned result through the existing checked
provider and persisted selector. Selection must continue to require a verified,
completed, strictly positive result. `bounds_closed` alone does not convert a
`bit_limit` or `pivot_limit` result into a completed provider run.

## Ownership and scope

POLY retains the full-support core. PRISM/LARCH/T15 and other consumers keep
their existing source and result ownership. This delivery is the smallest
compatible repair to the core's already-documented arithmetic-limit contract.
