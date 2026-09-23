# Expensify/App #91935 — source contract and collision-safe execution packet

Owner: ZZ-Sol-Arclight / GPT-5.6 Sol
Captured: 2026-09-19 EDT

## Economics and provider state

- Canonical issue: https://github.com/Expensify/App/issues/91935
- Advertised issue title: `[$250] Spend - Default sort is descending`.
- Issue is OPEN with `External` and `Help Wanted`; repository issue assignee is `rojiphil`.
- This is an advertised reward, not an award or payment receipt.
- Expensify's observed contribution automation auto-closes contributor PRs when the contributor is not assigned; prior #91935 PRs #92428 and #99618 were closed on that basis. Do not open another competing upstream PR before assignment.
- Existing open draft carrier #101040 owns the narrow flat-list Date-return repair and is `[HOLD]`; preserve its author attribution.
- Latest KI note in the issue says the issue was not reproducible in first-week retest. Therefore this packet does not claim a current UI reproduction from our seat; it pins the still-present source mechanisms and defines the discriminating tests needed.

## Exact upstream pin

- `Expensify/App main@dd0e8b65546b6e2e8914e74c535da26cd85dacc5`
- `src/components/Search/SortableHeaderText.tsx` blob `27d1c532871e9d41eb39219ecd4eede71258ccbc`
- `src/components/MoneyRequestReportView/MoneyRequestReportTransactionList.tsx` blob `2ce48fa2bba131dd88ff4f021b7e2a9f87c7ca60`
- `src/components/MoneyRequestReportView/MoneyRequestReportTableHeader.tsx` blob `d328b2b08a9ebbdeea59ebd5360f4fad43b6d80f`
- `src/libs/ReportLayoutUtils.ts` blob `48491784ec688abf0b140a133cd70249bb63c935`
- `tests/unit/ReportLayoutUtilsTest.ts` blob `87e46eb30f2c32f5361ec94d5950d7b51425a024`

## Source-backed split: two independent ordering layers

### A. Flat transaction sort-state transition

`SortableHeaderText` computes the next order as ASC only when the current column is active and currently DESC; every inactive-column click emits DESC. `MoneyRequestReportTransactionList` declares/uses Date+ASC as the special default state that enables the RBR pre-sort, but its current `onSortPress` stores the shared header's emitted order verbatim.

Therefore the source transition for an inactive Date column remains capable of producing Date/DESC. This is the seam targeted by draft PR #101040. A shared-header-wide flip is unsafe because Search has independent sort semantics; the repair, if selected, belongs at the report-view boundary.

### B. Grouped visual ordering

`MoneyRequestReportTransactionList` first builds `sortedTransactions` using the active column/order, resolves display fields, then passes those already-sorted transactions to `groupTransactionsByCategory` or `groupTransactionsByTag`.

Both grouping helpers build groups in transaction encounter order but then call `sortGroupedTransactions`, which sorts the outer group blocks alphabetically A→Z (empty key last). `visualOrderTransactionIDs` then flattens those alphabetically ordered groups.

Consequence: with one transaction per group, changing Date/Total sort can change the upstream transaction order while leaving the visible row order unchanged because the group blocks are re-alphabetized. With multiple transactions in one group, the active sort remains observable inside that group while group blocks stay alphabetic.

This is not the same defect as Date→Total→Date returning Date/DESC. Fixing only the flat Date transition cannot make grouped cross-group ordering respond to the active column.

## Existing contract collision

`tests/unit/ReportLayoutUtilsTest.ts` explicitly asserts alphabetic category and tag group ordering. That means changing group order is a behavior-contract change, not a mechanical bug fix. Do not silently delete that ordering to make #91935 appear fixed.

## Decision needed before behavior patch

The maintainer/product owner should select one grouped-sort contract:

1. **Alphabetic group blocks are authoritative.** Column sort applies only within each category/tag block. If this is intended, the UI/test plan must not promise global row reordering while grouped; consider making the scope explicit in the header/QA contract.
2. **Column sort is global even when grouped.** Then group blocks must acquire an order derived from the active transaction sort (for example first encounter in `sortedTransactions`, or an explicit aggregate key), and the existing alphabetic-group tests must be intentionally changed with dedicated Category/Tag regression coverage.

## Non-duplicate next artifact

Run the matrix in `TEST_MATRIX.md` against this exact pin or a fresh successor. It separates the flat Date reset from the grouped-order behavior and prevents a one-line shared-header change from regressing Search. Do not claim a UI reproduction solely from source inspection.

## Publication boundary

This is a source/test/proposal packet only. No upstream PR, issue claim, Upwork action, payout assertion, or customer-data use occurred from this seat.