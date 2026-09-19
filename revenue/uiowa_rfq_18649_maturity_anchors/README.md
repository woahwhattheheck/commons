# Common maturity anchors

**UIOWA-021.** One ordinal maturity scale used unchanged across development, security,
deployment and AI readiness, with observable anchors, transition criteria, and states that are
not levels.

Built by seat `OP5-EMBER` (Claude · Opus 5). Python 3 standard library only, no network,
deterministic.

> **These anchors are our proposed framework**, drafted for RFQ 18649 preparation. They are not
> a University of Iowa finding, not an industry standard, and not a certification scale. Every
> worked example is fictional and labelled as such.

## The problem it is built against

A maturity scale scored by counting evidence rewards whoever has the most documents. A group
with ten written policies and no practice outscores a group that does the work and writes little
down — the opposite of the truth. The order's phrase for this is *"without rewarding paperwork
alone"*.

So the **kind** of evidence sets a ceiling, and volume never buys it:

| Evidence kind | Ceiling | Why |
|---|---|---|
| `policy_document` | 2 | A document states an intention. A second document is not evidence either. |
| `interview_statement` | 2 | A description of the practice, not a record of the work. Counts toward level 2 only when corroborated. |
| `single_instance` | 3 | Shows the practice *can* happen. Not that it repeats. |
| `repeated_instances` | 4 | Repetition across people shows it survives the individuals doing it. |
| `outcome_measure` | 5 | Knowing the practice runs is not knowing it works. |

A test asserts that 1, 2, 5, 10 and 50 policy documents all produce **level 2**, and that one
real record of the work outranks fifty documents.

## A ceiling is not an award

The two questions are separate, and conflating them was a real bug caught during the build:

1. Which level's anchors does the evidence actually **satisfy**?
2. What ceiling does the **kind** of evidence impose?

The result is the lower of the two. Holding a policy document does not place a group at level 2 —
it means they cannot be above it. Before this was fixed, two interview statements that
*contradicted each other* evaluated to level 2, because the code read the ceiling as the answer.
They now evaluate to level 1, which is what the level-1 anchors say.

Every result carries `cap_reason` naming the specific anchor that was not met, and
`next_level_requires` naming the evidence that would lift it — transition criteria that execute
rather than describe:

```
DEP-01  deployment  3 Practised   repeated records exist but none covers more than one person
                                  or service, so the practice cannot yet be distinguished from
                                  one individual's habit
DEP-02  deployment  3 Practised   repetition is evidenced but no departures from the procedure
                                  are recorded anywhere; a process with no visible exceptions
                                  is usually one whose exceptions are not being written down
AI-01   ai_readiness 4 Repeatable an outcome measure is cited but its definition, period or
                                  denominator is not given, so it cannot be read
AI-04   ai_readiness 4 Repeatable the measure exists and is defined, but no change is evidenced
                                  as following from it; measuring is not adjusting
```

## The four patterns kept apart

The order requires that examples distinguish repeatable practice from policy-only claims,
isolated successes and missing evidence. Each is a separate classification, asserted:

| Pattern | Meaning |
|---|---|
| `repeatable_practice` | The work is recorded happening more than once. |
| `isolated_success` | One real instance. Genuine, and not yet a practice. |
| `policy_only_claim` | The practice is asserted — in a document or an interview — but nothing records the work. |
| `missing_evidence` | Nothing was supplied. **Not a low level.** |

## States that are not levels

`unassessed`, `not_applicable` and `insufficient_evidence` all carry `maturity_rank = null`, so
nothing can sort them onto the bottom of the scale.

The distinction that matters most: **an assessed criterion with no evidence returns
`insufficient_evidence`, not level 1.** Level 1 is a *finding* that the practice is absent — it
requires evidence showing absence. No evidence is a statement about our own collection, not about
the group. A test asserts the two produce different results.

`not_applicable` requires a stated `applicability_reason`; without one it is indistinguishable
from an area nobody looked at. Supplying evidence alongside it is refused — if evidence exists,
the practice applies.

## Handoff to UIOWA-022

`revenue/uiowa_rfq_18649_rating_model/` states that it *"intentionally does not invent the
maturity scale"* and takes the rank and label as inputs from the common-anchor method. This lane
emits exactly the fields that model declares: `criterion_id`, `area`, `service`,
`assessment_status`, `maturity_rank`, `maturity_label`, `evidence_ids` — written to
`sample_output/rating-model-input.json`. Composition, coverage and confidence remain that
model's job. No files in that lane were touched.

## Run it

```bash
cd revenue/uiowa_rfq_18649_maturity_anchors

python3 render_scale.py          # writes 21-maturity-scale.md and sample_output/
python3 render_scale.py --check  # evaluate the examples, exit non-zero on a data error
python3 -m unittest test_anchors # 48 tests
```

## Files

| File | What it is |
|---|---|
| `21-maturity-scale.md` | The documented scale (generated; the deliverable the order names) |
| `anchors.py` | The five levels, their anchors, the evidence ceilings, and the evaluator |
| `render_scale.py` | Renders the scale, the worked examples and the 022 handoff |
| `fixtures/worked_examples.json` | 12 fictional criteria across all four areas |
| `sample_output/` | A committed run |
| `test_anchors.py` | 48 tests |

## What is real and what is draft

**Real and working:** the scale and its anchors; the evidence-ceiling model; anchors-then-ceiling
evaluation; the four-pattern classifier; the not-a-level states; `cap_reason` and
`next_level_requires`; the 022 handoff; Markdown/CSV/JSON output; 48 tests.

**Draft:** the anchor wording itself, and the placement of each ceiling. Both are proposals for
discussion. The *shape* — that evidence kind bounds the level — is the argument; the exact
thresholds are negotiable.

## UNKNOWN inputs

- Whether this scale is acceptable to Clark's and to the University, and what the levels should
  be called. The five names here are ours.
- Whether five levels is the right number. Nothing in the method depends on five; `LEVELS` is a
  list.
- The real criteria per area. The twelve in the fixture are fictional illustrations, not a
  criterion set.
- Which criteria are legitimately `not_applicable` for each real group — that needs each group's
  own account of how it operates and cannot be inferred here.
- Where the ceilings should actually sit. `interview_statement` capping at 2 is a judgement that
  a described practice is weaker evidence than a recorded one; it is arguable.

No certification, compliance, accreditation or peer-percentile claim is made anywhere, and no
individual's performance is rated. A test greps the rendered documents for that vocabulary.
