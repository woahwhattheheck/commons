# UIOWA-073 — Knowledge and data readiness lab

A runnable, offline preparation kit for **AI knowledge and data readiness**.
It analyzes supplied source records, executes a lexical retrieval baseline, and
shows what those records can support. It does not run a language model or assign
an institutional maturity score.

All checked-in examples are fictional. ESS, RIS and IAM are assessment group
labels, not claims about University systems, staff, policies or performance.
This kit does not collect University data, change access, contact anyone, submit
an RFQ response, or create an engagement commitment.

## Start here

Python 3.10+ syntax; standard library only. No installation, service, credentials,
network, paid compute or model API is needed. Run from this directory:

```sh
python demo.py /tmp/uiowa-073-demo
python readiness.py /tmp/uiowa-073-demo/before/collection.json --out /tmp/uiowa-073-review
python -m unittest -v test_readiness.py
python -O -m unittest -v test_readiness.py
python -m py_compile readiness.py demo.py test_readiness.py
```

Use a new output directory for each retained run. These commands create or replace
their own named output files in the selected directory; they do not delete source
records. A malformed packet returns exit code 2 before reports are written. A
successful analysis returns 0 **even when it finds gaps**: completion is not a
readiness approval. Output-write failures also return 2 and may leave partial
outputs, so keep the prior successful run separately.

`demo.py` generates two versioned collections, individual Markdown source
documents, exact SHA-256 digests, reports and a computed comparison. It is the
canonical source of the fictional collection, not a generator of random data.
The checked-in `sample-results.md` records an actual run.

| File | Use |
| --- | --- |
| `readiness.py` | Validate, retrieve, analyze source support, render JSON/Markdown/CSV |
| `demo.py` | Generate before/after fictional documents, manifests and reports |
| `test_readiness.py` | Regression and command-line tests |
| `worksheet.md` | Seven-dimension interview and evidence instrument, worked preparation plan |
| `sample-results.md` | Measured rehearsal results and execution receipt |

## What to inspect in the demonstration

The before collection has eight documents and five questions. The after collection
has nine documents and the same questions, with explicit fictional repairs:

| Case | Before | Explicit preparation change |
| --- | --- | --- |
| ESS retry instructions | Active records say three and five attempts; one is stale | A fictional steward marks the old record superseded; recency alone never resolves the conflict |
| RIS budget handoff | Useful text exists but ownership, source location, readership context and review date are unknown | Supply those metadata records without changing the assertion text |
| RIS import terminology | The question uses different vocabulary and retrieves no documents | Add a documented vocabulary bridge and a new source revision |
| IAM recovery verification | Contact guidance exists; business verification is absent | Add a written fictional verification procedure, not a claim that an exercise happened |
| Unjudged relevance | A question has no relevance judgments | Keep retrieval precision and recall unknown in both collections |

The glossary documents and archived recovery material exercise distractors and
inactive evidence. The two collections are designed examples, not a representative
sample or a controlled comparison of AI systems. Relevance labels change when the
active source collection changes; do not interpret the comparison as a fixed-corpus
model benchmark. The tests isolate individual changes in addition to the combined
rehearsal.

## Input contract, version 1.0

The executable contract is `validate()` in `readiness.py`. UTF-8 JSON has unique
object keys, finite values, and an object at its root. Duplicate JSON keys and
non-finite constants are errors. Unknown extra fields are retained as input context
but do not change the calculation; `change_log` in the demo is such a field.

Root fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | Exactly `"1.0"` |
| `snapshot_id` | Nonempty stable identifier for this supplied collection |
| `synthetic` | Explicit Boolean; copied into reports, never inferred from content |
| `as_of` | Canonical `YYYY-MM-DD` analysis date |
| `documents` | Array of document records; IDs unique in the snapshot |
| `queries` | Array of assessment questions; IDs unique in the snapshot |

Every document has nonempty `id`, `title`, `revision`, `content` and `sha256`.
`sha256` must equal the SHA-256 of the exact UTF-8 `content` string. `group` is
`ESS`, `RIS` or `IAM`; `status` is `active`, `superseded` or `archived`.

The keys `owner`, `source_locator`, `access_semantics`, `reviewed_on`,
`captured_on` and `review_interval_days` must exist. Unknown values are JSON
`null`, not guessed values or empty strings. Dates, when known, use canonical
`YYYY-MM-DD`; the interval is a positive integer, not a Boolean. Owner and
location/readership descriptions, when known, are nonempty strings.

Each document has an `assertions` array. An assertion contains nonempty `scope`,
`key`, `value` and `quote`, plus integer `start_line` and `end_line`. Line numbers
are inclusive and one-based. The quote must exactly equal the indicated source
lines joined by a newline. This validates the **binding to source text**, not the
analyst's interpretation of that text. An empty assertion array is permitted and
reported as lacking structured assertions.

Questions have nonempty `id` and `question`, one `group`, positive integer `top_k`,
a nonempty, duplicate-free `required_facts` array of `{scope, key}`, and
`relevant_document_ids` as either a duplicate-free array or `null`. Relevance IDs
must name existing, active documents in the same analysis group. Missing or null
relevance judgments remain unknown. An empty array is an explicit judgment that
there are no relevant documents; it is not interchangeable with unknown.

The implementation partitions analysis by group to avoid comparing unrelated
facts. This is **not an authorization boundary**. `access_semantics` records the
source's existing readership/context as supplied. It is not parsed into access
rules, verified against a provider, used to filter retrieval, or changed by the
program. Use only evidence already appropriate for the actual analyst and
engagement, and keep private evidence outside this public repository.

## Calculation and interpretation

### Source condition

An active record with known owner, source locator, access context, capture date,
review date, review interval and structured assertions can contribute current
source support. A review age equal to the declared interval is within interval;
an older age is stale. A future review/capture date or a review later than its
capture is surfaced as an inconsistent record. Unknown dates or interval remain
unknown. The example's 30-day interval is a fictional analyst assumption, not a
University rule or universal freshness standard.

A hash proves consistency between supplied bytes and supplied digest, not who
wrote them, whether a source URL exists, whether a document is authoritative, or
whether its statements are true. A current review date is not proof of correctness.

### Contradictions and coverage

Assertions are grouped by `(group, scope, key)` using an unambiguous tuple
representation. Different exact values in active records produce a conflict.
The engine does not perform natural-language contradiction detection, normalize
units, infer supersession, choose the newest source, vote, or suppress a stale
conflicting record. Analysts must resolve aliases and meaning explicitly.

A conflict anywhere in the active supplied group is shown for a required fact,
even when the conflicting source is outside the retrieved top-k. This prevents
a favorable retrieval slice from hiding a known contradiction. Superseded and
archived sources remain in the supplied manifest but do not count as active
support or generate maintenance demands to refresh retired records.

For each required fact the report distinguishes:

- `conflicting`: active sources disagree on an explicitly declared value;
- `missing`: no active supplied assertion covers the fact;
- `retrieval_gap`: an active assertion exists but was not retrieved;
- `support_needs_preparation`: retrieved evidence exists but lacks current,
  complete source-condition records;
- `supported_by_current_record`: at least one retrieved record passes those
  record checks and no active conflict is known.

The coverage fraction is current-supported required facts divided by all declared
required facts for that question. It is task-specific source coverage, not a
maturity score, probability, or answer-correctness measure. A complete query is
labeled `complete_source_support_not_answer_validation` deliberately.

### Actual retrieval baseline

The program runs retrieval over active documents in the question's group. It
normalizes Unicode with NFKC and case-folding, tokenizes words, and removes the
small stopword set visible in source. It indexes title plus content, with:

```text
idf(term) = ln((1 + number_of_documents) / (1 + document_frequency)) + 1
weighted_tf(term) = 1 + ln(term_count)
vector_weight = weighted_tf * idf
score = cosine(query_vector, document_vector)
```

Only positive-overlap documents are returned, up to `top_k`. Ties resolve by
source ID. Out-of-vocabulary queries return an empty list, not padded matches.
Scores are rounded for display only after ranking. This is a transparent baseline,
not a semantic retriever or a claim about production search quality.

```text
hits = count(unique retrieved document IDs intersect unique relevant IDs)
precision = hits / count(unique actually retrieved document IDs)
recall = hits / count(unique relevant document IDs)
```

Every known metric carries its numerator and denominator. A zero denominator
produces `null`, not an invented zero or perfect score. No judgments produces
unknown numerator, denominator and value. Precision uses the actual returned
count, not the requested k. Analyst relevance judgments are assumptions to review;
the calculator cannot establish that they are correct or exhaustive.

## Outputs and the delivery interface

`report.json` is the canonical semantic output: version/snapshot/synthetic context,
source conditions, conflicts, per-question retrieval and fact support, and a
preparation backlog. Source references contain document ID, revision, SHA-256 and
exact line range. `report.md` presents the same results for a reader.

`preparation.csv` is an editable **display export**, with kind, subject, problem,
owner, evidence and next step. Unknown owners display as `UNKNOWN`. Formula-like
text receives a leading apostrophe so ordinary spreadsheet opening treats it as
text. That display encoding is not a change to the canonical JSON and should not
be silently round-tripped as an identifier. CSV is quoted using the standard
library; Unicode and multiline text are preserved.

For the existing evidence/report workbench, retain this report as a supporting
artifact. Map `query.id`, `query.group`, required fact and source references to
an analyst observation in the AI-readiness area; record actual interview support
and analyst disposition separately. A preparation backlog item is a request for
work, **not an accepted finding or recommendation**. This carrier does not mutate
the existing compiler's schema, generate its trusted output, or claim an integration
that has not been exercised. The worksheet describes the operator handoff.

## Scope, evidence and provenance

This kit implements the [UIOWA-073 work order](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789824753065929)
on the [live preparation board](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789823987058429).
Internal work record: [Commons issue 16131](https://github.com/woahwhattheheck/commons/issues/16131).

Operation: `uiowa-073-copperfinch-k73a-20260919`.
Builder: ZZ-COPPERFINCH-K73A, GPT-6 Astra Pro. The adjacent
[workbench](../uiowa_rfq_18649_workbench/README.md) remains unchanged.

No empirical AI productivity benefit, source authenticity, operational recovery,
University readiness, compliance, staff evaluation, commercial commitment or
permission change is established by this synthetic rehearsal.
