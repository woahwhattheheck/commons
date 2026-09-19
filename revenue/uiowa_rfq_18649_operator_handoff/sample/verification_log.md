# Component verification log

Every status below was produced by executing the component, not by reading its documentation. Each lane was copied to a temporary directory first; no lane outside this one was modified.

- survey root: `/tmp/claude-0/-home-user/6e551c41-37c5-5a0b-95f1-fb4584e151a7/scratchpad/m3QGjY`
- generated (UTC): 2026-09-19T14:16:38Z
- python: 3.11.15 · per-check timeout: 90s · checks executed: True
- counts: WORKING 43 · DRAFT 10 · MISSING 4 · UNMAPPED 0

## uiowa_rfq_18649_operator_handoff — WORKING

- phase: kickoff
- reason: executed 1 test file(s) here, 37 tests ran, all passed
- files: 26 (8 py, 10 doc, 7 data)

```
$ python3 -m unittest test_verify_kit  (cwd=.)
exit=0 timed_out=False tests_ran=37 duration=5.47s
.....................................
----------------------------------------------------------------------
Ran 37 tests in 5.349s

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
Ran 5 tests in 0.003s

OK
```

```
$ python3 -m unittest test_compiler  (cwd=.)
exit=0 timed_out=False tests_ran=29 duration=0.65s
.............................
----------------------------------------------------------------------
Ran 29 tests in 0.531s

OK
```

## uiowa_rfq_18649_build_board — DRAFT

- phase: kickoff
- reason: document component: 3 document/data files and no executable code; completeness of prose is not machine-checkable and needs a human read
- files: 3 (0 py, 2 doc, 1 data)

## uiowa_rfq_18649_capability_appendix — DRAFT

- phase: kickoff
- reason: check executed and did not pass: 1 of 1 test file(s) failed
- files: 15 (2 py, 5 doc, 8 data)

```
$ python3 -m unittest test_capability_appendix  (cwd=.)
exit=1 timed_out=False tests_ran=39 duration=0.18s
lity_appendix.RealRegister.test_five_claims_are_demonstrated)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/verify_kit_g0x3eumg/uiowa_rfq_18649_capability_appendix/test_capability_appendix.py", line 171, in test_five_claims_are_demonstrated
    self.assertEqual(len(self.demonstrated), 5)
AssertionError: 4 != 5

======================================================================
FAIL: test_the_unrun_claim_is_held_back (test_capability_appendix.RealRegister.test_the_unrun_claim_is_held_back)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/verify_kit_g0x3eumg/uiowa_rfq_18649_capability_appendix/test_capability_appendix.py", line 175, in test_the_unrun_claim_is_held_back
    self.assertEqual(ids, ["CAP-06"])
AssertionError: Lists differ: ['CAP-05', 'CAP-06'] != ['CAP-06']

First differing element 0:
'CAP-05'
'CAP-06'

First list contains 1 additional elements.
First extra element 1:
'CAP-06'

- ['CAP-05', 'CAP-06']
+ ['CAP-06']

----------------------------------------------------------------------
Ran 39 tests in 0.115s

FAILED (failures=3)
```

## uiowa_rfq_18649_scope_change — WORKING

- phase: kickoff
- reason: executed 1 test file(s) here, 48 tests ran, all passed
- files: 8 (2 py, 2 doc, 4 data)

```
$ python3 -m unittest test_scope_change  (cwd=.)
exit=0 timed_out=False tests_ran=48 duration=0.25s
................[scope] 1 not quotable, 1 no-charge cure(s) at $0.00 covering 7 h, 2 awaiting input, $25,384.00 of quoted change against an unchanged $24,000.00 base.
................................
----------------------------------------------------------------------
Ran 48 tests in 0.164s

OK
```

## uiowa_rfq_18649_bid_pack — WORKING

- phase: kickoff
- reason: executed 2 test file(s) here, 62 tests ran, all passed
- files: 36 (6 py, 25 doc, 3 data)

```
$ python3 -m unittest test_bid_pack  (cwd=.)
exit=0 timed_out=False tests_ran=35 duration=0.42s
/tmp/verify_kit_wufg76ay/uiowa_rfq_18649_bid_pack/test_bid_pack.py:205: ResourceWarning: unclosed file <_io.TextIOWrapper name='/tmp/bidpack-3jh9vci0/bid_pack.json' mode='r' encoding='utf-8'>
  data = json.load(open(os.path.join(self.tmp, "bid_pack.json"), encoding="utf-8"))
ResourceWarning: Enable tracemalloc to get the object allocation traceback
...................................
----------------------------------------------------------------------
Ran 35 tests in 0.306s

OK
```

```
$ python3 -m unittest test_packcheck  (cwd=.)
exit=0 timed_out=False tests_ran=27 duration=0.2s
...........................
----------------------------------------------------------------------
Ran 27 tests in 0.094s

OK
```

## uiowa_rfq_18649_filesystem_safety — WORKING

- phase: kickoff
- reason: executed 1 test file(s) here, 24 tests ran, all passed
- files: 16 (8 py, 4 doc, 4 data)

```
$ python3 -m unittest test_fsaudit  (cwd=.)
exit=0 timed_out=False tests_ran=24 duration=0.14s


  REVIEW_REQUIRED  lane_external/lane_external/test_sample_cleanup.py:12  shutil.rmtree(supplied_path)
                   target is the function parameter 'supplied_path' -- the caller chooses what gets removed
  REVIEW_REQUIRED  lane_external/lane_external/tool_argv.py:13  shutil.rmtree(workspace)
                   target is the function parameter 'workspace' -- the caller chooses what gets removed
  REVIEW_REQUIRED  lane_external/lane_external/tool_argv.py:17  shutil.rmtree(sys.argv[1])
                   target comes from sys.argv, which is external input
  REVIEW_REQUIRED  lane_external/lane_external/tool_argv.py:21  os.remove(os.path.join(root, name))
                   path is joined from externally controlled parts

wrote           3 file(s) under /tmp/tmp36i244jb
note            This is a SCREEN, not a proof. CLEAN means the screen found nothing it could see -- it does not mean the module is safe. Dynamic dispatch, getattr, C extensions and anything inside a subprocess are invisible to an AST. No safety score is produced and no lane is marked compliant.
.....................
----------------------------------------------------------------------
Ran 24 tests in 0.064s

OK
```

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
- reason: executed 1 test file(s) here, 34 tests ran, all passed
- files: 25 (3 py, 5 doc, 17 data)

```
$ python3 -m unittest test_rehearsal  (cwd=.)
exit=0 timed_out=False tests_ran=34 duration=0.15s
bb799a0fe...
  source_register.csv: digest afe26983a47e... != recorded b3a14aef8a55...
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
artifacts written to /tmp/uiowa092-bn2w3nr2/out/ (6 files + RUN_DIGEST.json)
REPRODUCIBLE: 6 artifacts match the recorded digests in /tmp/uiowa092-bn2w3nr2/out/RUN_DIGEST.json
....................
----------------------------------------------------------------------
Ran 34 tests in 0.082s

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
  File "/tmp/verify_kit_tknhq6fz/uiowa_rfq_18649_document_extraction/extract.py", line 253, in extract_pdf
    from pypdf import PdfReader
ModuleNotFoundError: No module named 'pypdf'

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/tmp/verify_kit_tknhq6fz/uiowa_rfq_18649_document_extraction/test_extract.py", line 42, in test_pdf_uses_page_locators
    result = extract.extract(FIXTURES / "sample.pdf")
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/tmp/verify_kit_tknhq6fz/uiowa_rfq_18649_document_extraction/extract.py", line 343, in extract
    segments, warnings = extract_pdf(path)
                         ^^^^^^^^^^^^^^^^^
  File "/tmp/verify_kit_tknhq6fz/uiowa_rfq_18649_document_extraction/extract.py", line 255, in extract_pdf
    raise ExtractionError(
extract.ExtractionError: PDF_BACKEND_UNAVAILABLE: install pypdf>=6,<7

----------------------------------------------------------------------
Ran 6 tests in 0.074s

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
exit=0 timed_out=False tests_ran=7 duration=0.06s
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
exit=0 timed_out=False tests_ran=8 duration=0.07s
........
----------------------------------------------------------------------
Ran 8 tests in 0.003s

OK
```

## uiowa_rfq_18649_security_event_review — WORKING

- phase: evidence_collection
- reason: executed 1 test file(s) here, 9 tests ran, all passed
- files: 7 (2 py, 3 doc, 2 data)

```
$ python3 -m unittest test_assess_security_events  (cwd=.)
exit=0 timed_out=False tests_ran=9 duration=0.07s
.........
----------------------------------------------------------------------
Ran 9 tests in 0.002s

OK
```

## uiowa_rfq_18649_observability — WORKING

- phase: evidence_collection
- reason: executed 1 test file(s) here, 5 tests ran, all passed
- files: 5 (2 py, 2 doc, 1 data)

```
$ python3 -m unittest test_observability  (cwd=.)
exit=0 timed_out=False tests_ran=5 duration=0.06s
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
exit=0 timed_out=False tests_ran=7 duration=0.06s
.......
----------------------------------------------------------------------
Ran 7 tests in 0.002s

OK
```

```
$ python3 -m unittest test_recovery_evidence  (cwd=.)
exit=0 timed_out=False tests_ran=50 duration=0.09s
.....................................error: cannot read estate file /tmp/verify_kit_dim0ltbp/uiowa_rfq_18649_recovery_evidence/nope.json: [Errno 2] No such file or directory: '/tmp/verify_kit_dim0ltbp/uiowa_rfq_18649_recovery_evidence/nope.json'
.............
----------------------------------------------------------------------
Ran 50 tests in 0.019s

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
exit=0 timed_out=False tests_ran=34 duration=0.66s
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
exit=0 timed_out=False tests_ran=43 duration=0.16s
...........................................
----------------------------------------------------------------------
Ran 43 tests in 0.087s

OK
```

## uiowa_rfq_18649_knowledge_readiness — MISSING

- phase: evidence_collection
- reason: no directory for this component exists under the survey root

## uiowa_rfq_18649_contractor_transition — WORKING

- phase: evidence_collection
- reason: executed 1 test file(s) here, 34 tests ran, all passed
- files: 9 (3 py, 2 doc, 4 data)

```
$ python3 -m unittest test_transition  (cwd=.)
exit=0 timed_out=False tests_ran=34 duration=0.21s
..................................
----------------------------------------------------------------------
Ran 34 tests in 0.144s

OK
```

## uiowa_rfq_18649_question_cards — WORKING

- phase: evidence_collection
- reason: executed 1 test file(s) here, 40 tests ran, all passed
- files: 11 (2 py, 2 doc, 7 data)

```
$ python3 -m unittest test_question_cards  (cwd=.)
exit=0 timed_out=False tests_ran=40 duration=0.1s
observations=11 cards=1 suppressed=1 errors=9 warnings=1 accounted_for=11/11
  ERROR   TEMPLATE_FIELD_MISSING     OBS-H1-MISSING-FIELD     reading_b
  ERROR   USELESS_QUESTION           OBS-H10-ONE-ANSWER       outcome_map
  ERROR   USELESS_QUESTION           OBS-H2-SAME-OUTCOME      outcome_map
  ERROR   VAGUE_EXAMPLE_REQUEST      OBS-H3-VAGUE-REQUEST     example_request
  ERROR   UNKNOWN_SOURCE_REF         OBS-H4-DANGLING-SOURCE   source_ids
  ERROR   LEADING_QUESTION           OBS-H5-LEADING           question
  ERROR   MISSING_ABSENCE_CAVEAT     OBS-H6-NO-CAVEAT         absence_caveat
  ERROR   NO_CARD_WITHOUT_REASON     OBS-H7-SUPPRESSED        no_card_reason
  ERROR   UNKNOWN_UNCERTAINTY_TYPE   OBS-H8-UNKNOWN-TYPE      uncertainty_type
  WARNING NO_SESSION_FOR_ROLE        OBS-H9-NO-SESSION        ask_role
.observations=10 cards=10 suppressed=0 errors=0 warnings=0 accounted_for=10/10
.export round trip OK: 10 row(s) re-import byte-identical (cards.csv)
......................................
----------------------------------------------------------------------
Ran 40 tests in 0.029s

OK
```

## uiowa_rfq_18649_deadline_continuity — WORKING

- phase: evidence_collection
- reason: executed 1 test file(s) here, 42 tests ran, all passed
- files: 9 (3 py, 2 doc, 4 data)

```
$ python3 -m unittest test_continuity  (cwd=.)
exit=0 timed_out=False tests_ran=42 duration=0.19s
..........................................
----------------------------------------------------------------------
Ran 42 tests in 0.122s

OK
```

## uiowa_rfq_18649_vocabulary_crosswalk — DRAFT

- phase: evidence_collection
- reason: check executed and did not pass: 1 of 1 test file(s) failed
- files: 10 (3 py, 2 doc, 5 data)

```
$ python3 -m unittest test_vocabulary  (cwd=.)
exit=1 timed_out=False tests_ran=24 duration=0.08s
e case: 'deployment' vs 'deployment_operations'.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/verify_kit__5zg_ced/uiowa_rfq_18649_vocabulary_crosswalk/test_vocabulary.py", line 214, in test_the_deployment_collision_that_caused_the_real_false_failure
    self.assertIn("deployment_operations", terms)
AssertionError: 'deployment_operations' not found in set()

======================================================================
FAIL: test_the_scan_found_a_real_disagreement (test_vocabulary.TestAgainstTheRealTree.test_the_scan_found_a_real_disagreement)
If every lane agreed, this package would have nothing to say.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/verify_kit__5zg_ced/uiowa_rfq_18649_vocabulary_crosswalk/test_vocabulary.py", line 177, in test_the_scan_found_a_real_disagreement
    self.assertGreater(len(sd_spellings), 2,
AssertionError: 0 not greater than 2 : expected several spellings of one area, saw []

----------------------------------------------------------------------
Ran 24 tests in 0.016s

FAILED (failures=3, errors=1)
```

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
exit=0 timed_out=False tests_ran=48 duration=0.29s
[prioritize] weighting 'inline': 9 ranked, 2 held for missing estimates (2 decision-blocking) out of 11.
[prioritize] weighting 'inline': 9 ranked, 2 held for missing estimates (1 decision-blocking) out of 11.
..[prioritize] weighting 'baseline': 8 ranked, 3 held for missing estimates (2 decision-blocking) out of 11.
[prioritize] sensitivity: top item stable = False; crossover sweep on 'security' found 17 reorder(s).
..............................................
----------------------------------------------------------------------
Ran 48 tests in 0.213s

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
Ran 6 tests in 0.003s

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
  File "/tmp/verify_kit_5ulstuiv/uiowa_rfq_18649_workbench/framework_crosswalk/test_framework_crosswalk.py", line 41, in test_duplicate_locator_is_rejected
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
Ran 9 tests in 0.520s

OK (skipped=1)
```

## uiowa_rfq_18649_capacity_benchmark — WORKING

- phase: analysis
- reason: executed 1 test file(s) here, 36 tests ran, all passed
- files: 9 (4 py, 2 doc, 3 data)

```
$ python3 -m unittest test_capacity_benchmark  (cwd=.)
exit=0 timed_out=False tests_ran=36 duration=1.2s
....................................
----------------------------------------------------------------------
Ran 36 tests in 1.117s

OK
```

## uiowa_rfq_18649_ai_opportunity_portfolio — WORKING

- phase: analysis
- reason: executed 1 test file(s) here, 39 tests ran, all passed
- files: 8 (2 py, 2 doc, 4 data)

```
$ python3 -m unittest test_opportunity_portfolio  (cwd=.)
exit=0 timed_out=False tests_ran=39 duration=1.22s
........PORTFOLIO DATA ERROR: OPP-ESS-01: input 'volume_items_per_year' is missing likely, high. Partial ranges are not completed with defaults.
...............................
----------------------------------------------------------------------
Ran 39 tests in 1.145s

OK
```

## uiowa_rfq_18649_ai_policy_to_workflow — WORKING

- phase: analysis
- reason: executed 1 test file(s) here, 36 tests ran, all passed
- files: 13 (2 py, 4 doc, 7 data)

```
$ python3 -m unittest test_policy_matrix  (cwd=.)
exit=0 timed_out=False tests_ran=36 duration=0.13s
......................FIXTURE ERROR: missing input file: /tmp/uiowa074-i61mqq3e/tasks.json
.FICTIONAL DATA. Example State University is an invented organization. No record here describes the University of Iowa or any real institution, policy, system, or person.
cells=15 assessed=10 not_assessed=4 blocked=1 gaps=3 strengths=5
CAUTION: 4 of 15 cells were never assessed. Gap and strength counts below describe ONLY the 10 assessed cells. Do not read '3 gaps' as '3 gaps exist' -- unexamined ground is not clean ground.
CAUTION: 1 cells cannot be resolved until the University answers a blocking interpretation question. They are excluded from gap and strength counts; their provisional reading is kept in reading_if_unblocked.
wrote matrix.csv matrix.md open_questions.csv findings.json -> /tmp/uiowa074-out-sko8hf7m
.............
----------------------------------------------------------------------
Ran 36 tests in 0.023s

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
outputs in /tmp/tmpajtzex45
...............
----------------------------------------------------------------------
Ran 49 tests in 0.054s

OK
```

## uiowa_rfq_18649_ai_integration — WORKING

- phase: analysis
- reason: executed 1 test file(s) here, 46 tests ran, all passed
- files: 24 (14 py, 4 doc, 6 data)

```
$ python3 -m unittest test_ai_integration  (cwd=.)
exit=0 timed_out=False tests_ran=46 duration=0.1s
..............................................
----------------------------------------------------------------------
Ran 46 tests in 0.007s

OK
```

## uiowa_rfq_18649_ai_eval_kit — WORKING

- phase: analysis
- reason: executed 1 test file(s) here, 29 tests ran, all passed
- files: 12 (3 py, 2 doc, 7 data)

```
$ python3 -m unittest test_eval_kit  (cwd=.)
exit=0 timed_out=False tests_ran=29 duration=0.11s
.............................
----------------------------------------------------------------------
Ran 29 tests in 0.033s

OK
```

## uiowa_rfq_18649_economics_resource_adapters — WORKING

- phase: analysis
- reason: executed 2 test file(s) here, 78 tests ran, all passed
- files: 16 (6 py, 2 doc, 8 data)

```
$ python3 -m unittest test_check_contract  (cwd=.)
exit=0 timed_out=False tests_ran=33 duration=0.09s
...........s.....................
----------------------------------------------------------------------
Ran 33 tests in 0.010s

OK (skipped=1)
```

```
$ python3 -m unittest test_integrate  (cwd=.)
exit=0 timed_out=False tests_ran=45 duration=0.07s
...sss...INTEGRATION ERROR: recommendation register at /tmp/tmp1nvhjgwp/bad.json is not valid JSON: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
.INTEGRATION ERROR: recommendation register not found at /tmp/tmpcp4ixl5s/nope.json
...sssssssssssssss.................
----------------------------------------------------------------------
Ran 45 tests in 0.004s

OK (skipped=18)
```

## uiowa_rfq_18649_roadmap_dependencies — WORKING

- phase: analysis
- reason: executed 1 test file(s) here, 47 tests ran, all passed
- files: 16 (2 py, 4 doc, 8 data)

```
$ python3 -m unittest test_depcheck  (cwd=.)
exit=0 timed_out=False tests_ran=47 duration=0.11s
08, R-10
  digest bd046e78095113dad303cd93ae9b701fce85a1f006ce95e09950f4bf95eed205
  outputs in /tmp/tmpajhwgr2f
roadmap RM-INCONSISTENT-v1: 13 items, 10 edges
  errors=4  unknown=3  open_questions=1  info=7
  parallel in 90-180   level 1: X-02, X-10, X-12, X-13
  ERROR dependency_cycle       X-06, X-07, X-08
  ERROR missing_prerequisite   X-99 -> X-04
  ERROR phase_inversion        X-02 -> X-03
  ERROR self_dependency        X-05 -> X-05
  digest 39c540bce82749859d1c1b3a2bd8d42b6d6f23ad90b1aa600d6e4d93b0341883
  outputs in /tmp/tmpajhwgr2f
.................roadmap RM-INCONSISTENT-v1: 13 items, 10 edges
  errors=4  unknown=3  open_questions=1  info=7
  parallel in 90-180   level 1: X-02, X-10, X-12, X-13
  ERROR dependency_cycle       X-06, X-07, X-08
  ERROR missing_prerequisite   X-99 -> X-04
  ERROR phase_inversion        X-02 -> X-03
  ERROR self_dependency        X-05 -> X-05
  digest 39c540bce82749859d1c1b3a2bd8d42b6d6f23ad90b1aa600d6e4d93b0341883
  rehearsal: errors 4 -> 0, unknown 3 -> 2 (a planner must clear the rest)
  outputs in /tmp/tmpwop52tng
.............................
----------------------------------------------------------------------
Ran 47 tests in 0.034s

OK
```

## uiowa_rfq_18649_ai_decision_case — WORKING

- phase: analysis
- reason: executed 1 test file(s) here, 34 tests ran, all passed
- files: 18 (6 py, 5 doc, 7 data)

```
$ python3 -m unittest test_ai_decision_case  (cwd=.)
exit=0 timed_out=False tests_ran=34 duration=0.12s
..................................
----------------------------------------------------------------------
Ran 34 tests in 0.047s

OK
```

## uiowa_rfq_18649_capacity_feasibility — WORKING

- phase: analysis
- reason: executed 1 test file(s) here, 51 tests ran, all passed
- files: 9 (2 py, 3 doc, 4 data)

```
$ python3 -m unittest test_capacity_roadmap  (cwd=.)
exit=0 timed_out=False tests_ran=51 duration=0.12s
...................................................
----------------------------------------------------------------------
Ran 51 tests in 0.054s

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

## uiowa_rfq_18649_traceability — WORKING

- phase: draft_review
- reason: executed 3 test file(s) here, 66 tests ran, all passed
- files: 39 (7 py, 22 doc, 10 data)

```
$ python3 -m unittest test_audit_assertions  (cwd=.)
exit=0 timed_out=False tests_ran=22 duration=0.07s
......................
----------------------------------------------------------------------
Ran 22 tests in 0.011s

OK
```

```
$ python3 -m unittest test_audit_self_sealing  (cwd=.)
exit=0 timed_out=False tests_ran=10 duration=0.46s
..........
----------------------------------------------------------------------
Ran 10 tests in 0.390s

OK
```

```
$ python3 -m unittest test_trace_check  (cwd=.)
exit=0 timed_out=False tests_ran=34 duration=0.22s
..................................
----------------------------------------------------------------------
Ran 34 tests in 0.145s

OK
```

## uiowa_rfq_18649_output_agreement — WORKING

- phase: draft_review
- reason: executed 1 test file(s) here, 41 tests ran, all passed
- files: 48 (3 py, 1 doc, 44 data)

```
$ python3 -m unittest test_output_agreement  (cwd=.)
exit=0 timed_out=False tests_ran=41 duration=0.11s
itation reaches nothing.


CROSS-OUTPUT AGREEMENT - corrected (regenerated)
==============================================================
errors: 1   warnings: 0
  DANGLING_ID                  1

FAIL - the outputs disagree:

[DANGLING_ID] ERROR
  conflict  : executive_summary <-> matrix
  field     : cites
  subject   : executive_summary:ES-05
  detail    : cites 'FND-SYN-ESS-XX-999', which is not defined in the matrix. A reader following this citation reaches nothing.

.CROSS-OUTPUT AGREEMENT - state_mismatch
==============================================================
errors: 1   warnings: 0
  STATE_MISMATCH               1

FAIL - the outputs disagree:

[STATE_MISMATCH] ERROR
  conflict  : presentation_source <-> matrix
  field     : status
  subject   : presentation_source:PS-02 (slide S3)
  detail    : states 'FND-SYN-RIS-SEC-001' is SUPPORTED; the matrix records PARTIAL.


CROSS-OUTPUT AGREEMENT - corrected (regenerated)
==============================================================
errors: 0   warnings: 0

PASS - the four outputs agree.
......................................
----------------------------------------------------------------------
Ran 41 tests in 0.023s

OK
```

## uiowa_rfq_18649_report_structure — WORKING

- phase: final_delivery
- reason: executed 1 test file(s) here, 55 tests ran, all passed
- files: 14 (3 py, 3 doc, 8 data)

```
$ python3 -m unittest test_report_structure  (cwd=.)
exit=0 timed_out=False tests_ran=55 duration=0.2s
atched : "non-compliant"
  in      : The service is non-compliant and we recommend purchasing a new tool.
  why     : States a compliance determination. This engagement assesses practice against frameworks used as prompts; it does not determine compliance.
  rewrite : Describe the observed practice and the gap against the referenced clause, e.g. 'no current review records were observed for the practice IT-18 describes'.

[PP-01] product_procurement  /tmp/tmp8ftgiri6/drifted.md:1
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
Ran 55 tests in 0.109s

OK (skipped=1)
```

## uiowa_rfq_18649_report_visuals — WORKING

- phase: final_delivery
- reason: executed 1 test file(s) here, 90 tests ran, all passed
- files: 37 (9 py, 6 doc, 2 data)

```
$ python3 -m unittest test_report_visuals  (cwd=.)
exit=0 timed_out=False tests_ran=90 duration=0.24s
vg
  55f321f0a4b9  cross-group.print.svg
  9f1d2fed9da4  cross-group.screen.mono.svg
  d7a0e1c821e5  cross-group.screen.svg
  39205ecd4971  evidence-coverage-table.md
  51025a06a601  evidence-coverage.print.mono.svg
  37f343e9b817  evidence-coverage.print.svg
  b445c051a5c8  evidence-coverage.screen.mono.svg
  8961f3d29334  evidence-coverage.screen.svg
  aaf90a616305  matrix-table.md
  d899c0aa4eac  matrix.print.mono.svg
  7181f3ed74bd  matrix.print.svg
  60d57f792ad3  matrix.screen.mono.svg
  de6b78b4f7c5  matrix.screen.svg
  18b568b03721  roadmap-table.md
  b5ef70d048e5  roadmap.print.mono.svg
  63966088f065  roadmap.print.svg
  97802a377b8e  roadmap.screen.mono.svg
  560dc4450dd2  roadmap.screen.svg
  ed21faeec943  states.print.mono.svg
  c708e94b4922  states.print.svg
  64c6e9cd9f8b  states.screen.mono.svg
  beb8c5b7e69d  states.screen.svg
  58d68707c760  text-alternatives.md

7 of 12 cells rated; 2 insufficient evidence; 1 not assessed; 1 not applicable; 1 sources disagree; 0 no record supplied.
......................................................................................
----------------------------------------------------------------------
Ran 90 tests in 0.151s

OK
```

## uiowa_rfq_18649_integration — WORKING

- phase: final_delivery
- reason: no unittest suite; documented runner `python3 integrate_tabular.py --repo /home/user/commons --out /tmp/verify_kit_out_flpo2l13/integration.json` was executed here and exited 0 with output
- files: 3 (2 py, 0 doc, 1 data)

```
$ python3 integrate_tabular.py --repo /home/user/commons --out /tmp/verify_kit_out_flpo2l13/integration.json
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

## uiowa_rfq_18649_acceptance_map — DRAFT

- phase: final_delivery
- reason: check executed and did not pass: 1 of 1 test file(s) failed
- files: 20 (4 py, 5 doc, 11 data)

```
$ python3 -m unittest test_acceptance_map  (cwd=.)
exit=1 timed_out=False tests_ran=18 duration=0.1s
==================================================
FAIL: test_deleting_a_bound_artifact_never_leaves_it_demonstrable (test_acceptance_map.TestHostileAndReadOnly.test_deleting_a_bound_artifact_never_leaves_it_demonstrable)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/verify_kit_m9d72jwo/uiowa_rfq_18649_acceptance_map/test_acceptance_map.py", line 269, in test_deleting_a_bound_artifact_never_leaves_it_demonstrable
    self.assertTrue(os.path.isfile(target))
AssertionError: False is not true

======================================================================
FAIL: test_cli_exits_3_instead_of_raising (test_acceptance_map.TestPacketDirectoryIsNotBlindlyDeleted.test_cli_exits_3_instead_of_raising)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/verify_kit_m9d72jwo/uiowa_rfq_18649_acceptance_map/test_acceptance_map.py", line 359, in test_cli_exits_3_instead_of_raising
    self.assertEqual(rc, 3)
AssertionError: 2 != 3

----------------------------------------------------------------------
Ran 18 tests in 0.022s

FAILED (failures=2, errors=10)
```

## uiowa_rfq_18649_milestone_packets — WORKING

- phase: final_delivery
- reason: executed 1 test file(s) here, 55 tests ran, all passed
- files: 32 (7 py, 16 doc, 9 data)

```
$ python3 -m unittest test_milestone_packets  (cwd=.)
exit=0 timed_out=False tests_ran=55 duration=0.21s
_OVERDUE             M-2 DEP-M2-01: IAM deployment log export outstanding; the IAM deployment cell stays UNKNOWN until it arrives - 15 day(s) past the needed-by date (needed by 2026-11-10, as of 2026-11-25)
  ERROR E_ARTIFACT_DOES_NOT_OPEN         M-3 final/appendix-evidence-v1.0.csv: UNRESOLVED_MISSING - no file at the cited path; the citation cannot be verified
  ERROR E_VERSION_NOT_IDENTIFIABLE       M-3 final/readout-deck-outline.md: opened (sha256 cd71874c4779...) but declared_version is UNKNOWN, so the delivered version cannot be named
  ERROR E_MISSING_DISPOSITION            M-3 IDX-M3-003: no disposition decision recorded. The item is not assigned a default; a person must decide retain / return / destroy / client-system.
  WARN  W_DEPENDENCY_UNDATED             M-3 DEP-M3-01: Client confirmation of the accessibility review scope for the final report - open with no agreed date; it cannot be called on time or late

wrote           17 file(s) under /tmp/tmplwmn9ejg/out
ERROR: engagement file not found: /tmp/tmplwmn9ejg/nope.json
....................................................
----------------------------------------------------------------------
Ran 55 tests in 0.122s

OK
```

## uiowa_rfq_18649_exec_summary — WORKING

- phase: final_delivery
- reason: executed 1 test file(s) here, 42 tests ran, all passed
- files: 13 (6 py, 3 doc, 4 data)

```
$ python3 -m unittest test_exec_summary  (cwd=.)
exit=0 timed_out=False tests_ran=42 duration=0.07s
..........................................
----------------------------------------------------------------------
Ran 42 tests in 0.004s

OK
```

## uiowa_rfq_18649_print_pagination — WORKING

- phase: final_delivery
- reason: executed 1 test file(s) here, 39 tests ran, all passed
- files: 24 (2 py, 7 doc, 9 data)

```
$ python3 -m unittest test_printreport  (cwd=.)
exit=0 timed_out=False tests_ran=39 duration=0.15s
son.
document                   render pages  defects  CLIPP  ORPHA  TABLE  CITAT
----------------------------------------------------------------------------
report_document            naive      4       65     64      0      1      0   no_text_lost=True pdf_valid=True
report_document            fixed      4        0      0      0      0      0   no_text_lost=True pdf_valid=True
boundary_orphan_heading    naive      2        1      0      1      0      0   no_text_lost=True pdf_valid=True
boundary_orphan_heading    fixed      2        0      0      0      0      0   no_text_lost=True pdf_valid=True
boundary_citation_split    naive      2        1      0      0      0      1   no_text_lost=True pdf_valid=True
boundary_citation_split    fixed      2        0      0      0      0      0   no_text_lost=True pdf_valid=True

fixed-renderer defects across all documents: 0
VISUAL CHECK BY A HUMAN: OUTSTANDING - not performed. Every page was checked geometrically; nobody has looked at the PDFs. They are in /tmp/uiowa123-cli-h0kl75fn so that it can be done.
.....................................
----------------------------------------------------------------------
Ran 39 tests in 0.086s

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
....wrote /tmp/tmp0txaleaz/a/readout-deck.md
wrote /tmp/tmp0txaleaz/a/readout-deck-ascii.txt
wrote /tmp/tmp0txaleaz/a/deck-report-agreement.md
wrote /tmp/tmp0txaleaz/a/readout-planning-table.csv
agreement: PASS (0 error(s), 0 warning(s))
wrote /tmp/tmp0txaleaz/b/readout-deck.md
wrote /tmp/tmp0txaleaz/b/readout-deck-ascii.txt
wrote /tmp/tmp0txaleaz/b/deck-report-agreement.md
wrote /tmp/tmp0txaleaz/b/readout-planning-table.csv
agreement: PASS (0 error(s), 0 warning(s))
.............................
----------------------------------------------------------------------
Ran 56 tests in 0.048s

OK
```

## uiowa_rfq_18649_qa_kit — MISSING

- phase: readout
- reason: no directory for this component exists under the survey root

## uiowa_rfq_18649_qa_refusal_contract — WORKING

- phase: readout
- reason: executed 1 test file(s) here, 57 tests ran, all passed
- files: 8 (5 py, 1 doc, 2 data)

```
$ python3 -m unittest test_qa  (cwd=.)
exit=0 timed_out=False tests_ran=57 duration=0.32s
.........................................................
----------------------------------------------------------------------
Ran 57 tests in 0.210s

OK
```
