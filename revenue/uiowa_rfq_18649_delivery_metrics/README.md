# UIOWA-064 software-delivery metrics

**Offline synthetic assessment instrument. Not University findings.**

Original calculator, fixture and method: ZZ-Semaphore / GPT-5.6 Sol, canonical PR #16142.
Coverage and input-integrity extension: ZZ-COPPERFINCH-8D42 / GPT-6 Astra Pro, issue #16282.

The existing calculator remains the single implementation. It calculates service-scoped delivery metrics, retains unknown evidence and produces no peer percentile, individual score or institutional maturity verdict.

## Run

From this directory (stdlib only; verified with Python 3.13.5):

```sh
python calculator.py fixtures/synthetic_deployments.csv \
  --window-start 2026-09-01T00:00:00Z \
  --window-end 2026-09-15T00:00:00Z \
  --recovery-observed-through 2026-09-15T00:00:00Z
python -m unittest discover -v
python -O -m unittest discover -v
python rehearse_coverage.py
```

The unchanged eight-deployment fixture yields 4 deployments/week, 46h median interval, 11h median / 14.875h mean change lead time, 3h recovery, 25% change fail rate and 25% rework. These are fictional data, not University measurements.

## Read and integrate

- [Data dictionary](64-data-dictionary.md) and [interpretation notes](64-interpretation-notes.md): original source concepts, event definitions and fixture.
- [Coverage contract](COVERAGE_CONTRACT.md): current recovery eligibility, cutoff, input validation and rate-bound semantics. This supplements the original documents' simplified coverage description.
- [Before](evidence/before.json) and [after](evidence/after.json): executed, source-hash-bound observations.
- [Validation manifest](evidence/validation.json) and [full test transcripts](evidence/test-logs.txt.bz2): 50 tests under ordinary and optimized Python. The compressed UTF-8 transcript is readable with `bz2.open` from Python's standard library.

No external service or model call is made. Keep the original evidence export with any report: COMPLETE means the required fields of the supplied cohort are complete, not that every source-system event has been exported.
