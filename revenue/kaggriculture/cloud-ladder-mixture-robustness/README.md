# TITAN V3 ladder-mixture robustness gate

Claim: `TITAN-V3-LADDER-MIXTURE-ROBUST-PROMOTION-20260910-01`

This package closes a release-selection failure that a pooled local benchmark cannot detect: a candidate can look better on the observed local opponent mix and still become worse when the hosted ladder assigns more games to a weak family. The gate emits the exact adverse opponent weights that defeat the candidate rather than treating all opponent × seat rows as exchangeable evidence.

It is additive analysis only. It does not mutate TITAN policy source, configuration, archives, pointers, providers, Kaggle submissions, or promotion state.

## Boundary with historical calibration

This gate is downstream of benchmark-family calibration.

- A calibration owner decides whether a local opponent family has demonstrated usable local-to-hosted sign behavior. Every family supplied here must carry `CALIBRATION_PASS` and an exact receipt hash.
- This package then asks a different question: assuming those families are eligible, does the release pair remain favorable over a declared uncertainty set for the *hosted opponent mixture*?

An uncalibrated family yields `BLOCK_UNCALIBRATED`; it is never silently dropped or assigned zero weight.

## Evidence contract

The input schema is `titan-v3-ladder-mixture-input/v1`. It requires:

1. distinct incumbent and candidate release IDs, source commits, and archive SHA-256 identities;
2. engine, evaluator, loader, panel, upstream causality, calibration-registry, per-family calibration, and hosted-snapshot receipt hashes;
3. one complete paired terminal row for every declared opponent family × environment seed × candidate seat;
4. exactly seats `0` and `1`, with 719 returned actions in both arms;
5. incumbent/candidate own and rival terminal cash, plus action- and trace-change flags;
6. hosted family counts, lower/upper possible weights, and a predeclared total-variation radius;
7. minimum independent seed-cluster count and explicit per-seed own-cash/margin floors.

Unknown fields, duplicate JSON keys, duplicate cells, missing seats, nonfinite numbers, Boolean-as-number inputs, family aliases, incomplete lifecycles, and infeasible weight declarations fail as malformed evidence. The tool normalizes exact numeric values to rational numbers before hashing, so equivalent input ordering and decimal/fraction spelling produce a stable receipt.

## Why seed clustering comes before mixture weighting

Both candidate seats for one environment seed share the same environment draw. Treating those mirrored rows as independent can inflate support. The gate first averages the two seats inside each opponent-family × seed cluster. For each family it records:

- the seed-cluster mean own-cash and margin deltas;
- the minimum per-seed deltas;
- outcome transitions derived from terminal banks;
- the full-family mean; and
- the minimum leave-one-seed-out mean.

The leave-one-seed-out floor, not the pooled cell mean, is the family effect used by the mixture optimizer. Any worsened `W → T/L` or `T → L` cell is a hard hold. Score movement without both action and trace movement is an evidence block, and the whole panel must reference an upstream `CAUSAL_PASS` receipt.

## Exact uncertainty set

For opponent families `i`, the hosted snapshot produces nominal weights `w0_i` from integer game counts. The caller declares lower and upper bounds `l_i`, `u_i`, and total-variation radius `epsilon`.

The admissible hosted mixtures are

```text
W = { w : sum_i w_i = 1,
          l_i <= w_i <= u_i,
          1/2 * sum_i |w_i - w0_i| <= epsilon }.
```

For own cash and margin separately, the gate solves

```text
min_{w in W} sum_i w_i * d_i
```

where `d_i` is the family leave-one-seed-out floor. The implementation uses exact `fractions.Fraction` arithmetic. Starting from the feasible nominal mix, a linear minimum is obtained by moving probability mass from the highest-effect available donor to the lowest-effect available receiver, respecting box capacities and the TV budget. A deterministic exhaustive-grid contract checks the greedy solver against all feasible grid points across multiple objective orderings.

Separate adverse witnesses are retained for own cash and margin. Requiring both minima to pass is conservative: the same ladder mixture need not minimize both metrics.

## Verdicts

- `ROBUST_ADVANCE`: every family is calibrated; evidence and seed coverage close; no outcome/tail regression exists; and worst-case own cash and margin are positive (or nonnegative only when explicitly configured).
- `ROBUST_HOLD`: structurally valid evidence fails an outcome, tail, or worst-mixture economic gate.
- `BLOCK_UNCALIBRATED`: at least one weighted family lacks `CALIBRATION_PASS`.
- `BLOCK_EVIDENCE`: upstream causality is not `CAUSAL_PASS`, or a terminal delta lacks action/trace movement.
- `MORE_EVIDENCE_REQUIRED`: a family lacks the predeclared independent seed count.
- `INACTIVE`: no tested action changed and no terminal value changed.
- `MALFORMED_EVIDENCE`: invalid schema or structural closure; CLI exit status `2`.

Every other valid verdict exits `0`. A hold is evidence, not an infrastructure failure.

## Reproduced mixture-shift predecessor

The workflow-generated fixture has a positive nominal own-cash effect of `+14.8`, dominated by a family weighted at 80%. A legal TV-radius `0.3` shift moves mass to the weak family:

```text
nominal:  arlene=.80, apex=.15, v1=.05
adverse:  arlene=.50, apex=.15, v1=.35
own cash: +14.8 -> -0.2
verdict:  ROBUST_HOLD
```

The exact predecessor is generated and asserted by `test_positive_nominal_mean_can_fail_under_legal_mixture_shift` and by the exact-head workflow.

## Source layout

The implementation is split into reviewable stdlib-only modules: strict primitives in `mixture_common.py`, evidence closure in `mixture_parse.py`, the exact TV optimizer in `mixture_optimize.py`, verdict construction in `mixture_evaluate.py`, and the fail-closed CLI in `mixture_gate.py`. The 32 contracts are grouped in three `test_contracts_*.py` files with fixtures in `test_support.py`.

## Run

```bash
cd revenue/kaggriculture/cloud-ladder-mixture-robustness
python -B -m unittest -v test_contracts_a.py test_contracts_b.py test_contracts_c.py
python -B mixture_gate.py \
  --input /path/to/panel-and-hosted-mixture.json \
  --output /tmp/titan-mixture-receipt.json
```

The current suite contains 32 adversarial contracts, including exact optimizer/exhaustive equivalence, Simpson-style mix reversal, fragile leave-one-seed-out support, mirrored-seat clustering, hidden outcome regression, source/causality blocking, duplicate/missing/malformed evidence, exact rational arithmetic, deterministic order-independent receipts, and CLI semantics.

## Integration intake for T08

This package should run only after a candidate panel has:

1. exact dependency-closed candidate/incumbent/opponent source receipts;
2. action-bound causal closure for every score-active cell;
3. historical benchmark-family calibration receipts; and
4. a hosted opponent-exposure snapshot whose family mapping and uncertainty bounds were declared before reading the candidate result.

T08 remains the one-tree integration and release authority. `ROBUST_ADVANCE` is a downstream evidence receipt, not autonomous promotion authority.
