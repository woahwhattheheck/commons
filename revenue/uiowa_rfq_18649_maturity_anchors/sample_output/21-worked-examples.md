# 21 - Worked examples: Worked examples: one scale, four assessment areas

> SYNTHETIC EXAMPLES using OUR PROPOSED ANCHOR FRAMEWORK. Fictional groups, fictional evidence. Not University of Iowa findings, not an industry standard, not a certification scale.

**These anchors are our proposed framework, drafted for RFQ 18649 preparation.** They are not a University of Iowa finding, not an industry standard, and not a certification scale. They are offered for discussion and expected to be renamed and adjusted.

The same scale applied in all four areas, including every state that is not a level.

| Criterion | Area | Service | Level | Pattern | Why not higher |
|---|---|---|---|---|---|
| **DEV-01** | development | ESS | 4 Repeatable | `repeatable_practice` | no outcome measure is supplied; knowing the practice runs is not knowing it works |
| **DEV-02** | development | RIS | 2 Defined on paper | `policy_only_claim` | the intended practice is stated, but nothing records the work itself. The strongest evidence supplied is policy or procedure document. A document states an intention. It is not evidence that anything happened, and a second document is not evidence either. |
| **SEC-01** | security | IAM | 5 Measured and adjusted | `repeatable_practice` | top of the scale; every anchor is evidenced |
| **SEC-02** | security | RIS | 3 Practised | `isolated_success` | one instance is evidenced; nothing shows the practice repeating across a stated window |
| **DEP-01** | deployment | ESS | 3 Practised | `repeatable_practice` | repeated records exist but none covers more than one person or service, so the practice cannot yet be distinguished from one individual's habit |
| **DEP-02** | deployment | RIS | 3 Practised | `repeatable_practice` | repetition is evidenced but no departures from the procedure are recorded anywhere; a process with no visible exceptions is usually one whose exceptions are not being written down |
| **DEP-03** | deployment | IAM | - `insufficient_evidence` | `missing_evidence` | no evidence was supplied, so no level is supportable |
| **AI-01** | ai_readiness | ESS | 4 Repeatable | `repeatable_practice` | an outcome measure is cited but its definition, period or denominator is not given, so it cannot be read |
| **AI-02** | ai_readiness | RIS | - `not_applicable` | `not_applicable` | not on the scale |
| **AI-03** | ai_readiness | IAM | - `unassessed` | `unassessed` | not on the scale |
| **AI-04** | ai_readiness | ESS | 4 Repeatable | `repeatable_practice` | the measure exists and is defined, but no change is evidenced as following from it; measuring is not adjusting |
| **DEV-03** | development | IAM | 1 Absent | `policy_only_claim` | no evidence states an intended practice that more than one person recognises; the descriptions supplied do not agree with each other |

## Each example in full

### DEV-01 - development / ESS

- **Result:** 4 (Repeatable)
- **Pattern:** Repeatable practice - the work is recorded happening more than once.
- **Why not higher:** no outcome measure is supplied; knowing the practice runs is not knowing it works
- **What would raise it:** A measure of whether the practice achieves what it is for, with its definition, period and denominator stated.
- **Note:** REPEATABLE PRACTICE. Code review runs across the team over a stated window, with exceptions written down.
- **Evidence supplied:**
  - `policy_document` (ceiling 2) - ESS engineering standard v3.1 s4 (fictional)
  - `repeated_instances` (ceiling 4) - Sampled merge records, 24 fictional changes, Jan-Mar window - 24 instances - covers more than one person or service - exceptions recorded

### DEV-02 - development / RIS

- **Result:** 2 (Defined on paper)
- **Pattern:** Claim without a practice record - the practice is asserted, in a document or an interview, but nothing records the work itself.
- **Why not higher:** the intended practice is stated, but nothing records the work itself. The strongest evidence supplied is policy or procedure document. A document states an intention. It is not evidence that anything happened, and a second document is not evidence either.
- **What would raise it:** At least one real instance of the practice being followed, with a record that is not the procedure document itself.
- **Note:** POLICY-ONLY CLAIM. Three documents, zero records of the work. The cap is the point: volume of paperwork does not move the level.
- **Evidence supplied:**
  - `policy_document` (ceiling 2) - RIS development handbook v2 (fictional)
  - `policy_document` (ceiling 2) - RIS branching guide (fictional)
  - `policy_document` (ceiling 2) - RIS review checklist template (fictional)
  - `interview_statement` (ceiling 2) - Interview, RIS lead, fictional

### SEC-01 - security / IAM

- **Result:** 5 (Measured and adjusted)
- **Pattern:** Repeatable practice - the work is recorded happening more than once.
- **Why not higher:** top of the scale; every anchor is evidenced
- **What would raise it:** This is the top of the scale. It is not a destination every practice should reach; cost has to justify it.
- **Note:** MEASURED AND ADJUSTED. An outcome measure with a stated denominator, reviewed, and a change evidenced as following from it.
- **Evidence supplied:**
  - `policy_document` (ceiling 2) - IAM access review procedure v5 (fictional)
  - `repeated_instances` (ceiling 4) - Access review records, 4 fictional quarterly cycles - 4 instances - covers more than one person or service - exceptions recorded
  - `outcome_measure` (ceiling 5) - Fictional access-review completion measure, Q1-Q4 - measure defined - change evidenced

### SEC-02 - security / RIS

- **Result:** 3 (Practised)
- **Pattern:** Isolated success - one real instance, nothing showing it repeats.
- **Why not higher:** one instance is evidenced; nothing shows the practice repeating across a stated window
- **What would raise it:** Repeated instances across a stated window, covering more than one person or service, with exceptions visible rather than absent.
- **Note:** ISOLATED SUCCESS. One real, well-evidenced instance. Genuine, and not yet a practice.
- **Evidence supplied:**
  - `single_instance` (ceiling 3) - Dependency remediation record, one fictional incident

### DEP-01 - deployment / ESS

- **Result:** 3 (Practised)
- **Pattern:** Repeatable practice - the work is recorded happening more than once.
- **Why not higher:** repeated records exist but none covers more than one person or service, so the practice cannot yet be distinguished from one individual's habit
- **What would raise it:** Repeated instances across a stated window, covering more than one person or service, with exceptions visible rather than absent.
- **Note:** CAPPED BELOW 4. Repetition is evidenced, but every record belongs to one engineer, so the practice cannot be told apart from one person's habit.
- **Evidence supplied:**
  - `policy_document` (ceiling 2) - ESS release procedure v2 (fictional)
  - `repeated_instances` (ceiling 4) - Release records, 11 fictional releases - 11 instances - exceptions recorded

### DEP-02 - deployment / RIS

- **Result:** 3 (Practised)
- **Pattern:** Repeatable practice - the work is recorded happening more than once.
- **Why not higher:** repetition is evidenced but no departures from the procedure are recorded anywhere; a process with no visible exceptions is usually one whose exceptions are not being written down
- **What would raise it:** Repeated instances across a stated window, covering more than one person or service, with exceptions visible rather than absent.
- **Note:** CAPPED BELOW 4 for the other reason: repetition across people, but no exception is recorded anywhere across 18 releases.
- **Evidence supplied:**
  - `repeated_instances` (ceiling 4) - Release records, 18 fictional releases - 18 instances - covers more than one person or service

### DEP-03 - deployment / IAM

- **Result:** not on the scale - `insufficient_evidence`
- **Pattern:** Missing evidence - nothing was supplied. Not a low level.
- **Why not higher:** no evidence was supplied, so no level is supportable
- **What would raise it:** Any record of the intended practice or of the work itself.
- **Note:** MISSING EVIDENCE. Assessed, nothing supplied. Not level 1.
- **Evidence supplied:** none

### AI-01 - ai_readiness / ESS

- **Result:** 4 (Repeatable)
- **Pattern:** Repeatable practice - the work is recorded happening more than once.
- **Why not higher:** an outcome measure is cited but its definition, period or denominator is not given, so it cannot be read
- **What would raise it:** A measure of whether the practice achieves what it is for, with its definition, period and denominator stated.
- **Note:** CAPPED BELOW 5. The measure is cited but its denominator is never stated, so it cannot be read.
- **Evidence supplied:**
  - `repeated_instances` (ceiling 4) - Assisted-change records, 9 fictional changes - 9 instances - covers more than one person or service - exceptions recorded
  - `outcome_measure` (ceiling 5) - Fictional productivity claim in a slide

### AI-02 - ai_readiness / RIS

- **Result:** not on the scale - `not_applicable`
- **Pattern:** Not applicable - the criterion has no subject in this group.
- **Why not higher:** not on the scale
- **Note:** NOT APPLICABLE. A fact about how this fictional group operates, not a gap in our evidence.
- **Evidence supplied:** none

### AI-03 - ai_readiness / IAM

- **Result:** not on the scale - `unassessed`
- **Pattern:** Not assessed - outside the agreed scope this round.
- **Why not higher:** not on the scale
- **Note:** UNASSESSED. Outside the agreed scope for this fictional group in this round.
- **Evidence supplied:** none

### AI-04 - ai_readiness / ESS

- **Result:** 4 (Repeatable)
- **Pattern:** Repeatable practice - the work is recorded happening more than once.
- **Why not higher:** the measure exists and is defined, but no change is evidenced as following from it; measuring is not adjusting
- **What would raise it:** A measure of whether the practice achieves what it is for, with its definition, period and denominator stated.
- **Note:** CAPPED BELOW 5 for the other reason: the measure is properly defined, but nothing changed as a result of it.
- **Evidence supplied:**
  - `repeated_instances` (ceiling 4) - Review records, 6 fictional cycles - 6 instances - covers more than one person or service - exceptions recorded
  - `outcome_measure` (ceiling 5) - Fictional acceptance-rate measure, stated definition/period/denominator - measure defined

### DEV-03 - development / IAM

- **Result:** 1 (Absent)
- **Pattern:** Claim without a practice record - the practice is asserted, in a document or an interview, but nothing records the work itself.
- **Why not higher:** no evidence states an intended practice that more than one person recognises; the descriptions supplied do not agree with each other
- **What would raise it:** A description of the intended practice that more than one person recognises, written or not.
- **Note:** LEVEL 1. A procedure exists nowhere and descriptions disagree.
- **Evidence supplied:**
  - `interview_statement` (ceiling 2) - Interviews, two fictional IAM engineers
