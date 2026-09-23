# Consolidated review and disposition register

**UIOWA-039 contribution · ZZ-QUARTZ-A91C · GPT-6 Astra Pro**

Recovered additive work, reconciled with the canonical ORRERY-K47 review-cycle
carrier in [issue #16139](https://github.com/woahwhattheheck/commons/issues/16139).
This module does not claim that carrier's ownership or replace its implementation.

An offline, editable JSON review register with deterministic JSON, CSV and Markdown
response-to-comments exports. It connects an original comment to a finding, the
finding's versioned evidence, a proposed edit, the complete recorded decision
history, and the resulting report revision. It deliberately preserves disagreements.

This is a proposed assessment-production tool, not University findings, a validated
maturity model, buyer acceptance, a billing decision, or a deployed customer product.
The included examples are wholly synthetic. No network, provider, scheduling, or
external-communication operation is present in the application.

## Namespace compatibility update

The event-register schema is now **`uiowa-rfq18649-review-register/v1`**. The old
`uiowa-rfq18649-review-cycle/v1` name belongs to ORRERY's different receipt-bound
patch-cycle format. Old register-shaped records require the explicit, non-destructive
[migration command and worked rehearsal](NAMESPACE_MIGRATION.md); canonical patch
cycles and mixed envelopes are rejected rather than silently reinterpreted. The
`compile_cycle` function name and workbench/native intake schemas are unchanged.

[NAMESPACE_VALIDATION.json](NAMESPACE_VALIDATION.json) records R6's 80 normal and
80 optimized tests (50 retained plus 30 new), source-bound migration verification,
byte-identical CLI outputs, and actual old/new-engine semantic comparison. Earlier
validation receipts below are retained historical generations, not expected hashes
for the corrected namespace. N3's browser work is independently documented in
[BROWSER_REHEARSAL.md](BROWSER_REHEARSAL.md).

## Run the complete rehearsal

Python 3.10 or later; standard library only. From this directory:

```sh
python make_examples.py
python review_register.py compile examples/synthetic-review-cycle.json --out rehearsal-output
python review_register.py handoff-intake examples/synthetic-workbench-handoff.json \
  --reviewer "Fictional assessor" --out rehearsal-intake.json
python native_handoff.py convert examples/native-workbench-handoff.json \
  --reviewer "Fictional assessor" --out native-intake.json
python native_handoff.py verify examples/native-workbench-handoff.json \
  native-intake.json --reviewer "Fictional assessor"
python -m unittest -v test_review_register.py test_native_handoff.py test_register_namespace.py
python -O -m unittest -v test_review_register.py test_native_handoff.py test_register_namespace.py
```

The output path must not exist. Re-running with another directory preserves every
previous export. `response.json` retains the full machine-readable history;
`response.csv` is a spreadsheet-readable working summary; `response.md` is the
reviewer's response-to-comments document. `manifest.json`, written last, lists
SHA-256 hashes of those three exact output files. Incomplete writes do not acquire
a completed manifest; originals are never modified. A failed write can leave an
incomplete new directory, which must not be mistaken for a complete export.

## What the example proves

Four comments span three report versions and two fictional reviewers. C-001 resolves
a wording clarification in draft-v2 without changing its evidence. C-002 replaces an
older checklist with an explicit revised evidence record in draft-v3. That later
change makes C-001's earlier resolution stale and returns it to the follow-up list,
without rewriting the historical decision. C-003 retains conflicting management and
practitioner accounts as **UNRESOLVED**. C-004 records rejection of an unsupported
institution-wide generalization; rejection is not deletion of the original comment.

Expected results: four comments; two recorded resolutions; one unresolved question;
one rejected proposed generalization; follow-up IDs `C-001` and `C-003`; stale
resolution `C-001`. Five actual synthetic text files accompany the evidence records;
every example source locator and whole-file hash is checked by the tests.

## Editable input schema

`examples/synthetic-review-cycle.json` is the complete editable template. All fields
shown below are required; unknown fields are diagnosed rather than silently dropped.
IDs are stable ASCII strings of at most 120 characters.

| Record | Fields and meaning |
|---|---|
| Packet | `schema` = `uiowa-rfq18649-review-register/v1`; boolean `synthetic`; `evidence`, `reports`, `comments` arrays |
| Evidence | Unique `id`, human-readable `label`, `source_locator`, lowercase whole-file `sha256` |
| Report | Unique `version`, claimed `receipt_sha256`, `supersedes`, `findings` |
| Finding | Stable `id`, `cell` containing `group` and `dimension`, `statement`, unique `evidence_refs` |
| Comment | Unique `id`, `reviewer`, original `report_version`, `finding_id`, `kind`, original `comment`, `proposed_edit`, recorded `events` |
| Event | Consecutive integer `sequence`, timezone-qualified RFC 3339 `at`, `actor`, `state`, nonempty `rationale`, `resulting_report_version` or `null` |

Groups are ESS, RIS and IAM. The retained register's internal dimensions are
`software_development`, `security`, `deployment` and `ai_readiness`. That first
spelling comes from the UI synthetic demo, not the parent compiler, which uses
`software`. The separate native adapter below makes this translation explicit. A cell
may have multiple findings; cells without findings are not assigned scores or
classified as weak. A finding ID cannot silently move to another cell.

Reports form an explicitly ordered, linear revision chain. The first `supersedes`
is `null`; each subsequent report names the immediately preceding version. The last
report is the target of the consolidated response. Branching report histories must
be reconciled into a linear export deliberately; this v1 tool does not choose a branch.
Changed source content receives a new evidence ID, retaining the old record for
historical references. Unresolved, duplicate or ambiguous IDs produce located errors.

## Decision lifecycle

Every comment begins OPEN. Supported recorded transitions:

```text
OPEN       -> ACCEPTED | REJECTED | DEFERRED | UNRESOLVED
ACCEPTED   -> RESOLVED | UNRESOLVED | DEFERRED
UNRESOLVED -> ACCEPTED | REJECTED | DEFERRED
DEFERRED   -> OPEN | ACCEPTED | REJECTED | UNRESOLVED
REJECTED   -> OPEN
RESOLVED   -> OPEN
```

ACCEPTED means the proposed response has been accepted **within the recorded analyst
review process**. It does not mean the edit is applied, an engagement is accepted,
or any commercial authority exists. Only RESOLVED binds a resulting report version.
A question may resolve by clarification against the original version; an applied
wording or evidence edit requires a later report version. Applying an older report
after an already-recorded newer resolution is diagnosed.

WORDING requires an actual statement edit and identical evidence references.
EVIDENCE_CHANGE requires explicit added or removed evidence-version references.
QUESTION supports clarification, and any evidence difference in its bound resulting
version is still displayed. Reopening preserves old events but clears the current
resolution binding. A later changed or removed target finding marks a prior
resolution stale. Reordering the same evidence references does not create false drift.
No timestamp, reviewer identity, or rationale is authenticated by this offline tool.

## Existing workbench integration

The retained `review_register.py handoff-intake` consumes the legacy synthetic-demo
vocabulary in the existing `uiowa-rfq18649-analyst-handoff-draft/v1` envelope. Real
parent-derived workbench exports use `software`, while the UI demo uses
`software_development`; neither producer was changed here.

Use **`native_handoff.py convert`** for either vocabulary. The adapter requires one
complete twelve-cell vocabulary; a mixed or incomplete packet is diagnosed. It
normalizes only the internal call to the retained validator, then exports the
original `cell` unchanged, the explicit `register_cell` alias, and the complete
original `source_handoff`, including all twelve notes and dispositions. The source
canonical hash and each intake ID bind the original input, not the normalized copy.
The `input_dimension_vocabulary` field describes spelling, not an authenticated
producer. Native output has its own schema,
`uiowa-rfq18649-native-review-intake-draft/v1`, so consumers do not mistake it for
an unchanged legacy protocol.

Both paths preserve supplied report receipts and synthetic labels. Nonempty notes
and non-UNREVIEWED dispositions become `OPEN_INTAKE_NOT_A_FINDING`, with
`finding_id=null` and `kind=null`. No finding, reviewer agreement or resolution is
invented from a browser note. Stable IDs distinguish reviewers, receipts, synthetic
versus nondemo inputs, original cell spelling and changed note content. Unchanged
comment IDs survive a source-array reorder; the whole-source hash still exposes
that reordering.

`native_handoff.verify(original_handoff, reviewer, intake)` recomputes the entire
result from the original inputs. A fabricated finding cannot be made valid merely
by recalculating the intake's own digest. This is consistency verification, not
source authenticity or a call to the parent compiler's verifier.

The supplied native fixture and tests exercise the actual inspected field names,
not a claim of actual University data, a live browser run or parent-compiler
execution. Sibling changes to the envelope require an explicit adapter update.
The native CLI regression launches real `python -O` subprocesses for conversion,
verification and non-overwrite handling. The retained core CLI test does not
propagate optimization automatically; its normal child execution is not relabeled.

### Native integration API

```python
from native_handoff import convert, verify
intake = convert(original_handoff, "Recorded reviewer role")
verify(original_handoff, "Recorded reviewer role", intake)
# Join to a published finding only after explicit analyst classification.
# Keep intake["comments"][i]["cell"] and ["register_cell"] distinguishable.
```

ORRERY's review-cycle and FARADAY's CSV import work can consume the published record
contract here without changing their own schemas implicitly. This contribution
provides intake and decision-history components; it does not automatically apply
edits to the canonical report, resolve recommendation priority, or claim full
UIOWA-094 rehearsal completion for the swarm.

## Integrity, privacy and interpretation

The source-packet hash and output receipt hash bind canonical JSON contents. The
export manifest binds exact generated file bytes. These are integrity metadata, not
signatures. Report receipt fields are **claimed bindings**: this tool does not call
the parent compiler's integrity verifier or authenticate source evidence files.
The example tests separately read back the included synthetic sources and hashes.

All output approval, submission, signature, invoice/payment, current-evidence-review
and recognized-revenue flags remain false. `synthetic=false` labels the Markdown
output **PRIVATE INPUT — NOT APPROVED FOR PUBLICATION**. Neither that label nor any
other metadata grants permission to publish real private records. Keep University,
prime, customer, credential and participant material out of the public repository.

Inputs are limited to 4 MiB. Duplicate JSON keys, non-finite numbers, unsupported
floating-point fields, unpaired Unicode surrogates, wrong types, broken references,
nonconsecutive event sequences and invalid transitions are diagnosed. CSV export
quotes formula-leading strings as text; Markdown output escapes embedded markup.
The source JSON remains unchanged. No application login or provider-access mechanism
is introduced; these checks validate record structure and preserve provenance.

## Engineering evidence

Source interface inspected on 2026-09-19:

- Workbench `app.js` blob `f180d24e5bb05489774d8c0baa4f60d3fd978656`.
- Workbench `index.html` blob `ad4bda4ec6be6fa02c1f33b3bf83fb7c009a13b6`.
- Workbench `README.md` blob `75a0f82b3df7a8ca0c5f34d2d24b4adcf8bf84a2`.
- Parent `workshare_constants.py` blob `ec65f4f4d5387d6c2546eee98101b34faa61b0bd`
  supplies the native `software` spelling.

The implementation is additive in this directory. It does not edit or replace the
compiler, workbench UI, report-diff tool, delivery-bundle exporter, or other agents'
lanes. The retained historical `VALIDATION.json` binds the five originally executed
Python files; `REHEARSAL_RESULTS.md` records that generation's example results and
commands. Seventy tests passed normally and under optimization for those exact
prior objects. R6's namespace-generation results and changed expected digests are
separately bound in `NAMESPACE_VALIDATION.json` and `NAMESPACE_MIGRATION.md`.
N3's browser execution remains separately documented in `BROWSER_VALIDATION.json`.
These results are not repository-wide or hosted-CI success. Provider merge and
Slack receipts belong to the PR and existing demo thread, not fabricated here.
