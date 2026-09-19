# UIOWA-117 — Check agreement across report outputs

**Status: PROPOSED CONSISTENCY CHECK / NOT A UNIVERSITY FINDING.**
Every identifier, status and figure in `fixtures/` is fiction. Nothing here describes the
University of Iowa.

Work order: *"Compare the matrix, recommendation register, executive summary, and presentation
source records for inconsistent IDs, counts, phase labels, estimates, and cited finding states.
Deliverable: Cross-output consistency checker and deliberate mismatch examples. Complete when:
Diagnostics name the conflicting artifacts and fields; actual regenerated examples agree after
correction."*

## The problem

A final delivery is not one artifact. It is a findings matrix, a recommendation register, an
executive summary and a presentation — and in this engagement they are produced by different
people at different times.

Each one is internally consistent. Each one's own tests pass. **Nothing checks that they agree with
each other.**

That is how an executive summary ends up saying "three priority findings" over a matrix holding
five, how a deck puts a recommendation in 0-90 days while the register says 90-180, and — worst —
how an estimate the register records as `UNKNOWN` turns up on a slide as a number. None of those are
caught by the lane that produced them, because within that lane nothing is wrong.

## Run it

```bash
cd revenue/uiowa_rfq_18649_output_agreement

python3 output_agreement.py fixtures/consistent                 # PASS, exit 0
python3 output_agreement.py fixtures/mismatched/count_mismatch  # FAIL, exit 1
python3 output_agreement.py fixtures/mismatched/state_mismatch --regenerate /tmp/fixed
python3 make_bundle.py                                          # rebuild every fixture
python3 -m unittest -v test_output_agreement.py                 # 41 tests
```

Exit code is non-zero on any error diagnostic, so this can gate a delivery build. Python 3 standard
library only; no network.

## What it checks

Four artifact classes — `matrix`, `recommendation_register`, `executive_summary`,
`presentation_source` — and ten diagnostics. Every one names **both** conflicting artifacts and the
exact field, because "the outputs disagree" is not actionable:

| Code | Catches |
|---|---|
| `COUNT_MISMATCH` | A count asserted in prose that the rows do not support. |
| `STATE_MISMATCH` | A finding's state stated downstream differs from the matrix. |
| `UNASSESSED_RESULT_CLAIMED` | An output states a **result** for a cell the matrix records as unassessed. |
| `PHASE_MISMATCH` | A recommendation's phase label differs between register and deck. |
| `PHASE_FABRICATED` | An unsequenced recommendation acquires a phase downstream. |
| `ESTIMATE_MISMATCH` | Two outputs carry different estimates for the same item. |
| `ESTIMATE_FABRICATED` | An estimate the register records as `UNKNOWN` appears downstream as a value. |
| `DANGLING_ID` | A cited ID that no source artifact defines. |
| `DUPLICATE_ID` | A repeated `finding_id`/`recommendation_id`, making every citation to it ambiguous. |
| `UNKNOWN_COUNT_SET` | A prose claim counting a set the checker has no definition for (warning). |

Sample diagnostic:

```
[ESTIMATE_FABRICATED] ERROR
  conflict  : executive_summary <-> recommendation_register
  field     : resource_note
  subject   : executive_summary:ES-06
  detail    : states 'About three days.' for REC-SYN-IAM-AI-001, but the register
              records 'UNKNOWN - cannot be estimated before the cell is assessed.'
              A missing estimate became a number somewhere between the register
              and this output.
```

Four pairs are kept deliberately distinct, because collapsing them would lose the finding:

- **`ESTIMATE_FABRICATED` vs `ESTIMATE_MISMATCH`.** Two different numbers is a transcription
  problem. `UNKNOWN` becoming a number is a fabrication. Tests assert each fixture raises one and
  not the other.
- **`UNASSESSED_RESULT_CLAIMED` vs `STATE_MISMATCH`.** Disagreeing about an assessed cell is an
  error of fact. Stating a result for a cell nobody assessed is an error about *our own evidence* —
  it converts "we did not look" into "we looked and it was fine."

## Named sets

Counts only mean something if "priority findings" means the same thing in every artifact, so the
checker owns the definitions (`COUNTABLE_SETS`): `findings`, `assessed_cells`, `unassessed_cells`,
`priority_findings` (status `PARTIAL` or `CONFLICT`), `supported_findings`, `recommendations`,
`near_term_recommendations` (horizon `0-90`).

`assessed_cells` and `unassessed_cells` partition the matrix, and a row with a blank or `UNKNOWN`
status counts as unassessed — never as a result, and never as a zero. A claim counting a set the
checker cannot define raises `UNKNOWN_COUNT_SET` rather than passing silently.

## The mismatch examples are generated, not hand-written

The completion condition is *"actual regenerated examples agree after correction."* A hand-written
broken file can show that a checker fires. It cannot show that the bundle was consistent before the
defect, or that it returns to consistent after correction.

So there is exactly **one** consistent bundle, and each of the ten defects is a single injection
into a copy of it. The tests assert the full round trip: consistent → clean; inject → that exact
diagnostic; regenerate → clean again.

## Correction means recomputing, not editing until the checker goes quiet

Counts, states, phase labels and estimates in a summary or a deck are **derived views** of the
matrix and the register, not independent facts. `regenerate_derived()` recomputes them from source.
Two rules make it trustworthy:

1. **It never rewrites human prose.** It corrects `asserted_count.value` from 3 to 5 and leaves the
   sentence saying "Three". That is exactly the state an author must review. Silently rewriting the
   sentence would hide the disagreement rather than resolve it — `test_regeneration_does_not_rewrite_human_prose`
   asserts this.
2. **It cannot invent a source.** A citation to an ID nobody defined, a duplicated row, and a count
   over an undefined set all *survive* regeneration, because there is nothing to recompute them
   from. `DEFECTS` declares per-defect whether regeneration clears it, and the suite asserts both
   directions — so `--regenerate` on a dangling citation still exits 1. A tool that reported those
   as "corrected" would be fabricating agreement.

## One legitimate cascade, declared

Nine of the ten defects produce exactly one diagnostic. `duplicate_id` produces two, and that is
correct: an extra matrix row really does change every count taken over the matrix, so the summary's
"ten assessed cells" really is wrong now. It is declared in `EXPECTED_CASCADE` with a test asserting
the cascade is *real* (10 → 11 assessed cells), so that any new cascade fails the isolation test and
has to be justified rather than quietly tolerated.

## Field names

Reused from the registers already landed by other lanes — `finding_id`, `recommendation_id`,
`status`, `confidence`, `horizon`, `finding_refs`, `resource_note`, `group`, `area` — and the
synthetic IDs match the corpus in `revenue/uiowa_rfq_18649_report_structure/` so the two lanes tell
one coherent fictional story. Nothing is renamed; a real matrix or register drops in without a
rename pass.

The executive summary and presentation are represented as **claim records** (`claim_id`, `text`,
plus optional `cites` / `asserted_count` / `asserted_state` / `asserted_horizon` /
`asserted_estimate`). A purely narrative claim that asserts nothing checkable is allowed and is not
an error — prose is not required to be a data structure.

## What is real, what is draft

**Real and runnable now:** the checker, all ten diagnostics, the bundle generator, the ten mismatch
fixtures, regeneration, the CLI, and 41 tests.

**Draft:** the claim-record shape for the summary and deck is this lane's proposal. Where
UIOWA-081's executive-summary kit and UIOWA-088's deck architecture define their own native claim
structures, the right move is a thin adapter into this shape — not a rename of theirs. Those lanes
are consumed as input contracts here; this lane does not edit them.

## University inputs that stay UNKNOWN

- The real matrix, register, summary and deck. Everything under `fixtures/` is fiction.
- Which countable sets the University's own report will actually assert over, and their agreed
  definitions. The seven here are a proposal.
- Whether a presentation is in scope at all (the RFQ treats the readout as optional).
- Who owns correcting a disagreement when two outputs conflict, and at which review gate this check
  runs.

## Scope boundary

This checks that a delivery's outputs agree with each other. It is not a formal audit and issues no
compliance determination. It does not assess any individual. It recommends no product or vendor. It
does not judge whether a finding is *correct* — only whether the artifacts describing it say the
same thing.

## Files

```
output_agreement.py         checker, 10 diagnostics, regeneration, CLI
make_bundle.py              consistent bundle + 10 defect injectors
test_output_agreement.py    41 unittest cases
fixtures/consistent/        the known-good bundle
fixtures/mismatched/<name>/ one deliberate defect each
```
