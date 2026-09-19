# Cross-lane reproducibility audit

> Each command documented in a lane's own README is run twice, in separate processes, with PYTHONHASHSEED=0 and 1, on two private copies at two different absolute paths. The full resulting trees are byte-compared. Nothing runs against the tree itself.

> **Reading UNKNOWN.** UNKNOWN means no documented command could be run. It is not a pass, and it is not a finding against the lane.

| verdict | count |
|---|---|
| `FAILED` | 13 |
| `REPRODUCIBLE` | 36 |
| `UNKNOWN` | 8 |
| `VARIES` | 4 |

| lane | verdict | detail |
|---|---|---|
| `uiowa_rfq_18649_acceptance_map` | **FAILED** | the documented command exited 2 and wrote nothing new: EXHIBIT NOT FOUND: ../uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md |
| `uiowa_rfq_18649_adoption_readiness` | **REPRODUCIBLE** | 14 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_ai_decision_case` | **REPRODUCIBLE** | 18 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_ai_eval_kit` | **REPRODUCIBLE** | 12 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_ai_integration` | **REPRODUCIBLE** | 24 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_ai_opportunity_portfolio` | **FAILED** | the documented command exited 1 and wrote nothing new: FileNotFoundError: [Errno 2] No such file or directory: 'mine.json' |
| `uiowa_rfq_18649_ai_policy_to_workflow` | **REPRODUCIBLE** | 13 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_ai_use_inventory` | **REPRODUCIBLE** | 15 files byte-identical |
| `uiowa_rfq_18649_base_fee_economics` | **REPRODUCIBLE** | 10 files byte-identical |
| `uiowa_rfq_18649_bid_pack` | **REPRODUCIBLE** | 36 files byte-identical |
| `uiowa_rfq_18649_build_board` | **UNKNOWN** | no README.md, so no documented command to run; not assessed |
| `uiowa_rfq_18649_capability_appendix` | **REPRODUCIBLE** | 15 files byte-identical |
| `uiowa_rfq_18649_capacity_benchmark` | **VARIES** | differs: `results/BENCHMARK_REPORT.md`, `results/benchmark_results.csv`, `results/benchmark_results.json`, `results/environment.json` (timestamp_like) |
| `uiowa_rfq_18649_capacity_feasibility` | **REPRODUCIBLE** | 9 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_capacity_scan` | **VARIES** | differs: `results/kit_scan_results.json` (unclassified) |
| `uiowa_rfq_18649_closeout` | **REPRODUCIBLE** | 15 files byte-identical |
| `uiowa_rfq_18649_contractor_transition` | **FAILED** | the documented command exited 1 and wrote nothing new: items=6 completed=2 unresolved=2 no_evidence=2 closed=False issues=0 |
| `uiowa_rfq_18649_deadline_continuity` | **REPRODUCIBLE** | 13 files byte-identical |
| `uiowa_rfq_18649_delivery_metrics` | **UNKNOWN** | no README.md, so no documented command to run; not assessed |
| `uiowa_rfq_18649_delivery_scan` | **FAILED** | the documented command exited 1 and wrote nothing new: This screen reuses the UIOWA-082 guard rather than reimplementing it. |
| `uiowa_rfq_18649_doc_usability` | **UNKNOWN** | README documents no runnable command; not assessed. This is not a pass. |
| `uiowa_rfq_18649_document_extraction` | **FAILED** | the documented command exited 1 and wrote nothing new: pyo3_runtime.PanicException: Python API call failed |
| `uiowa_rfq_18649_economics_resource_adapters` | **FAILED** | the documented command exited 2 and wrote nothing new: INTEGRATION ERROR: recommendation register not found at /tmp/ra_a_m9gtc26o/lane/fixtures/register.fallback.json |
| `uiowa_rfq_18649_exec_summary` | **REPRODUCIBLE** | 13 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_export_safety` | **VARIES** | differs: `examples/findings.json` (unclassified) |
| `uiowa_rfq_18649_filesystem_safety` | **FAILED** | the documented command exited 2 and wrote nothing new: ERROR: not a directory: /tmp/ra_a_dr131emz/lane/_audit_redirect/revenue |
| `uiowa_rfq_18649_handoff` | **REPRODUCIBLE** | 7 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_incident_learning` | **UNKNOWN** | every documented command was skipped; not assessed. This is not a pass. |
| `uiowa_rfq_18649_intake_rehearsal` | **REPRODUCIBLE** | 25 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_integration` | **UNKNOWN** | no README.md, so no documented command to run; not assessed |
| `uiowa_rfq_18649_milestone_packets` | **REPRODUCIBLE** | 32 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_mobilization` | **UNKNOWN** | README documents no runnable command; not assessed. This is not a pass. |
| `uiowa_rfq_18649_observability` | **REPRODUCIBLE** | 5 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_operator_handoff` | **VARIES** | differs: `sample/component_status.json`, `sample/verification_log.md` (unclassified) |
| `uiowa_rfq_18649_outcome_measurement` | **REPRODUCIBLE** | 7 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_output_agreement` | **REPRODUCIBLE** | 48 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_print_pagination` | **REPRODUCIBLE** | 24 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_prioritization` | **REPRODUCIBLE** | 12 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_qa_refusal_contract` | **REPRODUCIBLE** | 8 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_question_cards` | **REPRODUCIBLE** | 11 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_rating_model` | **UNKNOWN** | no README.md, so no documented command to run; not assessed |
| `uiowa_rfq_18649_readout_deck` | **REPRODUCIBLE** | 13 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_recovery_evidence` | **REPRODUCIBLE** | 16 files byte-identical |
| `uiowa_rfq_18649_release_provenance` | **REPRODUCIBLE** | 9 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_release_recovery_case` | **REPRODUCIBLE** | 19 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_report_structure` | **FAILED** | the documented command exited 1 and wrote nothing new: FileNotFoundError: [Errno 2] No such file or directory: 'path/to/draft.md' |
| `uiowa_rfq_18649_report_visuals` | **REPRODUCIBLE** | 37 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_roadmap_dependencies` | **REPRODUCIBLE** | 16 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_run_sweep` | **FAILED** | the documented command exited 2 and wrote nothing new: error: root /tmp/ra_a_1d1vfdeg/lane/_audit_redirect/repo does not exist |
| `uiowa_rfq_18649_scope_change` | **REPRODUCIBLE** | 8 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_secure_guidance` | **REPRODUCIBLE** | 7 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_security_event_review` | **REPRODUCIBLE** | 8 files byte-identical |
| `uiowa_rfq_18649_synthetic_collection` | **UNKNOWN** | README documents no runnable command; not assessed. This is not a pass. |
| `uiowa_rfq_18649_test_data_readiness` | **REPRODUCIBLE** | 10 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_traceability` | **FAILED** | the documented command exited 1 and wrote nothing new: FileNotFoundError: [Errno 2] No such file or directory: '/tmp/ra_a_bymk1s9o/lane/_audit_redirect/revenue' |
| `uiowa_rfq_18649_traceability_rehearsal` | **REPRODUCIBLE** | 8 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_uncertainty_lint` | **REPRODUCIBLE** | 5 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_unknown_propagation` | **REPRODUCIBLE** | 11 files byte-identical; committed artifacts still match the code |
| `uiowa_rfq_18649_vocabulary_crosswalk` | **FAILED** | the documented command exited 2 and wrote nothing new: FILE NOT FOUND: ../uiowa_rfq_18649_intake_rehearsal/artifacts/assessment_matrix.csv |
| `uiowa_rfq_18649_workbench` | **FAILED** | the documented command exited 1 and wrote nothing new: ModuleNotFoundError: No module named 'playwright' |
| `uiowa_rfq_18649_workshare` | **FAILED** | the documented command exited 2 and wrote nothing new: ERROR: cannot open input safely: /tmp/ra_a_0f9ut3fe/lane/_audit_redirect/uiowa-report.json: No such file or directory |

## Commands run

**`uiowa_rfq_18649_acceptance_map`**

- `python3 build_index.py --revenue-root .. --out output` → FAILED — the documented command exited 2 and wrote nothing new: EXHIBIT NOT FOUND: ../uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md
- `python3 -m unittest test_acceptance_map` → SKIPPED — test suite, not an artifact command
- `python3 exhibit_parser.py ../uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md` → FAILED — the documented command exited 1 and wrote nothing new: FileNotFoundError: [Errno 2] No such file or directory: '../uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md'

**`uiowa_rfq_18649_adoption_readiness`**

- `python3 readiness.py` → REPRODUCIBLE
- `python3 readiness.py --instrument-only` → REPRODUCIBLE
- `python3 readiness.py --teams fixtures/hostile_teams.json --outdir out_hostile` → REPRODUCIBLE
- `python3 readiness.py --catalog fixtures/hostile_catalog.json --outdir out_badplan` → REPRODUCIBLE
- `python3 -m unittest -v test_readiness` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_ai_decision_case`**

- `python3 ai_decision_case.py --case fixtures/beneficial.json` → REPRODUCIBLE
- `python3 ai_decision_case.py --case fixtures/unfavourable.json --sweep` → REPRODUCIBLE
- `python3 ai_decision_case.py --case fixtures/undecidable.json --format json` → REPRODUCIBLE
- `python3 ai_decision_case.py --case fixtures/beneficial.json --set analyst_hourly_cost=40 --diff` → REPRODUCIBLE
- `python3 -m unittest test_ai_decision_case -v` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_ai_eval_kit`**

- `python3 eval_kit.py validate` → REPRODUCIBLE
- `python3 eval_kit.py report` → REPRODUCIBLE
- `python3 eval_kit.py check-digest` → REPRODUCIBLE
- `python3 -m unittest -v` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_ai_integration`**

- `python3 build_kit.py` → REPRODUCIBLE
- `python3 demo_swap.py` → REPRODUCIBLE
- `python3 -m unittest -v test_ai_integration` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_ai_opportunity_portfolio`**

- `python3 opportunity_portfolio.py` → REPRODUCIBLE
- `python3 opportunity_portfolio.py --composite` → REPRODUCIBLE
- `python3 opportunity_portfolio.py --candidates mine.json --out /tmp/run` → FAILED — the documented command exited 1 and wrote nothing new: FileNotFoundError: [Errno 2] No such file or directory: 'mine.json'
- `python3 -m unittest test_opportunity_portfolio -v` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_ai_policy_to_workflow`**

- `python3 policy_matrix.py` → REPRODUCIBLE
- `python3 policy_matrix.py --fixtures fixtures --out /tmp/out` → REPRODUCIBLE
- `python3 -m unittest test_policy_matrix -v` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_ai_use_inventory`**

- `python3 inventory.py --input fixtures/synthetic_ai_use.json --outdir out` → REPRODUCIBLE
- `python3 inventory.py --input fixtures/synthetic_ai_use.json --print` → REPRODUCIBLE
- `python3 inventory.py --input fixtures/synthetic_ai_use_hostile.json --print` → REPRODUCIBLE
- `python3 interview_guide.py --guide` → REPRODUCIBLE
- `python3 interview_guide.py --probes fixtures/synthetic_ai_use.json` → REPRODUCIBLE
- `python3 -m unittest -v test_inventory` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_base_fee_economics`**

- `python3 analyze.py --resolve WP5.correction_hours=14,22,40` → REPRODUCIBLE
- `python3 analyze.py` → REPRODUCIBLE
- `python3 analyze.py --check` → REPRODUCIBLE
- `python3 -m unittest test_cost_model` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_bid_pack`**

- `python3 bid_pack.py --manifest fixtures/manifest.json --out sample_output` → REPRODUCIBLE
- `python3 bid_pack.py --manifest fixtures/manifest.json --out /tmp/x --strict` → REPRODUCIBLE
- `python3 packcheck.py sample_output/proposal.pdf sample_output/proposal.docx` → REPRODUCIBLE
- `python3 -m unittest test_bid_pack test_packcheck -v` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_capability_appendix`**

- `python3 capability_appendix.py record --observed-on 2026-09-19` → REPRODUCIBLE
- `python3 capability_appendix.py build --outdir out` → REPRODUCIBLE
- `python3 -m unittest -v test_capability_appendix` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_capacity_benchmark`**

- `python3 -m unittest discover -v` → SKIPPED — test suite, not an artifact command
- `python3 benchmark.py` → VARIES
- `python3 benchmark.py --sizes small` → VARIES
- `python3 generate_collection.py --profile medium --out /tmp/c` → REPRODUCIBLE
- `python3 workflow.py /tmp/c --mode optimized --out /tmp/out` → FAILED — the documented command exited 1 and wrote nothing new: WorkflowError: required input is missing: manifest.json

**`uiowa_rfq_18649_capacity_feasibility`**

- `python3 capacity_roadmap.py check --items data/roadmap-items.json --capacity data/capacity-assumptions.json` → REPRODUCIBLE
- `python3 capacity_roadmap.py plan --items data/roadmap-items.json --capacity data/capacity-assumptions.json --outdir examples` → REPRODUCIBLE
- `python3 capacity_roadmap.py rules` → REPRODUCIBLE
- `python3 -m unittest -v test_capacity_roadmap` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_capacity_scan`**

- `python3 -m unittest discover -v` → SKIPPED — test suite, not an artifact command
- `python3 scan_kit.py --revenue ../ --out results` → VARIES
- `python3 scan_hotspots.py <any-directory>` → SKIPPED — uses shell redirection or chaining, which this audit does not run through a shell

**`uiowa_rfq_18649_closeout`**

- `python -m unittest -v test_closeout.py` → SKIPPED — test suite, not an artifact command
- `python closeout.py sample/engagement.json sample/evidence_inventory.csv sample/disposition_log.csv --as-of 2026-12-21 --json-out /tmp/uiowa-closeout.json --md-out /tmp/uiowa-closeout.md` → REPRODUCIBLE

**`uiowa_rfq_18649_contractor_transition`**

- `python3 transition.py --input fixtures/contractor_transition.json --outdir out` → REPRODUCIBLE
- `python3 transition.py --input fixtures/contractor_transition.json --print` → FAILED — the documented command exited 1 and wrote nothing new: items=6 completed=2 unresolved=2 no_evidence=2 closed=False issues=0
- `python3 transition.py --input fixtures/contractor_transition_unsafe.json` → FAILED — the documented command exited 3 and wrote nothing new:   POSSIBLE_REAL_ID_NUMBER SYN-APP-003.note -- a nine-digit run is the shape of a real university ID
- `python3 -m unittest -v test_transition` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_deadline_continuity`**

- `python3 continuity.py --input fixtures/ris_deadline_scenario.json --outdir out` → REPRODUCIBLE
- `python3 continuity.py --input fixtures/ris_deadline_scenario.json --print` → REPRODUCIBLE
- `python3 -m unittest -v test_continuity` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_delivery_scan`**

- `python3 delivery_scan.py --root ..` → FAILED — the documented command exited 1 and wrote nothing new: This screen reuses the UIOWA-082 guard rather than reimplementing it.
- `python3 delivery_scan.py --root .. --out out/` → FAILED — the documented command exited 1 and wrote nothing new: This screen reuses the UIOWA-082 guard rather than reimplementing it.
- `python3 delivery_scan.py --root .. --fail-on-flag` → FAILED — the documented command exited 1 and wrote nothing new: This screen reuses the UIOWA-082 guard rather than reimplementing it.
- `python3 -m unittest -v test_delivery_scan.py` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_document_extraction`**

- `python -m pip install -r requirements.txt` → SKIPPED — environment or network command
- `python make_synthetic_corpus.py` → REPRODUCIBLE
- `python extract.py fixtures/sample.pdf > /tmp/sample-pdf.json` → SKIPPED — uses shell redirection or chaining, which this audit does not run through a shell
- `python extract.py fixtures/sample.docx > /tmp/sample-docx.json` → SKIPPED — uses shell redirection or chaining, which this audit does not run through a shell
- `python extract.py fixtures/sample.txt > /tmp/sample-text.json` → SKIPPED — uses shell redirection or chaining, which this audit does not run through a shell
- `python -m unittest -v test_extract.py` → SKIPPED — test suite, not an artifact command
- `python extract.py fixtures/sample.pdf` → FAILED — the documented command exited 1 and wrote nothing new: pyo3_runtime.PanicException: Python API call failed
- `python extract.py fixtures/sample.docx` → REPRODUCIBLE
- `python extract.py fixtures/sample.txt` → REPRODUCIBLE

**`uiowa_rfq_18649_economics_resource_adapters`**

- `python3 integrate.py` → FAILED — the documented command exited 2 and wrote nothing new: INTEGRATION ERROR: recommendation register not found at /tmp/ra_a_m9gtc26o/lane/fixtures/register.fallback.json
- `python3 -m unittest discover -p "test_*.py"` → SKIPPED — test suite, not an artifact command
- `python3 check_contract.py --explain resource` → REPRODUCIBLE
- `python3 check_contract.py --resource your_086_output.json` → FAILED — the documented command exited 2 and wrote nothing new: UNUSABLE: your_086_output.json not found
- `python3 check_contract.py --economics your_078_output.json` → FAILED — the documented command exited 2 and wrote nothing new: UNUSABLE: your_078_output.json not found
- `python3 check_contract.py --portfolio your_072_output.json` → FAILED — the documented command exited 2 and wrote nothing new: UNUSABLE: your_072_output.json not found
- `python3 check_contract.py --resource your.json --json` → FAILED — the documented command exited 2 and wrote nothing new: UNUSABLE: your.json not found

**`uiowa_rfq_18649_exec_summary`**

- `python3 build_summary.py` → REPRODUCIBLE
- `python3 -m unittest -v test_exec_summary` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_export_safety`**

- `python3 export_safety.py scan --root ..` → VARIES
- `python3 export_safety.py scan --root .. --lane uiowa_rfq_18649_workbench` → VARIES
- `python3 export_safety.py scan --root .. --skip-lane uiowa_rfq_18649_export_safety` → VARIES
- `python3 export_safety.py scan --root fixtures --include-self-fixtures --out /tmp/fx` → REPRODUCIBLE
- `python3 export_safety.py scan --root .. --fail-on HIGH` → VARIES
- `python3 -m unittest -v` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_filesystem_safety`**

- `python3 fs_safety.py --root /path/to/revenue --lane-prefix uiowa_rfq_18649 --output-dir examples/live_snapshot` → FAILED — the documented command exited 2 and wrote nothing new: ERROR: not a directory: /tmp/ra_a_dr131emz/lane/_audit_redirect/revenue

**`uiowa_rfq_18649_handoff`**

- `python handoff.py validate examples/planned_release.json` → REPRODUCIBLE
- `python handoff.py render examples/planned_release.json` → REPRODUCIBLE
- `python handoff.py validate examples/urgent_maintenance.json` → REPRODUCIBLE
- `python -m unittest discover -s tests -v` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_incident_learning`**

- `python incident_learning.py examples.json` → SKIPPED — script 'incident_learning.py' is not in this lane
- `python incident_learning.py examples.json --out /tmp/uiowa-067-result.json` → SKIPPED — script 'incident_learning.py' is not in this lane
- `python -m unittest -v test_incident_learning.py` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_intake_rehearsal`**

- `python3 rehearse_intake.py --collection sources --out artifacts` → REPRODUCIBLE
- `python3 rehearse_intake.py --collection sources --out artifacts --check-digest` → REPRODUCIBLE
- `python3 -m unittest test_rehearsal` → SKIPPED — test suite, not an artifact command
- `python3 rehearse_intake.py --collection sources --out artifacts --extra-collection ../uiowa_rfq_18649_synthetic_collection` → REPRODUCIBLE

**`uiowa_rfq_18649_milestone_packets`**

- `python3 milestone_packets.py fixtures/engagement.json --artifact-root fixtures/artifacts --output-dir examples --as-of 2026-11-25` → REPRODUCIBLE
- `python3 -m unittest test_milestone_packets -v` → SKIPPED — test suite, not an artifact command
- `python3 -O -m unittest test_milestone_packets` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_observability`**

- `python observability.py examples.json` → REPRODUCIBLE
- `python observability.py examples.json --out /tmp/uiowa-065-result.json` → REPRODUCIBLE
- `python -m unittest -v test_observability.py` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_operator_handoff`**

- `python3 -m unittest test_verify_kit` → SKIPPED — test suite, not an artifact command
- `python3 verify_kit.py --root fixtures/minikit --manifest fixtures/minikit_manifest.json` → REPRODUCIBLE
- `python3 verify_kit.py --root ../ --timeout 90 --out-json sample/component_status.json --out-csv sample/component_status.csv --out-md sample/verification_log.md` → VARIES
- `python3 render_guide.py --status sample/component_status.json --out OPERATOR_GUIDE.md` → REPRODUCIBLE
- `python3 command_index.py --root ../ --out COMMAND_INDEX.md --out-json sample/command_index.json` → VARIES

**`uiowa_rfq_18649_outcome_measurement`**

- `python analyze.py validate --recommendations recommendations.csv --register measure_register.csv --measurements examples/measurements.csv` → REPRODUCIBLE
- `python analyze.py report --recommendations recommendations.csv --register measure_register.csv --measurements examples/measurements.csv` → REPRODUCIBLE
- `python -m unittest discover -s tests -v` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_output_agreement`**

- `python3 output_agreement.py fixtures/consistent` → REPRODUCIBLE
- `python3 output_agreement.py fixtures/mismatched/count_mismatch` → REPRODUCIBLE
- `python3 output_agreement.py fixtures/mismatched/state_mismatch --regenerate /tmp/fixed` → REPRODUCIBLE
- `python3 make_bundle.py` → REPRODUCIBLE
- `python3 -m unittest -v test_output_agreement.py` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_print_pagination`**

- `python3 printreport.py` → REPRODUCIBLE
- `python3 printreport.py --document fixtures/report_document.json --out /tmp/out` → REPRODUCIBLE
- `python3 -m unittest test_printreport -v` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_prioritization`**

- `python3 prioritize.py` → REPRODUCIBLE
- `python3 prioritize.py --weights baseline --json-out out.json --csv-out out.csv --markdown-out out.md` → REPRODUCIBLE
- `python3 prioritize.py --weights quality-led` → REPRODUCIBLE
- `python3 prioritize.py --weights "quality=0.1,security=0.8,delivery=0.1"` → REPRODUCIBLE
- `python3 prioritize.py --sweep-dimension delivery --sweep-steps 200` → REPRODUCIBLE
- `python3 -m unittest -v test_prioritize.py` → SKIPPED — test suite, not an artifact command
- `python3 -O -m unittest test_prioritize.py` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_qa_refusal_contract`**

- `python3 cli.py audit` → REPRODUCIBLE
- `python3 cli.py drill` → REPRODUCIBLE
- `python3 cli.py ask "Has RIS tested restoring from backup?"` → REPRODUCIBLE
- `python3 cli.py ask "Which team is the worst?"` → REPRODUCIBLE
- `python3 cli.py ask "What is the uptime SLA for the student information system?"` → REPRODUCIBLE
- `python3 cli.py ask "Which team is the worst?" --json` → REPRODUCIBLE
- `python3 cli.py explain "what is the mean time to recovery for RIS"` → REPRODUCIBLE
- `python3 cli.py claim-types` → REPRODUCIBLE
- `python3 -m unittest test_qa.py` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_question_cards`**

- `python3 question_cards.py build` → REPRODUCIBLE
- `python3 question_cards.py check` → REPRODUCIBLE
- `python3 question_cards.py check --observations observations_hostile.json --out /tmp/h` → REPRODUCIBLE
- `python3 question_cards.py search --query "role:iam_administrator"` → REPRODUCIBLE
- `python3 question_cards.py search --query "type:ABSENT_EVIDENCE inventory"` → REPRODUCIBLE
- `python3 question_cards.py search --query "OBS-ESS-SEC-07"` → REPRODUCIBLE
- `python3 question_cards.py verify-export` → REPRODUCIBLE
- `python3 -m unittest -v` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_readout_deck`**

- `python3 deck_architecture.py check --report data/example-report.json --deck data/example-readout-deck.json` → REPRODUCIBLE
- `python3 deck_architecture.py render --report data/example-report.json --deck data/example-readout-deck.json --outdir examples` → REPRODUCIBLE
- `python3 deck_architecture.py rules` → REPRODUCIBLE
- `python3 -m unittest -v test_deck_architecture` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_recovery_evidence`**

- `python assess_recovery.py fixtures/synthetic_recovery_records.json --json-output /tmp/uiowa-068-report.json --csv-output /tmp/uiowa-068-matrix.csv --markdown-output /tmp/uiowa-068-scenario.md` → REPRODUCIBLE
- `python -m unittest -v test_assess_recovery.py` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_release_provenance`**

- `python provenance.py fixtures.json --case complete --artifact-root . --format markdown` → REPRODUCIBLE
- `python provenance.py fixtures.json --case missing-build --format markdown` → REPRODUCIBLE
- `python provenance.py fixtures.json --case digest-mismatch --format json` → REPRODUCIBLE
- `python provenance.py --schema` → REPRODUCIBLE
- `python -m unittest -v test_provenance.py` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_release_recovery_case`**

- `python3 release_recovery_case.py case.json --format markdown` → REPRODUCIBLE
- `python3 release_recovery_case.py fixtures/clean.json --format json` → REPRODUCIBLE
- `python3 release_recovery_case.py fixtures/timeline-disagreement.json` → REPRODUCIBLE
- `python3 release_recovery_case.py fixtures/ordering-inversion.json --format csv` → REPRODUCIBLE
- `python3 release_recovery_case.py case.json --json-output out/case_report.json --csv-output out/agreement_matrix.csv --markdown-output out/case_report.md --emit-provenance out/projected_provenance_packet.json --emit-recovery out/projected_recovery_records.json --emit-environment out/projected_environment_view.json` → REPRODUCIBLE
- `python3 release_recovery_case.py --schema` → REPRODUCIBLE
- `python3 make_fixtures.py` → REPRODUCIBLE
- `python3 -m unittest -v test_release_recovery_case.py` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_report_structure`**

- `python3 report_structure.py --check` → REPRODUCIBLE
- `python3 report_structure.py --verify-workbench ../..` → REPRODUCIBLE
- `python3 report_structure.py --scope-guard` → REPRODUCIBLE
- `python3 -m unittest -v test_report_structure.py` → SKIPPED — test suite, not an artifact command
- `python3 report_structure.py --render-template examples/report_template.md --render-sample examples/report_sample.md --render-map-csv examples/content_map.csv` → REPRODUCIBLE
- `python3 scope_guard.py path/to/draft.md --show-neutralized` → FAILED — the documented command exited 1 and wrote nothing new: FileNotFoundError: [Errno 2] No such file or directory: 'path/to/draft.md'

**`uiowa_rfq_18649_report_visuals`**

- `python3 render_report_visuals.py` → REPRODUCIBLE
- `python3 render_report_visuals.py --audit` → REPRODUCIBLE
- `python3 render_report_visuals.py --check-encoding` → REPRODUCIBLE
- `python3 -m unittest test_report_visuals` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_roadmap_dependencies`**

- `python3 depcheck.py --outdir out_consistent` → REPRODUCIBLE
- `python3 depcheck.py --roadmap fixtures/roadmap_inconsistent.json --outdir out_inconsistent --rehearse-repairs` → REPRODUCIBLE
- `python3 depcheck.py --roadmap fixtures/hostile_roadmap.json --outdir out_hostile` → REPRODUCIBLE
- `python3 -m unittest -v test_depcheck` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_run_sweep`**

- `python3 run_sweep.py --root /path/to/repo --observed-on 2026-09-19 --outdir out` → FAILED — the documented command exited 2 and wrote nothing new: error: root /tmp/ra_a_1d1vfdeg/lane/_audit_redirect/repo does not exist
- `python3 -m unittest -v test_run_sweep` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_scope_change`**

- `python3 scope_change.py` → REPRODUCIBLE
- `python3 scope_change.py --json-out out.json --csv-out out.csv --markdown-out out.md` → REPRODUCIBLE
- `python3 scope_change.py --sweep-role lead_reviewer` → REPRODUCIBLE
- `python3 -m unittest -v test_scope_change.py` → SKIPPED — test suite, not an artifact command
- `python3 -O -m unittest test_scope_change.py` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_secure_guidance`**

- `python3 assess_guidance.py fixtures/synthetic_guidance_packet.json --csv-out examples/guidance-usability.csv --md-out examples/discussion-pack.md` → REPRODUCIBLE
- `python3 -m unittest -v test_assess_guidance.py` → SKIPPED — test suite, not an artifact command
- `python3 -O -m unittest -v test_assess_guidance.py` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_security_event_review`**

- `python3 assess_security_events.py fixtures/synthetic_events.json --json-out /tmp/uiowa060-assessment.json --csv-out examples/security-event-evidence-matrix.csv --md-out examples/event-to-resolution-timeline.md` → REPRODUCIBLE
- `python3 -m unittest -v test_assess_security_events.py` → SKIPPED — test suite, not an artifact command
- `python3 -O -m unittest -v test_assess_security_events.py` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_test_data_readiness`**

- `python3 test_data_assessor.py fixtures/catalog.synthetic.json` → REPRODUCIBLE
- `python3 test_data_assessor.py fixtures/catalog.synthetic.json --format json --output report.json` → REPRODUCIBLE
- `python3 -m unittest -v tests/test_assessor.py` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_traceability`**

- `python3 trace_check.py bundle` → REPRODUCIBLE
- `python3 trace_check.py bundle_drifted` → REPRODUCIBLE
- `python3 trace_check.py bundle --format markdown` → REPRODUCIBLE
- `python3 trace_check.py bundle --format json` → REPRODUCIBLE
- `python3 trace_check.py bundle --rules` → REPRODUCIBLE
- `python3 -m unittest test_trace_check -v` → SKIPPED — test suite, not an artifact command
- `python3 trace_check.py bundle --register` → REPRODUCIBLE
- `python3 trace_check.py bundle --seal` → REPRODUCIBLE
- `python3 audit_self_sealing.py /path/to/revenue` → FAILED — the documented command exited 1 and wrote nothing new: FileNotFoundError: [Errno 2] No such file or directory: '/tmp/ra_a_bymk1s9o/lane/_audit_redirect/revenue'
- `python3 audit_self_sealing.py /path/to/revenue --only <lane>` → SKIPPED — uses shell redirection or chaining, which this audit does not run through a shell
- `python3 audit_self_sealing.py /path/to/revenue --format json` → FAILED — the documented command exited 1 and wrote nothing new: FileNotFoundError: [Errno 2] No such file or directory: '/tmp/ra_a_ior07ze6/lane/_audit_redirect/revenue'
- `python3 audit_assertions.py /path/to/revenue` → FAILED — the documented command exited 1 and wrote nothing new: FileNotFoundError: [Errno 2] No such file or directory: '/tmp/ra_a_ifj6bos9/lane/_audit_redirect/revenue'
- `python3 audit_assertions.py /path/to/revenue --format json` → FAILED — the documented command exited 1 and wrote nothing new: FileNotFoundError: [Errno 2] No such file or directory: '/tmp/ra_a_m7xeime4/lane/_audit_redirect/revenue'

**`uiowa_rfq_18649_traceability_rehearsal`**

- `python validate_trace.py .` → REPRODUCIBLE

**`uiowa_rfq_18649_uncertainty_lint`**

- `python3 cli.py scan <dir>` → SKIPPED — uses shell redirection or chaining, which this audit does not run through a shell
- `python3 cli.py scan <dir> --all` → SKIPPED — uses shell redirection or chaining, which this audit does not run through a shell
- `python3 cli.py scan <dir> --json` → SKIPPED — uses shell redirection or chaining, which this audit does not run through a shell
- `python3 cli.py score` → REPRODUCIBLE
- `python3 cli.py explain` → REPRODUCIBLE
- `python3 -m unittest test_lint.py` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_unknown_propagation`**

- `python3 scan_unknowns.py --root ..` → REPRODUCIBLE
- `python3 scan_unknowns.py --root fixtures --lane-prefix lane_ --crosswalk ""` → REPRODUCIBLE
- `python3 -m unittest -v test_scan_unknowns.py` → SKIPPED — test suite, not an artifact command
- `python3 -O -m unittest test_scan_unknowns.py` → SKIPPED — test suite, not an artifact command

**`uiowa_rfq_18649_vocabulary_crosswalk`**

- `python3 reconcile.py --revenue-root .. --out output` → REPRODUCIBLE
- `python3 -m unittest test_vocabulary` → SKIPPED — test suite, not an artifact command
- `python3 scan_vocabulary.py ..` → REPRODUCIBLE
- `python3 join_safety.py --revenue-root .. --left uiowa_rfq_18649_intake_rehearsal/artifacts/assessment_matrix.csv --right uiowa_rfq_18649_synthetic_collection/coverage_matrix.csv` → FAILED — the documented command exited 2 and wrote nothing new: FILE NOT FOUND: ../uiowa_rfq_18649_intake_rehearsal/artifacts/assessment_matrix.csv

**`uiowa_rfq_18649_workbench`**

- `python3 server.py --port 8765` → SKIPPED — starts a server
- `python3 -m py_compile server.py test_workbench.py browser_acceptance.py` → SKIPPED — starts a server
- `python3 -m unittest -v test_workbench.py` → SKIPPED — test suite, not an artifact command
- `python3 -O -m unittest -v test_workbench.py` → SKIPPED — test suite, not an artifact command
- `python3 browser_acceptance.py` → FAILED — the documented command exited 1 and wrote nothing new: ModuleNotFoundError: No module named 'playwright'

**`uiowa_rfq_18649_workshare`**

- `python compiler.py compile fixtures/synthetic_packet.json fixtures/synthetic_authority.json /tmp/uiowa-report.json` → REPRODUCIBLE
- `python compiler.py verify /tmp/uiowa-report.json` → FAILED — the documented command exited 2 and wrote nothing new: ERROR: cannot open input safely: /tmp/ra_a_0f9ut3fe/lane/_audit_redirect/uiowa-report.json: No such file or directory
- `python compiler.py render /tmp/uiowa-report.json /tmp/uiowa-report.md` → FAILED — the documented command exited 2 and wrote nothing new: ERROR: cannot open input safely: /tmp/ra_a_n9dzfwiw/lane/_audit_redirect/uiowa-report.json: No such file or directory
- `python -m unittest -v test_compiler.py` → SKIPPED — test suite, not an artifact command
- `python -O -m unittest -v test_compiler.py` → SKIPPED — test suite, not an artifact command
