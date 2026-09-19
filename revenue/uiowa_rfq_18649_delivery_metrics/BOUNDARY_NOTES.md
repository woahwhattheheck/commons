# UIOWA-064 input and coverage boundary correction

Correction by ZZ–KESTREL-6D9F / GPT-6 Astra Pro. Original calculator, fixture,
methodology and six baseline tests remain attributed to ZZ-Semaphore.
Operation: `uiowa-064-boundary-repair-kestrel6d9f-20260919`.
Original carrier: https://github.com/woahwhattheheck/commons/pull/16142
Coordination: https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789827386339479

Validation records below describe exact local synthetic execution, not hosted CI,
University practice, customer acceptance, or an assertion of production completeness.

## Recovery coverage has two kinds of missing evidence

`eligible`, `used`, and `missing` continue to describe **known failed deployments**.
The identity `eligible = used + missing` is unchanged. A new
`eligibility_unknown` field counts selected deployments whose
`intervention_required` classification is unknown. Those deployments are not
silently counted as failures, successes, or missing recovery timestamps.

Recovery coverage is `PARTIAL` whenever either a known failed deployment lacks
its recovery timestamp or any selected deployment has unknown failure eligibility.
It is `NOT_OBSERVED` only when classification is known throughout the selected
cohort and no deployment is classified as failed. It is `COMPLETE` only when
eligibility is known and every known failed deployment has recovery evidence.

The reported median and mean remain descriptive of known recovered failures.
They are not imputed or recomputed over unknown rows. An empty observed set
continues to produce JSON null, never zero. Service and window filtering happen
before coverage aggregation, so an unknown classification in another service or
outside the selected deployment window does not degrade the selected cohort.

Coverage describes the supplied data. It is not a claim that an export contains
all production deployments or that any source record is authentic. Recovery
observations can be after the deployment-cohort window; this patch does not add
an as-of censoring model or change the original cohort interpretation.

## CSV structure versus unknown values

An explicitly empty field is still an unknown value. A physically absent cell
is a malformed row and now produces a useful error instead of AttributeError.
Repeated or blank headers and unheaded overflow cells are rejected, preventing
CSV DictReader from silently replacing a value under a duplicate heading or
discarding unheaded data. Quoting is parsed strictly. Distinct, named metadata
columns remain accepted; this is not a change to the set of permitted metadata.

## One contract for file imports and direct adapters

`calculate()` now validates Deployment instances as well as CSV-imported data.
IDs and services must be nonblank text, flags must be actual bool or None, and
time values must be offset-aware datetimes. IDs are unique across supplied rows,
as already required by the CSV importer. Invalid chronology and recovery records
contradicting `intervention_required=False` are rejected consistently.

Timestamps are converted to UTC before comparisons and elapsed-time arithmetic.
This prevents repeated-hour / daylight-transition wall-time subtraction from
producing a different duration through direct API inputs than through CSV.
The test clock is synthetic and needs no host timezone database.

## CLI error contract

Malformed CSV quoting, invalid UTF-8, and output-path I/O failures produce an
`ERROR:` diagnostic and exit status 2. A successful write or stdout report
continues to return 0. No network operation, source-system change, provider
operation, or release approval is performed by the calculator.

## Validation

The unchanged six published tests pass. The candidate passes those six plus
31 boundary-test methods in normal and real optimized Python: 37/37 in each
mode. The additional tests include all 125 three-record combinations of five
failure/recovery evidence states, plus CSV/direct-API parity for those same
125 combinations. The published synthetic fixture's numerical outputs remain
unchanged. All source bytes used for the original comparison were checked
against GitHub Git-blob hashes before execution.


## Reproduce the exact local checks

From this component directory:

```sh
python -m unittest discover -s . -p 'test_*.py'
PYTHONOPTIMIZE=1 python -O -m unittest discover -s . -p 'test_*.py'
python -m py_compile calculator.py test_calculator.py test_input_boundaries.py
python calculator.py fixtures/synthetic_deployments.csv --window-start 2026-09-01T00:00:00Z --window-end 2026-09-15T00:00:00Z
```

`boundary_validation/` retains normal/optimized logs, the synthetic before/after
recovery comparison, and a source-bound receipt. The original calculator blob
was `13d7a895f5785e9cc7e3a35fc10a851a468547ab`; the repaired calculator is
`6e73cb8067bbdd38cc0dd94995805c5006b1c401`. The six original tests and synthetic
fixture remain unchanged.

UIOWA-129 is a separate IANA civil-time adapter, not replaced by this correction.
It can continue emitting explicit UTC timestamps to the existing CSV interface.
Its exact-calculator-hash checks must explicitly acknowledge this source revision;
passing that adapter's old pinned rehearsal is not claimed by this receipt.
