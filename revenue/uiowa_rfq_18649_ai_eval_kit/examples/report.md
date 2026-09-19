# AI usefulness evaluation — results

**UIOWA-075 preparation artifact. Every task, output, reviewer and locator below is FICTION** invented for this kit. Nothing here is a University of Iowa finding, system, document or person.

## What was measured

Four measures, kept separate on purpose:

- **Correctness** — of what the output asserted, how much was right (precision against the answer key).
- **Completeness** — of what the answer key requires, how much the output covered.
- **Repair time** — minutes to make the output usable. Reported as **MEASURED** where an operator timed it and **MODELED** where the answer key's repair costs were used. The two are never averaged together.
- **Usefulness** — expressed as net minutes saved against an explicit `from_scratch_minutes` assumption, not as an opinion. Where that assumption or the generation time is absent, the task's usefulness is `UNKNOWN` and it leaves the total.

No model is called by this kit. It scores recorded outputs. **It produces no single composite score and does not rate any individual.**

## Workflow: `assisted-draft-v1`

AI-assisted draft + analyst review (FICTIONAL recorded run)

> Recorded offline. generation_minutes is wall-clock to first complete draft; recorded_repair_minutes is an operator-measured figure where one was taken, and null where repair time was NOT measured.

| Measure | Value | Basis |
|---|---|---|
| Tasks scored | 12 of 12 | — |
| Tasks NOT_RUN (excluded from every denominator) | none | — |
| Completeness (mean) | 0.7292 | answer key |
| Correctness (mean) | 0.75 | answer key |
| Repair minutes — measured subtotal | 112 | MEASURED on 11 task(s) |
| Repair minutes — modeled, all scored tasks | 109 | MODELED from answer key |
| Tasks with no measured repair time | DOC-MIS-04 | UNKNOWN |
| Forbidden-element fires (wrong/invented/stale assertions) | 3 | answer key |
| Missing-information tasks where the output did NOT abstain | DOC-MIS-04, TST-MIS-08 | answer key |
| Generation minutes (timed tasks) | 27 | recorded |
| Repair minutes used (timed tasks) | 144 | measured where available, else modeled |
| From-scratch minutes (timed tasks) | 380 | stated assumption |
| **Net minutes saved (timed tasks)** | 209 | derived |
| Tasks with UNKNOWN time inputs (excluded) | REQ-MIS-12 | UNKNOWN |

### By case class

| Case class | Scored | Completeness | Correctness | Modeled repair (min) | Forbidden fires |
|---|---|---|---|---|---|
| ordinary | 3 | 0.9167 | 1.0 | 11 | 0 |
| ambiguous | 3 | 1.0 | 1.0 | 0 | 0 |
| stale_context | 3 | 0.6667 | 0.6667 | 31 | 1 |
| missing_information | 3 | 0.3333 | 0.3333 | 67 | 2 |

### Per task

| Task | Class | Status | Variant | Compl. | Corr. | Repair (min) | Basis | Net saved (min) | Fired | Tied |
|---|---|---|---|---|---|---|---|---|---|---|
| DOC-ORD-01 | ordinary | SCORED | V1 | 1.0 | 1.0 | 6 | MEASURED | 37 | — | — |
| DOC-AMB-02 | ambiguous | SCORED | V1 | 1.0 | 1.0 | 4 | MEASURED | 24 | — | — |
| DOC-STA-03 | stale_context | SCORED | V1 | 0.0 | 0.0 | 28 | MEASURED | 4 | F-RETIRED-EP | — |
| DOC-MIS-04 | missing_information | SCORED | V1 | 0.0 | 0.0 | 34 | MODELED | -16 | F-INVENT-RET | — |
| TST-ORD-05 | ordinary | SCORED | V1 | 1.0 | 1.0 | 8 | MEASURED | 49 | — | — |
| TST-AMB-06 | ambiguous | SCORED | V2 | 1.0 | 1.0 | 5 | MEASURED | 32 | — | — |
| TST-STA-07 | stale_context | SCORED | V1 | 1.0 | 1.0 | 9 | MEASURED | 37 | — | — |
| TST-MIS-08 | missing_information | SCORED | V1 | 0.0 | 0.0 | 31 | MEASURED | -8 | F-INVENT-409 | — |
| REQ-ORD-09 | ordinary | SCORED | V1 | 0.75 | 1.0 | 12 | MEASURED | 16 | — | — |
| REQ-AMB-10 | ambiguous | SCORED | V1 | 1.0 | 1.0 | 3 | MEASURED | 20 | — | — |
| REQ-STA-11 | stale_context | SCORED | V1 | 1.0 | 1.0 | 4 | MEASURED | 14 | — | — |
| REQ-MIS-12 | missing_information | SCORED | V1 | 1.0 | 1.0 | 2 | MEASURED | UNKNOWN | — | — |

## Workflow: `manual-draft-v1`

Unassisted analyst draft (FICTIONAL recorded run)

> Recorded offline. Same 12 tasks, same reviewers. REQ-STA-11 was NOT attempted in this run; there is deliberately no record for it.

| Measure | Value | Basis |
|---|---|---|
| Tasks scored | 11 of 12 | — |
| Tasks NOT_RUN (excluded from every denominator) | REQ-STA-11 | — |
| Completeness (mean) | 0.9242 | answer key |
| Correctness (mean) | 1.0 | answer key |
| Repair minutes — measured subtotal | 17 | MEASURED on 11 task(s) |
| Repair minutes — modeled, all scored tasks | 19 | MODELED from answer key |
| Tasks with no measured repair time | none | UNKNOWN |
| Forbidden-element fires (wrong/invented/stale assertions) | 0 | answer key |
| Missing-information tasks where the output did NOT abstain | none | answer key |
| Generation minutes (timed tasks) | 317 | recorded |
| Repair minutes used (timed tasks) | 17 | measured where available, else modeled |
| From-scratch minutes (timed tasks) | 360 | stated assumption |
| **Net minutes saved (timed tasks)** | 26 | derived |
| Tasks with UNKNOWN time inputs (excluded) | REQ-MIS-12 | UNKNOWN |

### By case class

| Case class | Scored | Completeness | Correctness | Modeled repair (min) | Forbidden fires |
|---|---|---|---|---|---|
| ordinary | 3 | 0.8889 | 1.0 | 12 | 0 |
| ambiguous | 3 | 0.8333 | 1.0 | 7 | 0 |
| stale_context | 2 | 1.0 | 1.0 | 0 | 0 |
| missing_information | 3 | 1.0 | 1.0 | 0 | 0 |

### Per task

| Task | Class | Status | Variant | Compl. | Corr. | Repair (min) | Basis | Net saved (min) | Fired | Tied |
|---|---|---|---|---|---|---|---|---|---|---|
| DOC-ORD-01 | ordinary | SCORED | V1 | 1.0 | 1.0 | 0 | MEASURED | 5 | — | — |
| DOC-AMB-02 | ambiguous | SCORED | V1 | 0.5 | 1.0 | 7 | MEASURED | -3 | — | — |
| DOC-STA-03 | stale_context | SCORED | V1 | 1.0 | 1.0 | 0 | MEASURED | 5 | — | — |
| DOC-MIS-04 | missing_information | SCORED | V1 | 1.0 | 1.0 | 0 | MEASURED | 2 | — | — |
| TST-ORD-05 | ordinary | SCORED | V1 | 0.6666666666666666 | 1.0 | 10 | MEASURED | -2 | — | — |
| TST-AMB-06 | ambiguous | SCORED | V1 | 1.0 | 1.0 | 0 | MEASURED | 5 | — | — |
| TST-STA-07 | stale_context | SCORED | V1 | 1.0 | 1.0 | 0 | MEASURED | 6 | — | — |
| TST-MIS-08 | missing_information | SCORED | V1 | 1.0 | 1.0 | 0 | MEASURED | 3 | — | — |
| REQ-ORD-09 | ordinary | SCORED | V1 | 1.0 | 1.0 | 0 | MEASURED | 2 | — | — |
| REQ-AMB-10 | ambiguous | SCORED | V2 | 1.0 | 1.0 | 0 | MEASURED | 3 | — | — |
| REQ-STA-11 | stale_context | NOT_RUN | — | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | — | — |
| REQ-MIS-12 | missing_information | SCORED | V1 | 1.0 | 1.0 | 0 | MEASURED | UNKNOWN | — | — |

## Paired comparison

Paired on the 11 tasks both workflows scored. Excluded as unpaired: REQ-STA-11 — not zero-filled.

| Measure | assisted-draft-v1 | manual-draft-v1 |
|---|---|---|
| Completeness (mean) | 0.7045 | 0.9242 |
| Correctness (mean) | 0.7273 | 1.0 |
| Modeled repair total (min) | 109 | 19 |
| Forbidden fires | 3 | 0 |
| Generation minutes (timed) | 25 | 317 |
| Repair minutes used (timed) | 140 | 17 |
| Net minutes saved (timed) | 195 | 26 |

Four measures, reported separately. This kit deliberately emits no single composite usefulness score: the reader has to see the trade between speed and repair, not a number that hides it.

## What this result does NOT say

- It does not say either workflow is approved, certified or compliant.
- It does not rank any analyst. The unit of measurement is a workflow.
- It does not generalize past these 12 fictional tasks. A different task mix, especially a different share of missing-information cases, moves the answer.
- Where an input was absent it stayed `UNKNOWN`. No absent value was read as a zero, a pass, or a maturity rating.

## Export warnings

| Row | Field | Warning |
|---|---|---|
| 4 | reviewer_note | formula-like value neutralized on export |

These values were neutralized for spreadsheet safety on CSV export and are restored exactly on import. They were flagged, not silently changed.
