# Integration decision worksheet

One worksheet per candidate workflow. Every verdict below names the question that produced it.

**Reading the verdicts.** `SUPPORTED` / `SUPPORTED_WITH_CAUTIONS` are real readings. `DISQUALIFIED` means a hard condition failed. `UNDETERMINED` means a question that is *decisive* for that pattern has no answer yet -- it is not a soft yes, it is a instruction to go get the evidence. `NO_SIGNAL` means nothing in the answers speaks to it either way.

## Question set

- **`answer_useful_within`** (enum) - How soon must the answer be available to still be useful?
- **`consequential`** (bool) - Can the output cause an effect that is hard to reverse, or that a named person would be accountable for?
- **`degraded_answer_exists`** (bool) - Is there a DEFINED, usable answer for this workflow when the capability is unavailable? (a fallback that has never been exercised is UNKNOWN)
- **`peak_items_per_hour`** (number) - Peak inbound items per hour for this workflow.
- **`reviewer_capacity_items_per_hour`** (number) - Reviewer capacity in items per hour, MEASURED on reviewing drafts (not inferred from the unaided process).
- **`staged_copies_permitted`** (bool) - May this content be copied into an internal queue, result store and dead-letter queue, under its own handling terms?
- **`durable_queue_available`** (bool) - Does durable queue infrastructure with an OWNED and monitored dead-letter path already exist?
- **`single_owner_for_deadline_and_fallback`** (bool) - Is there one named owner for the request deadline AND the degraded answer?
- **`payload_contains_restricted_content`** (bool) - Does the payload contain content whose handling terms restrict crossing an external boundary?
- **`baseline_measured`** (bool) - Has the non-AI baseline been measured on the same items, so benefit can be stated as a difference?

## Service request intake triage  (`HRI-INTAKE-01` - FICTIONAL)

| Question | Answer |
|---|---|
| `answer_useful_within` | only_in_session |
| `consequential` | no |
| `degraded_answer_exists` | yes |
| `peak_items_per_hour` | 240 |
| `reviewer_capacity_items_per_hour` | UNKNOWN |
| `staged_copies_permitted` | UNKNOWN |
| `durable_queue_available` | yes |
| `single_owner_for_deadline_and_fallback` | yes |
| `payload_contains_restricted_content` | yes |
| `baseline_measured` | yes |

Derived: peak volume exceeds measured reviewer capacity -> **UNKNOWN**

| Pattern | Fit | Why |
|---|---|---|
| Synchronous in-request call | `SUPPORTED_WITH_CAUTIONS` | supports via `answer_useful_within`: the answer is only useful inside the session, which is what this pattern is for; caution via `payload_contains_restricted_content`: live records cross the boundary at full fidelity in this pattern |
| Human-in-the-loop review step | `UNDETERMINED` | blocked: decisive question `reviewer_capacity_items_per_hour + peak_items_per_hour` is UNKNOWN; caution via `consequential`: low-stakes reversible output; a review step may cost more than the errors it prevents |
| Asynchronous queued / batch processing | `DISQUALIFIED` | DISQUALIFY via `answer_useful_within`: the answer is only useful inside the session; out-of-band completion cannot serve it; blocked: decisive question `staged_copies_permitted` is UNKNOWN; supports via `peak_items_per_hour`: volume is high enough that throughput, not per-item latency, is the right thing to optimize |

**Unanswered worksheet questions (UNKNOWN, not zero):**

- `reviewer_capacity_items_per_hour` - Reviewer capacity in items per hour, MEASURED on reviewing drafts (not inferred from the unaided process).
- `staged_copies_permitted` - May this content be copied into an internal queue, result store and dead-letter queue, under its own handling terms?

**Unresolved evidence carried from the patterns still in play:**

- (A_SYNCHRONOUS_IN_REQUEST) Measured p50/p95/p99 of the target capability class under the institution's own payload sizes -- UNKNOWN until run.
- (A_SYNCHRONOUS_IN_REQUEST) The surrounding service's current request timeout and connection-pool limits -- UNKNOWN (institution input).
- (A_SYNCHRONOUS_IN_REQUEST) Whether a usable degraded answer exists for each candidate workflow, or only in principle -- UNKNOWN until each workflow owner states it.
- (C_HUMAN_IN_THE_LOOP_REVIEW) Reviewer capacity in items per person-hour for each candidate workflow -- UNKNOWN; must be measured, not estimated from the unaided process, because reviewing a draft and producing one are different tasks.
- (C_HUMAN_IN_THE_LOOP_REVIEW) Who owns the auto-accept threshold -- UNKNOWN (institution input); an unowned threshold moves informally.
- (C_HUMAN_IN_THE_LOOP_REVIEW) Whether reviewer decision records may be retained and reused, and for how long -- UNKNOWN.
- (C_HUMAN_IN_THE_LOOP_REVIEW) Whether the unaided path can still be executed today -- UNKNOWN until someone runs it.

## Retrospective document classification backfill  (`HRI-ARCHIVE-02` - FICTIONAL)

| Question | Answer |
|---|---|
| `answer_useful_within` | days |
| `consequential` | no |
| `degraded_answer_exists` | yes |
| `peak_items_per_hour` | 4000 |
| `reviewer_capacity_items_per_hour` | UNKNOWN |
| `staged_copies_permitted` | yes |
| `durable_queue_available` | yes |
| `single_owner_for_deadline_and_fallback` | yes |
| `payload_contains_restricted_content` | no |
| `baseline_measured` | no |

Derived: peak volume exceeds measured reviewer capacity -> **UNKNOWN**

| Pattern | Fit | Why |
|---|---|---|
| Asynchronous queued / batch processing | `SUPPORTED` | supports via `answer_useful_within`: completion-time commitment fits comfortably; supports via `peak_items_per_hour`: volume is high enough that throughput, not per-item latency, is the right thing to optimize |
| Human-in-the-loop review step | `UNDETERMINED` | blocked: decisive question `reviewer_capacity_items_per_hour + peak_items_per_hour` is UNKNOWN; caution via `consequential`: low-stakes reversible output; a review step may cost more than the errors it prevents; caution via `baseline_measured`: no measured unassisted-reviewer baseline, so any benefit claim from this pattern would be unfalsifiable |
| Synchronous in-request call | `DISQUALIFIED` | DISQUALIFY via `answer_useful_within`: the answer is not needed in-session, so holding a user request open buys nothing and costs availability |

**Unanswered worksheet questions (UNKNOWN, not zero):**

- `reviewer_capacity_items_per_hour` - Reviewer capacity in items per hour, MEASURED on reviewing drafts (not inferred from the unaided process).

**Unresolved evidence carried from the patterns still in play:**

- (B_ASYNCHRONOUS_QUEUED_BATCH) Whether durable queue infrastructure with a monitored dead-letter path already exists and who operates it -- UNKNOWN (institution input).
- (B_ASYNCHRONOUS_QUEUED_BATCH) Acceptable completion-time commitment per candidate workflow -- UNKNOWN until the workflow owner states it; do not infer it from current runtimes.
- (B_ASYNCHRONOUS_QUEUED_BATCH) Retention terms permitted for staged copies of the queued content -- UNKNOWN and must be answered before, not after, build.
- (B_ASYNCHRONOUS_QUEUED_BATCH) Reprocessing budget when the capability version changes -- UNKNOWN.
- (C_HUMAN_IN_THE_LOOP_REVIEW) Reviewer capacity in items per person-hour for each candidate workflow -- UNKNOWN; must be measured, not estimated from the unaided process, because reviewing a draft and producing one are different tasks.
- (C_HUMAN_IN_THE_LOOP_REVIEW) Who owns the auto-accept threshold -- UNKNOWN (institution input); an unowned threshold moves informally.
- (C_HUMAN_IN_THE_LOOP_REVIEW) Whether reviewer decision records may be retained and reused, and for how long -- UNKNOWN.
- (C_HUMAN_IN_THE_LOOP_REVIEW) Whether the unaided path can still be executed today -- UNKNOWN until someone runs it.

## Award eligibility narrative drafting  (`HRI-AWARD-03` - FICTIONAL)

| Question | Answer |
|---|---|
| `answer_useful_within` | hours |
| `consequential` | yes |
| `degraded_answer_exists` | UNKNOWN |
| `peak_items_per_hour` | 30 |
| `reviewer_capacity_items_per_hour` | 12 |
| `staged_copies_permitted` | UNKNOWN |
| `durable_queue_available` | no |
| `single_owner_for_deadline_and_fallback` | no |
| `payload_contains_restricted_content` | yes |
| `baseline_measured` | yes |

Derived: peak volume exceeds measured reviewer capacity -> **yes**

| Pattern | Fit | Why |
|---|---|---|
| Asynchronous queued / batch processing | `UNDETERMINED` | blocked: decisive question `staged_copies_permitted` is UNKNOWN; supports via `answer_useful_within`: completion-time commitment fits comfortably; caution via `durable_queue_available`: no existing durable queue with an owned dead-letter path; first-integration effort is at the top of the range and ongoing operations are a new burden |
| Synchronous in-request call | `DISQUALIFIED` | DISQUALIFY via `answer_useful_within`: the answer is not needed in-session, so holding a user request open buys nothing and costs availability; blocked: decisive question `degraded_answer_exists` is UNKNOWN; caution via `single_owner_for_deadline_and_fallback`: deadline and fallback are unowned; this is the split-ownership failure this pattern is most exposed to; caution via `consequential`: consequential output with no review step; consider composing with pattern C; caution via `payload_contains_restricted_content`: live records cross the boundary at full fidelity in this pattern |
| Human-in-the-loop review step | `DISQUALIFIED` | DISQUALIFY via `reviewer_capacity_items_per_hour`: peak volume exceeds measured reviewer capacity, so the review step would become a rubber stamp -- worse than no review, because it manufactures the appearance of oversight; supports via `consequential`: the action is consequential, which is the condition this pattern exists for |

**Unanswered worksheet questions (UNKNOWN, not zero):**

- `degraded_answer_exists` - Is there a DEFINED, usable answer for this workflow when the capability is unavailable? (a fallback that has never been exercised is UNKNOWN)
- `staged_copies_permitted` - May this content be copied into an internal queue, result store and dead-letter queue, under its own handling terms?

**Unresolved evidence carried from the patterns still in play:**

- (B_ASYNCHRONOUS_QUEUED_BATCH) Whether durable queue infrastructure with a monitored dead-letter path already exists and who operates it -- UNKNOWN (institution input).
- (B_ASYNCHRONOUS_QUEUED_BATCH) Acceptable completion-time commitment per candidate workflow -- UNKNOWN until the workflow owner states it; do not infer it from current runtimes.
- (B_ASYNCHRONOUS_QUEUED_BATCH) Retention terms permitted for staged copies of the queued content -- UNKNOWN and must be answered before, not after, build.
- (B_ASYNCHRONOUS_QUEUED_BATCH) Reprocessing budget when the capability version changes -- UNKNOWN.

## Deliberately malformed intake record  (`HRI-MALFORMED-99` - FICTIONAL - hostile-input probe, not a real candidate workflow)

| Question | Answer |
|---|---|
| `answer_useful_within` | UNKNOWN |
| `consequential` | UNKNOWN |
| `degraded_answer_exists` | UNKNOWN |
| `peak_items_per_hour` | UNKNOWN |
| `reviewer_capacity_items_per_hour` | UNKNOWN |
| `staged_copies_permitted` | UNKNOWN |
| `durable_queue_available` | UNKNOWN |
| `single_owner_for_deadline_and_fallback` | UNKNOWN |
| `payload_contains_restricted_content` | UNKNOWN |
| `baseline_measured` | UNKNOWN |

Derived: peak volume exceeds measured reviewer capacity -> **UNKNOWN**

| Pattern | Fit | Why |
|---|---|---|
| Synchronous in-request call | `UNDETERMINED` | blocked: decisive question `answer_useful_within` is UNKNOWN; blocked: decisive question `degraded_answer_exists` is UNKNOWN |
| Asynchronous queued / batch processing | `UNDETERMINED` | blocked: decisive question `answer_useful_within` is UNKNOWN; blocked: decisive question `staged_copies_permitted` is UNKNOWN |
| Human-in-the-loop review step | `UNDETERMINED` | blocked: decisive question `consequential` is UNKNOWN; blocked: decisive question `reviewer_capacity_items_per_hour + peak_items_per_hour` is UNKNOWN |

**Unanswered worksheet questions (UNKNOWN, not zero):**

- `answer_useful_within` - How soon must the answer be available to still be useful?
- `baseline_measured` - Has the non-AI baseline been measured on the same items, so benefit can be stated as a difference?
- `consequential` - Can the output cause an effect that is hard to reverse, or that a named person would be accountable for?
- `degraded_answer_exists` - Is there a DEFINED, usable answer for this workflow when the capability is unavailable? (a fallback that has never been exercised is UNKNOWN)
- `durable_queue_available` - Does durable queue infrastructure with an OWNED and monitored dead-letter path already exist?
- `payload_contains_restricted_content` - Does the payload contain content whose handling terms restrict crossing an external boundary?
- `peak_items_per_hour` - Peak inbound items per hour for this workflow.
- `reviewer_capacity_items_per_hour` - Reviewer capacity in items per hour, MEASURED on reviewing drafts (not inferred from the unaided process).
- `single_owner_for_deadline_and_fallback` - Is there one named owner for the request deadline AND the degraded answer?
- `staged_copies_permitted` - May this content be copied into an internal queue, result store and dead-letter queue, under its own handling terms?

**Malformed answers discarded (treated as UNKNOWN, never as a default):**

- answer_useful_within='someday' not in ('only_in_session', 'minutes', 'hours', 'days')
- consequential='yes' is not a boolean
- peak_items_per_hour='lots' is not a number

**Unresolved evidence carried from the patterns still in play:**

- (A_SYNCHRONOUS_IN_REQUEST) Measured p50/p95/p99 of the target capability class under the institution's own payload sizes -- UNKNOWN until run.
- (A_SYNCHRONOUS_IN_REQUEST) The surrounding service's current request timeout and connection-pool limits -- UNKNOWN (institution input).
- (A_SYNCHRONOUS_IN_REQUEST) Whether a usable degraded answer exists for each candidate workflow, or only in principle -- UNKNOWN until each workflow owner states it.
- (B_ASYNCHRONOUS_QUEUED_BATCH) Whether durable queue infrastructure with a monitored dead-letter path already exists and who operates it -- UNKNOWN (institution input).
- (B_ASYNCHRONOUS_QUEUED_BATCH) Acceptable completion-time commitment per candidate workflow -- UNKNOWN until the workflow owner states it; do not infer it from current runtimes.
- (B_ASYNCHRONOUS_QUEUED_BATCH) Retention terms permitted for staged copies of the queued content -- UNKNOWN and must be answered before, not after, build.
- (B_ASYNCHRONOUS_QUEUED_BATCH) Reprocessing budget when the capability version changes -- UNKNOWN.
- (C_HUMAN_IN_THE_LOOP_REVIEW) Reviewer capacity in items per person-hour for each candidate workflow -- UNKNOWN; must be measured, not estimated from the unaided process, because reviewing a draft and producing one are different tasks.
- (C_HUMAN_IN_THE_LOOP_REVIEW) Who owns the auto-accept threshold -- UNKNOWN (institution input); an unowned threshold moves informally.
- (C_HUMAN_IN_THE_LOOP_REVIEW) Whether reviewer decision records may be retained and reused, and for how long -- UNKNOWN.
- (C_HUMAN_IN_THE_LOOP_REVIEW) Whether the unaided path can still be executed today -- UNKNOWN until someone runs it.
