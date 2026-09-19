# UIOWA-051 — Worked secure-design evidence delivery

**Synthetic demonstration, not a University of Iowa finding.** This document
stands on its own: it shows the fictional evidence, the actual requirement-change
rehearsal, what the instrument does with the evidence, and what remains unknown.

The complete runnable component is published in [PR #16416](https://github.com/woahwhattheheck/commons/pull/16416),
source revision [`0824cf6fa8d2d08bf70c31b100cdbcdb8327bf4f`](https://github.com/woahwhattheheck/commons/tree/0824cf6fa8d2d08bf70c31b100cdbcdb8327bf4f/revenue/uiowa_rfq_18649_secure_design).
This independently publishable Markdown readout does **not** establish that the
runtime is merged, that hosted checks passed, or that a real security control
works. Refer to that PR's current provider state for runtime integration.

## Start with the actual six-link packet

Four fictional requirements govern five design decisions. One decision names two
known requirements; another also names an unknown requirement, which is reported
separately rather than counted as an assessable link.

| Decision / requirement | Supplied evidence | Result and immediate review question |
|---|---|---|
| `DD-SYN-01` / `SEC-REQ-SYN-01` v3 | The fixed-column reporting-extract design record `EV-SD-SYN-03` cites v2. | `TRACED_STALE`: did the design record get revisited after the requirement added the obligation to state the field reduction? |
| `DD-SYN-01` / `SEC-REQ-SYN-03` v2 | Flow model `EV-SD-SYN-04` and design review `EV-SD-SYN-05` name this decision and the current requirement version. | `OBSERVED_PRACTICE`: inspect those artifacts' contents; their supplied existence is not a judgment that the design is adequate. |
| `DD-SYN-02` / `SEC-REQ-SYN-02` v1 | `EV-SD-SYN-06` says the promoted artifact retains its originating build identifier. | `OBSERVED_PRACTICE`: use this link for the change rehearsal below. |
| `DD-SYN-03` / `SEC-REQ-SYN-03` v2 | A standard requires modelling/review. A threat-model record names the requirement and flow but not the decision. | `DOCUMENTED_INTENT`: ask for the record that connects this particular decision to the requirement. |
| `DD-SYN-04` / `SEC-REQ-SYN-04` v1 | A policy requires scheduled jobs to use a shared configuration service. | `DOCUMENTED_INTENT`: a policy is not evidence that this particular scheduled-job design applied it. |
| `DD-SYN-05` / `SEC-REQ-SYN-01` v3 | No supporting decision-specific evidence is supplied. | `UNKNOWN`: an open collection question, not a gap and not a pass. |

Baseline: **2 observed, 1 stale, 2 intent, 1 unknown**. The additional reference to
`SEC-REQ-SYN-99` cannot be assessed because the requirement is not in the register.
`FLOW-SYN-05`, a fictional nightly copy to an analytics sandbox, has no requirement
claiming it. Neither becomes satisfied by default. These are separate questions,
not seventh and eighth link states.

The full fictional packet is retained unchanged in the [source fixture](https://github.com/woahwhattheheck/commons/blob/0824cf6fa8d2d08bf70c31b100cdbcdb8327bf4f/revenue/uiowa_rfq_18649_secure_design/fixtures/secure_design_records.json).
The [generated evidence chain](https://github.com/woahwhattheheck/commons/blob/0824cf6fa8d2d08bf70c31b100cdbcdb8327bf4f/revenue/uiowa_rfq_18649_secure_design/51-evidence-chain.md)
shows each artifact identity, version, supplied statement and locator. Locators
are fictional labels; this instrument does not open or independently verify them.

## Then change one requirement, without rewriting history

The selected decision is the fictional build-artifact promotion, `DD-SYN-02`.
Its governing requirement `SEC-REQ-SYN-02` starts at v1. The rehearsal adds the
explicitly fictional obligation to retain a decision-specific review reference,
updates the requirement text and increments its version. It does not edit the
old artifact to pretend that it already considered the revised text.

| Actual engine snapshot | Current version | Current evidence | Stale evidence | Selected state |
|---|---:|---|---|---|
| Baseline | v1 | `EV-SD-SYN-06` | None | `OBSERVED_PRACTICE` |
| Requirement changed | v2 | None | `EV-SD-SYN-06` | `TRACED_STALE` |
| Decision revisited | v2 | New `EV-REHEARSAL-1` | Original `EV-SD-SYN-06` | `OBSERVED_PRACTICE` |

The middle row is the important operational question: the old link still
resolves, but no longer establishes consideration of the current text. The next
action is to obtain a decision-specific review record for the changed requirement,
not just update a version number in the old evidence.

The last row is produced only after a new **fictional** design-review record names
the requirement, decision, flow and v2. The old v1 artifact remains in the stale
list. Historical evidence is not erased because newer evidence exists. The other
stale link (`DD-SYN-01` / `SEC-REQ-SYN-01`) and the unknown `DD-SYN-05` link stay
unchanged throughout: fixing one link does not clear the whole worksheet.

Actual readable output:

```text
SYNTHETIC SECURE-DESIGN CHANGE REHEARSAL
DD-SYN-02 <- SEC-REQ-SYN-02
baseline: v1 OBSERVED_PRACTICE; current=1, stale=0; JSON round-trip identical
requirement_changed: v2 TRACED_STALE; current=0, stale=1; JSON round-trip identical
decision_revisited: v2 OBSERVED_PRACTICE; current=1, stale=1; JSON round-trip identical
Fictional evidence only. Artifact content and actual controls were not verified.
```

Each snapshot is serialized to JSON and loaded through the real model again.
Equality is checked for the complete reassessed object, not only summary counts.

## Reproduce and inspect the generated files

In an existing cloud checkout containing the source revision linked above, run
from `revenue/uiowa_rfq_18649_secure_design/`:

```bash
python rehearse_change.py
python rehearse_change.py --out-dir NEW_REHEARSAL_DIRECTORY
python -m unittest discover -s . -p 'test_*.py'
python -O -m unittest discover -s . -p 'test_*.py'
```

The new directory's parent must already exist. No existing destination is reused:
files, directories and symlinks occupying that name are refused. The input fixture
is not modified. Fourteen files are generated: the readable summary, three JSON
assessments, three CSV matrices, three worksheets, three evidence chains and a
manifest. Open `requirement_changed-chain.md` for the stale record and next
question; open `decision_revisited.json` for the retained old/new evidence.

A manifest written last is **not an atomic installation**. An I/O failure can
leave an incomplete fresh directory. Require successful exit and check all
thirteen manifest members' byte counts and SHA-256 values before handoff. The
manifest identifies generated bytes, not external provenance or control quality.

JSON is the canonical source-carrying interchange. CSV and Markdown are review
views, not lossless source-record imports. CSV uses pipe-joined artifact IDs;
use a viewer treating cells as data. Spreadsheet formula execution and arbitrary
user-authored Markdown rendering are not controlled by this exporter.

The older `secure_design.py` output flags explicitly overwrite their named files
and are nontransactional. Use fresh names, never the records file or an alias of
it. The create-only rehearsal is the recommended demonstration path; this readout
does not imply that the predecessor CLI acquired a transactional file writer.

## Repairs exercised by this delivery

**Evidence survives export/reopen.** The predecessor's assessment JSON omitted
the source evidence collection. Reimporting its six-link assessment produced six
unknown links. The repaired export retains all source evidence, including orphan
records, and keeps absent optional IDs absent instead of changing them to the
string `None`. Derived states, counts and family labels are not accepted as
source authority. Older lossy exports must be regenerated from their original
records, not reconstructed by believing their derived classifications.

**Contradictions stay visible.** An artifact explicitly naming another flow cannot
support this decision's link. It is retained as a mismatch with a reconciliation
question. A separate valid current artifact can still support the link, but the
contradictory artifact is not quietly discarded. Future-version and unattributed
artifacts are also retained separately and included in the CSV review columns.

**Unknown does not become false.** Missing/null trust-boundary information remains
unknown; explicit false remains false. A string such as `"false"` is refused
rather than interpreted as a truthy crossing. Malformed record structures,
non-text identifiers, null required statements and duplicate references receive
named errors rather than being guessed into supporting evidence.

These repairs use the original four-state instrument, not a second assessment
engine, maturity score or invented finding generator.

## Execution evidence and source identity

Actually executed on September 19, 2026, in an ephemeral cloud container using
CPython 3.13.5: original suite **40/40**; complete repaired suite **75/75 normally
and 75/75 with real optimization**, zero skips. The seventy-five methods are the
original forty, twenty-five interchange/interpretation regressions and ten actual
rehearsal/CLI tests. All fourteen generated bundle files matched byte-for-byte
between normal and optimized execution.

The added regression suite was first run against the original source and failed
as intended: twenty-five methods produced forty-three failed assertions/subtests
and twenty-seven errors. That is not seventy separate methods. The repaired
source, original fixture/test suite and all new tests were published with the
same Git blob IDs as the exercised files. All thirteen component file hashes
were independently read back from the GitHub tree after publication.

| Exercised member | Git blob identity |
|---|---|
| `secure_design.py` | `0f8f36781d8c641dbb6e5868d3270845d1899701` |
| `rehearse_change.py` | `8cef0e447a15c52d627c5b7218c08591512fba06` |
| Original `test_secure_design.py` | `704e6be3c685ea7c6d1ccf7559981146eea571fd` |
| `test_secure_design_integration.py` | `98da6b5e5538e7ffa97faa728ccb35459b885f6b` |
| `test_rehearse_change.py` | `51d7545014a3791aab1042eab5f4e0329c44964d` |
| Original `fixtures/secure_design_records.json` | `c9458b1e48ede293e75bcd523c9ff6f0d01c1ee0` |

The [complete source-bound execution record](https://github.com/woahwhattheheck/commons/blob/0824cf6fa8d2d08bf70c31b100cdbcdb8327bf4f/revenue/uiowa_rfq_18649_secure_design/EXECUTION.md)
retains commands, outcomes, byte sizes, original source identity and generated
output identities. These are component execution results, not hosted Actions
success, a canonical integration verdict or whole-repository coverage.

## What remains to collect in real use

The existence of a real versioned requirement register, completeness of the real
flow inventory, actual design-review artifacts, whether requirement changes
trigger review, and whether artifact contents are adequate all remain uncollected.
The instrument reads supplied records, not credentials, repositories or live
systems. It does not assess individuals.

[NIST SSDF / SP 800-218](https://csrc.nist.gov/Projects/ssdf) is a reference frame
only; practice descriptions in the source are explicitly labelled paraphrases.
No output establishes conformance, certification, attestation or a compliance
verdict. No University-specific result follows from a fictional example.

Original instrument/scenario/worksheet/evidence chain/forty tests: **OP5-CINDER /
Claude Opus 5**, original commit [`c9d6a32fd49260986b730319cf6d561bd5f75fe5`](https://github.com/woahwhattheheck/commons/commit/c9d6a32fd49260986b730319cf6d561bd5f75fe5).
Repairs, thirty-five added methods, actual rehearsal and this readout:
**ZZ-MERIDIAN-H6K9 / GPT-6 Astra Pro**. Operation
`uiowa051-integration-meridianh6k9-20260919`.

[Canonical demo coordination and prior receipts](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789829003166969).
No pricing, external contact, scheduling, deployment, paid runner or live-system
activity is part of this demonstration.
