# CSV export-safety audit — UIOWA RFQ 18649 delivery kit

Read-only audit of every published `*.csv` in the delivery kit, against the one standard they all share: **the file has to be usable by a Clark's or University reader who does not have the producing environment.**

**This report edits nothing.** Findings are handed to the lane that owns the file, with the exact path, row and column.

- Files scanned: **170** across **50** lane(s)
- Data rows: **8740** · cells: **74588**
- Cells already neutralized against formula injection: **1**
- Findings: **25**

| Code | Count |
|---|---|
| `LEADING_COMMENT_LINE` | 20 |
| `NULL_SEMANTICS_AMBIGUOUS` | 3 |
| `NULL_SEMANTICS_DECLARED` | 1 |
| `RAGGED_ROW` | 1 |

## What a clean result does not mean

Zero findings means **no issue detected by these eight checks** — never "certified", "compliant" or "safe". A file that could not be read is reported as `UNREADABLE` and counts as UNKNOWN, never as a pass. These checks look at bytes, not at whether the numbers in the file are right.

## Findings by lane

### `uiowa_rfq_18649_acceptance_map` — 6 finding(s)

| Severity | Code | File | Row | Column | Detail |
|---|---|---|---|---|---|
| LOW | `LEADING_COMMENT_LINE` | `output/acceptance_index.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |
| LOW | `LEADING_COMMENT_LINE` | `output/needs_engagement_evidence.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |
| LOW | `LEADING_COMMENT_LINE` | `output/sample_packet/uiowa_rfq_18649_intake_rehearsal__artifacts__assessment_matrix.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |
| LOW | `LEADING_COMMENT_LINE` | `output/sample_packet/uiowa_rfq_18649_intake_rehearsal__artifacts__evidence_register.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |
| LOW | `LEADING_COMMENT_LINE` | `output/sample_packet/uiowa_rfq_18649_intake_rehearsal__artifacts__intake_diagnostics.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |
| LOW | `LEADING_COMMENT_LINE` | `output/sample_packet/uiowa_rfq_18649_intake_rehearsal__artifacts__source_register.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |

### `uiowa_rfq_18649_ai_eval_kit` — 1 finding(s)

| Severity | Code | File | Row | Column | Detail |
|---|---|---|---|---|---|
| INFO | `NULL_SEMANTICS_DECLARED` | `examples/results.csv` | — | analyst_followup | 2 empty cell(s) alongside 'NA'x2, in a file that uses the \\N null sentinel. The three states ARE distinguishable, but only to a reader who knows the convention: ship a column dictionary beside the file |

### `uiowa_rfq_18649_intake_rehearsal` — 11 finding(s)

| Severity | Code | File | Row | Column | Detail |
|---|---|---|---|---|---|
| LOW | `LEADING_COMMENT_LINE` | `artifacts/assessment_matrix.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |
| LOW | `LEADING_COMMENT_LINE` | `artifacts/evidence_register.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |
| LOW | `LEADING_COMMENT_LINE` | `artifacts/intake_diagnostics.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |
| LOW | `LEADING_COMMENT_LINE` | `artifacts/source_register.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |
| LOW | `LEADING_COMMENT_LINE` | `sources/ess/ess-deploy-log-2026-08.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |
| LOW | `LEADING_COMMENT_LINE` | `sources/ess/ess-pull-request-sample-2026Q3.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |
| LOW | `LEADING_COMMENT_LINE` | `sources/iam/iam-change-review-export-2026-08.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |
| LOW | `LEADING_COMMENT_LINE` | `sources/iam/iam-recert-campaign-2026Q2.csv` | 0 | — | 2 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |
| LOW | `LEADING_COMMENT_LINE` | `sources/ris/ris-backup-job-report-2026-08.csv` | 0 | — | 2 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |
| LOW | `LEADING_COMMENT_LINE` | `sources/ris/ris-release-sample-2026Q3.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |
| LOW | `LEADING_COMMENT_LINE` | `sources/ris/ris-vuln-scan-2026-09.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |

### `uiowa_rfq_18649_readout_deck` — 2 finding(s)

| Severity | Code | File | Row | Column | Detail |
|---|---|---|---|---|---|
| MEDIUM | `NULL_SEMANTICS_AMBIGUOUS` | `examples/readout-planning-table.csv` | — | deck_value | 8 empty cell(s) alongside 'UNKNOWN'x4, and no declared null sentinel; a reader cannot tell 'never recorded' from 'recorded as empty' from 'not applicable', and those are three different facts |
| MEDIUM | `NULL_SEMANTICS_AMBIGUOUS` | `examples/readout-planning-table.csv` | — | report_value | 8 empty cell(s) alongside 'UNKNOWN'x4, and no declared null sentinel; a reader cannot tell 'never recorded' from 'recorded as empty' from 'not applicable', and those are three different facts |

### `uiowa_rfq_18649_vocabulary_crosswalk` — 3 finding(s)

| Severity | Code | File | Row | Column | Detail |
|---|---|---|---|---|---|
| LOW | `LEADING_COMMENT_LINE` | `output/needs_a_decision.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |
| LOW | `LEADING_COMMENT_LINE` | `output/observations.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |
| LOW | `LEADING_COMMENT_LINE` | `output/term_crosswalk.csv` | 0 | — | 1 comment line(s) before the header; a spreadsheet import shows them as a one-cell row and then reads the real header as data, so the columns arrive unnamed. Consider a sidecar notice file, or accept it and say so in the lane's README |

### `uiowa_rfq_18649_workbench` — 2 finding(s)

| Severity | Code | File | Row | Column | Detail |
|---|---|---|---|---|---|
| MEDIUM | `NULL_SEMANTICS_AMBIGUOUS` | `41-synthetic-change-trace.csv` | — | gap_or_conflict | 9 empty cell(s) alongside 'none'x1, and no declared null sentinel; a reader cannot tell 'never recorded' from 'recorded as empty' from 'not applicable', and those are three different facts |
| HIGH | `RAGGED_ROW` | `41-synthetic-change-trace.csv` | 8 | — | 22 cells against a 21-column header; every column after the break is misaligned |

