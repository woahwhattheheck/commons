# University of Iowa RFQ 18649 - Assessment Report (SYNTHETIC SAMPLE)

> **SYNTHETIC EXAMPLE - NOT A UNIVERSITY FINDING.** Every group, finding, identifier, date and number below is fiction, written to exercise the report structure. Nothing here describes the University of Iowa.

**Status:** SYNTHETIC SAMPLE  
**Report structure:** `uiowa-rfq-18649-report-structure-v1`  
**Purpose:** demonstrate that the structure accepts the planned matrix and register outputs and renders a complete report from them.

## Scope boundary

This assessment is not a formal audit and issues no compliance determination, certification or attestation. No statement rates, ranks or evaluates a named individual. No vendor selection or product purchase is recommended.

---

## 1. Executive Summary

Twelve group-by-area cells were in scope. 11 were reached; 5 are supported by direct current evidence, 5 are partial or carry conflicting evidence, and 1 could not be assessed with the evidence supplied.

- **Holds up.** Merges to the two sampled ESS repositories require a passing build-and-test status check and at least one approving review; the configuration export and the pull-request sample agree. (FND-SYN-ESS-SD-001, confidence MODERATE).
- **Holds up.** Production deployments in the sampled window were recorded with a change reference, an approver and a rollback note. (FND-SYN-ESS-DEP-001, confidence MODERATE).
- **Does not yet hold up.** A dependency-scanning step runs in the sampled pipelines, but no record was observed of how findings are triaged or closed. (FND-SYN-ESS-SEC-001, confidence LOW). Pipeline definition observed; no triage or closure records reviewed.
- **Does not yet hold up.** Assisted coding tools are in informal use by some ESS developers; no group-level guidance on review of generated code was observed. (FND-SYN-ESS-AI-001, confidence LOW). Two interview statements; no policy, inventory or usage record reviewed.
- **Not assessed.** IAM/AI (FND-SYN-IAM-AI-001): No source of any type was reviewed for this cell. This is a statement about the evidence collected, not about the group. Resolving question: Schedule the AI-readiness session with the IAM group, or record the cell as out of scope by agreement.

Proposed in the first 90 days:

- REC-SYN-ESS-SD-001: Produce an authoritative inventory of in-scope ESS repositories and their protection settings, so coverage can be stated for the group rather than for a sample. (from FND-SYN-ESS-SD-001)
- REC-SYN-IAM-DEP-001: Identify the system of record for emergency identity changes and confirm whether the supplied export is complete for that path. Investigate first; do not change the process on the current evidence. (from FND-SYN-IAM-DEP-001)
- REC-SYN-CROSS-SEC-001: For each access-review requirement, record which enumerated population it applies to and which query establishes that population. (from FND-SYN-RIS-SEC-001;FND-SYN-IAM-SEC-001)

---

## 2. Engagement Scope and Assessment Areas

In scope: ESS, RIS and IAM across software development (SD), security (SEC), deployment and operations (DEP), and AI readiness (AI) - twelve cells.

| group | areas reached | areas not assessed |
|---|---|---|
| ESS | AI, DEP, SD, SEC | none |
| RIS | DEP, SD, SEC | none |
| IAM | DEP, SD, SEC | AI |

---

## 3. Methodology

16 synthetic evidence items were collected across 7 source types.

| source type | items |
|---|---|
| change_records | 5 |
| configuration_export | 4 |
| interview | 3 |
| inventory_query | 1 |
| limited_search | 1 |
| policy | 1 |
| procedure | 1 |

Framework references were used as interview and artifact prompts. A framework practice is a prompt, not a criterion, and no cell is scored against one.

---

## 4. Evidence Standard, Confidence and Limitations

Confidence is recorded on five dimensions and is never averaged into a single number. The dimensions are reported alongside each evidence item in Appendix A.

| confidence | evidence items | meaning |
|---|---|---|
| HIGH | 2 | direct, current, representative, corroborated |
| LOW | 5 | indirect, stale, single-source, or uncorroborated |
| MODERATE | 6 | direct but narrow, or current without independent corroboration |
| NOT_EVIDENCED | 1 | no source was observed for the claim |
| UNRESOLVED | 2 | material sources disagree and the conflict is open |

`NOT_EVIDENCED` means no source was reviewed. It is not a negative finding about the group, and it is not a zero.

---

## 5. Peer and Published-Practice Context

| peer | measure | value | denominator/scope | comparison status | note |
|---|---|---|---|---|---|
| Synthetic Public R1 University A | Published minimum lead time for highest-risk changes | 10 business days | Highest-risk changes; raw count not stated | context_only | A lead-time policy, not observed deployment performance. The risk model and the business-day clock would both have to be matched before any comparison. |
| Synthetic Public R1 University B | Privileged accounts with a second factor | 100% | Denominator not published | not_comparable_without_normalization | Without the published denominator and the definition of 'privileged', this figure cannot be set beside the enumerated population in FND-SYN-IAM-SEC-001. |
| Synthetic Public R1 University C | Annual privileged-access review completion | Reported as routine | Not stated | historical_not_current_benchmark | Seven years old and narrative rather than measured. Useful as context for what peers describe, not as a current benchmark. |

Every row above carries its own comparison status. Rows marked `context_only` or `not_comparable_without_normalization` cannot support a comparison and are presented as context. No percentile, ranking or standing against peers is stated anywhere in this report.

---

## 6. Current-State Matrix

| group \ area | SD software dev | SEC security | DEP deployment/ops | AI readiness |
|---|---|---|---|---|
| ESS | SUPPORTED (MODERATE) FND-SYN-ESS-SD-001 | PARTIAL (LOW) FND-SYN-ESS-SEC-001 | SUPPORTED (MODERATE) FND-SYN-ESS-DEP-001 | PARTIAL (LOW) FND-SYN-ESS-AI-001 |
| RIS | PARTIAL (LOW) FND-SYN-RIS-SD-001 | PARTIAL (LOW) FND-SYN-RIS-SEC-001 | SUPPORTED (MODERATE) FND-SYN-RIS-DEP-001 | UNKNOWN - not assessed |
| IAM | SUPPORTED (MODERATE) FND-SYN-IAM-SD-001 | SUPPORTED (HIGH) FND-SYN-IAM-SEC-001 | CONFLICT (UNRESOLVED) FND-SYN-IAM-DEP-001 | UNKNOWN (NOT_EVIDENCED) FND-SYN-IAM-AI-001 |

*10 of 12 cells carry an assessed status. Cells shown as `UNKNOWN - not assessed` are a statement about the evidence collected, not about the group, and are excluded from every count of assessed cells rather than counted as zero.*

---

## 7.1. Group Findings - Enterprise Systems and Services (ESS)

### FND-SYN-ESS-SD-001 - ESS / SD (SUPPORTED, confidence MODERATE)

Merges to the two sampled ESS repositories require a passing build-and-test status check and at least one approving review; the configuration export and the pull-request sample agree.

*Scope limit:* Two of an unstated number of ESS repositories; repository population was never enumerated.

| evidence | type | claim | directness | recency | representativeness | corroboration | confidence |
|---|---|---|---|---|---|---|---|
| EV-SYN-ESS-SD-CFG-001 | configuration_export | Repository A requires a successful build-and-test status check and one approving review before merge | DIRECT | CURRENT | SINGLE | INDEPENDENT | MODERATE |
| EV-SYN-ESS-SD-PR-002 | change_records | All 22 sampled merges to repositories A and B carry a passing check and an approving reviewer | DIRECT | CURRENT | SAMPLED | INDEPENDENT | MODERATE |
| EV-SYN-ESS-SD-INT-003 | interview | Participant states review before merge is required across ESS | INDIRECT | CURRENT | SINGLE | SAME_SYSTEM | LOW |

*Open question:* Provide an authoritative repository inventory so coverage can be stated for the group rather than for two repositories.

### FND-SYN-ESS-SEC-001 - ESS / SEC (PARTIAL, confidence LOW)

A dependency-scanning step runs in the sampled pipelines, but no record was observed of how findings are triaged or closed.

*Scope limit:* Pipeline definition observed; no triage or closure records reviewed.

| evidence | type | claim | directness | recency | representativeness | corroboration | confidence |
|---|---|---|---|---|---|---|---|
| EV-SYN-ESS-SEC-CFG-004 | configuration_export | A dependency-scanning stage is defined in the sampled pipeline | DIRECT | CURRENT | SINGLE | NO_CORROBORATION | LOW |

*Open question:* Supply six months of scanner findings with their disposition, or the queue the team works them from.

### FND-SYN-ESS-DEP-001 - ESS / DEP (SUPPORTED, confidence MODERATE)

Production deployments in the sampled window were recorded with a change reference, an approver and a rollback note.

*Scope limit:* One month of deployment records for one ESS application.

| evidence | type | claim | directness | recency | representativeness | corroboration | confidence |
|---|---|---|---|---|---|---|---|
| EV-SYN-ESS-DEP-CHG-005 | change_records | All 9 production deployments in the window carry a change reference, an approver and a rollback note | DIRECT | CURRENT | POPULATION_BOUNDED | SAME_SYSTEM | MODERATE |

*Open question:* Extend the sample across a release cycle that includes an emergency change.

### FND-SYN-ESS-AI-001 - ESS / AI (PARTIAL, confidence LOW)

Assisted coding tools are in informal use by some ESS developers; no group-level guidance on review of generated code was observed.

*Scope limit:* Two interview statements; no policy, inventory or usage record reviewed.

| evidence | type | claim | directness | recency | representativeness | corroboration | confidence |
|---|---|---|---|---|---|---|---|
| EV-SYN-ESS-AI-INT-006 | interview | Two participants describe informal individual use of assisted coding tools | INDIRECT | CURRENT | SINGLE | NO_CORROBORATION | LOW |

*Open question:* Is there written guidance on reviewing AI-generated code, and who owns it?

---

## 7.2. Group Findings - Research Information Systems (RIS)

### FND-SYN-RIS-SD-001 - RIS / SD (PARTIAL, confidence LOW)

A documented intake-to-release path exists; the one traced change followed it, with the review stage completed after deployment rather than before.

*Scope limit:* A single traced change; the deviation may or may not be typical.

| evidence | type | claim | directness | recency | representativeness | corroboration | confidence |
|---|---|---|---|---|---|---|---|
| EV-SYN-RIS-SD-CHG-007 | change_records | Change RQ-118 records intake, build and deployment; the review sign-off timestamp follows the deployment timestamp | DIRECT | CURRENT | SINGLE | NO_CORROBORATION | MODERATE |
| EV-SYN-RIS-SD-DOC-008 | procedure | The documented procedure places review sign-off before deployment | INDIRECT | AGING | UNKNOWN | CONTRADICTED | LOW |

*Open question:* Trace five further RIS changes, including at least one urgent change, before describing the sequence as usual practice.

### FND-SYN-RIS-SEC-001 - RIS / SEC (PARTIAL, confidence LOW)

A published standard requires annual privileged-access review for research systems. No completed review record was observed for any in-scope RIS system.

*Scope limit:* Policy intent only. Absence of a record in the material supplied is not evidence that the review did not happen.

| evidence | type | claim | directness | recency | representativeness | corroboration | confidence |
|---|---|---|---|---|---|---|---|
| EV-SYN-RIS-SEC-POL-009 | policy | The published standard requires an annual privileged-access review | INDIRECT | STALE | POPULATION_UNKNOWN | NO_CORROBORATION | LOW |
| EV-SYN-RIS-SEC-INV-010 | limited_search | A search of the supplied document share returned no completed privileged-access review for any RIS system | NEAR_DIRECT | CURRENT | POPULATION_UNKNOWN | NO_CORROBORATION | NOT_EVIDENCED |

*Open question:* Provide the most recent completed privileged-access review for two RIS systems, or name the system of record that holds them.

### FND-SYN-RIS-DEP-001 - RIS / DEP (SUPPORTED, confidence MODERATE)

Scheduled maintenance for the sampled RIS service is announced in advance and tracked to a close-out note.

*Scope limit:* Three maintenance events for one service.

| evidence | type | claim | directness | recency | representativeness | corroboration | confidence |
|---|---|---|---|---|---|---|---|
| EV-SYN-RIS-DEP-CHG-011 | change_records | Three maintenance events were announced in advance and each closed with a completion note | DIRECT | CURRENT | POPULATION_BOUNDED | SAME_SYSTEM | MODERATE |

*Open question:* Confirm the same practice holds during the grant-deadline period, when windows are constrained.

---

## 7.3. Group Findings - Identity and Access Management (IAM)

### FND-SYN-IAM-SD-001 - IAM / SD (SUPPORTED, confidence MODERATE)

IAM connector changes are developed in version control with peer review recorded before release.

*Scope limit:* One connector repository over one quarter.

| evidence | type | claim | directness | recency | representativeness | corroboration | confidence |
|---|---|---|---|---|---|---|---|
| EV-SYN-IAM-SD-CFG-012 | configuration_export | The connector repository records an approving review on every merge in the quarter | DIRECT | CURRENT | POPULATION_BOUNDED | NO_CORROBORATION | MODERATE |

*Open question:* Does the same path apply to configuration changes made directly in the vendor console?

### FND-SYN-IAM-SEC-001 - IAM / SEC (SUPPORTED, confidence HIGH)

Privileged administrative access to the identity platform required a second factor for every account in the enumerated population at the time of capture.

*Scope limit:* Bounded inventory query over all 14 privileged accounts at capture time; the completeness of the query is documented.

| evidence | type | claim | directness | recency | representativeness | corroboration | confidence |
|---|---|---|---|---|---|---|---|
| EV-SYN-IAM-SEC-INV-013 | inventory_query | All 14 accounts returned by the privileged-account query have a second factor enrolled | DIRECT | CURRENT | POPULATION_BOUNDED | INDEPENDENT | HIGH |
| EV-SYN-IAM-SEC-CFG-014 | configuration_export | The platform policy requires a second factor for the administrator role | DIRECT | CURRENT | POPULATION_BOUNDED | INDEPENDENT | HIGH |

*Open question:* Re-run the enumeration at engagement close to confirm the population has not changed.

### FND-SYN-IAM-DEP-001 - IAM / DEP (CONFLICT, confidence UNRESOLVED)

Interview statements describe a change record for every production identity change; the change export shows 3 of 14 emergency changes in the window with no linked record.

*Scope limit:* The conflict is unresolved. Either the export is incomplete or the practice has an undocumented exception path; the evidence supplied cannot distinguish the two.

| evidence | type | claim | directness | recency | representativeness | corroboration | confidence |
|---|---|---|---|---|---|---|---|
| EV-SYN-IAM-DEP-INT-015 | interview | Participant states every production identity change gets a change record | INDIRECT | CURRENT | SINGLE | CONTRADICTED | UNRESOLVED |
| EV-SYN-IAM-DEP-CHG-016 | change_records | 3 of 14 emergency identity changes in the window carry no linked change record | DIRECT | CURRENT | POPULATION_UNKNOWN | CONTRADICTED | UNRESOLVED |

*Open question:* Which system of record holds emergency identity changes, and is the supplied export complete for that window?

### FND-SYN-IAM-AI-001 - IAM / AI (UNKNOWN, confidence NOT_EVIDENCED)

Not assessed. No evidence was supplied for AI readiness in IAM within the engagement window.

*Scope limit:* No source of any type was reviewed for this cell. This is a statement about the evidence collected, not about the group.

*No evidence item is registered for this finding - status UNKNOWN.*

*Open question:* Schedule the AI-readiness session with the IAM group, or record the cell as out of scope by agreement.

---

## 8. Cross-Cutting Themes

### THM-SYN-001 - Where a control is enforced by system configuration it is demonstrable; where it depends on a documented expectation it is not yet demonstrated.

*Spans:* ESS;RIS;IAM / SD;SEC  
*Findings:* FND-SYN-ESS-SD-001;FND-SYN-IAM-SEC-001;FND-SYN-RIS-SEC-001;FND-SYN-RIS-SD-001  
*Counter-evidence:* FND-SYN-ESS-DEP-001 is a records-based practice, not a system-enforced control, and is nonetheless supported by a complete month of records.  
*Scope limit:* Rests on four findings, three of which are bounded to one or two services. It does not cover DEP in ESS or any AI cell.

### THM-SYN-002 - Evidence coverage is thinnest where a practice spans a boundary - emergency paths, console-side changes, and work that crosses from one team's system of record into another's.

*Spans:* ESS;IAM / SD;DEP  
*Findings:* FND-SYN-IAM-DEP-001;FND-SYN-ESS-DEP-001;FND-SYN-IAM-SD-001  
*Counter-evidence:* UNKNOWN  
*Scope limit:* Two groups only. RIS was not sampled across an emergency path, so the pattern is not established there.

### THM-SYN-003 - AI readiness is the least evidenced area in this engagement: one cell rests on two interview statements and one was not assessed at all.

*Spans:* ESS;IAM / AI  
*Findings:* FND-SYN-ESS-AI-001;FND-SYN-IAM-AI-001  
*Counter-evidence:* UNKNOWN  
*Scope limit:* This is a statement about evidence collected, not about AI capability in any group. RIS/AI was not reached at all and is absent from the matrix.

Each theme names the individual findings it spans. A theme is a reading of those findings, not a replacement for them; the findings remain the record.

---

## 9. Recommendations by Group and Department

### ESS

| id | recommendation | from findings | rationale | resource note | depends on |
|---|---|---|---|---|---|
| REC-SYN-ESS-SD-001 | Produce an authoritative inventory of in-scope ESS repositories and their protection settings, so coverage can be stated for the group rather than for a sample. | FND-SYN-ESS-SD-001 | The supported finding rests on two repositories out of an unenumerated population; the inventory converts a sample statement into a population statement. | One analyst, estimated under a week. Estimate supplied by the assessment team, not measured. | UNKNOWN |
| REC-SYN-ESS-AI-001 | Decide and write down how generated code is reviewed before it reaches a production branch, and name the owner of that guidance. | FND-SYN-ESS-AI-001 | Informal use is already happening; the gap is written guidance and an owner, not tooling. | Guidance drafting only. No tool, licence or purchase is implied by this recommendation. | REC-SYN-ESS-SD-001 |

### RIS

| id | recommendation | from findings | rationale | resource note | depends on |
|---|---|---|---|---|---|
| REC-SYN-RIS-SEC-001 | Establish where completed privileged-access reviews are retained for research systems, and make the retention location part of the standard itself. | FND-SYN-RIS-SEC-001 | The standard states the requirement but names no system of record, so a completed review cannot be located even when it has been done. | UNKNOWN - depends on whether a system of record already exists. | REC-SYN-CROSS-SEC-001 |

### IAM

| id | recommendation | from findings | rationale | resource note | depends on |
|---|---|---|---|---|---|
| REC-SYN-IAM-DEP-001 | Identify the system of record for emergency identity changes and confirm whether the supplied export is complete for that path. Investigate first; do not change the process on the current evidence. | FND-SYN-IAM-DEP-001 | The interview and the export disagree and the evidence cannot distinguish an incomplete export from an undocumented exception path. Acting on either reading now would be acting on a guess. | Half a day of IAM operations time to identify the system of record. | UNKNOWN |
| REC-SYN-IAM-AI-001 | Hold the AI-readiness session with the IAM group that the engagement window did not accommodate, or record the cell as out of scope by agreement. | FND-SYN-IAM-AI-001 | The cell was not assessed. Until it is, there is no finding to sequence a recommendation against. | UNKNOWN - cannot be estimated before the cell is assessed. | UNKNOWN |

### CROSS

| id | recommendation | from findings | rationale | resource note | depends on |
|---|---|---|---|---|---|
| REC-SYN-CROSS-SEC-001 | For each access-review requirement, record which enumerated population it applies to and which query establishes that population. | FND-SYN-RIS-SEC-001;FND-SYN-IAM-SEC-001 | The one HIGH-confidence finding in this engagement is the one with a documented enumerated population. Naming the population is what made it checkable. | Estimated two days across the security and identity groups. | UNKNOWN |

Each recommendation names the findings that motivate it and does not inherit their confidence. Recommendations describe capabilities and decisions; selecting or purchasing a product is the University's own process.

---

## 10. Prioritization and Phasing

### 0-90 days

| id | recommendation | depends on | resource note |
|---|---|---|---|
| REC-SYN-ESS-SD-001 | Produce an authoritative inventory of in-scope ESS repositories and their protection settings, so coverage can be stated for the group rather than for a sample. | UNKNOWN | One analyst, estimated under a week. Estimate supplied by the assessment team, not measured. |
| REC-SYN-IAM-DEP-001 | Identify the system of record for emergency identity changes and confirm whether the supplied export is complete for that path. Investigate first; do not change the process on the current evidence. | UNKNOWN | Half a day of IAM operations time to identify the system of record. |
| REC-SYN-CROSS-SEC-001 | For each access-review requirement, record which enumerated population it applies to and which query establishes that population. | UNKNOWN | Estimated two days across the security and identity groups. |

### 90-180 days

| id | recommendation | depends on | resource note |
|---|---|---|---|
| REC-SYN-RIS-SEC-001 | Establish where completed privileged-access reviews are retained for research systems, and make the retention location part of the standard itself. | REC-SYN-CROSS-SEC-001 | UNKNOWN - depends on whether a system of record already exists. |
| REC-SYN-ESS-AI-001 | Decide and write down how generated code is reviewed before it reaches a production branch, and name the owner of that guidance. | REC-SYN-ESS-SD-001 | Guidance drafting only. No tool, licence or purchase is implied by this recommendation. |

### 180+ days

*No items.*

### Unsequenced - estimate missing

| id | recommendation | depends on | resource note |
|---|---|---|---|
| REC-SYN-IAM-AI-001 | Hold the AI-readiness session with the IAM group that the engagement window did not accommodate, or record the cell as out of scope by agreement. | UNKNOWN | UNKNOWN - cannot be estimated before the cell is assessed. |

An item whose horizon is `UNKNOWN` sits in the unsequenced bucket with the missing input named. It is not defaulted into a later phase, which would present a guess as a plan.

---

## A. Appendix A - Supporting Evidence

| evidence | finding | group/area | type | source | captured | represents | claim | scope limit | state | confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| EV-SYN-ESS-SD-CFG-001 | FND-SYN-ESS-SD-001 | ESS/SD | configuration_export | synthetic-ess-repo-A-branch-rule.json | 2026-09-08T13:10:00Z | 2026-09-08 | Repository A requires a successful build-and-test status check and one approving review before merge | One ESS repository only | SUPPORTING | MODERATE |
| EV-SYN-ESS-SD-PR-002 | FND-SYN-ESS-SD-001 | ESS/SD | change_records | synthetic-ess-pr-sample-2026Q3.csv | 2026-09-08T13:40:00Z | 2026-07-01/2026-09-05 | All 22 sampled merges to repositories A and B carry a passing check and an approving reviewer | Sampled merges, not the full merge population | SUPPORTING | MODERATE |
| EV-SYN-ESS-SD-INT-003 | FND-SYN-ESS-SD-001 | ESS/SD | interview | synthetic-interview-ess-02 | 2026-09-04T15:00:00Z | 2026-09-04 | Participant states review before merge is required across ESS | One participant; participant perspective, not group-wide practice | SUPPORTING | LOW |
| EV-SYN-ESS-SEC-CFG-004 | FND-SYN-ESS-SEC-001 | ESS/SEC | configuration_export | synthetic-ess-pipeline-def.yaml | 2026-09-08T14:05:00Z | 2026-09-08 | A dependency-scanning stage is defined in the sampled pipeline | Establishes that the stage runs; establishes nothing about how findings are handled | SUPPORTING | LOW |
| EV-SYN-ESS-DEP-CHG-005 | FND-SYN-ESS-DEP-001 | ESS/DEP | change_records | synthetic-ess-deploy-log-2026-08.csv | 2026-09-09T10:00:00Z | 2026-08-01/2026-08-31 | All 9 production deployments in the window carry a change reference, an approver and a rollback note | One month, one application; the window contains no emergency change | SUPPORTING | MODERATE |
| EV-SYN-ESS-AI-INT-006 | FND-SYN-ESS-AI-001 | ESS/AI | interview | synthetic-interview-ess-05 | 2026-09-05T11:00:00Z | 2026-09-05 | Two participants describe informal individual use of assisted coding tools | Participant perspective; no usage record or guidance document reviewed | SUPPORTING | LOW |
| EV-SYN-RIS-SD-CHG-007 | FND-SYN-RIS-SD-001 | RIS/SD | change_records | synthetic-ris-change-RQ-118 | 2026-09-10T09:30:00Z | 2026-08-19/2026-08-27 | Change RQ-118 records intake, build and deployment; the review sign-off timestamp follows the deployment timestamp | A single change; establishes this change's sequence only | SUPPORTING | MODERATE |
| EV-SYN-RIS-SD-DOC-008 | FND-SYN-RIS-SD-001 | RIS/SD | procedure | synthetic-ris-release-procedure-v2.md | 2026-09-10T09:45:00Z | 2025-11-01 | The documented procedure places review sign-off before deployment | Documented intent; does not establish what the team does | CONFLICTING | LOW |
| EV-SYN-RIS-SEC-POL-009 | FND-SYN-RIS-SEC-001 | RIS/SEC | policy | synthetic-research-systems-standard-v1.pdf | 2026-09-11T14:20:00Z | 2025-03-01 | The published standard requires an annual privileged-access review | Policy intent; implementation not demonstrated | SUPPORTING | LOW |
| EV-SYN-RIS-SEC-INV-010 | FND-SYN-RIS-SEC-001 | RIS/SEC | limited_search | synthetic-ris-document-share-search | 2026-09-11T15:00:00Z | 2026-09-11 | A search of the supplied document share returned no completed privileged-access review for any RIS system | Bounded to the material supplied. Absence here is not evidence the review did not occur elsewhere. | NO_EVIDENCE_OBSERVED | NOT_EVIDENCED |
| EV-SYN-RIS-DEP-CHG-011 | FND-SYN-RIS-DEP-001 | RIS/DEP | change_records | synthetic-ris-maintenance-2026Q3.csv | 2026-09-11T16:10:00Z | 2026-07-01/2026-09-10 | Three maintenance events were announced in advance and each closed with a completion note | Three events for one service | SUPPORTING | MODERATE |
| EV-SYN-IAM-SD-CFG-012 | FND-SYN-IAM-SD-001 | IAM/SD | configuration_export | synthetic-iam-connector-repo-rules.json | 2026-09-12T10:00:00Z | 2026-09-12 | The connector repository records an approving review on every merge in the quarter | One repository; console-side configuration changes are outside version control | SUPPORTING | MODERATE |
| EV-SYN-IAM-SEC-INV-013 | FND-SYN-IAM-SEC-001 | IAM/SEC | inventory_query | synthetic-iam-privileged-account-query | 2026-09-12T11:30:00Z | 2026-09-12 | All 14 accounts returned by the privileged-account query have a second factor enrolled | Complete for the queried universe at capture time; the query definition is recorded | SUPPORTING | HIGH |
| EV-SYN-IAM-SEC-CFG-014 | FND-SYN-IAM-SEC-001 | IAM/SEC | configuration_export | synthetic-iam-policy-export.json | 2026-09-12T11:45:00Z | 2026-09-12 | The platform policy requires a second factor for the administrator role | Configuration state at capture time | SUPPORTING | HIGH |
| EV-SYN-IAM-DEP-INT-015 | FND-SYN-IAM-DEP-001 | IAM/DEP | interview | synthetic-interview-iam-03 | 2026-09-05T13:00:00Z | 2026-09-05 | Participant states every production identity change gets a change record | Participant perspective | CONFLICTING | UNRESOLVED |
| EV-SYN-IAM-DEP-CHG-016 | FND-SYN-IAM-DEP-001 | IAM/DEP | change_records | synthetic-iam-change-export-2026Q3.csv | 2026-09-12T12:15:00Z | 2026-07-01/2026-09-10 | 3 of 14 emergency identity changes in the window carry no linked change record | Completeness of the export for emergency changes is not established | CONFLICTING | UNRESOLVED |

*Findings with no registered evidence item: FND-SYN-IAM-AI-001. These are carried as UNKNOWN in the matrix and are listed in Appendix C.*

---

## B. Appendix B - Source and Version Register

*In a real engagement this appendix is rendered from the landed source and version registers (`source_version_register`, `policy_context_register`), pinning every framework to the version actually used. This synthetic sample does not restate those registers.*

---

## C. Appendix C - Open Questions and Unresolved Inputs

| finding | group/area | status | what is unresolved | what would resolve it |
|---|---|---|---|---|
| FND-SYN-ESS-SEC-001 | ESS/SEC | PARTIAL | Pipeline definition observed; no triage or closure records reviewed. | Supply six months of scanner findings with their disposition, or the queue the team works them from. |
| FND-SYN-ESS-AI-001 | ESS/AI | PARTIAL | Two interview statements; no policy, inventory or usage record reviewed. | Is there written guidance on reviewing AI-generated code, and who owns it? |
| FND-SYN-RIS-SD-001 | RIS/SD | PARTIAL | A single traced change; the deviation may or may not be typical. | Trace five further RIS changes, including at least one urgent change, before describing the sequence as usual practice. |
| FND-SYN-RIS-SEC-001 | RIS/SEC | PARTIAL | Policy intent only. Absence of a record in the material supplied is not evidence that the review did not happen. | Provide the most recent completed privileged-access review for two RIS systems, or name the system of record that holds them. |
| FND-SYN-IAM-DEP-001 | IAM/DEP | CONFLICT | The conflict is unresolved. Either the export is incomplete or the practice has an undocumented exception path; the evidence supplied cannot distinguish the two. | Which system of record holds emergency identity changes, and is the supplied export complete for that window? |
| FND-SYN-IAM-AI-001 | IAM/AI | UNKNOWN | No source of any type was reviewed for this cell. This is a statement about the evidence collected, not about the group. | Schedule the AI-readiness session with the IAM group, or record the cell as out of scope by agreement. |

This appendix exists so that an absent input never has to become a zero, a pass or a rating anywhere else in the report.

---
