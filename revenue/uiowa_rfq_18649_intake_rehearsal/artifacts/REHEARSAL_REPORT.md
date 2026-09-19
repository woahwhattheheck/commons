# UIOWA-092 - intake-to-assessment rehearsal report

> **SYNTHETIC REHEARSAL OUTPUT - every organization, document, number and quotation below is fictional, authored for the UIOWA-092 integration rehearsal. Nothing here is a University of Iowa record, measurement, or finding.**

Collection `COLL-SYN-092-A` · declared as-of `2026-09-19` · 12 sources declared, 11 resolved, 16 observations accepted, 5 interview excerpts.

## 1. The twelve cells

Three fictional groups by the four assessment areas. `UNKNOWN` means the evidence was insufficient - it is not a gap, not a zero, and not a pass.

| Cell | Group | Area | State | Observations | Usable sources |
| --- | --- | --- | --- | --- | --- |
| `CELL-ESS-SD` | ESS | Software development | **DEMONSTRATED_STRENGTH** | 2 | 2 |
| `CELL-ESS-SEC` | ESS | Security | **PARTIAL** | 1 | 0 |
| `CELL-ESS-DEP` | ESS | Deployment and operations | **MIXED** | 2 | 2 |
| `CELL-ESS-AI` | ESS | AI readiness | **UNKNOWN** | 0 | 0 |
| `CELL-RIS-SD` | RIS | Software development | **OBSERVED_GAP** | 2 | 1 |
| `CELL-RIS-SEC` | RIS | Security | **MIXED** | 2 | 1 |
| `CELL-RIS-DEP` | RIS | Deployment and operations | **OBSERVED_GAP** | 1 | 1 |
| `CELL-RIS-AI` | RIS | AI readiness | **PARTIAL** | 1 | 0 |
| `CELL-IAM-SD` | IAM | Software development | **CONFLICT** | 2 | 1 |
| `CELL-IAM-SEC` | IAM | Security | **DEMONSTRATED_STRENGTH** | 1 | 2 |
| `CELL-IAM-DEP` | IAM | Deployment and operations | **UNKNOWN** | 1 | 0 |
| `CELL-IAM-AI` | IAM | AI readiness | **PARTIAL** | 1 | 1 |

State tally: DEMONSTRATED_STRENGTH 2, OBSERVED_GAP 2, MIXED 2, CONFLICT 1, PARTIAL 3, UNKNOWN 2.

## 2. Why each cell says what it says

**`CELL-ESS-SD` - ESS / Software development: DEMONSTRATED_STRENGTH**

Direct artifact evidence from independent observations across source types change_record, configuration_export.

Observations: `OBS-SYN-ESS-SD-001`, `OBS-SYN-ESS-SD-002`.

- Follow-up: Confirm the repository inventory is complete before any group-wide statement.
- Follow-up: Widen the sample or request the full merge history for the period.

**`CELL-ESS-SEC` - ESS / Security: PARTIAL**

Support is interview statement only (OBS-SYN-ESS-SEC-001). The practice is stated, not demonstrated; no artifact was produced.

Observations: `OBS-SYN-ESS-SEC-001`.

- Follow-up: Request one completed quarterly review with its date and the reviewing role.

**`CELL-ESS-DEP` - ESS / Deployment and operations: MIXED**

Direct evidence supports both a strength and a shortfall in this area; both are reported rather than netted against each other.

Observations: `OBS-SYN-ESS-DEP-001`, `OBS-SYN-ESS-DEP-002`.

- Follow-up: Ask whether exceptions are recorded in a separate system, or whether these were unexcepted.
- Follow-up: Confirm whether the log is the authoritative record or a secondary copy.

**`CELL-ESS-AI` - ESS / AI readiness: UNKNOWN**

No evidence was supplied for this cell.

**`CELL-RIS-SD` - RIS / Software development: OBSERVED_GAP**

Direct artifact evidence of a shortfall against a stated expectation (OBS-SYN-RIS-SD-001, OBS-SYN-RIS-SD-002).

Observations: `OBS-SYN-RIS-SD-001`, `OBS-SYN-RIS-SD-002`.

- Follow-up: Ask whether test evidence is held outside the release record, and for which releases.
- Follow-up: Ask whether this was an exception, a data-entry error, or a normal practice.

**`CELL-RIS-SEC` - RIS / Security: MIXED**

Direct evidence supports both a strength and a shortfall in this area; both are reported rather than netted against each other.

Observations: `OBS-SYN-RIS-SEC-001`, `OBS-SYN-RIS-SEC-002`.

- Follow-up: Ask where overdue findings are escalated and whether any acceptance exists off-report.
- Follow-up: Confirm scan coverage against the application inventory.

**`CELL-RIS-DEP` - RIS / Deployment and operations: OBSERVED_GAP**

Direct artifact evidence of a shortfall against a stated expectation (OBS-SYN-RIS-DEP-001).

Observations: `OBS-SYN-RIS-DEP-001`.

- Follow-up: Request the date and outcome of the most recent restoration test, if one exists.

**`CELL-RIS-AI` - RIS / AI readiness: PARTIAL**

Support is interview statement only (OBS-SYN-RIS-AI-001). The practice is stated, not demonstrated; no artifact was produced.

Observations: `OBS-SYN-RIS-AI-001`.

- Follow-up: Ask what inputs were used and whether any team-level guidance exists.

**`CELL-IAM-SD` - IAM / Software development: CONFLICT**

Sources disagree about the same claim (conflict group IAM-SD-REVIEW). The disagreement is retained rather than resolved by the tool.

Observations: `OBS-SYN-IAM-SD-001`, `OBS-SYN-IAM-SD-002`.

- Follow-up: Ask whether review is recorded outside this export for the other three changes.
- Follow-up: Reconcile the stated practice with the three changes that record no reviewer.

**`CELL-IAM-SEC` - IAM / Security: DEMONSTRATED_STRENGTH**

Direct artifact evidence, corroborated across more than one source type (OBS-SYN-IAM-SEC-001).

Observations: `OBS-SYN-IAM-SEC-001`.

- Follow-up: Request the next campaign's export to confirm the four exceptions closed at expiry.

**`CELL-IAM-DEP` - IAM / Deployment and operations: UNKNOWN**

Evidence was identified but none of it resolved to readable material (OBS-SYN-IAM-DEP-001). Nothing is established about this area in either direction.

Observations: `OBS-SYN-IAM-DEP-001`.

Evidence still outstanding: `SRC-SYN-IAM-05`.

- Follow-up: Re-request the August deployment export, or agree an alternative record.

**`CELL-IAM-AI` - IAM / AI readiness: PARTIAL**

Direct evidence establishes context or intent but does not demonstrate a practice in operation.

Observations: `OBS-SYN-IAM-AI-001`.

- Follow-up: Ask what would trigger a start and who would own an evaluation.

## 3. Observable handling of missing and malformed input

0 rejected, 2 degraded, 1 noted. No input was discarded silently; every row below carries its locator.

| # | Severity | Reason | Record | Locator | Effect |
| --- | --- | --- | --- | --- | --- |
| 1 | NOTE | `INT_NO_CLAIM` | `INT-SYN-IAM-03` | OBS-SYN-IAM-DEP-001 | contributes no support; the cited evidence remains outstanding |
| 2 | DEGRADE | `OBS_UNRESOLVED_SOURCE` | `OBS-SYN-IAM-DEP-001` | SRC-SYN-IAM-05#whole file | citation retained but carries no evidentiary weight |
| 3 | DEGRADE | `SRC_MISSING` | `SRC-SYN-IAM-05` | iam/iam-deploy-log-2026-08.csv | retained as UNRESOLVED; cannot support any observation |

## 4. What this rehearsal does not establish

- Nothing here is a University of Iowa finding, record or measurement. Every organization, document, number and quotation is fictional.
- No maturity score, rating, percentile, certification or compliance verdict is produced anywhere in this package, and no individual's performance is assessed.
- A cell reading `UNKNOWN` records that the assessment lacks evidence. It is not a statement that the practice is absent.

## 5. University inputs still UNKNOWN

- Which real University applications, platforms and shared services are in RFQ scope, and who owns each lifecycle stage - UNKNOWN.
- Which real records the University can release as evidence, in what form, and with what retention constraint - UNKNOWN.
- Which roles are available for interview and in what window - UNKNOWN.
- Whether the four assessment areas map to the University's own internal division of work - UNKNOWN.
- Every quantity in this package is fictional. No real deployment count, account count, finding count or release count has been observed - UNKNOWN.
