# UIOWA-064 input and coverage semantics

The calculator and CSV example originate with Semaphore; the shared input/UTC and recovery-eligibility behavior comes from KESTREL-6D9F. See [the input dictionary](64-data-dictionary.md) and [metric interpretation](64-interpretation-notes.md) for the working interface.

## Recovery coverage

`eligible`, `used`, and `missing` describe known failed deployments, with `eligible = used + missing`. `eligibility_unknown` separately counts selected deployments without a failure classification; these are not silently counted as failures or successes. Unknown eligibility or an unobserved recovery makes coverage `PARTIAL`. `NOT_OBSERVED` requires known classifications and no observed failures. An empty duration set produces JSON null, not zero.

Service/window selection precedes coverage aggregation. A recovery cutoff affects observation of selected failures, not deployment selection. Without a cutoff, all supplied recoveries are used retrospectively. Coverage never establishes source-export completeness, record authenticity, or historical classification availability.

## File imports and direct adapters

Explicit empty optional fields remain unknown; physically absent cells, repeated or blank headers, unheaded overflow cells, and malformed quoting are errors. Distinct named metadata columns remain accepted. CSV and direct `Deployment` inputs require unique nonblank IDs, nonblank services, actual Boolean values or None, and offset-aware timestamps. Impossible chronology and recovery records contradicting an explicitly non-failed deployment are errors.

UTC normalization precedes comparisons and elapsed-time arithmetic, including direct API calls. A civil-time adapter may supply explicit UTC timestamps through this same interface; no hash-pinned rehearsal is needed to use it.

## Errors

Successful stdout or file reports return exit 0. Input and output failures produce an `ERROR:` diagnostic and exit 2. The calculator performs no provider operation or source-system change. Follow [the operator guide](OPERATOR_OUTPUT_REHEARSAL.md) for report publication.
