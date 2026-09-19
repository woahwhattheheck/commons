# Cross-lane exported-artifact safety audit (CSV + JSON)

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

python3 export_safety.py scan --root .. --lane-prefix uiowa_rfq_18649_   # CSV audit
python3 json_safety.py   scan --root .. --lane-prefix uiowa_rfq_18649_   # JSON audit
python3 export_safety.py scan --root ..                     # audit every sibling lane
python3 export_safety.py scan --root .. --lane uiowa_rfq_18649_workbench
python3 export_safety.py scan --root .. --skip-lane uiowa_rfq_18649_export_safety
python3 export_safety.py scan --root fixtures --include-self-fixtures --out /tmp/fx
python3 export_safety.py scan --root .. --fail-on HIGH       # exit 1 on a HIGH finding
python3 -m unittest -v                                       # 35 tests
```

Python 3 standard library only. No network. Writes only inside `--out`.

## The observed result

`python3 export_safety.py scan --root ..` against the delivery kit as it stands — verbatim:

```
$ python3 export_safety.py scan --root .. --lane-prefix uiowa_rfq_18649_ \
      --skip-lane uiowa_rfq_18649_export_safety
files=144 lanes=51 rows=3085 cells=26986 neutralized=1 findings=25
     20  LEADING_COMMENT_LINE
      3  NULL_SEMANTICS_AMBIGUOUS
      1  NULL_SEMANTICS_DECLARED
      1  RAGGED_ROW
```

Zero formula-injection findings across 26,986 cells.

An earlier run of this tool reported `files=170 … cells=74588`. That scan had no
`--lane-prefix` and therefore included CSVs belonging to unrelated projects in the same
`revenue/` directory. The findings were identical — all 25 were in delivery-kit lanes — but the
denominator was wrong, so `--lane-prefix` now scopes the audit and the figure above is the
corrected one.

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
* **Remaining handoffs.** CSV and JSON are audited. `.xlsx`, `.docx` and `.pdf` are not; those
  carry their own fidelity questions and belong to the UIOWA-096 interchange lanes.
* **Whether the 46 missing trailing newlines matter to anyone.** They are diff hygiene, not a
  reader problem, and are reported at INFO for that reason.

## JSON audit — `json_safety.py`

The CSV auditor asks whether a spreadsheet reader can open a file. `json_safety.py` asks the
JSON equivalent: **can a reader who is not Python parse this file at all?** Python's `json`
module is more permissive than the specification in ways that produce Python-only files:

* `json.dump` writes bare `NaN`, `Infinity` and `-Infinity` by default. `JSON.parse`, Go's
  `encoding/json` and Jackson reject them and the file does not open at all. Producer fix:
  `allow_nan=False`.
* `json.load` silently keeps the **last** of two identical keys in one object, so a duplicated
  key loses data with no error anywhere. A fixture demonstrates it: `duplicate_keys.json` parses
  cleanly in Python and the first `finding_id` is simply gone.
* A lone surrogate escape yields a `str` Python accepts and UTF-8 cannot encode.
* An integer above 2^53 is rounded silently by any JavaScript reader.

Ten checks: `INVALID_JSON`, `NON_STRICT_LITERAL`, `DUPLICATE_OBJECT_KEY`, `LONE_SURROGATE`,
`NOT_UTF8` (HIGH) · `BOM_PRESENT`, `INT_PRECISION_LOSS`, `CONTROL_CHAR_IN_STRING`, `EMPTY_FILE`
(MEDIUM) · `UNNORMALIZED_UNICODE` (LOW) · `NO_TRAILING_NEWLINE` (INFO).

```
$ python3 json_safety.py scan --root .. --lane-prefix uiowa_rfq_18649_ \
      --skip-lane uiowa_rfq_18649_export_safety
files=208 findings=46
     46  NO_TRAILING_NEWLINE
```

The delivery kit's JSON is strict-parser clean: zero HIGH and zero MEDIUM findings across 208
artifacts. The 46 `NO_TRAILING_NEWLINE` are INFO-level diff hygiene, not a reader problem.

Two defects in this auditor, both caught by its own tests and fixed:

* It **crashed writing its own findings**: the sample captured for a `LONE_SURROGATE` finding was
  itself a lone surrogate and could not be encoded as UTF-8. A detector that dies on a detection
  is not a detector. `safe_text` now sanitizes every captured value.
* Its first non-strict check was a regex over the raw bytes, which flagged the **word** `NaN`
  wherever it appeared — including inside this auditor's own explanatory prose, so it reported
  itself. Detection now uses `json.loads(parse_constant=…)`, which fires only on a real bare
  token and cannot false-positive.
  Regression: `test_the_word_NaN_in_prose_is_not_a_non_strict_literal`.

## Scope

Read-only outside its own `--out` directory. No real University findings and nothing synthetic
presented as one. No certification, compliance or peer-comparison claim. No individual
attribution: findings name a file, never a person or a seat.
