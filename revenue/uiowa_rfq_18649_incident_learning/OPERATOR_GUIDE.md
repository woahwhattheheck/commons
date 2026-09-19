# UIOWA-067 · Incident learning and follow-through

An executable, offline assessment-preparation kit by **ZZ-HELIODORE-67 / GPT-6 Astra Pro**. Operation: `uiowa-067-heliodore67-20260919`. Internal work record: [#16149](https://github.com/woahwhattheheck/commons/issues/16149). Source work order: [UIOWA-067](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789824744501299).

**The supplied ESS, RIS and IAM histories are entirely fictional. They are not University findings, a maturity score, a formal audit, an employee evaluation, or a commercial product recommendation.** This directory does not contact services, change production, schedule work, or alter source records.

## Run the complete rehearsal

Python 3.10+ language features; execution verified with CPython 3.13.5 on an ephemeral Linux cloud container. No third-party packages, credentials, network connection or application installation required. From the repository root:

```sh
python -m unittest discover -s revenue/uiowa_rfq_18649_incident_learning -v
python revenue/uiowa_rfq_18649_incident_learning/fixture.py /tmp/uiowa-067-demo
python revenue/uiowa_rfq_18649_incident_learning/report.py /tmp/uiowa-067-demo/packet.json --format markdown > /tmp/uiowa-067-demo/report.md
python revenue/uiowa_rfq_18649_incident_learning/report.py /tmp/uiowa-067-demo/packet.json --format json > /tmp/uiowa-067-demo/report.json
python revenue/uiowa_rfq_18649_incident_learning/report.py /tmp/uiowa-067-demo/packet.json --format csv > /tmp/uiowa-067-demo/actions.csv
```

The fixture command writes `packet.json` and the human-readable `synthetic-evidence.md`. The report contains every cited source ID, locator and excerpt. Move the whole demo directory to another operator; its reports and evidence remain readable without the producing environment. Use a new output directory for a fresh fixture run: the fixture generator replaces its two named generated files. The report command only reads its input and writes standard output. Invalid inputs return code 2 and an explanation on standard error without a partial report. Successful analysis returns 0 even when evidence is missing: a gap is a result, not an execution failure.

### Demonstrated acceptance result

29 tests pass, including three executable export formats and preservation of the input bytes. The synthetic packet produces:

| Result | Expected |
|---|---|
| Incident records / unique corrective actions | 3 / 6 |
| Closed, implementation and verification evidenced | ACT-01 |
| Closed but implementation/verification not established | ACT-03 |
| Documented replacement, not completed improvement | ACT-04 → ACT-05 |
| Open work | ACT-02, ACT-05, ACT-06 |
| Overdue unresolved actions at 2026-09-19 00:00 UTC | ACT-02: 9 days; ACT-03: 7 days; ACT-05: 2 days |
| ESS impact-to-restoration / detection-to-restoration | 60 / 55 minutes |
| IAM impact-to-restoration | UNKNOWN: unsupported start milestone |
| RIS restoration-to-verification | UNKNOWN: missing verification milestone |
| ACT-01 comparison | 6/1,000 before versus 2/2,000 after = 6 versus 1 per 1,000 attempts |

The final row is a **descriptive synthetic comparison**, not proof that ACT-01 caused improvement. The tool makes no statistical-significance or lasting-reliability claim. Its comparison uses exact rational arithmetic for ordering before converting displayed rates to floating point. Zero exposure, missing counts, missing measurement sources, incomplete coverage, changed units/cohorts, overlapping windows, a baseline extending beyond implementation, or follow-up preceding completion cannot become a positive result.

## What the files do

- `contract.py`: validates identifiers, references, source kinds, aware timestamps, milestones, action links, replacement graph and measurement windows; rejects duplicate JSON keys and malformed inputs.
- `analyze.py`: derives evidence states, as-of aging, supported timeline intervals, normalized descriptive measurements and condition-to-backlog traces without assigning maturity.
- `report.py`: command-line entry point and JSON, typed CSV, and Markdown views with a source appendix.
- `fixture.py`: reproducible fictional incident/decision/change/verification/measurement records, with missing information intentionally retained.
- `test_incident_learning.py`: behavioral, boundary, malformed-input, export and CLI regression tests.
- `RUBRIC.md`: practical interview and artifact-review instrument, interpretation examples, and adoption options.
- `SCHEMA.md`: data dictionary and integration contract.

## Evidence interpretation

A reported `closed` label is not verified implementation. `implementation_verified` means the supplied record has a completion timestamp, correctly typed implementation sources observed no later than completion, and verification sources observed at or after completion. It is a record-based characterization, **not source authentication or a guarantee that a particular test is sufficient**. An analyst must inspect source content, scope, chronology and relevance.

An interview alone cannot establish a measured incident timeline. Only milestones linked to retained incident or verification records contribute elapsed intervals. Missing or unsupported endpoints stay null. A retained incident record may contain retrospective times; the operator must check clock accuracy and uncertainty rather than interpreting three-decimal arithmetic as measurement precision. Each stage is a canonical milestone, not a full event stream; use notes/locators to preserve repeated attempts and select milestones consistently.

A replaced action retains the decision rationale, evidence and successor. The replacement must preserve the original contributing conditions, cannot refer to itself, and cannot form a cycle. `replacement_documented` does not verify the successor or erase its overdue state. No evidence is deleted. A closed-but-unverified action remains unresolved for aging; this is **evidence follow-through aging**, not a claim that an employee missed a contractual deadline. A verified late completion retains lateness separately.

The same corrective action may serve multiple incidents and is counted once. A shared dependency recurring in two records is not two independent group-practice observations or a recurrence rate. Coverage labels apply to the supplied incident sample, not the whole organization. The kit does not infer absence of incidents from an empty export.

## Integration boundary

This is an additive specialist preparation kit, not another core workbench or report compiler. Its JSON exposes stable `incidents`, `actions`, `conditions` and `sources` arrays. Preserve these IDs and source locators when mapping evidence into the existing workshare/workbench. Map each incident to its group and deployment/operations area; treat action evidence states as observations, **never as automatic area-level maturity ratings**. The source appendix can accompany a report-bundle export. A core-workbench adapter is not claimed to exist in this carrier.

Needed for a real engagement: an agreed sampling window and incident census/completeness basis; service boundaries and user-impact definitions; retained incident records and clock/timezone meanings; postmortem review/sharing evidence; backlog links and owner roles; implementation and business-verification artifacts; measured exposure and comparable cohort definitions; explanation of alternatives and open disagreements. Do not populate these with the fictional packet or publish confidential source material into the public repository.

## Method reference and limits

Primary reference, accessed September 19, 2026: Google SRE, [Chapter 15: Postmortem Culture: Learning from Failure](https://sre.google/sre-book/postmortem-culture/), especially “Google’s Postmortem Philosophy,” “Collaborate and Share Knowledge,” and “Ask for Feedback on Postmortem Effectiveness.” The relevant principles are documenting impact and response, examining contributing conditions without personal blame, reviewing and sharing lessons, and following preventive work. This kit's state machine, aging rules, schema and comparison checks are **TJLabs proposed assessment mechanics**, not a Google standard, validated Iowa maturity scale, or claim about either organization's actual practices.
