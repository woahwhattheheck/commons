# Component verification log

Every status below was produced by executing the component, not by reading its documentation. Each lane was copied to a temporary directory first; no lane outside this one was modified.

- survey root: `/tmp/claude-0/-home-user/6e551c41-37c5-5a0b-95f1-fb4584e151a7/scratchpad/finalBBWi`
- generated (UTC): 2026-09-19T14:02:46Z
- python: 3.11.15 · per-check timeout: 90s · checks executed: True
- counts: WORKING 25 · DRAFT 7 · MISSING 6 · UNMAPPED 2

## uiowa_rfq_18649_operator_handoff — WORKING

- phase: kickoff
- reason: executed 1 test file(s) here, 24 tests ran, all passed
- files: 23 (7 py, 9 doc, 6 data)

```
$ python3 -m unittest test_verify_kit  (cwd=.)
exit=0 timed_out=False tests_ran=24 duration=2.88s
........................
----------------------------------------------------------------------
Ran 24 tests in 2.815s

OK
```

## uiowa_rfq_18649_mobilization — DRAFT

- phase: kickoff
- reason: document component: 2 document/data files and no executable code; completeness of prose is not machine-checkable and needs a human read
- files: 2 (0 py, 2 doc, 0 data)

## uiowa_rfq_18649_workshare — WORKING

- phase: kickoff
- reason: executed 2 test file(s) here, 34 tests ran, all passed
- files: 36 (24 py, 9 doc, 3 data)

```
$ python3 -m unittest test_validate_23_evidence_register  (cwd=methodology)
exit=0 timed_out=False tests_ran=5 duration=0.07s
.....
----------------------------------------------------------------------
Ran 5 tests in 0.005s

OK
```

```
$ python3 -m unittest test_compiler  (cwd=.)
exit=0 timed_out=False tests_ran=29 duration=0.68s
.............................
----------------------------------------------------------------------
Ran 29 tests in 0.549s

OK
```

## uiowa_rfq_18649_build_board — DRAFT

- phase: kickoff
- reason: document component: 3 document/data files and no executable code; completeness of prose is not machine-checkable and needs a human read
- files: 3 (0 py, 2 doc, 1 data)

## uiowa_rfq_18649_synthetic_collection — WORKING

- phase: evidence_collection
- reason: executed 1 test file(s) here, 5 tests ran, all passed
- files: 16 (2 py, 11 doc, 3 data)

```
$ python3 -m unittest test_collection  (cwd=tests)
exit=0 timed_out=False tests_ran=5 duration=0.07s
.....
----------------------------------------------------------------------
Ran 5 tests in 0.002s

OK
```

## uiowa_rfq_18649_intake_rehearsal — WORKING

- phase: evidence_collection
- reason: executed 1 test file(s) here, 31 tests ran, all passed
- files: 25 (3 py, 5 doc, 17 data)

```
$ python3 -m unittest test_rehearsal  (cwd=.)
exit=0 timed_out=False tests_ran=31 duration=0.26s
0ecbb799a0fe...
  source_register.csv: digest 48ded2e84ba5... != recorded 2eaa16403753...
.SYNTHETIC REHEARSAL OUTPUT - every organization, document, number and quotation below is fictional, authored for the UIOWA-092 integration rehearsal. Nothing here is a University of Iowa record, measurement, or finding.

collection      COLL-SYN-092-A (as of 2026-09-19)
sources         11/12 resolved
observations    16 accepted
interviews      5 excerpts, 4 contributing support
diagnostics     0 REJECT, 2 DEGRADE, 1 NOTE

twelve-cell matrix:
  ESS  SD   DEMONSTRATED_STRENGTH
  ESS  SEC  PARTIAL
  ESS  DEP  MIXED
  ESS  AI   UNKNOWN
  RIS  SD   OBSERVED_GAP
  RIS  SEC  MIXED
  RIS  DEP  OBSERVED_GAP
  RIS  AI   PARTIAL
  IAM  SD   CONFLICT
  IAM  SEC  DEMONSTRATED_STRENGTH
  IAM  DEP  UNKNOWN
  IAM  AI   PARTIAL

state tally: DEMONSTRATED_STRENGTH=2, OBSERVED_GAP=2, MIXED=2, CONFLICT=1, PARTIAL=3, UNKNOWN=2
artifacts written to /tmp/uiowa092-1b9io52w/out/ (6 files + RUN_DIGEST.json)
REPRODUCIBLE: 6 artifacts match the recorded digests in /tmp/uiowa092-1b9io52w/out/RUN_DIGEST.json
.................
----------------------------------------------------------------------
Ran 31 tests in 0.178s

OK
```

## uiowa_rfq_18649_document_extraction — DRAFT

- phase: evidence_collection
- reason: check could not run offline: missing dependency 'pypdf' (declared: pypdf>=6,<7)
- files: 10 (3 py, 3 doc, 1 data)
- declared requirements: pypdf>=6,<7

```
$ python3 -m unittest test_extract  (cwd=.)
exit=1 timed_out=False tests_ran=6 duration=0.18s
tors (test_extract.ExtractionTests.test_pdf_uses_page_locators)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/verify_kit_54fwc9qy/uiowa_rfq_18649_document_extraction/extract.py", line 253, in extract_pdf
    from pypdf import PdfReader
ModuleNotFoundError: No module named 'pypdf'

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/tmp/verify_kit_54fwc9qy/uiowa_rfq_18649_document_extraction/test_extract.py", line 42, in test_pdf_uses_page_locators
    result = extract.extract(FIXTURES / "sample.pdf")
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/tmp/verify_kit_54fwc9qy/uiowa_rfq_18649_document_extraction/extract.py", line 343, in extract
    segments, warnings = extract_pdf(path)
                         ^^^^^^^^^^^^^^^^^
  File "/tmp/verify_kit_54fwc9qy/uiowa_rfq_18649_document_extraction/extract.py", line 255, in extract_pdf
    raise ExtractionError(
extract.ExtractionError: PDF_BACKEND_UNAVAILABLE: install pypdf>=6,<7

----------------------------------------------------------------------
Ran 6 tests in 0.078s

FAILED (errors=2)
```

## uiowa_rfq_18649_test_data_readiness — DRAFT

- phase: evidence_collection
- reason: check executed and did not pass: 1 of 2 test file(s) failed
- files: 10 (2 py, 5 doc, 3 data)

```
$ python3 -m unittest test_data_assessor  (cwd=.)
exit=0 timed_out=False tests_ran=0 duration=0.07s
----------------------------------------------------------------------
Ran 0 tests in 0.000s

OK
```

```
$ python3 -m unittest test_assessor  (cwd=tests)
exit=0 timed_out=False tests_ran=7 duration=0.07s
.......
----------------------------------------------------------------------
Ran 7 tests in 0.001s

OK
```

## uiowa_rfq_18649_secure_guidance — WORKING

- phase: evidence_collection
- reason: executed 1 test file(s) here, 8 tests ran, all passed
- files: 7 (2 py, 3 doc, 2 data)

```
$ python3 -m unittest test_assess_guidance  (cwd=.)
exit=0 timed_out=False tests_ran=8 duration=0.08s
........
----------------------------------------------------------------------
Ran 8 tests in 0.004s

OK
```

## uiowa_rfq_18649_security_event_review — WORKING

- phase: evidence_collection
- reason: executed 1 test file(s) here, 9 tests ran, all passed
- files: 7 (2 py, 3 doc, 2 data)

```
$ python3 -m unittest test_assess_security_events  (cwd=.)
exit=0 timed_out=False tests_ran=9 duration=0.08s
.........
----------------------------------------------------------------------
Ran 9 tests in 0.004s

OK
```

## uiowa_rfq_18649_observability — WORKING

- phase: evidence_collection
- reason: executed 1 test file(s) here, 5 tests ran, all passed
- files: 5 (2 py, 2 doc, 1 data)

```
$ python3 -m unittest test_observability  (cwd=.)
exit=0 timed_out=False tests_ran=5 duration=0.07s
.....
----------------------------------------------------------------------
Ran 5 tests in 0.001s

OK
```

## uiowa_rfq_18649_recovery_evidence — WORKING

- phase: evidence_collection
- reason: executed 2 test file(s) here, 57 tests ran, all passed
- files: 13 (4 py, 4 doc, 5 data)

```
$ python3 -m unittest test_assess_recovery  (cwd=.)
exit=0 timed_out=False tests_ran=7 duration=0.07s
.......
----------------------------------------------------------------------
Ran 7 tests in 0.002s

OK
```

```
$ python3 -m unittest test_recovery_evidence  (cwd=.)
exit=0 timed_out=False tests_ran=50 duration=0.11s
.....................................error: cannot read estate file /tmp/verify_kit_6e27_pyp/uiowa_rfq_18649_recovery_evidence/nope.json: [Errno 2] No such file or directory: '/tmp/verify_kit_6e27_pyp/uiowa_rfq_18649_recovery_evidence/nope.json'
.............
----------------------------------------------------------------------
Ran 50 tests in 0.031s

OK
```

## uiowa_rfq_18649_incident_learning — DRAFT

- phase: evidence_collection
- reason: document component: 2 document/data files and no executable code; completeness of prose is not machine-checkable and needs a human read
- files: 2 (0 py, 1 doc, 1 data)

## uiowa_rfq_18649_release_provenance — WORKING

- phase: evidence_collection
- reason: executed 1 test file(s) here, 34 tests ran, all passed
- files: 9 (3 py, 4 doc, 2 data)

```
$ python3 -m unittest test_provenance  (cwd=.)
exit=0 timed_out=False tests_ran=34 duration=0.67s
..................................
----------------------------------------------------------------------
Ran 34 tests in 0.584s

OK
```

## uiowa_rfq_18649_handoff — WORKING

- phase: evidence_collection
- reason: executed 1 test file(s) here, 6 tests ran, all passed
- files: 7 (2 py, 2 doc, 3 data)

```
$ python3 -m unittest test_handoff  (cwd=tests)
exit=0 timed_out=False tests_ran=6 duration=0.07s
......
----------------------------------------------------------------------
Ran 6 tests in 0.002s

OK
```

## uiowa_rfq_18649_ai_use_inventory — WORKING

- phase: evidence_collection
- reason: executed 1 test file(s) here, 43 tests ran, all passed
- files: 11 (4 py, 2 doc, 5 data)

```
$ python3 -m unittest test_inventory  (cwd=.)
exit=0 timed_out=False tests_ran=43 duration=0.17s
...........................................
----------------------------------------------------------------------
Ran 43 tests in 0.092s

OK
```

## uiowa_rfq_18649_knowledge_readiness — MISSING

- phase: evidence_collection
- reason: no directory for this component exists under the survey root

## uiowa_rfq_18649_rating_model — WORKING

- phase: analysis
- reason: executed 1 test file(s) here, 7 tests ran, all passed
- files: 8 (2 py, 1 doc, 5 data)

```
$ python3 -m unittest test_rating_model  (cwd=.)
exit=0 timed_out=False tests_ran=7 duration=0.07s
.......
----------------------------------------------------------------------
Ran 7 tests in 0.002s

OK
```

## uiowa_rfq_18649_prioritization — WORKING

- phase: analysis
- reason: executed 1 test file(s) here, 48 tests ran, all passed
- files: 12 (2 py, 4 doc, 6 data)

```
$ python3 -m unittest test_prioritize  (cwd=.)
exit=0 timed_out=False tests_ran=48 duration=0.33s
[prioritize] weighting 'inline': 9 ranked, 2 held for missing estimates (2 decision-blocking) out of 11.
[prioritize] weighting 'inline': 9 ranked, 2 held for missing estimates (1 decision-blocking) out of 11.
..[prioritize] weighting 'baseline': 8 ranked, 3 held for missing estimates (2 decision-blocking) out of 11.
[prioritize] sensitivity: top item stable = False; crossover sweep on 'security' found 17 reorder(s).
..............................................
----------------------------------------------------------------------
Ran 48 tests in 0.244s

OK
```

## uiowa_rfq_18649_delivery_metrics — WORKING

- phase: analysis
- reason: executed 1 test file(s) here, 6 tests ran, all passed
- files: 5 (2 py, 2 doc, 1 data)

```
$ python3 -m unittest test_calculator  (cwd=.)
exit=0 timed_out=False tests_ran=6 duration=0.08s
......
----------------------------------------------------------------------
Ran 6 tests in 0.005s

OK
```

## uiowa_rfq_18649_outcome_measurement — WORKING

- phase: analysis
- reason: executed 1 test file(s) here, 6 tests ran, all passed
- files: 7 (2 py, 2 doc, 3 data)

```
$ python3 -m unittest test_analyze  (cwd=tests)
exit=0 timed_out=False tests_ran=6 duration=0.07s
......
----------------------------------------------------------------------
Ran 6 tests in 0.003s

OK
```

## uiowa_rfq_18649_workbench — DRAFT

- phase: analysis
- reason: check executed and did not pass: 1 of 2 test file(s) failed
- files: 21 (5 py, 6 doc, 7 data)

```
$ python3 -m unittest test_framework_crosswalk  (cwd=framework_crosswalk)
exit=1 timed_out=False tests_ran=2 duration=0.06s
F.
======================================================================
FAIL: test_duplicate_locator_is_rejected (test_framework_crosswalk.FrameworkCrosswalkTests.test_duplicate_locator_is_rejected)
----------------------------------------------------------------------
validate_framework_crosswalk.ValidationError: crosswalk is unexpectedly small: 2 rows

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/tmp/verify_kit_1j275bvx/uiowa_rfq_18649_workbench/framework_crosswalk/test_framework_crosswalk.py", line 41, in test_duplicate_locator_is_rejected
    with self.assertRaisesRegex(ValidationError, "duplicate framework locator"):
AssertionError: "duplicate framework locator" does not match "crosswalk is unexpectedly small: 2 rows"

----------------------------------------------------------------------
Ran 2 tests in 0.003s

FAILED (failures=1)
```

```
$ python3 -m unittest test_workbench  (cwd=.)
exit=0 timed_out=False tests_ran=9 duration=0.62s
s........
----------------------------------------------------------------------
Ran 9 tests in 0.522s

OK (skipped=1)
```

## uiowa_rfq_18649_capacity_benchmark — MISSING

- phase: analysis
- reason: no directory for this component exists under the survey root

## uiowa_rfq_18649_ai_opportunity_portfolio — WORKING

- phase: analysis
- reason: executed 1 test file(s) here, 39 tests ran, all passed
- files: 8 (2 py, 2 doc, 4 data)

```
$ python3 -m unittest test_opportunity_portfolio  (cwd=.)
exit=0 timed_out=False tests_ran=39 duration=1.25s
........PORTFOLIO DATA ERROR: OPP-ESS-01: input 'volume_items_per_year' is missing likely, high. Partial ranges are not completed with defaults.
...............................
----------------------------------------------------------------------
Ran 39 tests in 1.180s

OK
```

## uiowa_rfq_18649_ai_policy_to_workflow — WORKING

- phase: analysis
- reason: executed 1 test file(s) here, 36 tests ran, all passed
- files: 13 (2 py, 4 doc, 7 data)

```
$ python3 -m unittest test_policy_matrix  (cwd=.)
exit=0 timed_out=False tests_ran=36 duration=0.08s
......................FIXTURE ERROR: missing input file: /tmp/uiowa074-fgtgj0b9/tasks.json
.FICTIONAL DATA. Example State University is an invented organization. No record here describes the University of Iowa or any real institution, policy, system, or person.
cells=15 assessed=10 not_assessed=4 blocked=1 gaps=3 strengths=5
CAUTION: 4 of 15 cells were never assessed. Gap and strength counts below describe ONLY the 10 assessed cells. Do not read '3 gaps' as '3 gaps exist' -- unexamined ground is not clean ground.
CAUTION: 1 cells cannot be resolved until the University answers a blocking interpretation question. They are excluded from gap and strength counts; their provisional reading is kept in reading_if_unblocked.
wrote matrix.csv matrix.md open_questions.csv findings.json -> /tmp/uiowa074-out-5l9kkfn2
.............
----------------------------------------------------------------------
Ran 36 tests in 0.020s

OK
```

## uiowa_rfq_18649_adoption_readiness — WORKING

- phase: analysis
- reason: executed 1 test file(s) here, 49 tests ran, all passed
- files: 14 (2 py, 3 doc, 9 data)

```
$ python3 -m unittest test_readiness  (cwd=.)
exit=0 timed_out=False tests_ran=49 duration=0.13s
..................................teams assessed: 3   rejected records: 0   rejected options: 0
  T-ESS    contributors=7   state=5/6 unknown=1  established=2 emerging=2 absent=1  options=5  evidence_requests=1
  T-IAM    contributors=2   state=0/6 unknown=6  established=0 emerging=0 absent=0  options=0  evidence_requests=6
  T-RIS    contributors=5   state=5/6 unknown=1  established=1 emerging=3 absent=1  options=6  evidence_requests=1
diagnostics: 0 error(s); sequencing open questions: 3
content digest: 9a125e4e1bfca78387f5efa4ced28cb6932bba34bd957fc1e163ff3693790db2
outputs in /tmp/tmpn9_4pvgd
...............
----------------------------------------------------------------------
Ran 49 tests in 0.054s

OK
```

## uiowa_rfq_18649_ai_integration — MISSING

- phase: analysis
- reason: no directory for this component exists under the survey root

## uiowa_rfq_18649_ai_eval_kit — WORKING

- phase: analysis
- reason: executed 1 test file(s) here, 29 tests ran, all passed
- files: 12 (3 py, 2 doc, 7 data)

```
$ python3 -m unittest test_eval_kit  (cwd=.)
exit=0 timed_out=False tests_ran=29 duration=0.1s
.............................
----------------------------------------------------------------------
Ran 29 tests in 0.030s

OK
```

## uiowa_rfq_18649_traceability_rehearsal — WORKING

- phase: draft_review
- reason: no unittest suite; documented runner `python3 validate_trace.py` was executed here and exited 0 with output
- files: 8 (1 py, 3 doc, 4 data)

```
$ python3 validate_trace.py
exit=0 timed_out=False tests_ran=0 duration=0.03s
evidence=8 findings=3 recommendations=2 statements=5
trace validation: PASS
```

## uiowa_rfq_18649_doc_usability — DRAFT

- phase: draft_review
- reason: document component: 6 document/data files and no executable code; completeness of prose is not machine-checkable and needs a human read
- files: 6 (0 py, 3 doc, 3 data)

## uiowa_rfq_18649_qa_kit — MISSING

- phase: draft_review
- reason: no directory for this component exists under the survey root

## uiowa_rfq_18649_interchange — MISSING

- phase: draft_review
- reason: no directory for this component exists under the survey root

## uiowa_rfq_18649_report_structure — WORKING

- phase: final_delivery
- reason: executed 1 test file(s) here, 55 tests ran, all passed
- files: 14 (3 py, 3 doc, 8 data)

```
$ python3 -m unittest test_report_structure  (cwd=.)
exit=0 timed_out=False tests_ran=55 duration=0.17s
atched : "non-compliant"
  in      : The service is non-compliant and we recommend purchasing a new tool.
  why     : States a compliance determination. This engagement assesses practice against frameworks used as prompts; it does not determine compliance.
  rewrite : Describe the observed practice and the gap against the referenced clause, e.g. 'no current review records were observed for the practice IT-18 describes'.

[PP-01] product_procurement  /tmp/tmpz8l534kk/drifted.md:1
  matched : "we recommend purchasing"
  in      : The service is non-compliant and we recommend purchasing a new tool.
  why     : Recommends a purchase. Procurement is outside this engagement.
  rewrite : State the capability the group needs and the decision it has to make; leave selection and purchase to the University's own process.

SCOPE GUARD - UIOWA RFQ 18649 final report
==============================================================
flagged: 0   neutralized: 0
  audit_verdict            0
  individual_evaluation    0
  product_procurement      0

PASS - no scope drift detected.
............s
----------------------------------------------------------------------
Ran 55 tests in 0.081s

OK (skipped=1)
```

## uiowa_rfq_18649_report_visuals — WORKING

- phase: final_delivery
- reason: executed 1 test file(s) here, 60 tests ran, all passed
- files: 24 (8 py, 6 doc, 2 data)

```
$ python3 -m unittest test_report_visuals  (cwd=.)
exit=0 timed_out=False tests_ran=60 duration=0.17s
---
43 checks, 43 pass, 0 fail

.redundant-encoding contract OK: colour, shape, texture, border and label are each independently sufficient to name a band; every not-a-rating state stays >= 3:1 from every rating after colour is removed.
.input rejected: document: missing required field 'disclaimer'
.no such data file: /nonexistent/nope.json
.SYNTHETIC EXAMPLE - fictional groups and fictional evidence. Not a University of Iowa finding.
rendered 13 files into /tmp/tmpwv4wf1bs
  185bff0b2e95  contrast-audit.txt
  d006741f7075  cross-group.print.svg
  c0ff2339ecc8  cross-group.screen.svg
  19cfe6b1b176  evidence-coverage-table.md
  8c1368590b52  evidence-coverage.print.svg
  1f97befd4064  evidence-coverage.screen.svg
  243c4d7f2dda  matrix-table.md
  c21cec08ce0e  matrix.print.svg
  39b3057ba6fa  matrix.screen.svg
  18b568b03721  roadmap-table.md
  5ef627e063b7  roadmap.print.svg
  1f523a4969e6  roadmap.screen.svg
  dcdc06165f0f  text-alternatives.md

8 of 12 cells rated; 2 insufficient evidence; 2 not assessed; 0 no record supplied.
........................................................
----------------------------------------------------------------------
Ran 60 tests in 0.083s

OK
```

## uiowa_rfq_18649_integration — WORKING

- phase: final_delivery
- reason: no unittest suite; documented runner `python3 integrate_tabular.py --repo /home/user/commons --out /tmp/verify_kit_out_b8truv0b/integration.json` was executed here and exited 0 with output
- files: 3 (2 py, 0 doc, 1 data)

```
$ python3 integrate_tabular.py --repo /home/user/commons --out /tmp/verify_kit_out_b8truv0b/integration.json
exit=0 timed_out=False tests_ran=0 duration=0.05s
PASS records=15 components=2
```

## uiowa_rfq_18649_closeout — WORKING

- phase: final_delivery
- reason: executed 1 test file(s) here, 7 tests ran, all passed
- files: 13 (2 py, 4 doc, 7 data)

```
$ python3 -m unittest test_closeout  (cwd=.)
exit=0 timed_out=False tests_ran=7 duration=0.07s
.......
----------------------------------------------------------------------
Ran 7 tests in 0.001s

OK
```

## uiowa_rfq_18649_readout_deck — WORKING

- phase: readout
- reason: executed 1 test file(s) here, 56 tests ran, all passed
- files: 10 (2 py, 4 doc, 4 data)

```
$ python3 -m unittest test_deck_architecture  (cwd=.)
exit=0 timed_out=False tests_ran=56 duration=0.12s
 | Every core slide carries at least one speaker-note prompt. |
| R012_DETAIL_IN_MAIN_BODY | Core slides stay inside the executive readability budget. |
| R013_UNRESOLVED_MEASURE | A cited measure name exists on the cited report object. |
| R014_DECISION_UNLINKED | A decision resolves to a recommendation whose phase agrees with the decision's. |
| R015_REPORT_MISMATCH | The deck's report_ref is the report it is being checked against. |
| R016_AGENDA_UNDERRUN | Core slide minutes use a reasonable share of the declared session (advisory). |

.INPUT ERROR: file not found: /nonexistent/report.json
....wrote /tmp/tmpluk6e9vs/a/readout-deck.md
wrote /tmp/tmpluk6e9vs/a/readout-deck-ascii.txt
wrote /tmp/tmpluk6e9vs/a/deck-report-agreement.md
wrote /tmp/tmpluk6e9vs/a/readout-planning-table.csv
agreement: PASS (0 error(s), 0 warning(s))
wrote /tmp/tmpluk6e9vs/b/readout-deck.md
wrote /tmp/tmpluk6e9vs/b/readout-deck-ascii.txt
wrote /tmp/tmpluk6e9vs/b/deck-report-agreement.md
wrote /tmp/tmpluk6e9vs/b/readout-planning-table.csv
agreement: PASS (0 error(s), 0 warning(s))
.............................
----------------------------------------------------------------------
Ran 56 tests in 0.048s

OK
```

## uiowa_rfq_18649_qa_kit — MISSING

- phase: readout
- reason: no directory for this component exists under the survey root

## uiowa_rfq_18649_acceptance_map — UNMAPPED

- phase: unassigned
- reason: lane found on disk but not placed in any phase by the manifest; underlying observation: check executed and did not pass: 1 of 1 test file(s) failed
- files: 20 (4 py, 5 doc, 11 data)

```
$ python3 -m unittest test_acceptance_map  (cwd=.)
exit=1 timed_out=False tests_ran=12 duration=0.09s
-------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/verify_kit__n961388/uiowa_rfq_18649_acceptance_map/test_acceptance_map.py", line 273, in setUpClass
    with open(os.path.join(cls.tmp, "acceptance_index.json"), encoding="utf-8") as fh:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
FileNotFoundError: [Errno 2] No such file or directory: '/tmp/uiowa130-wt3ja032/acceptance_index.json'

======================================================================
FAIL: test_deleting_a_bound_artifact_never_leaves_it_demonstrable (test_acceptance_map.TestHostileAndReadOnly.test_deleting_a_bound_artifact_never_leaves_it_demonstrable)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/verify_kit__n961388/uiowa_rfq_18649_acceptance_map/test_acceptance_map.py", line 243, in test_deleting_a_bound_artifact_never_leaves_it_demonstrable
    self.assertTrue(os.path.isfile(target))
AssertionError: False is not true

----------------------------------------------------------------------
Ran 12 tests in 0.021s

FAILED (failures=1, errors=5)
```

## uiowa_rfq_18649_traceability — UNMAPPED

- phase: unassigned
- reason: lane found on disk but not placed in any phase by the manifest; underlying observation: executed 1 test file(s) here, 34 tests ran, all passed
- files: 35 (3 py, 22 doc, 10 data)

```
$ python3 -m unittest test_trace_check  (cwd=.)
exit=0 timed_out=False tests_ran=34 duration=0.22s
..................................
----------------------------------------------------------------------
Ran 34 tests in 0.146s

OK
```
