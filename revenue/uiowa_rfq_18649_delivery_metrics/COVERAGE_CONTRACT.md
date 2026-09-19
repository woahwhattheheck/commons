# Recovery coverage and input-integrity contract

**Synthetic software verification only; not University findings.**

Owner: ZZ-COPPERFINCH-8D42 / GPT-6 Astra Pro. Operation `uiowa064-correctness-copperfinch8d42-20260919`; issue #16282. Extends the existing Semaphore calculator from #16142, without replacing its metric definitions or original fixture.

## Why this extension exists

The source-bound rehearsal executes the same cases against predecessor blob `13d7a895f5785e9cc7e3a35fc10a851a468547ab` and repaired blob `bca1a6b315cb23fcf0641c9c0aa524bfecc4c860`.

| Synthetic case | Executed predecessor | Executed repaired result |
|---|---|---|
| One recovered failure plus one unknown failure classification | Recovery COMPLETE, 3h | PARTIAL, observed-case 3h retained, eligibility_unknown=1 |
| Unknown failure classification alone | NOT_OBSERVED | PARTIAL, no invented duration |
| Direct call with commit after deployment | -1h lead time, COMPLETE | DataError |
| Duplicate direct-call deployment ID | Counted twice | DataError |
| Integer 1 instead of Boolean failure flag | Known nonfailure, rate=0 | DataError |
| Short CSV row | Uncaught AttributeError | DataError with line context |
| Duplicate header, anonymous extra cell, blank notes | Accepted | DataError |
| Recovery beyond an explicitly requested cutoff | No cutoff interface | Retained as after-cutoff evidence, not used in observed recovery statistics |

The retrospective calculation of a late recovery was not itself an arithmetic bug. The new cutoff is an additive evidence-selection interface, not a retroactive change to the default.

## Recovery eligibility is distinct from missing recovery time

For the selected service and start-inclusive/end-exclusive deployment window:

- `eligible` is the number of deployments explicitly classified as failures.
- `used` is the number of those known failures with usable recovery timestamps under the chosen follow-up mode.
- `missing` is the remaining known failures: missing timestamp or supplied recovery beyond the explicit cutoff. Thus `eligible = used + missing`.
- `eligibility_unknown` counts deployments whose failure classification is unknown. They are not guessed to be failures or nonfailures, and do not enter the known-failure denominator.

Recovery status is PARTIAL when either missing recovery evidence or unknown eligibility exists. It is NOT_OBSERVED only when there are no known failures and no unknown failure classifications. Otherwise it is COMPLETE. A recovery timestamp alone never establishes failure classification.

`evidence` retains exact deployment IDs in `observed_recovery_ids`, `missing_recovery_timestamp_ids`, `recovered_after_cutoff_ids`, and `unknown_failure_classification_ids`, plus a count of known nonfailures. These categories support follow-up rather than hiding exclusions inside an average.

## Separate deployment selection from recovery follow-up

`--recovery-observed-through` / `recovery_observed_through` is optional, timezone-aware and inclusive. It must be at or after the deployment-window end. A recovery exactly at the cutoff is usable; one after it is not. Missing and after-cutoff records remain distinct. Mean and median describe observed recovery cases only; unresolved cases can bias them, so PARTIAL statistics are not estimates of a fully observed cohort.

Without the option, all supplied recovery timestamps remain usable, preserving the original retrospective behavior. `scope.recovery_follow_up_mode` explicitly states either `ALL_SUPPLIED_RECORDS_RETROSPECTIVE` or `EXPLICIT_RECOVERY_CUTOFF`, and `scope.recovery_observed_through` records the cutoff or null.

**This is not a complete historical as-of query.** The input schema does not contain timestamps for failure/rework classification decisions or evidence ingestion. Both `classification_as_of_verified` and `source_export_completeness_verified` are false. A retrospective export can contain classifications learned later; the recovery cutoff cannot erase that limitation.

## Preserve partial-rate denominators and reveal logical bounds

The existing change-fail and rework `rate` and `percent` still divide positive classifications by known classifications, with `denominator_basis=KNOWN_CLASSIFICATION_ONLY` and the existing coverage fields.

The additive `full_cohort_rate_bounds` reports lower=positive/total and upper=(positive+unknown)/total over the supplied, selected cohort. For one known failure and one unknown classification, the known-only rate is 100%, while the all-row logical range is 50%-100%. With every classification unknown, the rate remains null and the logical range is 0%-100%.

These are missing-classification extremes, **not confidence intervals, predictions, imputations or peer benchmarks**. They are rounded to six decimal places. Different service/window selections get their own denominators.

## Input contract applies at both public entry points

CSV loading and direct Python calls share validation before service/window filtering. Datetime values are normalized to UTC. IDs, service and notes must be nonblank text; normalized duplicate IDs are rejected, including duplicates outside a later filter. Flags must be actual Boolean values or None, not integers, strings or containers. Impossible chronology is rejected.

CSV supports UTF-8 with or without BOM, quoted commas, Unicode and multiline notes. Missing required columns, blank or duplicate headers, short or long rows, invalid UTF-8 and malformed quoting produce DataError. Extra **named** columns remain accepted for compatibility, but are not calculated or exported by the Deployment dataclass; retain the original source when using extensions. Blank notes are now rejected consistently with the original dictionary's stated requirement.

The CLI returns exit 2 with ERROR text for data and filesystem failures. It will not overwrite its input CSV, including a symbolic or hard-link alias. This prevents accidental self-overwrite in the ordinary offline workflow; it is not a concurrent-filesystem security boundary. An empty selected cohort continues to raise an error rather than inventing zero deployment frequency without source-completeness evidence.

## Reproduce the evidence

From this directory:

```sh
python -m unittest discover -v
python -O -m unittest discover -v
python rehearse_coverage.py > /tmp/uiowa64-after.json
```

The retained run used Python 3.13.5: 50/50 tests passed normally (5.780s) and optimized (5.784s). Optimized tests propagate `-O` to CLI subprocesses. The original six tests and fixture bytes are unchanged; the 44 new tests include all 81 four-record tri-state classification combinations and order invariance.

For the source-bound negative control, extract the trusted predecessor from an existing repository checkout, not from an untrusted module:

```sh
git show 92fecdaf18b4c700f14e4859f502fb7f240433cd:revenue/uiowa_rfq_18649_delivery_metrics/calculator.py > /tmp/uiowa64-predecessor.py
python rehearse_coverage.py --calculator /tmp/uiowa64-predecessor.py > /tmp/uiowa64-before.json
UIOWA64_CALCULATOR_PATH=/tmp/uiowa64-predecessor.py python -m unittest test_coverage_contract -v
```

The negative-control run exits 1: 44 tests run, with 52 failing and 107 erroring assertions/subtests, including absent new interface fields. Those counts are **not 159 distinct defects**. The before/after JSON gives the concrete executed application outcomes. The rehearsal records observations and source hashes; independent unittest expectations decide correctness.

Read the complete normal/optimized transcripts without extra dependencies:

```sh
python -c "import bz2; print(bz2.open('evidence/test-logs.txt.bz2', 'rt').read())"
```

## Scope and provenance

The [official DORA guide](https://dora.dev/guides/dora-metrics/) (updated 2026-01-05, checked 2026-09-19) is the source for the five service-scoped software-delivery metric concepts. This contract's coverage accounting, observation cutoff, aggregation and logical bounds are explicit TJLabs implementation choices, not claims that DORA mandates these fields.

No University performance, institutional maturity, compliance, individual productivity, customer acceptance or full-system deployment has been established by these synthetic tests. Original authorship and source material are retained in the sibling dictionary, notes and fixture.
