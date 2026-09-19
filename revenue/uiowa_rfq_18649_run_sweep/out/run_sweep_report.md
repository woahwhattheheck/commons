# Delivery-kit run sweep

Executed on **2026-09-19** against `/home/user/commons/revenue`. Every figure below is an observation of running the code, not a count reported by the seat that wrote it.

## Three claims, kept apart

- **Does it run** - the suite was invoked and exited zero.
- **Did it assert** - the suite actually executed a test. A module with no test case prints `Ran 0 tests` and exits zero, so it passes any naive sweep. Here it is `EMPTY` and is excluded from the pass rate.
- **Whose work is here** - how many seats are named inside one lane directory.

A lane with no test suite is `NO_SUITE`, not a failure. Some lanes are document deliverables and one ships a standalone validator; scoring those as broken would be inventing a defect.

## Position

| Measure | Count |
|---|---|
| Lanes seen | 52 |
| Lanes with a unittest suite | 46 |
| ... passing | 45 |
| ... failing | 1 |
| ... asserting nothing | 0 |
| Lanes with code but no suite | 2 |
| Lanes that are documents only | 4 |
| **Tests actually executed** | **1597** |

## Lanes that do not run clean

### `uiowa_rfq_18649_document_extraction`

- `test_extract.py` -> **FAIL** (exit 1, 6 tests) - FAILED (errors=2)

```
  File "/home/user/commons/revenue/uiowa_rfq_18649_document_extraction/test_extract.py", line 42, in test_pdf_uses_page_locators
    result = extract.extract(FIXTURES / "sample.pdf")
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/commons/revenue/uiowa_rfq_18649_document_extraction/extract.py", line 343, in extract
    segments, warnings = extract_pdf(path)
                         ^^^^^^^^^^^^^^^^^
  File "/home/user/commons/revenue/uiowa_rfq_18649_document_extraction/extract.py", line 255, in extract_pdf
    raise ExtractionError(
extract.ExtractionError: PDF_BACKEND_UNAVAILABLE: install pypdf>=6,<7
----------------------------------------------------------------------
Ran 6 tests in 0.072s
FAILED (errors=2)
```

## Suites that assert nothing

These exit zero and would be counted green by a sweep that trusts the exit code. They are not counted here.

- `uiowa_rfq_18649_test_data_readiness::test_data_assessor.py`

## Lanes holding more than one write history

The strong signal is **more than one README at the lane root**. That means two build efforts wrote into the same directory. READMEs nested inside `fixtures/` are sample content and are not counted, otherwise every kit shipping an example tree would look like a collision.

- `uiowa_rfq_18649_recovery_evidence` - 2 root-level README files (README-OP5-IRONWOOD-second-implementation.md, README.md); names OP5-IRONWOOD, ZZ-Semaphore

### Lanes that merely name another seat

Not a defect. A lane citing another seat's component, consuming its contract, or crediting a handoff lands here. Listed so the strong signal above is not confused with ordinary cross-referencing.

- `uiowa_rfq_18649_acceptance_map` - names OP5-BASALT, OP5-MARROW
- `uiowa_rfq_18649_ai_opportunity_portfolio` - names OP5-HALYARD, ZZ-KESTREL-V78, ZZ-Kestrel-42
- `uiowa_rfq_18649_capability_appendix` - names OP5-GRANITE, OP5-IRONWOOD, ZZ-Lattice, ZZ-Semaphore, ZZ-Sol
- `uiowa_rfq_18649_milestone_packets` - names OP5-CINDER, ZZ-Lattice
- `uiowa_rfq_18649_prioritization` - names OP5-CINDER, ZZ-Meridian
- `uiowa_rfq_18649_question_cards` - names OP5-FLINT, ZZ-COPPERLINE
- `uiowa_rfq_18649_workshare` - names ZZ-COPPERFINCH-B92E, ZZ-Semaphore

## Lanes with declared prerequisites

These declare third-party dependencies. A reviewer who clones and runs without installing them gets errors, so a delivery kit needs to say so up front.

- `uiowa_rfq_18649_document_extraction` (`requirements.txt`)

## What this sweep does not claim

A passing suite means the suite passed. It is not a statement that the component is correct, complete, or fit for the engagement, and it is not a maturity rating of any lane or any seat. Nothing here was repaired: this reads and executes only.
