# Threat model

## Threats handled

- **Survivorship averages:** failed and timed-out rows cannot disappear before
  aggregation; any non-complete or missing cell invalidates the panel.
- **Grid substitution:** seeds, opponents, and both seats are predeclared and
  compared as an exact Cartesian product.
- **Duplicate weighting:** duplicate cell keys are rejected instead of counted
  twice.
- **Provenance substitution:** engine, runner, control archive, and candidate
  archive identities must match the frozen contract.
- **NaN/Infinity and malformed numeric evidence:** non-finite JSON constants,
  booleans-as-numbers, and score vectors other than length two are rejected.
- **Mean-only selection:** result flips, pair balance, opponent strata, seat
  strata, median, and worst-cell behavior are explicit checks.
- **Policy drift:** every policy field is mandatory and embedded in the report.
- **Parser ambiguity:** duplicate JSON object keys and unknown schema keys are
  rejected.
- **Input replacement:** symlink inputs are rejected; exact input hashes are
  written to deterministic output.
- **Torn reports:** reports are written and fsynced to a temporary file, then
  atomically replaced.

## Threats not handled

- A malicious evaluator that fabricates internally self-consistent rows.
- Incorrect engine/source hashes supplied identically to contract and evidence.
  Independent artifact construction and receipt review remain necessary.
- Hidden-state leakage or an invalid opponent implementation.
- Multiple-hypothesis bias, confidence intervals, or generalization beyond the
  declared seeds. Use a separately frozen development selector and disjoint
  holdout contract; generic statistical tooling may consume this gate's aligned
  cells afterward.
- Policy semantics that do not produce the intended action/state change. Each
  candidate still needs an official-engine transition oracle and action trace.
- Automatic production promotion. This tool never modifies a runtime, archive,
  release pointer, or provider state.

The gate proves that a declared paired panel is complete and that its observed
metrics satisfy a frozen decision contract. It does not prove why a candidate
won, that it will generalize, or that it is safe to deploy without review.
