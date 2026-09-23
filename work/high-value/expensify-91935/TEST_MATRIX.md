# #91935 discriminating test matrix

Pin: `Expensify/App main@dd0e8b65546b6e2e8914e74c535da26cd85dacc5`

## Fixture design

Use synthetic test transactions only. Give rows different transaction dates and different amounts so ASC/DESC is visible; do not rely on same-day stable-sort ties. For grouped cases, cover both (a) one row per Category/Tag and (b) multiple rows in one group.

| Case | Layout | Grouping | Action | Source-predicted current result | What it discriminates |
| --- | --- | --- | --- | --- | --- |
| F1 | flat | none | initial | Date/ASC + RBR pre-sort eligible | baseline default |
| F2 | flat | none | Date → Total | Total/DESC | inactive header defaults DESC |
| F3 | flat | none | Date → Total → Date | Date/DESC | flat return-to-default mismatch |
| F4 | flat | none | Date active, click Date twice | DESC then ASC | active-column toggle must stay intact |
| C1 | grouped | Category; one row/group | sort Date ASC↔DESC | group blocks remain category A→Z | outer group sort masks transaction sort |
| C2 | grouped | Category; multiple rows/group | sort Date ASC↔DESC | group blocks A→Z; rows inside a group reorder | separates outer vs inner ordering |
| T1 | grouped | Tag; one row/group | sort Total ASC↔DESC | group blocks remain tag A→Z | tag parity |
| T2 | grouped | Tag; multiple rows/group | sort Total ASC↔DESC | group blocks A→Z; rows inside a group reorder | tag inner ordering |
| R1 | grouped | Category or Tag | Date → Total → Date | combines inactive-column Date/DESC with fixed A→Z group blocks | proves two mechanisms coexist |
| S1 | Search table | none | switch inactive Date column | preserve Search's established default/toggle contract | catches shared-header regression |

## Component boundaries to exercise

- Drive the real report header chain (`MoneyRequestReportTableHeader` → `SortableTableHeader` → `SortableHeaderText`) for F2/F3/F4 instead of reimplementing the ternary in a test helper.
- Exercise `MoneyRequestReportTransactionList` state for `isDefaultSort` so Date/ASC and the RBR-set gate are observed together.
- Exercise the actual `groupTransactionsByCategory` and `groupTransactionsByTag` helpers for grouped cases; assert both group-key order and transaction IDs within each group.
- Keep one Search regression proving the report-specific repair does not alter unrelated Search sorting behavior.

## Acceptance fork

If product chooses alphabetic group blocks as authoritative, C1/T1 should be documented expected behavior and #91935 should be scoped to the flat Date reset only.

If product chooses global column sort while grouped, C1/T1 should become failing regressions on current main and the implementation must deliberately replace alphabetic outer-group ordering with a selected sort-derived policy; existing alphabetic group-order tests must be updated explicitly, not bypassed.