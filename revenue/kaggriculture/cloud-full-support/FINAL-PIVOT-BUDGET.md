# Final-pivot arithmetic-budget enforcement

This repair changes only the existing exact simplex loop in
`cloud-full-support/full_support.py`. POLY remains the core owner; no alternate
solver, selector, objective, scenario model, controller or game runner is added.

## Defect

The loop previously found the next entering variable before checking the current
exact tableau against `max_bits`. That ordering is usually equivalent, but not
after the final pivot: if that pivot both closes the optimum and grows an exact
numerator or denominator beyond the declared budget, the next iteration sees no
entering variable and exits `optimal` without checking the oversized tableau.
Downstream consumers may then select a plan even though the provider exceeded a
public computation limit.

## Repair

Check the tableau's exact rational bit lengths before accepting the no-entering
optimal exit. A boundary result is now `status="bit_limit"`, retains the zero
baseline row, carries a valid lower/upper-bound certificate, and remains
ineligible for PRISM/LARCH selection. Pivot-limit ordering is unchanged: a solve
that actually reaches optimality using exactly the allowed number of pivots can
still report `optimal`.

The cache key and result remain unchanged. It still includes the complete ordered
rational table plus `max_pivots` and `max_bits`, and callers receive detached
results. No default budget, alpha, probability, plan identity, receipt or
certificate format changes.

## Executed evidence

Base runtime Git blob: `7f7e2e9d62a655e24219490e9c54ab23019f1520`.
The retained cloud packet for that exact source executed 21 regression methods
and 222 old/fixed comparisons: 213 outputs were byte-equivalent and nine changed
only at the corrected final-pivot budget boundary. All 72 default-budget cases
were unchanged. The repository-native test added here independently discovers
nine deterministic legal boundary tables, checks valid baseline certificates,
cache/budget identity and 72 default-budget tables.

These are finite-table implementation tests, not games, solver-strength results,
scenario probabilities or a policy promotion. No game seeds, Kaggle operation,
workflow dispatch, provider write or owner-PC compute are involved.

## Reproduce

From the repository root:

```sh
python -B -m unittest -v \
  revenue/kaggriculture/cloud-full-support/test_final_pivot_budget.py
python -B -m unittest discover \
  -s revenue/kaggriculture/cloud-full-support -p 'test_*.py'
```

For a consumer check, invoke `solve_full_table(table, max_bits=16)` on any boundary
table returned by the test helper. The result must be `bit_limit`, `exact=false`,
`support=[0]`, and pass `verify_certificate`. Re-running the same table with a
large sufficient budget completes the same ordered finite problem normally.

## Consumer boundary

PRISM and LARCH should continue using their existing rule: select only a valid,
completed, positive optimum. `bounds_closed` or a mathematically optimal tableau
at a computation-limit exit does not by itself convert the provider run into a
completed result. No consumer source change is required for this repair.
