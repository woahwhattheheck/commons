# Policy-to-practice matrix — Example State University (FICTIONAL)

> **FICTIONAL DATA. Example State University is an invented organization. No record here describes the University of Iowa or any real institution, policy, system, or person.**

Prepared for leadership discussion. NIST AI RMF is used as a reference for organizing discussion, **not** as a certification checklist: <https://www.nist.gov/itl/ai-risk-management-framework>.

## How to read this

Three things are kept apart on purpose and are never merged into one verdict:

| Column | What it is |
|---|---|
| **Stated policy** | What is written down, and whether it is in force. |
| **Implementation evidence** | What an assessor actually observed. |
| **Open questions** | What the University must clarify before anyone can judge the cell. |

`LOOKED_NONE_FOUND` (somebody checked, the practice was absent) and `NOT_GATHERED` (nobody checked) are different states. Only the first is a gap. The second stays UNKNOWN and is excluded from every count below.

## Counts

| Measure | Count |
|---|---|
| cells total | 15 |
| cells assessed | 10 |
| cells not assessed | 4 |
| cells blocked on clarification | 1 |
| gaps among assessed | 3 |
| strengths among assessed | 5 |
| open questions total | 5 |
| open questions blocking | 1 |

Raw integers only. No percentage is reported, because a percentage implies a complete denominator and this assessment has 4 unassessed cells.

### Read this before quoting any count above

- 4 of 15 cells were never assessed. Gap and strength counts below describe ONLY the 10 assessed cells. Do not read '3 gaps' as '3 gaps exist' -- unexamined ground is not clean ground.
- 1 cells cannot be resolved until the University answers a blocking interpretation question. They are excluded from gap and strength counts; their provisional reading is kept in reading_if_unblocked.

## Matrix

| Task | Accountable role | Stated policy | Policy in force? | Implementation evidence | Reading | Open questions |
|---|---|---|---|---|---|---|
| TSK-01 — Author application code with an AI coding assistant | Application Developer (supervised by Engineering Manager, Enterprise Applications) | POL-AI-01 Generative AI Acceptable Use Standard | HAS_ACTIVE_POLICY | ASSERTED_ONLY | **STATED_PRACTICE_UNCORROBORATED** | Q-03 |
| TSK-01 — Author application code with an AI coding assistant | Application Developer (supervised by Engineering Manager, Enterprise Applications) | POL-DATA-03 Institutional Data Classification and Handling Standard | HAS_ACTIVE_POLICY | LOOKED_NONE_FOUND | **STATED_NOT_PRACTICED** | Q-03 |
| TSK-02 — Review a change that contains AI-generated code | Change Reviewer of record | POL-AI-01 Generative AI Acceptable Use Standard | HAS_ACTIVE_POLICY | EVIDENCED_DIRECT | **ALIGNED** | — |
| TSK-02 — Review a change that contains AI-generated code | Change Reviewer of record | POL-AI-04 AI Output Review and Accountability Guideline | HAS_NONBINDING_POLICY | EVIDENCED_DIRECT | **PRACTICE_AHEAD_OF_POLICY** | Q-02 |
| TSK-02 — Review a change that contains AI-generated code | Change Reviewer of record | POL-SEC-07 Secure Development Lifecycle Standard | HAS_ACTIVE_POLICY | EVIDENCED_DIRECT | **ALIGNED** | — |
| TSK-03 — Triage an incoming support ticket using AI summarization | Service Desk Lead | POL-AI-01 Generative AI Acceptable Use Standard | HAS_ACTIVE_POLICY | ASSERTED_ONLY | **STATED_PRACTICE_UNCORROBORATED** | — |
| TSK-03 — Triage an incoming support ticket using AI summarization | Service Desk Lead | POL-AI-04 AI Output Review and Accountability Guideline | HAS_NONBINDING_POLICY | NOT_GATHERED | **NOT_ASSESSED** | Q-02 |
| TSK-04 — Draft user-facing documentation with an AI assistant | Documentation Owner (unit-level) | POL-AI-01 Generative AI Acceptable Use Standard | HAS_ACTIVE_POLICY | NOT_GATHERED | **NOT_ASSESSED** | — |
| TSK-04 — Draft user-facing documentation with an AI assistant | Documentation Owner (unit-level) | POL-AI-04 AI Output Review and Accountability Guideline | HAS_NONBINDING_POLICY | NOT_GATHERED | **NOT_ASSESSED** | Q-02 |
| TSK-05 — Assemble a data extract used as AI prompt or retrieval context | Data Steward (unit-level) | POL-DATA-03 Institutional Data Classification and Handling Standard | HAS_ACTIVE_POLICY | EVIDENCED_INDIRECT | **BLOCKED_ON_CLARIFICATION** | Q-01 |
| TSK-06 — Evaluate and onboard a new AI vendor tool | Procurement Liaison with Information Security review | POL-AI-02 AI Tool Procurement and Vendor Review Procedure | HAS_ACTIVE_POLICY | EVIDENCED_DIRECT | **ALIGNED** | Q-04 |
| TSK-07 — Approve a release containing AI-assisted changes | Release Approver of record | POL-SEC-07 Secure Development Lifecycle Standard | HAS_ACTIVE_POLICY | NOT_GATHERED | **NOT_ASSESSED** | — |
| TSK-08 — Handle AI prompt and response logs that may contain institutional data | System Owner | POL-DATA-03 Institutional Data Classification and Handling Standard | HAS_ACTIVE_POLICY | LOOKED_NONE_FOUND | **STATED_NOT_PRACTICED** | — |
| TSK-08 — Handle AI prompt and response logs that may contain institutional data | System Owner | POL-SEC-07 Secure Development Lifecycle Standard | HAS_ACTIVE_POLICY | LOOKED_NONE_FOUND | **STATED_NOT_PRACTICED** | Q-05 |
| TSK-09 — Notice and respond to a vendor model or version change | Platform Engineering (practice observed; no role is named for this task in any policy reviewed) | (none) (no written policy covers this task) | NO_POLICY | EVIDENCED_DIRECT | **UNDOCUMENTED_PRACTICE** | — |

## What each reading means

| Reading | Counts as | Meaning |
|---|---|---|
| `ALIGNED` | strength | Policy is in force and an artifact was inspected showing the practice. |
| `ALIGNED_INDIRECT` | strength | Policy is in force; a related artifact implies the practice. Weaker than a direct inspection. |
| `STATED_PRACTICE_UNCORROBORATED` | neither | Policy is in force and staff say they follow it, but nothing was found that corroborates it. Not a finding either way. |
| `STATED_NOT_PRACTICED` | gap | Policy is in force, an assessor looked, and the practice was absent. A real gap. |
| `PRACTICE_AHEAD_OF_POLICY` | strength | The practice is happening, but the policy behind it is draft or superseded. The work is real; the mandate is not. |
| `POLICY_NOT_IN_FORCE` | neither | A draft or superseded policy exists and the practice was not found. Not a violation -- nothing binds yet. |
| `UNDOCUMENTED_PRACTICE` | strength | The practice is demonstrably happening with no written policy behind it. A strength that depends on the people currently doing it. |
| `UNCLEAR_ON_BOTH_SIDES` | neither | Nothing binding is written and nothing corroborates the claimed practice. Needs fieldwork, not a verdict. |
| `NOT_ADDRESSED` | gap | No policy covers this task and an assessor confirmed the practice is absent. |
| `NOT_ASSESSED` | neither — UNKNOWN | UNKNOWN. No evidence was gathered for this cell. Not a gap, not a pass, not a zero. |
| `BLOCKED_ON_CLARIFICATION` | neither — blocked | Cannot be resolved until the University answers an interpretation question. Any verdict here would be guesswork. |

## Questions requiring University clarification

These are not findings. They are the points where the assessor cannot honestly decide a cell without the University saying how its own policy is meant to read.

| ID | Blocking? | Asked of | Question | Why it matters |
|---|---|---|---|---|
| Q-01 | **YES** | Institutional Data Governance Council | Does the definition of institutional data in POL-DATA-03 cover prompt text and retrieval context submitted to an external AI vendor, or only data at rest and in transit between University systems? | If prompt text is in scope, the existing extract request form is the wrong instrument and every AI retrieval path needs a handling decision. If it is out of scope, the current practice is already correct. The assessor cannot pick one without the Council saying which reading is intended, so this cell is reported as BLOCKED rather than guessed. |
| Q-02 | no | AI Governance Working Group | Should current practice be described against the draft POL-AI-04, or only against the active POL-AI-01, for the duration of this assessment? | Non-blocking: what the assessor observed can be recorded either way. It changes only whether observed practice is described as ahead of a draft or as unattributed. Answering it before the final report avoids re-litigating three cells. |
| Q-03 | no | Office of the CIO and Human Resources | When AI-assisted code is authored by a student employee, which role is accountable under POL-AI-01: the supervising engineer, the unit manager, or the student? | POL-AI-01 is silent on student employment. Non-blocking for the matrix because the practice observed is the same either way, but leadership will be asked this and should not be asked it for the first time in the readout. |
| Q-04 | no | Procurement Services | Does AI tool in POL-AI-02 include AI features switched on inside products already under contract, or only newly licensed AI products? | The three inspected review records are all net-new products. If embedded features are in scope, the procurement path has an untested population; if not, the current records are complete for what the procedure covers. |
| Q-05 | no | Information Security Office and University Records Management | Which retention schedule governs AI prompt and response logs where the prompt may contain institutional data: the application log schedule in SEC-07, or the records schedule for the underlying record class? | Non-blocking: the gap is established either way, because neither schedule is currently applied. The answer determines what the remediation target is, not whether there is one. |

## What this assessment refuses to produce

- No maturity level, readiness level, or tier is computed. The four NIST AI RMF functions are used as a sort key only; this is not a conformance assessment and the AI RMF is not a certification. Reference: https://www.nist.gov/itl/ai-risk-management-framework
- No single score, index, or percentage summarizing the organization is produced. Calling score() raises ScoreRefused.
- No percentage is reported over a denominator that includes NOT_ASSESSED cells. Counts are raw integers so an unfinished assessment cannot be read as a proportion of a complete one.
- NOT_ASSESSED is never counted as a gap, a pass, or a zero. It means nobody looked.
- An interview assertion is never promoted to implementation evidence.
- No individual is scored. The accountable unit is a ROLE.
- No peer comparison, percentile, benchmark, or 'typical institution' claim is made.
- NIST AI RMF subcategory-level mapping is UNKNOWN and is not invented.
