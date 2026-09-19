# AI workflow lifecycle and observability — UIOWA-079

**Working offline preparation kit. Every example is synthetic; no AI model was called.**
This package follows a workflow change from retained input versions through
case-level observations, investigation evidence, corrective changes, and follow-up.
It is not a maturity score, University finding, live monitoring agent, or proof
that a hosted model can be replayed. It makes no product recommendation.

Operation: `uiowa-079-ibis79a6-20260919`. Author: ZZ-IBIS-79A6 / GPT-6 Astra Pro.
Work-order source: demo channel message `1789824783.436139`; first durable claim
`1789824864.374529`. Integration path is additive and self-contained.

## Run the complete rehearsal

Python 3.10+ and its standard library are sufficient. From the repository root:

```sh
python -m revenue.uiowa_rfq_18649_ai_lifecycle.example > /tmp/ai-lifecycle-record.json
python -m revenue.uiowa_rfq_18649_ai_lifecycle.lifecycle /tmp/ai-lifecycle-record.json --out /tmp/ai-lifecycle-review
python -m revenue.uiowa_rfq_18649_ai_lifecycle.lifecycle --schema > /tmp/ai-lifecycle-schema.json
python -m unittest revenue.uiowa_rfq_18649_ai_lifecycle.test_lifecycle -v
python -O -m unittest revenue.uiowa_rfq_18649_ai_lifecycle.test_lifecycle -v
```

The same three programs work as direct files, for example
`python revenue/uiowa_rfq_18649_ai_lifecycle/example.py`. On Windows, use a
writable working directory in place of `/tmp`. No credentials, model service,
network connection, configuration download, or shell execution of record values
is involved. Output files are replaced in the explicitly selected output directory;
use a fresh directory when retaining previous reviews.

Expected CLI receipt:

```text
OK 4 versions, 5 runs, 4 comparisons; data=synthetic; replay=not_executed
```

`review.json` is a structured **assessment projection**, not a replacement for
the original input record. Retain the input JSON containing the source and output
content alongside it. `review.md` presents the version timeline and bounded
comparisons. `timeline.csv` provides the chronological version/incident display.
Formula-like CSV values receive a leading apostrophe; JSON retains exact text.
CSV and Markdown are reader views, not lossless interchange formats.

## Worked story and the decisions it supports

The fictional release-summary workflow encounters three kinds of change:

| Change | Computed synthetic result | Appropriate interpretation |
|---|---|---|
| v1 to v2: shorten the prompt | Pass rate 75% to 50%; mean repair 30 to 75 seconds; mean latency 950 to 700 ms, four measured cases each | Faster generation coincides with worse recorded quality and more repair. Inspect `run-2/c` and its source rather than celebrate latency alone. |
| v2 to v3: model, prompt and source all change | Pass rate 50% to 100%; repair 75 to 0 seconds; latency 700 to 900 ms | A matched fixed-task follow-up improves, but the three simultaneous changes prevent attribution to the prompt or model alone. No statistical claim is made. |
| v3 to an incomplete rereview | Quality has three measured cases and one unknown; latency remains fully measured | The quality delta is unknown because measured case coverage differs. Latency can still be compared separately. |
| v3 to v4: new runtime cohort and missing context | Different dataset, case population and observation kind; model revision, retained source and owner unknown | No before/after delta. Collect the missing context and design a matched evaluation rather than interpret cohort change as model regression. |

The closed fictional incident retains `run-2/c` → `investigation-1` → `v3` →
`corrective-followup`. It is labeled **reported_resolved**, not independently
proven effective in production. A second incident remains open with missing output,
source snapshot and support ownership. These are distinct evidence gaps, not an
invented assessment of an actual University team.

The case outcomes, timings, and narrative outputs in `example.py` are authored
rehearsal records. The executable calculates their aggregate values; it does not
score the output text automatically and it did not measure model performance.

## Contract and interpretation

`contract.py` is the single source for JSON Schema 2020-12. `--schema` exports it.
The runtime implements exactly the schema vocabulary this contract uses, plus
reference, content-integrity and chronological checks. It is not a general-purpose
JSON Schema implementation. Null means unknown; an empty collection contains no
observations. Required structural fields must be present even when nullable.

| Collection | Meaning and stable link |
|---|---|
| `artifacts` | Source/prompt/configuration/dataset/rubric/protocol/output/investigation versions; UTF-8 text, digest, locator and capture time. Locators are descriptive and never fetched. |
| `versions` | Workflow lineage, model family and pinned revision when known, prompt/config/source IDs, effective time, lifecycle state, accountable support role and change rationale. |
| `runs` | Evaluation or runtime observation, exact version, cohort, dataset/rubric/protocol and evaluator revision; case-level pass/unknown, active repair seconds, latency milliseconds and output ID. |
| `comparisons` | Explicit baseline/candidate run IDs; there is no automatic selection of a favorable run. |
| `incidents` | Affected run/case, symptom, owner, opening/resolution, retained investigation artifacts, corrective version and explicit follow-up comparison. |

A verified SHA-256 proves only that retained text matches the supplied digest.
A digest without text is **declared**, not byte-verified; missing digests remain
unknown. Retained input material does not establish provider availability, model
weights, deterministic behavior, evaluation validity, or successful rerun. The
report always says `replay_state: not_executed`.

Comparable deltas require matching observation kind, cohort, evaluator revision,
dataset/rubric/protocol content digests and case population. Each metric additionally
requires the same nonempty set of measured case IDs. Equal declared digests permit
a descriptive comparison but retain `context_basis: declared_or_unknown_digests`;
missing or conflicting digests do not. Byte-identical dataset aliases are allowed.
Model, prompt and source changes remain visible as possible explanatory factors.
This is not a randomized experiment, significance test or causal estimator.

The record contract deliberately treats a support change as metadata, never an
access-control action. It does not change deployment, rollback, credentials,
permissions, retention policies or the behavior of the agent fleet.

## Investigation worksheet

Use [WORKSHEET.md](WORKSHEET.md) with a delivery practitioner and the workflow's
support role. Record evidence locators and unresolved answers, not just yes/no
self-report. Complete the record with real engagement evidence only when that
evidence is available through the agreed engagement handling route; never copy
confidential material into this public preparation repository.

## Integration seam for the delivery kit

Import `analyze(record)` from this package's `lifecycle` module; it returns a
plain dict or raises `InvalidRecord`. `export(report, Path(...))` produces the
three reader/machine projections. `load(Path(...))` rejects duplicate JSON keys
and non-finite constants. Package-relative imports avoid collisions with other
assessment tools named `contract`, `example` or `lifecycle`.

Keep the original IDs and the `data_status` marker when embedding this result in
UIOWA-098/100. `workflow_id` is not a group or maturity cell: map it to an existing
assessment area/group only with supplied evidence. Map findings to relevant
version/run/incident IDs and preserve missing-value reasons and denominators.
Do not turn `retained_inputs`, `comparable`, or `reported_resolved` into an
institutional pass. The kit has no dependency on unfinished sibling components.

## Remaining actual engagement inputs

Real workflow inventory and support roles; model/revision/configuration availability;
retained prompts and relevant source versions; authorized source/output locators;
evaluation tasks, rubrics and reviewer protocol; timestamped case measurements;
change records and investigation/follow-up evidence. Actual adoption, benefits,
University maturity, causality and successful model replay remain unestablished.
