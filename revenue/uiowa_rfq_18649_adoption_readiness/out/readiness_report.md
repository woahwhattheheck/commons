# Organizational AI adoption readiness - worked assessment

**Work order:** UIOWA-077  
**Instrument:** `UIOWA-077-AIR-v1`  
**Option catalog:** `UIOWA-077-OPTIONS-v1`  
**Content digest:** `9a125e4e1bfca78387f5efa4ced28cb6932bba34bd957fc1e163ff3693790db2`

> All team records in this run are SYNTHETIC and labelled fiction. No figure here is a measured University value, and no statement here is a University finding.

> This artifact produces capability STATES and COUNTS. It does not produce a composite score, a maturity level, a peer percentile, a certification or compliance claim, or any assessment of an individual employee.

**Reading `UNKNOWN`.** `UNKNOWN` means the evidence to state a capability was not available - too few contributors, or too few observed indicators. It is not a low result, it is excluded from every denominator, and it produces an evidence request rather than a development option.

**Floors in this run:** at least 3 contributors per team and at least 2 observed indicators per dimension.

## T-ESS - Enterprise Support Services (synthetic)

Contributors represented: **7**

Dimensions with a state: **5 of 6**. UNKNOWN: **1** (excluded from every denominator). Of those assessed - established 2, emerging 2, absent 1.

| dimension | state | why | evidence looked at |
|---|---|---|---|
| AI literacy | **EMERGING** | Resolved from 3 observed indicator(s). | SYNTHETIC interview note: team says people ask in the team channel; no consultable page named · SYNTHETIC wiki page 'Assistive tools in ESS', last reviewed 2026-04-11 · SYNTHETIC wiki searched for a failure-mode note; none present |
| Practical training | **ESTABLISHED** | Resolved from 2 observed indicator(s). | SYNTHETIC onboarding checklist v3, section 'assisted ticket triage' · SYNTHETIC training roster FY-S, sessions 4-6, tasks 'ticket triage' and 'macro drafting' |
| Workflow fit | **UNKNOWN** | No indicator for this dimension has supplied evidence. | - |
| Available support | **ESTABLISHED** | Resolved from 2 observed indicator(s). | SYNTHETIC escalation matrix page, revision 7 · SYNTHETIC queue routing rule AIHELP-01, owner recorded as a role |
| Knowledge sharing | **EMERGING** | Resolved from 2 observed indicator(s). | SYNTHETIC channel #ess-tips, 22 pinned entries, no review dates · SYNTHETIC entries inspected; none carries a last-checked date |
| Capacity to evaluate new approaches | **ABSENT** | Resolved from 3 observed indicator(s). | SYNTHETIC change log searched for an evaluation note; none present · SYNTHETIC interview note: team could not name who can stop an adopted approach · SYNTHETIC no acceptance check or known-answer set found |

### Evidence needed before any plan can be made here

**Workflow fit** - No indicator for this dimension has supplied evidence.

*Validating evidence:* The artifacts listed below, or a written statement that the practice does not exist here.

- `FIT-1` - Which recurring workflows currently include an assisted step, and at which point in the procedure?  
  *Ask to see:* The procedure document showing the step.
- `FIT-2` - Where was an assisted step tried and then narrowed or removed?  
  *Ask to see:* The change note, ticket, or decision record.
- `FIT-3` - Which steps are explicitly excluded from assistance, and on what basis?  
  *Ask to see:* The written exclusion and its stated reason.

### Capability-development options

#### 0-90 days

**`OPT-EVAL-01`** (evaluation_capacity, currently ABSENT)

- *Capability gained:* A written evaluation note for any new approach trialled, recording the task, the check applied, the result, and the keep-or-drop decision.
- *Staff effort:* 8-16 person_hours (one_time)
- *Assumption basis:* Assumes a one-page format agreed once and then reused; excludes the effort of running any particular trial, which belongs to that trial.
- *Validating evidence:* The team's existing change-note or decision-record format, if any, and the recorded effort of adopting the last such format.
- *Dependencies:* none
- *Observable indicator:* At least one completed evaluation note exists naming the task, the check applied, and the decision taken.

**`OPT-LIT-01`** (ai_literacy, currently EMERGING)

- *Capability gained:* A shared written boundary the team can cite: what these tools are used for here, what they are not used for, and where to check when a request sits on the line.
- *Staff effort:* 12-24 person_hours (one_time)
- *Assumption basis:* Assumes one drafting pass by a team lead plus one review round with the team, on a team that already has a place to publish internal guidance. Excludes any institution-wide policy negotiation.
- *Validating evidence:* Time recorded against the two most recent comparable internal guidance pages this unit produced, and confirmation that an internal publishing location already exists.
- *Dependencies:* none
- *Observable indicator:* A dated guidance page exists and at least one ticket or thread cites it when resolving a borderline request.

**`OPT-SHR-01`** (knowledge_sharing, currently EMERGING)

- *Capability gained:* A register where a working approach is written down with the task it applies to, so it is reusable by someone who was not in the conversation.
- *Staff effort:* 6-14 person_hours (one_time)
- *Assumption basis:* Assumes the register is a page in an existing wiki or documentation system and that seeding it uses approaches the team already has in informal circulation.
- *Validating evidence:* A count of approaches currently circulating informally (from the team's own channel history) and the documentation system's existing page-creation process.
- *Dependencies:* none
- *Observable indicator:* Entries exist, each names the task it applies to, and at least one entry was added by someone other than its originator.

#### 90-180 days

**`OPT-SHR-02`** (knowledge_sharing, currently EMERGING)

- *Capability gained:* A review cycle over the register so entries carry a last-checked date and stale entries are corrected or retired rather than silently followed.
- *Staff effort:* 3-8 person_hours_per_month (recurring)
- *Assumption basis:* Assumes a register in the range of twenty to sixty entries and a monthly pass by one reviewer; scales with entry count, not with team size.
- *Validating evidence:* The actual entry count in the register after it has been in use for one quarter, and the time the first review pass takes when measured.
- *Dependencies:* `OPT-SHR-01`
- *Observable indicator:* Entries carry a last-checked date, and at least one entry has been corrected or retired as a result of a review.

#### 180+ days

**`OPT-LIT-02`** (ai_literacy, currently EMERGING)

- *Capability gained:* Team-specific guidance covering the data the team actually handles in its own systems, rather than general guidance that leaves the hard cases unresolved.
- *Staff effort:* 40-90 person_hours (one_time)
- *Assumption basis:* Assumes coordination with whoever owns the data-handling rules for the systems in question, and one revision round after the first cases surface.
- *Validating evidence:* Identification of the data-handling rule owner for each system in scope, and the turnaround time that owner has needed on comparable requests.
- *Dependencies:* `OPT-LIT-01`
- *Observable indicator:* Guidance names the team's own systems and data categories, and a previously unresolved borderline case has been decided by reference to it.

## T-IAM - Identity and Access Management (synthetic)

Contributors represented: **2**

Dimensions with a state: **0 of 6**. UNKNOWN: **6** (excluded from every denominator). Of those assessed - established 0, emerging 0, absent 0.

| dimension | state | why | evidence looked at |
|---|---|---|---|
| AI literacy | **UNKNOWN** | Signal comes from 2 contributor(s); the floor for an organizational reading is 3. This is thin evidence, not a low capability. | SYNTHETIC IAM decision tree, revision 2 · SYNTHETIC IAM standards page, section 'tooling' |
| Practical training | **UNKNOWN** | Signal comes from 2 contributor(s); the floor for an organizational reading is 3. This is thin evidence, not a low capability. | - |
| Workflow fit | **UNKNOWN** | Signal comes from 2 contributor(s); the floor for an organizational reading is 3. This is thin evidence, not a low capability. | - |
| Available support | **UNKNOWN** | Signal comes from 2 contributor(s); the floor for an organizational reading is 3. This is thin evidence, not a low capability. | SYNTHETIC no escalation path located · SYNTHETIC no named destination located for assisted-workflow questions |
| Knowledge sharing | **UNKNOWN** | Signal comes from 2 contributor(s); the floor for an organizational reading is 3. This is thin evidence, not a low capability. | - |
| Capacity to evaluate new approaches | **UNKNOWN** | Signal comes from 2 contributor(s); the floor for an organizational reading is 3. This is thin evidence, not a low capability. | SYNTHETIC no acceptance check located · SYNTHETIC one undated trial note, no decision recorded |

### Evidence needed before any plan can be made here

**AI literacy** - Signal comes from 2 contributor(s); the floor for an organizational reading is 3. This is thin evidence, not a low capability.

*Validating evidence:* Responses from at least 3 contributors on this team, or an explicit record that the team is smaller than the floor so its reading stays UNKNOWN by design.

- `LIT-3` - How does the team describe what these tools get wrong on the work you actually do?  
  *Ask to see:* Any written note of known failure modes for the tasks currently in use.

**Practical training** - Signal comes from 2 contributor(s); the floor for an organizational reading is 3. This is thin evidence, not a low capability.

*Validating evidence:* Responses from at least 3 contributors on this team, or an explicit record that the team is smaller than the floor so its reading stays UNKNOWN by design.

- `TRN-1` - What hands-on practice has the team had on its own recurring tasks, as opposed to a general awareness session?  
  *Ask to see:* Training record or session notes naming the tasks practised.
- `TRN-2` - How does someone joining the team learn the assisted parts of the workflow?  
  *Ask to see:* Onboarding material that covers the assisted step.

**Workflow fit** - Signal comes from 2 contributor(s); the floor for an organizational reading is 3. This is thin evidence, not a low capability.

*Validating evidence:* Responses from at least 3 contributors on this team, or an explicit record that the team is smaller than the floor so its reading stays UNKNOWN by design.

- `FIT-1` - Which recurring workflows currently include an assisted step, and at which point in the procedure?  
  *Ask to see:* The procedure document showing the step.
- `FIT-2` - Where was an assisted step tried and then narrowed or removed?  
  *Ask to see:* The change note, ticket, or decision record.
- `FIT-3` - Which steps are explicitly excluded from assistance, and on what basis?  
  *Ask to see:* The written exclusion and its stated reason.

**Available support** - Signal comes from 2 contributor(s); the floor for an organizational reading is 3. This is thin evidence, not a low capability.

*Validating evidence:* Responses from at least 3 contributors on this team, or an explicit record that the team is smaller than the floor so its reading stays UNKNOWN by design.


**Knowledge sharing** - Signal comes from 2 contributor(s); the floor for an organizational reading is 3. This is thin evidence, not a low capability.

*Validating evidence:* Responses from at least 3 contributors on this team, or an explicit record that the team is smaller than the floor so its reading stays UNKNOWN by design.

- `SHR-1` - Where does a useful approach that one person worked out get recorded so others can use it?  
  *Ask to see:* The register, page, or channel, with its actual entries.
- `SHR-2` - How is that shared material reviewed or corrected when it stops being right?  
  *Ask to see:* Review or last-checked dates on entries.

**Capacity to evaluate new approaches** - Signal comes from 2 contributor(s); the floor for an organizational reading is 3. This is thin evidence, not a low capability.

*Validating evidence:* Responses from at least 3 contributors on this team, or an explicit record that the team is smaller than the floor so its reading stays UNKNOWN by design.

- `EVL-3` - Who can stop an approach the team has already adopted, and on what evidence?  
  *Ask to see:* The written decision owner or reversal criterion.

## T-RIS - Research Infrastructure Services (synthetic)

Contributors represented: **5**

Dimensions with a state: **5 of 6**. UNKNOWN: **1** (excluded from every denominator). Of those assessed - established 1, emerging 3, absent 1.

| dimension | state | why | evidence looked at |
|---|---|---|---|
| AI literacy | **ESTABLISHED** | Resolved from 3 observed indicator(s). | SYNTHETIC 'RIS assistive tooling scope' page, last reviewed 2026-06-02 · SYNTHETIC 'known failure modes' note listing 4 task-specific failures · SYNTHETIC decision checklist 'is this task in scope', 9 items |
| Practical training | **ABSENT** | Resolved from 2 observed indicator(s). | SYNTHETIC no training record found for any hands-on session · SYNTHETIC onboarding material reviewed; no assisted step described |
| Workflow fit | **EMERGING** | Resolved from 3 observed indicator(s). | SYNTHETIC procedure 'dataset intake', step 4 marked assisted · SYNTHETIC procedures searched for a written exclusion; none present · SYNTHETIC ticket RIS-3312 narrows an assisted step, reason field left blank |
| Available support | **UNKNOWN** | 1 of 2 indicators observed; the floor for stating a capability state is 2. | SYNTHETIC queue RIS-HELP routing rule |
| Knowledge sharing | **EMERGING** | Resolved from 2 observed indicator(s). | SYNTHETIC interview note: team describes a well-used shared approach, but no register was produced when asked · SYNTHETIC no reviewed or dated shared material located |
| Capacity to evaluate new approaches | **EMERGING** | Resolved from 3 observed indicator(s). | SYNTHETIC 12-item known-answer check set with recorded results · SYNTHETIC interview note: team names a reversal owner verbally; no written decision owner produced · SYNTHETIC pilot note 'Q1-S extraction trial' with keep/drop decision |

**Evidence-strength notes**

- SHR-1: ESTABLISHED downgraded to EMERGING (recollection_only) - the only evidence is an interview statement, not a record.
- EVL-3: ESTABLISHED downgraded to EMERGING (recollection_only) - the only evidence is an interview statement, not a record.

### Evidence needed before any plan can be made here

**Available support** - 1 of 2 indicators observed; the floor for stating a capability state is 2.

*Validating evidence:* The artifacts listed below, or a written statement that the practice does not exist here.

- `SUP-2` - What happens to that question when the usual contact is unavailable?  
  *Ask to see:* The escalation path, if it is written down.

### Capability-development options

#### 0-90 days

**`OPT-SHR-01`** (knowledge_sharing, currently EMERGING)

- *Capability gained:* A register where a working approach is written down with the task it applies to, so it is reusable by someone who was not in the conversation.
- *Staff effort:* 6-14 person_hours (one_time)
- *Assumption basis:* Assumes the register is a page in an existing wiki or documentation system and that seeding it uses approaches the team already has in informal circulation.
- *Validating evidence:* A count of approaches currently circulating informally (from the team's own channel history) and the documentation system's existing page-creation process.
- *Dependencies:* none
- *Observable indicator:* Entries exist, each names the task it applies to, and at least one entry was added by someone other than its originator.

#### 90-180 days

**`OPT-EVAL-02`** (evaluation_capacity, currently EMERGING)

- *Capability gained:* A scheduled evaluation cycle with a known-answer check set, so a change in output quality is detectable rather than inferred from how the output reads.
- *Staff effort:* 20-48 person_hours (one_time)
- *Assumption basis:* Assumes ten to twenty check items drawn from work the team has already completed and whose correct answers are already known; excludes building any new tooling.
- *Validating evidence:* Whether completed work with known-correct answers is retrievable for the tasks in scope, and how long assembling the first ten items actually takes.
- *Dependencies:* `OPT-EVAL-01`
- *Observable indicator:* A check set exists, has been run more than once, and a run has produced a recorded difference that changed a decision.

**`OPT-FIT-01`** (workflow_fit, currently EMERGING)

- *Capability gained:* Two recurring workflows mapped end to end, with the points where assistance is permitted and the points where it is excluded both marked in the procedure.
- *Staff effort:* 24-56 person_hours (one_time)
- *Assumption basis:* Assumes the two workflows already have some written procedure to amend rather than being mapped from scratch, and that exclusions can be decided inside the team.
- *Validating evidence:* Whether written procedures exist for the two candidate workflows, and whether any exclusion requires sign-off outside the team.
- *Dependencies:* `OPT-LIT-01`
- *Observable indicator:* Both procedures show the assisted step and at least one written exclusion with a stated reason.

**`OPT-SHR-02`** (knowledge_sharing, currently EMERGING)

- *Capability gained:* A review cycle over the register so entries carry a last-checked date and stale entries are corrected or retired rather than silently followed.
- *Staff effort:* 3-8 person_hours_per_month (recurring)
- *Assumption basis:* Assumes a register in the range of twenty to sixty entries and a monthly pass by one reviewer; scales with entry count, not with team size.
- *Validating evidence:* The actual entry count in the register after it has been in use for one quarter, and the time the first review pass takes when measured.
- *Dependencies:* `OPT-SHR-01`
- *Observable indicator:* Entries carry a last-checked date, and at least one entry has been corrected or retired as a result of a review.

**`OPT-TRN-01`** (practical_training, currently ABSENT)

- *Capability gained:* Hands-on practice on two of the team's own recurring tasks, with the resulting procedures updated to describe the assisted step.
- *Staff effort:* 30-70 person_hours (one_time)
- *Assumption basis:* Assumes a team in the range of five to ten contributors, two tasks in scope, preparation by one person and attendance by the rest; assumes no external trainer is engaged.
- *Validating evidence:* The real contributor count for the team, the recorded duration of its last hands-on session of any kind, and whether an external trainer is required by local practice.
- *Dependencies:* `OPT-LIT-01`
- *Observable indicator:* A training record names the two tasks practised, and both task procedures have been updated to describe the assisted step.

#### 180+ days

**`OPT-FIT-02`** (workflow_fit, currently EMERGING)

- *Capability gained:* The mapped workflows instrumented so rework is visible, making it possible to see whether an assisted step reduced total effort or moved it downstream.
- *Staff effort:* 50-120 person_hours (one_time)
- *Assumption basis:* Assumes the workflow already passes through a system that can record a rework event; if rework is currently invisible, discovery effort is not included here.
- *Validating evidence:* Whether the systems carrying these workflows already record a reopen, revision, or return-for-correction event, and whether that record is retrievable.
- *Dependencies:* `OPT-EVAL-02`, `OPT-FIT-01`
- *Observable indicator:* Rework counts for the two workflows are retrievable for a period before and a period after the assisted step was introduced.

### Sequencing findings

- **prerequisite_not_in_plan** (`OPT-EVAL-02`, open_question): Prerequisite 'OPT-EVAL-01' is not in this team's plan, because the capability it builds is not a gap here. Confirm it is genuinely already satisfied before scheduling 'OPT-EVAL-02'.
- **prerequisite_not_in_plan** (`OPT-FIT-01`, open_question): Prerequisite 'OPT-LIT-01' is not in this team's plan, because the capability it builds is not a gap here. Confirm it is genuinely already satisfied before scheduling 'OPT-FIT-01'.
- **prerequisite_not_in_plan** (`OPT-TRN-01`, open_question): Prerequisite 'OPT-LIT-01' is not in this team's plan, because the capability it builds is not a gap here. Confirm it is genuinely already satisfied before scheduling 'OPT-TRN-01'.
