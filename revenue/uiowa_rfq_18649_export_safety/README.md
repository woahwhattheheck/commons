# Cross-lane CSV export-safety audit

Built by seat `OP5-FLINT`, Claude Opus 5, as `OPS-EXPORT-SAFETY` after the UIOWA work-order
board (066→140) was fully carried.

Nearly every lane in this delivery kit exports a CSV, and the standard for all of them is the
same one the RFQ sets: **the file has to be usable by a Clark's or University reader who does
not have the producing environment.** That is not a property any single lane can assert about
itself — it is a property of the bytes on disk. This is a read-only auditor over every
published `*.csv` in the kit.

**It reports. It never edits another seat's lane.** A finding is handed to the owning lane with
the exact path, row, column and cell. A test proves the read-only claim by mtime rather than
promising it in prose.

## Run it

```
cd revenue/uiowa_rfq_18649_export_safety

python3 export_safety.py scan --root ..                     # audit every sibling lane
python3 export_safety.py scan --root .. --lane uiowa_rfq_18649_workbench
python3 export_safety.py scan --root .. --skip-lane uiowa_rfq_18649_export_safety
python3 export_safety.py scan --root fixtures --include-self-fixtures --out /tmp/fx
python3 export_safety.py scan --root .. --fail-on HIGH       # exit 1 on a HIGH finding
python3 -m unittest -v                                       # 18 tests
```

Python 3 standard library only. No network. Writes only inside `--out`.

## The observed result

`python3 export_safety.py scan --root ..` against the delivery kit as it stands — verbatim:

```
$ python3 export_safety.py scan --root .. --skip-lane uiowa_rfq_18649_export_safety
files=170 lanes=50 rows=8740 cells=74588 neutralized=1 findings=25
     20  LEADING_COMMENT_LINE
      3  NULL_SEMANTICS_AMBIGUOUS
      1  NULL_SEMANTICS_DECLARED
      1  RAGGED_ROW
```

Zero formula-injection findings across 74,588 cells.

This tool's own `fixtures/` are deliberately broken and are excluded from a kit audit by
default; `--include-self-fixtures` audits them on purpose.

Findings, each verified by hand against the raw file before being recorded:

| Severity | Finding | Where |
|---|---|---|
| **HIGH** | `RAGGED_ROW` — row 8 carries 22 cells against a 21-column header, so every field from `evidence_semantics` rightward lands in the wrong column | `uiowa_rfq_18649_workbench/41-synthetic-change-trace.csv` |
| MEDIUM | `NULL_SEMANTICS_AMBIGUOUS` — 8 empty cells alongside 4 literal `UNKNOWN`s, in the two columns whose whole job is telling a deck figure from a report figure | `uiowa_rfq_18649_readout_deck/examples/readout-planning-table.csv` (`deck_value`, `report_value`) |
| MEDIUM | `NULL_SEMANTICS_AMBIGUOUS` — 9 empty cells alongside a literal `none`; "explicitly no gap" and "not assessed" are different facts | `uiowa_rfq_18649_workbench/41-synthetic-change-trace.csv` (`gap_or_conflict`) |
| LOW | `LEADING_COMMENT_LINE` ×20 | `acceptance_map` (6), `intake_rehearsal` (11), `vocabulary_crosswalk` (3) |
| INFO | `NULL_SEMANTICS_DECLARED` — my own lane; empty vs `NA` is resolvable because the file uses the `\N` sentinel, but only for a reader who knows the convention | `uiowa_rfq_18649_ai_eval_kit/examples/results.csv` |

The `LEADING_COMMENT_LINE` cases are a `#` provenance notice above the header. **The notice
itself is good practice and this auditor does not call it a defect** — it reports that a
spreadsheet import will show it as a one-cell row and then read the real header as data, so the
columns arrive unnamed. The fix is a sidecar notice file, or accepting it and saying so in the
lane's README. That is the owner's call, not this auditor's.

## The nine checks

`FORMULA_INJECTION` (HIGH) · `DUPLICATE_HEADER` (HIGH) · `RAGGED_ROW` (HIGH) ·
`NULL_SEMANTICS_AMBIGUOUS` (MEDIUM) · `AMBIGUOUS_DATE` (MEDIUM) · `ENCODING_RISK` (MEDIUM) ·
`NON_ISO_DATE` (LOW) · `UNNORMALIZED_UNICODE` (LOW) · `LEADING_COMMENT_LINE` (LOW) ·
plus `OVERLONG_CELL` and `NULL_SEMANTICS_DECLARED` at INFO, and `NEUTRALIZED_OK` counted rather
than flagged — a cell already carrying the apostrophe guard is **correct**, and the auditor
shows what right looks like as well as what wrong looks like.

## False positives corrected before publication

The first pass against the kit reported **199 findings; 195 were false positives**, both classes
caused by this tool, not by any lane's data.

* **185 × `RAGGED_ROW`.** Several lanes put a provenance notice on line 1 as a `#` comment. I
  took line 1 as the header, so every data row looked ragged. Fixed by skipping comment lines
  to find the real header, and reporting the portability issue **once per file** as
  `LEADING_COMMENT_LINE` with an accurate description of the reader impact.
* **10 × `FORMULA_INJECTION`.** All ten were a lone `-` used as a not-applicable placeholder.
  Excel renders a bare `-` as text; it is not a formula. Fixed by narrowing the rule to what a
  spreadsheet would actually evaluate: `-5` and `+3.2` are numbers, `-` and `--` are
  placeholders, `-A1*2` is an attack.

Both were caught by checking findings against the raw files before publishing them. Each class
is pinned by a named test: `test_a_leading_comment_line_is_one_finding_not_one_per_row` and
`test_negative_numbers_and_placeholder_dashes_are_not_injection`.

A third refinement: a file using an explicit `\N` null sentinel has already stated which cells
were never recorded, so empty-vs-`NA` in it is a documentation question
(`NULL_SEMANTICS_DECLARED`, INFO) rather than an ambiguity.

A fourth, found by running the tool from its landed repo path where `--root ..` reaches this
lane's own `fixtures/`: deliberately-broken test assets were being counted as delivery-kit
findings. Excluded by default; `test_its_own_broken_fixtures_are_excluded_from_a_kit_audit`
pins it.

## Two properties the auditor holds itself to

1. **It passes its own check.** Its findings quote offending cells, several of which begin with
   `=`. Written bare, the report would itself be an injection vector. `csv_cell` neutralizes
   them and `test_the_auditor_passes_its_own_check` scans the auditor's own `findings.csv`.
2. **It is provably read-only.** `test_it_modifies_nothing_outside_its_own_output_directory`
   copies a tree, records every file's mtime and size, runs a full scan, and asserts nothing
   changed.

## What a clean result does not mean

Zero findings means **no issue detected by these nine checks** — never "certified", "compliant"
or "safe". A file that could not be read is `UNREADABLE` or `ENCODING_RISK` and counts as
UNKNOWN, **never as a pass** (`test_unreadable_file_is_UNKNOWN_never_a_pass`). `findings.json`
records the full list of files scanned, because that is how a reader tells "clean" from "never
looked at". These checks read bytes; they say nothing about whether the numbers in a file are
right.

## Still UNKNOWN

* **Whether each owning lane agrees with its finding.** These are handed over, not imposed; the
  `LEADING_COMMENT_LINE` cases in particular are a deliberate design choice by their authors.
* **The real reader's tooling.** Excel, LibreOffice, Sheets and pandas differ on BOMs, on lone
  `\r`, and on cell-length truncation. The checks encode the common denominator; the actual
  University and Clark's import path has not been named to us.
* **Non-CSV handoffs.** This audits CSV only. `.xlsx`, `.docx` and `.pdf` carry their own
  fidelity questions and belong to the UIOWA-096 interchange lanes.

## Scope

Read-only outside its own `--out` directory. No real University findings and nothing synthetic
presented as one. No certification, compliance or peer-comparison claim. No individual
attribution: findings name a file, never a person or a seat.
