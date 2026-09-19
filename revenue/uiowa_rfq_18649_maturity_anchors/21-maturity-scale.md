# 21 - Common maturity anchors

**These anchors are our proposed framework, drafted for RFQ 18649 preparation.** They are not a University of Iowa finding, not an industry standard, and not a certification scale. They are offered for discussion and expected to be renamed and adjusted.

One ordinal scale, used unchanged across development, security, deployment and AI readiness.

## Why the scale is bounded by evidence kind

A maturity scale scored by counting evidence rewards whoever has the most documents. A group with ten written policies and no practice outscores a group that does the work and writes little down, which is the opposite of the truth.

So the **kind** of evidence sets a ceiling, and volume never buys it:

| Evidence kind | Ceiling | Why |
|---|---|---|
| `policy_document` - Policy or procedure document | **2** | A document states an intention. It is not evidence that anything happened, and a second document is not evidence either. |
| `interview_statement` - Interview statement | **2** | What people say the practice is tells us the intended practice. On its own it is a description, not a record of the work. It counts toward level 2 only when corroborated -- one person's account is a claim, and two accounts that disagree are evidence that no practice is defined. |
| `single_instance` - Record of one instance of the work | **3** | One instance shows the practice can happen. It does not show it repeating. |
| `repeated_instances` - Records of repeated instances across a window | **4** | Repetition across people or services shows the practice survives the particular individuals doing it. |
| `outcome_measure` - Outcome measure with definition, period and denominator | **5** | Knowing the practice runs is not knowing it works. |

**Interview statements need corroboration.** A document states an intended practice by existing. An interview statement counts toward level 2 only when it is corroborated (`states_intended_practice`): one person's account is a claim, and two accounts that disagree are evidence that no practice is defined, which is level 1.

A ceiling is not an award. Holding a policy document does not place a group at level 2; it means they cannot be **above** it. The level reached is the highest one whose anchors are actually evidenced, and then the ceiling is applied. The lower of the two wins.

## The levels

### Level 1 - Absent

**What this level measures:** Whether the practice happens at all.

**Observable anchors** - all must be evidenced:

- No procedure, written or understood, governs how this is done.
- People describe what they personally do; descriptions do not agree.
- No record exists that the activity took place.

**To reach level 2:** A description of the intended practice that more than one person recognises, written or not.

### Level 2 - Defined on paper

**What this level measures:** Whether an intended practice exists and is stated. NOT whether it happens.

**Observable anchors** - all must be evidenced:

- A procedure exists and can be produced on request.
- People can say what the procedure requires.
- No evidence yet shows the procedure being followed in real work.

**To reach level 3:** At least one real instance of the practice being followed, with a record that is not the procedure document itself.

### Level 3 - Practised

**What this level measures:** Whether the practice has actually been carried out.

**Observable anchors** - all must be evidenced:

- At least one real instance is evidenced by a record of the work, not by the procedure that asks for it.
- The instance can be followed from request to completion.
- Nothing yet shows the practice holding across time, people or services.

**To reach level 4:** Repeated instances across a stated window, covering more than one person or service, with exceptions visible rather than absent.

### Level 4 - Repeatable

**What this level measures:** Whether the practice holds up when the particular people change.

**Observable anchors** - all must be evidenced:

- Multiple instances across a stated observation window.
- More than one person or service is covered, so the practice is not one individual's habit.
- Departures from the procedure are recorded as exceptions rather than being invisible.

**To reach level 5:** A measure of whether the practice achieves what it is for, with its definition, period and denominator stated.

### Level 5 - Measured and adjusted

**What this level measures:** Whether the practice is known to work, and is changed when it does not.

**Observable anchors** - all must be evidenced:

- An outcome measure exists with a stated definition, period and denominator.
- The measure has been reviewed, and at least one change followed from what it showed.
- The change itself is evidenced, not only proposed.

**Note:** This is the top of the scale. It is not a destination every practice should reach; cost has to justify it.

## States that are not levels

These answer different questions from "how mature is this?". Each carries `maturity_rank = null`, so nothing can sort it onto the bottom of the scale, and none is counted as a low level.

| Status | Meaning |
|---|---|
| `unassessed` | Outside the agreed scope for this criterion. Not a level. |
| `not_applicable` | This practice does not apply to how the group operates. Nothing is missing. |
| `insufficient_evidence` | We looked; what was supplied does not support any level. |

`not_applicable` requires a stated `applicability_reason`. Without one it is indistinguishable from an area nobody looked at, which is the failure this distinction exists to prevent.

An assessed criterion with no evidence returns `insufficient_evidence`, **not level 1**. Level 1 is a finding that the practice is absent; no evidence is a statement about our own collection.

## The four patterns the examples keep apart

| Pattern | Meaning |
|---|---|
| `repeatable_practice` | Repeatable practice - the work is recorded happening more than once. |
| `isolated_success` | Isolated success - one real instance, nothing showing it repeats. |
| `policy_only_claim` | Claim without a practice record - the practice is asserted, in a document or an interview, but nothing records the work itself. |
| `missing_evidence` | Missing evidence - nothing was supplied. Not a low level. |

## Handoff to UIOWA-022

The rating model in `revenue/uiowa_rfq_18649_rating_model/` states that it does not invent the maturity scale and takes the rank and label as inputs. This method emits exactly the fields that model declares: `criterion_id`, `area`, `service`, `assessment_status`, `maturity_rank`, `maturity_label`, `evidence_ids`. Composition of those observations, coverage and confidence remain that model's job, not this one's.
