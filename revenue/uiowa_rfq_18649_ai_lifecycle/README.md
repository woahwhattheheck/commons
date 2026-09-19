# UIOWA-079 — AI workflow lifecycle and observability

An offline, vendor-neutral assessment instrument for answering **what changed, which retained evidence supports the observed behavior, and what remains unavailable for reproduction**. This is preparation tooling, not a University assessment result, model benchmark, deployment, or certification.

Operation: `uiowa-079-quartz71-20260919`. Builder: ZZ-QUARTZ-71 / GPT-6 Astra Pro. Work order: UIOWA-079 in the existing Michael live-demo workstream. The component is isolated from the workbench/compiler and does not change their scoring, interfaces, or authority semantics.

## Run a complete example

From a checkout of this directory, using Python 3.10 or later:

```sh
python make_fixture.py
python -W error -m unittest -v test_lifecycle.py
python -O -m unittest -q test_lifecycle.py
python lifecycle.py synthetic-lifecycle.json --out sample-output
```

The executable and tests use only the Python standard library. The tested development runtime is Python 3.13.5; other supported-by-syntax versions have not been exercised here. The fixture generator writes `synthetic-lifecycle.json` beside itself. The inspector writes three files to the selected output directory:

|File|Use|
|---|---|
|`lifecycle-report.json`|Lossless interchange: evidence identity, integrity states, releases, case/run traces, runtime observations, comparisons and timeline.|
|`lifecycle-report.md`|Readable release/comparison/case/investigation report; a checked-in example is `SAMPLE_REPORT.md`.|
|`case-trace.csv`|Display-oriented case trace for a spreadsheet or report appendix. Formula-like supplied text is prefixed with an apostrophe; use JSON, not CSV, for exact identifier interchange.|

Expected CLI receipt:

```text
releases=4 transitions=3 evidence=SYNTHETIC_RETAINED_OUTPUT_RESCORING rerun=NOT_PERFORMED
```

**What actually runs:** strict record validation, UTF-8 SHA-256 checks, deterministic exact-JSON rescoring of authored output fixtures, cohort comparison, and report export. No model, prompt, environment manifest, evidence text, or source locator is executed. No network call or provider credential is used. Generating the fixture does not generate AI answers.

## Worked behavior, not a productivity claim

The fictional workflow extracts owner/deadline fields from fictional release handoffs. `make_fixture.py` contains the complete source material, expected answers, authored observations, manifests and investigation notes.

|Release|Change|Rescored result|Interpretation|
|---|---|---|---|
|v1|Initial synthetic baseline|2 of 3 cases pass|An unsupported deadline was filled in.|
|v2|Only the prompt changes|1 of 3 cases passes|The new prompt encourages filling missing information; the retained outputs contain an additional invented owner.|
|v3|Only the named synthetic model revision changes|3 of 3 cases pass|The retained outputs now preserve unknown values. This is a matched-cohort association, not an executed model comparison or causal finding.|
|v4|Sources and cohort change; model revision and support role are missing|3 of 3 scored cases pass, but only 3 of 4 declared cases are scored|Case D's output was not retained. Changed evaluation conditions suppress a numeric improvement delta.|

The v1→v2 paired pass-rate difference is −1/3 (−33.3 **percentage points**), and v2→v3 is +2/3 (+66.7 percentage points). The report formats rate differences as percentages; they are absolute rate differences, not relative percentage improvements. These three-case fixtures do not estimate general performance or statistical significance.

The v2 runtime example contains one supplied success, one error and one unknown outcome. Latency is deliberately unrecorded. None of these records represents a live University incident or measured production performance.

## Record and integration contract

`schema.json` is the structural JSON Schema. `lifecycle.validate()` additionally checks unique IDs, reference resolution, timezone-aware chronology, parent continuity, dataset membership and evaluation uniqueness. Schema conformance alone does not establish these relational properties. `lifecycle.inspect()` then verifies retained bytes and computes evidence states. Do not replace this with schema-only validation.

|Record|Fields that preserve meaning|
|---|---|
|Artifact|Stable ID, exact UTF-8 content or explicit null, expected SHA-256, source locator. Hashes prove byte consistency only, not authenticity.|
|Case|Input artifact, expected-answer artifact and source-artifact references.|
|Release|Workflow/group, timestamp and parent, model name/revision, prompt/configuration/code/environment artifacts, input sources, declared cohort, evaluator, owner/support roles, change reason and investigation references.|
|Run|Release/case/input/output binding, evaluation versus runtime, timestamp, success/error/unknown, optional latency and incident reference.|
|Event|Release, time, event kind, evidence references and investigation/change narrative.|

Group tags are `ESS`, `RIS`, or `IAM`; output area is `ai-readiness`, matching the existing assessment vocabulary. The supplied worked workflow is fictional ESS only. Other groups can use the same schema with their own separately identified workflows; this does not populate the twelve-cell matrix or infer unassessed group findings.

For downstream evidence/report integration, carry `bundle_sha256`, release `manifest_sha256`, `workflow_id`, `group`, `assessment_area`, release ID, case ID, run ID and the artifact locators. Preserve `synthetic` and `evidence_kind`. These are assessment observations to link into an existing evidence register; they are **not** workshare compiler packets, maturity ratings, authoritative findings, approval receipts or ready-to-submit records. `INTERVIEW.md` gives collection questions and improvement options.

## Comparison and missing-evidence semantics

Pass rate is `passed_cases / scored_cases`; coverage is `scored_cases / declared_cases`. Empty denominators produce null, not zero. Report the numerator, denominator and coverage together.

A missing run/output, unsuccessful or unknown run outcome, incorrect input binding, undeclared source, unavailable/mismatched artifact, malformed JSON or unsupported evaluator leaves the case **UNSCORED** with a reason. It is not silently counted as pass or as a measured model failure. Integrity states are `VERIFIED`, `MISMATCH`, and `UNAVAILABLE`. All declared shared input components/sources must be verifiable before rescoring; an unavailable shared source can therefore make the release unscorable.

Comparisons name changed components. A changed source set, dataset or evaluator yields `NOT_COMPARABLE` and no numeric delta. Unchanged conditions with incomplete matched observations yield `PARTIAL_COHORT`; its delta describes the named paired cases only. No paired observations yield `NO_PAIRED_EVIDENCE`. A full matched cohort yields `COMPARABLE`, not a causal verdict.

A model revision string does not prove the provider can rerun it. Retention of a model artifact is reported separately, and every release remains `rerun_status=NOT_PERFORMED`. Missing revision, owner/support role or retained input appears as a lineage gap. An actual model rerun requires a separate explicitly implemented execution record and evaluation design; this instrument does not perform one.

Version 1 supports one evaluation observation per release/case. Replicate batches must be represented as separately identified cohorts/releases rather than silently selecting the best output. A future replicate-aware adapter must preserve every run, seed/configuration, cohort membership and aggregation rule; it must not reuse this single-observation field to hide variation.

## Handling and limitations

The checked-in materials are synthetic. Keep real University/customer data, credentials and private artifacts out of this public repository. A real engagement's evidence collection and storage arrangements remain inputs to establish outside this preparation kit. `synthetic=false` labels supplied observations as source-authenticity-unverified; it does not grant them authority.

The inspector is a small offline tool for evidence-sized collections. It loads the bundle in memory and has no large-stream throughput claim. It provides no AI usefulness rubric beyond the stated exact-JSON fixture evaluator, no commercial cost model, no employee score, and no automatic recommendation ranking. Markdown/CSV are reading surfaces; JSON retains exact values and evidence distinctions. This kit does not contact anyone, schedule meetings, change fleet operation, deploy a service, submit a proposal or authorize spending.
