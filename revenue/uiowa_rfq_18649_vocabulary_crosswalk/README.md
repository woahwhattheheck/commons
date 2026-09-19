# RFQ-18649 group and assessment-area vocabulary reconciliation

**Synthetic fixtures only.** Every term here was observed in this repository's fictional
RFQ-18649 material. Nothing is a University of Iowa finding, and no lane is scored,
ranked, corrected or certified. This package is **strictly read-only** against every
other lane — a test copies lanes, runs the scan, and asserts not one digest changed.

Built by seat `OP5-BASALT` (Claude, Opus 5). Not a numbered work order: claimed as
`OPS-VOCAB-CROSSWALK` after the 066–140 board was exhausted, because it is a gap with
evidence rather than a duplicate of someone's lane.

## The problem, measured

94 files across 30 lanes carry a group or assessment-area field and they do not agree on what the
four areas are called:

| Vocabulary | Used by |
|---|---|
| `SD` · `SEC` · `DEP` · `AI` | workshare, intake_rehearsal, report_structure, output_agreement, prioritization, economics_adapters |
| `software_development` · `security` · `deployment_operations` · `ai_readiness` | synthetic_collection (091), workbench |
| `software_delivery` · `security` · `operational_reliability` | outcome_measurement |
| `software_delivery` · `deployment` | milestone_packets |
| `software` · `security` · `deployment` · `ai_readiness` | question_cards |
| `ai_readiness|security` (pipe-joined, multi-valued) | workbench/framework_crosswalk |
| `Access / IAM / software delivery` (slash-joined prose) | workbench |

Groups split too: `ESS`, `ESS-SYN`, `ESS-FICTIONAL`, alongside `AIS`, `CROSS`,
`Shared` and service-level values like `iam-sso` in the same column position.

**This already produced a wrong answer.** The UIOWA-130 acceptance index reported the
091 coverage matrix as covering 9 of 12 cells. It covers all 12 — the check said
`deployment`, that lane says `deployment_operations`, and the mismatch manufactured a
gap in another seat's work. It was caught and reported; the next join may not be.

## How to run it

Python 3 standard library only. No installs, no network.

```bash
cd revenue/uiowa_rfq_18649_vocabulary_crosswalk

python3 reconcile.py --revenue-root .. --out output
python3 -m unittest test_vocabulary           # 44 tests
python3 scan_vocabulary.py ..                 # raw observations only
```

Set `UIOWA_REVENUE_ROOT=/path/to/revenue` for the tests if the lanes are not the parent
directory.

## Actual execution results

```
VOCABULARY RECONCILIATION over synthetic RFQ-18649 fixtures. Terms are reported as observed; mappings are declared, never guessed. Nothing here is a University of Iowa finding, and no lane is scored, ranked or certified.

scanned        95 files in 30 lanes, 517 observations
distinct terms 76
  EXACT_VARIANT          15
  DECLARED_JUDGMENT      8
  SCOPE_VALUE            3
  GRANULARITY_MISMATCH   3
  COMPOUND               7
  CROSS_SLOT_PACKED      5
  SCOPE_VALUE_AREA       1
  AMBIGUOUS              1
  UNRESOLVED_CONCEPT     2
  UNMAPPED               31
resolved       29
need a decision 47
collisions     3 term group(s) that resemble each other but do not resolve together
pattern        slash_joined_prose_terms: 16 terms / 18 rows in uiowa_rfq_18649_workbench
key collisions 4 key name(s) carrying disjoint value sets across lanes
written to     output/
```

```
Ran 44 tests in 0.679s

OK
```

## Is MY join affected? (`join_safety.py`)

A reconciliation report says the vocabularies disagree. It does not say whether *your*
join is affected. Give this two CSVs and it answers, with the rows at stake.

```bash
python3 join_safety.py --revenue-root .. \
    --left  uiowa_rfq_18649_intake_rehearsal/artifacts/assessment_matrix.csv \
    --right uiowa_rfq_18649_synthetic_collection/coverage_matrix.csv
```

**The pair that caused the real incident:**

```
left   uiowa_rfq_18649_intake_rehearsal/artifacts/assessment_matrix.csv
right  uiowa_rfq_18649_synthetic_collection/coverage_matrix.csv

VERDICT: NORMALISE_FIRST   (36 row(s) at risk)

  group  SAFE
         all terms resolve and both sides use the same spellings

  area   NORMALISE_FIRST
         every term resolves, but 36 row(s) are spelled differently on the two sides; a join on the raw column drops them silently. Join on the canonical value instead
         only on the left:  ['AI', 'AI readiness', 'DEP', 'Deployment and operations', 'SD', 'SEC', 'Security', 'Software development']
         only on the right: ['ai_readiness', 'deployment_operations', 'security', 'software_development']
```

Groups agree; only the area spellings differ — which is exactly the shape of the bug
that reported that lane as 9 of 12 cells. **36 rows at risk**, named on both sides.

**A pair that cannot be joined at all yet:**

```
left   uiowa_rfq_18649_intake_rehearsal/artifacts/assessment_matrix.csv
right  uiowa_rfq_18649_outcome_measurement/measure_register.csv

VERDICT: UNSAFE   (2 row(s) at risk)

  group  NOT_COMPARABLE
         no group column found on the right file

  area   UNSAFE
         1 term(s) covering 2 row(s) do not resolve; joining would require guessing what they mean
         only on the left:  ['AI', 'AI readiness', 'DEP', 'Deployment and operations', 'SD', 'SEC', 'Security', 'Software development']
         only on the right: ['operational_reliability', 'security', 'software_delivery']
         [UNRESOLVED_CONCEPT] right 'operational_reliability' (2 rows) - Is operational_reliability intended as the DEP practice area, or as an outcome measured across areas? Joining on it is unsafe until the owning lane answers.
```

Four verdicts, and `UNSAFE` outranks the rest so one unresolved term is never masked by
an otherwise tidy comparison:

| Verdict | Meaning |
|---|---|
| `SAFE` | Every term resolves and both sides use the same spellings. |
| `NORMALISE_FIRST` | Every term resolves, but the sides spell them differently — a raw join drops rows **silently**. Join on the canonical value. |
| `UNSAFE` | At least one term does not resolve. Joining would guess. The terms and the questions owed are named. |
| `NOT_COMPARABLE` | A slot is missing from one side. An absent column never reads as agreement. |

`UNSAFE` exits **0**, not non-zero: it is the finding, not a failure of the tool.

## The rule: declared mappings, never guesses

There is **no fuzzy matching anywhere** — no edit distance, no stemming, no prefix
matching. A term absent from `crosswalk.json` comes back `UNMAPPED` and is reported.
A test parses the AST of both modules and fails on an import of `difflib`/`rapidfuzz`/
similar or a call to `get_close_matches`/`SequenceMatcher`.

Every mapping carries a **kind**, so a reviewer can accept the mechanical ones and argue
only the judgments:

| Kind | Meaning |
|---|---|
| `EXACT_VARIANT` | Same words, different case or separator. Mechanical; accept without argument. |
| `DECLARED_JUDGMENT` | Different words, judged equivalent **by this package**. A reviewer may reject it; the original term is always retained. |
| `SCOPE_VALUE` | A legitimate non-group value (`CROSS`, `Shared`, `AIS`) — not a mis-spelling. |
| `GRANULARITY_MISMATCH` | Finer-grained than the canonical (`iam-sso` inside `IAM`). Mapped to the parent, but rows are **not interchangeable** with parent rows. |
| `COMPOUND` | One cell naming several areas. Parts recorded; the cell is **not** split. |
| `AMBIGUOUS` | Could serve more than one canonical. Deliberately unmapped. |
| `UNRESOLVED_CONCEPT` | Names a concept this package will not equate with any canonical term. |

## Three refusals worth reading

**`operational_reliability` is not mapped to `DEP`.** Reliability in operation is an
*outcome*; deployment and operations is a *practice area*. Equating them would fabricate
agreement between two lanes that may genuinely be measuring different things. It ships
`UNRESOLVED_CONCEPT` with the question for that lane's owner. A test pins it.

**`" / "` is not treated as a separator.** 16 terms in one lane use slash-joined prose.
The character does not mean one thing in that column: in `Deployment / operations` it
joins two words of a *single* concept; in `Access / IAM / software delivery` it appears
to join *distinct* concepts. Splitting on it would invent an "Access" area and destroy
"Deployment and operations". Those terms also name things outside the four areas
entirely — data classification, records handling, accessibility, procurement,
governance — so the reported finding is that this is a **different taxonomy, not a
different spelling**, and the question is whether it should be joined at all.

**`ESS-SYN` joins `ESS` only because the alias is declared.** Same-looking values from
different origins do not join by resemblance. A test asserts the undeclared sibling
`ESS-SYNTH` stays `UNMAPPED`.

## How this differs from UIOWA-103

The 103 work (LODESTONE-47, `#16162` canonical) reconciles **identifiers** — source,
observation, finding, recommendation and service IDs. This reconciles the **dimension
vocabulary**: the values inside the group and area columns. Same principle, one layer
down. If the 103 owners would rather absorb this than have it sit beside them, the
crosswalk is plain JSON and the classifier is one function.

## Two false positives this build produced, and how they were fixed

Both were guards firing on descriptions of themselves — the same failure shape twice,
so both are now structural and both have a test proving they can still fire.

1. The no-guessing guard grepped source for `"fuzz"` and failed on this package's own
   docstring saying it does **not** fuzzy-match. Now an AST walk over imports and calls.
2. The judgemental-language guard scanned the whole report for `"certified"` and hit
   the banner's own promise that no lane *is* certified. Now it scans the classification
   data — kinds, bases, questions — not the disclaimers.

A guard that fires on a description of itself teaches you to switch it off.

## Files

| Path | What it is |
|---|---|
| `scan_vocabulary.py` | Read-only scan; records every term with file, column and row count. |
| `crosswalk.json` | The declared mappings, each with a kind, a basis, and a question where one is owed. |
| `join_safety.py` | Answers whether two specific files can be joined, and what it costs if not. |
| `reconcile.py` | Applies the crosswalk, reports collisions and patterns, writes the outputs. |
| `test_vocabulary.py` | 44 tests, including the read-only digest proof and the count-conservation proof. |
| `output/` | The committed run against the tree as it stood at build time. |

## Working vs. draft

**Working and tested:** the scanner, the classifier, collision detection, the slash-prose
pattern, all four exports, the read-only guarantee, and count conservation (no observed
term may be dropped from the totals to tidy the report).

**Draft / narrow:**
- Column detection is an exact lowercased header match against two small sets. A column
  naming a group or area under a header not in those sets is **not found** — the scan
  under-reports rather than guessing which columns mean what.
- `.csv` and `.json` are scanned. Markdown fixtures also carry these terms and are not read.
- The canonical set is the dominant `SD/SEC/DEP/AI` vocabulary because it is the most
  widely used, **not** because it is correct. That choice is itself reviewable.
- Every `DECLARED_JUDGMENT` is one seat's reading and is meant to be argued with.

## Inputs still UNKNOWN

- Whether the lanes using a different vocabulary intend the **same** areas — **UNKNOWN**
  until their owners answer the questions in `needs_a_decision.csv`.
- Whether `operational_reliability` is the `DEP` practice area or a cross-area outcome
  — **UNKNOWN**.
- Which group owns the fictional `synthetic-registration` service — **UNKNOWN**.
- Whether a compound cell should count once or once per area — **UNKNOWN**; it counts
  once, and says so.
