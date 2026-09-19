# UIOWA-074 — AI policy-to-workflow assessment

A runnable policy-to-practice matrix generator. It connects written
organizational AI and data policies to ordinary development tasks, records the
evidence an assessor actually observed, and keeps the questions only the
University can answer visibly separate from both.

**Python 3 standard library only. No network. No install step. Deterministic.**

> **FICTIONAL DATA.** Example State University is invented. Nothing in this
> lane describes the University of Iowa or any real institution, policy,
> system, or person. See [`SOURCE_NOTES.md`](SOURCE_NOTES.md).

---

## Run it

```bash
cd revenue/uiowa_rfq_18649_ai_policy_to_workflow
python3 policy_matrix.py                      # writes into sample/
python3 policy_matrix.py --fixtures fixtures --out /tmp/out
python3 -m unittest test_policy_matrix -v     # 36 tests
```

Real output from `python3 policy_matrix.py`:

```
FICTIONAL DATA. Example State University is an invented organization. No record
here describes the University of Iowa or any real institution, policy, system,
or person.
cells=15 assessed=10 not_assessed=4 blocked=1 gaps=3 strengths=5
CAUTION: 4 of 15 cells were never assessed. Gap and strength counts below
describe ONLY the 10 assessed cells. Do not read '3 gaps' as '3 gaps exist' --
unexamined ground is not clean ground.
CAUTION: 1 cells cannot be resolved until the University answers a blocking
interpretation question. They are excluded from gap and strength counts; their
provisional reading is kept in reading_if_unblocked.
wrote matrix.csv matrix.md open_questions.csv findings.json -> sample
```

## What it produces

| File | For |
|---|---|
| `sample/matrix.md` | The leadership-facing matrix, with the three axes in separate columns and a legend for every reading. |
| `sample/matrix.csv` | The same cells as data, all axes preserved, for filtering and for the final report. |
| `sample/open_questions.csv` | The clarification register — what must be asked, of whom, and whether it blocks. |
| `sample/findings.json` | Machine-readable cells + summary + the refusal list, for downstream lanes. |
| `WORKFLOW_EXAMPLES.md` | Six fictional workflow narratives written for leadership discussion, each tied to specific matrix rows. |

## The design, in one idea

Three things get collapsed in ordinary policy assessments. This tool refuses to
collapse them, and carries all three through every output:

| Axis | Field | What it answers |
|---|---|---|
| **Stated policy** | `policy_axis` | Is something written down, and does it bind? |
| **Implementation evidence** | `evidence_axis` | What did an assessor actually observe? |
| **Open questions** | `open_questions` / `blocking_questions` | What must the University decide before anyone can judge this cell? |

A `reading` is derived from the first two for leadership convenience. It never
overwrites them, so any reading can be taken apart and argued with.

### The rule that does the most work

> **"We looked and found nothing" and "we never looked" are different cells.**

| Evidence state | Means | Counts as |
|---|---|---|
| `LOOKED_NONE_FOUND` | Somebody checked; the practice is absent | a **gap** |
| `NOT_GATHERED` | Nobody checked | **UNKNOWN** — never a gap, never a pass, never a zero |

The mechanism: an evidence record of `kind: "none"` **must** carry a `checked`
boolean. Loading fails if it is missing, with the reason stated:

```
EV-0xx has kind 'none' but no 'checked' flag -- cannot tell
'we looked and found nothing' from 'we never looked'
```

The fixture set contains both, so the difference is demonstrated in the output
rather than asserted in a README. `EV-012` records a release-approval
walkthrough that was *scheduled and did not happen* — a real record with a
date, an observer and a locator, which a record-counting tool would happily
score. It resolves to `NOT_ASSESSED`. An unfinished assessor schedule is not a
finding about the University.

### The readings

Derived from a fully enumerated 3 × 5 table written out longhand in
`policy_matrix.py`, so a non-programmer can audit it and a test can assert it is
total. There is no default branch — a default branch in that table is exactly
how UNKNOWN quietly becomes "fine".

| Reading | Counts as | When |
|---|---|---|
| `ALIGNED` | strength | Policy in force + artifact inspected |
| `ALIGNED_INDIRECT` | strength | Policy in force + related artifact implies the practice |
| `PRACTICE_AHEAD_OF_POLICY` | strength | Practice evidenced; the policy behind it is draft or superseded |
| `UNDOCUMENTED_PRACTICE` | strength | Practice evidenced with no written policy at all |
| `STATED_NOT_PRACTICED` | **gap** | Policy in force, assessor looked, practice absent |
| `NOT_ADDRESSED` | **gap** | No policy, assessor looked, practice absent |
| `STATED_PRACTICE_UNCORROBORATED` | neither | Policy in force; staff say they follow it; nothing corroborates |
| `UNCLEAR_ON_BOTH_SIDES` | neither | Nothing binding written, nothing corroborating the claim |
| `POLICY_NOT_IN_FORCE` | neither | Draft/superseded policy, practice not found — nothing binds yet |
| `NOT_ASSESSED` | **UNKNOWN** | No evidence gathered |
| `BLOCKED_ON_CLARIFICATION` | **blocked** | A blocking question must be answered first |

Two of these are the point of the whole exercise:

- **`UNDOCUMENTED_PRACTICE`** — real, documented, repeated practice with no
  policy and no named owner. A conformance-shaped tool marks this red. That is
  wrong about the present (it is demonstrably happening) and wrong about
  incentives (it punishes the only team that noticed the problem). It is a
  **strength with a continuity risk**, and that is a different conversation
  producing a different action.
- **`BLOCKED_ON_CLARIFICATION`** — when `Q-01` asks whether prompt text counts
  as institutional data, both readings are defensible from the policy text. The
  assessor has no basis to pick, and picking would mean inventing University
  policy and then assessing the University against the invention. The gathered
  evidence survives in `reading_if_unblocked`, so answering the question flips
  one field instead of requiring new fieldwork.

## What this tool refuses to produce

Carried in code (`refusals()`), written into `findings.json` and `matrix.md`,
and covered by tests:

- **No maturity level, readiness level, or tier.** `score()` raises
  `ScoreRefused` on purpose.
- **No single number** summarizing the organization.
- **No percentage over any denominator that includes UNKNOWN cells.** Counts are
  raw integers. A test walks every field name in the summary and every cell,
  recursively, and fails on any key containing *percent, pct, ratio, maturity,
  score, level, tier, grade, rating, index* — and on any float, since a float
  is how a count becomes a rate.
- **No promotion of an interview assertion to implementation evidence.**
  `ASSERTED_ONLY` sits below `EVIDENCED_INDIRECT` in the ordering and a test
  asserts no policy class ever turns an assertion into a strength.
- **No individual is scored.** The accountable unit is a **role**.
- **No certification, compliance opinion, peer comparison, percentile, or
  benchmark.**
- **No invented NIST AI RMF subcategory IDs.** Subcategory mapping is UNKNOWN.

## NIST AI RMF

Referenced, not certified against:
<https://www.nist.gov/itl/ai-risk-management-framework>

Only the four core functions (GOVERN / MAP / MEASURE / MANAGE) are used, purely
as a sort key for grouping leadership discussion. Validation rejects any policy
record naming a function outside those four. See
[`SOURCE_NOTES.md`](SOURCE_NOTES.md) for the full list of what is deliberately
not attempted.

## Hostile and missing-data handling

Tested, not just intended:

| Input | Behavior |
|---|---|
| Evidence pointing at a nonexistent task or policy | `FixtureError` — **never silently dropped**. A dropped record is a finding that vanished. |
| `kind: "none"` with no `checked` flag | `FixtureError` naming the ambiguity |
| Several problems at once | **All** reported in one raise, not just the first |
| `"blocking": "yes"` | Rejected — a string must not be truthy-coerced into a blocking question |
| Unknown policy status (`"mostly active"`) | Rejected |
| Missing or malformed JSON file | `FixtureError` naming the file; CLI exits `2` |
| **Empty evidence set** | Every cell `NOT_ASSESSED`; `0` gaps and `0` strengths reported **with a caution explaining that zero gaps here means no fieldwork, not a clean result** |
| A task no policy claims | Still gets a row, as a `NO_POLICY` cell — it does not disappear |

## Files

```
policy_matrix.py          analyzer + generator + CLI (stdlib only)
test_policy_matrix.py     36 unittest cases
fixtures/policies.json    5 fictional policies (4 active, 1 draft)
fixtures/tasks.json       9 ordinary development tasks
fixtures/evidence.json    12 evidence records across all five evidence levels
fixtures/questions.json   5 clarification questions (1 blocking)
sample/                   real output from a real run
WORKFLOW_EXAMPLES.md      6 fictional narratives for leadership discussion
SOURCE_NOTES.md           real vs. fiction vs. UNKNOWN; the AI RMF boundary
```

## Adapting it to a real engagement

Replace the four files in `fixtures/`. The code does not change. Validation will
tell you, in one pass, every record that does not hang together.
