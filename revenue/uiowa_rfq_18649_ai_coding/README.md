# UIOWA-076 — AI-assisted coding workflow evidence kit

**SYNTHETIC PREPARATION ONLY.** This is a working, offline rehearsal tool and a proposed interview method, not University findings, an employee assessment, proof of AI benefit, or a procurement recommendation. Author: ZZ-COPPERFIN-73 / GPT-6 Astra Pro. Operation: `uiowa-076-copperfin73-20260919`.

The question is not whether a model produces code quickly. It is whether a change is understood, verified, repaired, integrated and maintained successfully, with all relevant effort and uncertainty visible. This kit follows six fictional changes through those stages. It never calls a model, executes supplied code, reads a live system, or changes a workbench score.

## Run from a fresh source checkout

Python 3.10 or newer; standard library only. From this directory:

```sh
python -m unittest discover -s . -p 'test_ai_coding.py' -v
python -O -m unittest discover -s . -p 'test_ai_coding.py'
python rehearse.py --out /tmp/uiowa076-rehearsal
python ai_coding.py /tmp/uiowa076-rehearsal/synthetic/changes.json --out /tmp/uiowa076-second-report
```

Use another new or empty directory on Windows, such as `C:\Temp\uiowa076-rehearsal`. `rehearse.py` refuses a nonempty destination; it does not reset existing work. The analyzer validates the entire input and retained sources before writing reports. Exit 0 means the file contract and computations completed, **not** that the assessed workflow is good. Exit 2 explains malformed input or an I/O failure. An I/O failure during output writing may leave a partial report directory: require all three output files and a matching manifest before using it.

The rehearsal generates complete editable input JSON, a human-readable source history with 77 line-bound evidence entries, and `reports/report.json`, `reports/report.md`, `reports/changes.csv`, `reports/manifest.json`. The full histories are generated from the explicit case definitions in `rehearse.py`, not downloaded or fabricated by a live model. `SAMPLE_RESULTS.md` records the observed results and facilitator route. `RUBRIC.md` supplies the assessment and interview worksheet.

## Input contract, version 1.0

`ai_coding.py` is the authoritative executable contract. Unknown fields, duplicate keys and unresolved references are errors rather than silently discarded content. The generated `synthetic/changes.json` is a populated, editable example of every field.

| Object | Required fields / meaning |
|---|---|
| Dataset | `schema_version="1.0"`, `synthetic=true`, `as_of` with explicit UTC offset, `evidence`, nonempty `changes` |
| Evidence | Unique `id`; UTF-8 file `path` relative to input JSON; full-file `sha256`; one-based inclusive `start_line`, `end_line`; `kind` (`artifact`, `observation`, `interview`); offset-bearing `observed_at` no later than cutoff |
| Change | Unique `id`; `group` ESS/RIS/IAM; `mode` assisted/manual; `pair_id`; `context`; `started_at`; `accepted_at` or null; `acceptance_evidence_ids`; `effort`; `coverage`; `practices`; `followup` |
| Context | `task_fingerprint`, `stack`, `complexity`, `criticality`; exact values retained, not inferred from group names |
| Effort entry | Globally unique `id`; `stage`; nonnegative finite `minutes` or null; `evidence_ids`. Prefer decimal strings, up to six fractional places. Never allocate the same work twice. |
| Stage coverage | All six stages required, each with `state` complete/partial/unknown, explanatory `basis` and `evidence_ids` |
| Practice | All five criteria required, each with `state`, `rationale`, `evidence_ids`. See rubric for state semantics. |
| Follow-up | Positive integer `days`; `observed_through` or null; `coverage`; `reported_faults` nonnegative integer or null; `evidence_ids` |

The tool intentionally accepts only explicitly synthetic packets. A real engagement needs a separate agreed evidence-handling process and its real facts; relabeling actual private records as synthetic is not a supported route. Group names in examples do not imply any knowledge of actual University systems or behavior.

## Accounting and evidence semantics

The six effort stages are `understand`, `author`, `test`, `repair`, `integrate`, `maintain`. Authoring includes context/prompt preparation and first-draft inspection, not just model response latency. Generation latency alone must not be entered as the human authoring effort. Delivery effort sums the first five stages; lifecycle effort adds maintenance over the declared follow-up window. Units are **person-minutes**, including reviewer/support effort, not elapsed time. Elapsed start-to-acceptance is a separate field; parallel people can produce more person-minutes than elapsed minutes. Tooling setup, subscriptions, infrastructure charges, opportunity cost and cash benefits are outside this tool: carry them separately into the economics lane, never infer them from saved minutes.

`recorded_minutes` sums present amounts even when coverage is incomplete. `complete_minutes` is null unless the stage coverage is explicitly complete, the coverage statement and every allocated amount have retained direct support, and no amount is missing. A complete empty stage can be zero only with its supporting coverage statement. A missing entry is otherwise not evidence of zero work. Evidence type is a supplied classification: the program checks reference integrity and downgrades interview-only claims; an assessor still must read the excerpt and verify relevance, authenticity and whether the coverage claim is warranted. A checksum cannot do that.

Maintenance and fault comparisons require supported acceptance and a complete, directly supported window ending **exactly** at `accepted_at + days`. A shorter window is incomplete. A longer window must first be sliced to the declared duration; it cannot silently pass as an equal-duration comparison. Maintenance effort must be allocated to that same interval. No acceptance means no supported follow-up. Zero faults means zero recorded faults within a complete specified collection window, not proof that no defect exists. Fault severity, exposure, detectability and business impact still require qualitative interpretation; raw fault counts are not an overall quality score.

A contrast requires one assisted and one manual record, equal group and all context fields, equal observation days, supported acceptance, complete lifecycle effort and complete known fault counts. All deltas are **assisted minus manual**. Negative effort means fewer recorded person-minutes. Unmatched context, unknown outcomes or missing effort suppress all deltas and name the unresolved conditions. This conservative pair rule is a proposed method, not a validated causal estimator. Selection bias, learning effects, task equivalence, review depth, model/context versions and observation exposure must be addressed before attributing real changes to AI. The examples are paired fictional alternatives, not measured treatment arms.

## Output contract and integration

JSON retains decimal amounts as exact strings and missing totals as null, plus supplied/effective practice states, rationale, reasons, context, change and pair IDs, and the evidence registry with exact excerpts. It is the lossless analysis format. CSV is a **summary export**, not an input round-trip: null becomes the explicit string `UNKNOWN`; it contains stable IDs and summary numeric fields only. Do not join its identifiers to another component solely by spelling: namespace them with this component and schema version. Markdown provides human-readable results and in-document evidence anchors; retained file paths are relative to the input JSON directory, not the report directory. The appendix copies each exact source excerpt, so it is inspectable without a web connection.

The output manifest hashes the three report files. It establishes consistency, not signature, provider execution, source authenticity, final acceptance or payment. Identical source bytes and inputs produce identical report bytes; no current clock, random choices or network calls participate. Inputs and source files are never intentionally overwritten; output/input aliases are rejected. Keep a retained source bundle alongside reports for future re-analysis.

This component is additive and independent of occupied workbench/compiler, AI evaluation, economics and lifecycle components. Consumers can use `load_report(Path(...))`, `analyze(data, root)`, or the CLI without an application server. Suggested integration seam: retain namespace, source locator/hash, original value, coverage reason, observation window and synthetic label when mapping a change outcome into the common evidence register. Do not convert a `stated` practice or incomplete pair into an assessed maturity value.
