# UIOWA-062 — delivery-flow assessment

A complete offline instrument for reviewing supplied delivery records across build,
verification, packaging, promotion and deployment. It produces a five-stage matrix,
time-coverage measures and source-linked follow-up questions. It does not contact a
pipeline, deploy software, approve a release, rank teams or establish University
practice. The included ESS, RIS and IAM services are entirely fictional.

## Run the worked example

Python 3.10 or newer; standard library only. From the repository root:

```sh
python revenue/uiowa_rfq_18649_delivery_flow/delivery_flow.py --input revenue/uiowa_rfq_18649_delivery_flow/synthetic.json
python revenue/uiowa_rfq_18649_delivery_flow/delivery_flow.py --input revenue/uiowa_rfq_18649_delivery_flow/synthetic.json --format json --output delivery-review-01.json
python -m unittest -v test_uiowa_delivery_flow
python -O -m unittest -v test_uiowa_delivery_flow
```

The first command prints Markdown. The second creates a **new** JSON report. Choose
another output name for each revision; existing files, input aliases, symlinks and
hardlinks are not overwritten. Exit 0 means a report was generated, not that a
process is effective or approved. Exit 2 indicates invalid input or an I/O failure.
A failed write may leave a partial **new** output: creation is not atomic delivery.
Retain only successful output, check the exit status and compare `source_sha256`
with the exact input. Parsing and input hashing use the same captured bytes.

`synthetic-report.md` is the actual readable CLI output. `FACILITATOR.md` is the
standalone interview, worked-rehearsal and action-disposition instrument.
`EXECUTION.json` identifies the exercised source, fixture, tests, commands and
outputs. It is a local cloud execution record, not a GitHub Actions receipt.

## Edit the packet without changing the source

`synthetic.json` is ordinary UTF-8 JSON. Copy and pretty-print it for review:

```sh
python -m json.tool revenue/uiowa_rfq_18649_delivery_flow/synthetic.json editable-delivery.json
python revenue/uiowa_rfq_18649_delivery_flow/delivery_flow.py --input editable-delivery.json --format json --output edited-review-01.json
```

Run these commands only with new destination names. `json.tool` is an independent
Python utility and does not provide this instrument's create-only output contract.
Formatting changes the input digest but not the calculations. Preserve the original
source export and locators; the report is not a general lossless editor for all
extra packet fields. Attempt and evidence objects are retained, but unrecognized
packet/trace fields are not an interchange guarantee.

### Packet and trace contract

| Object | Required fields and interpretation |
|---|---|
| Packet | `schema_version: "uiowa-delivery-flow/v1"`; explicit Boolean `synthetic`; timezone-bearing `observed_at`; 1–200 `traces` |
| Trace | Unique `id`; `group` ESS/RIS/IAM; `service`; `requested_at`; `evidence` list; `attempts` list; `reproducibility` object |
| Evidence | Trace-local unique `id`; nonempty `locator`; `recorded_at` no later than observation. Optional metadata is retained, not authenticated. |
| Attempt identity | Trace-local unique `id`; one of the five `stage` names; nonempty `step`; integer `attempt` from 1–1000. `(stage, step, attempt)` must be unique. |
| Attempt context | `mode` manual/automated; `owner_role` nonempty string or null; `evidence_refs` list, possibly empty. References must resolve within the same trace. |
| Attempt times | `queued_at`, `started_at`, `finished_at`, each a timestamp or null. Known values must be ordered and within request through observation. |
| Attempt state | `progress_state` queued/running/finished/unknown; `result` success/failure/cancelled/unknown. Finished state, a finish timestamp and a nonunknown result must agree. |
| Reproducibility | `status` observed_match/observed_mismatch/documented_only/unknown; `evidence_refs`. Nonunknown states require references. This is a **supplied observation label**, not a digest comparison performed by this tool. |

Timestamps include seconds and `Z` or a numeric offset, for example
`2026-09-01T09:00:00Z` or `2026-09-01T05:00:00-04:00`. Calendar-invalid values,
missing timezones, malformed offsets and timestamps after observation are refused.
One microsecond through six fractional-second digits is supported. Input is bounded
at 4 MiB, 200 traces and 1,000 attempts per trace. Duplicate JSON keys, non-finite
numbers and ambiguous identity whitespace are refused, not silently normalized.

### Unknown is different from zero

| Known record | Queue measure | Execution measure |
|---|---|---|
| Queue, start and finish present; finished result supplied | Queue → start, complete | Start → finish, complete |
| Queue and start present; explicitly running at observation | Queue → start, complete | Start → observation, censored lower bound |
| Queue present; explicitly queued at observation | Queue → observation, censored lower bound | Unknown |
| Queue present; current progress unknown and no start | Unknown, **not** the entire apparent waiting window | Unknown |
| Finished result and timestamp supplied, start missing | Unknown if queue exists but no start | Unknown, **not** queue → finish |

An empty attempts list leaves all five stages UNKNOWN. A missing stage might be
combined with another step, external/shared, intentionally absent or simply not
exported. None is inferred. An ordinal 2 without ordinal 1 produces a history
question, not an invented failed first run. Absence of references remains visible
and creates a source request; it does not delete a supplied record.

## Read the quantities correctly

All duration values are seconds. `attempt_count` is the denominator for the queue
and execution measure-count dictionaries. A missing dictionary category has zero
records, not evidence about missing attempts outside the export. Each stage exposes
its own record count and result distribution. No success-rate or maturity score is
computed from a convenience sample.

`execution_attempt_seconds_sum` sums known per-attempt durations and can exceed
elapsed delivery time during parallel execution. It is not labor effort, utilization
or person-hours. Queue/execution unions measure elapsed covered intervals, not the
sum of records. Their overlap is retained: **queue union + execution union − overlap
= observed activity union**. Censored intervals only describe the observed window.

`failed_execution_seconds_lower_bound` and `repeat_execution_seconds_lower_bound`
can count the same attempt; never add them as waste or savings. Missing durations
contribute no known seconds, so a zero lower bound with unknown measurements is
not a measured absence of work. The measure counts and attempt rows must accompany
aggregate totals.

`unattributed_window_seconds` is observation-window time outside known queue or
execution intervals. It includes periods after a recorded deployment, work outside
the export and genuine unknowns. It is **not demonstrated idle time**. The first
recorded successful deployment latency describes the supplied finish timestamp;
an unreferenced success does not establish release approval or service recovery.

## Three contrasting results

| Fictional trace | Attempts | Execution sum / union | Queue union | Shared queue/execution time | Activity union | First recorded deployment |
|---|---:|---:|---:|---:|---:|---|
| ESS | 7 | 31 / 23 minutes | 16 minutes | 1 minute | 38 minutes | 38 minutes after request |
| RIS | 4 | 55 / 55 minutes | 43 minutes | 40 minutes | 58 minutes | Unknown |
| IAM | 2 | 1 / 1 minute known | 1 minute known | 0 minutes known | 2 minutes known | 14 minutes after request, unreferenced |

ESS has one failed unit-test attempt and one repeated attempt. A parallel
integration check overlaps both, so shortening the unit path might not shorten the
critical path. The 10-minute manual promotion queue is observed, but its cause and
purpose are not known. RIS has a 44-minute running lower bound and a 40-minute
queued lower bound; its promotion wait remains unknown. IAM has a recorded build
success without a start, missing earlier history and three missing stage records.
These examples must not be used as a ranking of the real groups.

## Source and contribution record

Original operation, design and historical 43-test report: **ZZ-COPPERLEAF-63**,
[issue #16100](https://github.com/woahwhattheheck/commons/issues/16100) and
[original work thread](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789824599096919).
The interval-union, explicit progress-state and censored-time design is retained.
The published implementation, 38-method recovery suite, editable example and
operator instrument here are **ZZ–HALYARD-86-D62 / GPT-6 Astra Pro**. The original
43-method suite was not supplied to this recovery and is not represented as rerun.

This package evaluates supplied metadata consistency and derives questions. Source
references are locators, not proof that a real export was independently read. A
reproducibility label, named owner or successful finish is never a substitute for
the underlying evidence. Real assessment requires a facilitator to read sources,
resolve contradictory accounts and record the disposition using `FACILITATOR.md`.
