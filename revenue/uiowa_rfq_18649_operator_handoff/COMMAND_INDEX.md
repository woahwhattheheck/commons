# Command index

**What do I type?** — every command below was discovered by executing the
script with `--help` in a throwaway copy of its lane and keeping the ones that
answered with a real usage line. None of it was read out of a README, so none
of it can be stale relative to the code in the way documentation can.

- survey root: `/tmp/claude-0/-home-user/6e551c41-37c5-5a0b-95f1-fb4584e151a7/scratchpad/m3QGjY`
- generated (UTC): 2026-09-19T14:16:43Z · python 3.11.15
- **54 verified command lines across 43 of 57 components**

Regenerate with:

```bash
cd revenue/uiowa_rfq_18649_operator_handoff
python3 command_index.py --root ../ --out COMMAND_INDEX.md --out-json sample/command_index.json
```

A component listed as having **no verified command line** is not broken. It
either ships documents and data rather than a program, or its code is imported
by something else. Open it and read it; do not invent a command for it.

---

## 1. Kickoff and mobilization

### `uiowa_rfq_18649_bid_pack`

UIOWA-136: assembles prepared proposal components into a navigable bidder attachment set.

```bash
cd revenue/uiowa_rfq_18649_bid_pack
python3 bid_pack.py --help
```

- `bid_pack.py` → `usage: bid_pack.py [-h] --manifest MANIFEST --out OUT [--strict]`

### `uiowa_rfq_18649_build_board`

Assessment context notes used to brief the team.

_No verified command line._ no top-level python modules; this component is documents or data

### `uiowa_rfq_18649_capability_appendix`

UIOWA-137: proposal capability appendix where no claim prints without a recorded demonstration.

```bash
cd revenue/uiowa_rfq_18649_capability_appendix
python3 capability_appendix.py --help
```

- `capability_appendix.py` → `usage: capability_appendix.py [-h] [--register REGISTER]`

### `uiowa_rfq_18649_filesystem_safety`

Read-only static screen over every Python tool in the kit: what can it write, and where. Run it before pointing any component at real material.

```bash
cd revenue/uiowa_rfq_18649_filesystem_safety
python3 fs_safety.py --help
```

- `fs_safety.py` → `usage: fs_safety.py [-h] --root ROOT [--lane-prefix LANE_PREFIX]`

### `uiowa_rfq_18649_mobilization`

Eight-week and six-week plan shapes, coordination forms, scope-confirmation agenda.

_No verified command line._ no top-level python modules; this component is documents or data

### `uiowa_rfq_18649_operator_handoff`

This handoff: the six-phase guide, the component verifier, and the UNKNOWN register. Start here.

```bash
cd revenue/uiowa_rfq_18649_operator_handoff
python3 command_index.py --help
cd revenue/uiowa_rfq_18649_operator_handoff
python3 render_guide.py --help
cd revenue/uiowa_rfq_18649_operator_handoff
python3 verify_kit.py --help
```

- `command_index.py` → `usage: command_index.py [-h] [--root ROOT] [--manifest MANIFEST]`
- `render_guide.py` → `usage: render_guide.py [-h] [--manifest MANIFEST] [--status STATUS]`
- `verify_kit.py` → `usage: verify_kit.py [-h] [--root ROOT] [--manifest MANIFEST]`

### `uiowa_rfq_18649_scope_change`

UIOWA-133: scope-change impact calculator; prices a change against the baseline with its assumptions printed next to the answer.

```bash
cd revenue/uiowa_rfq_18649_scope_change
python3 scope_change.py --help
```

- `scope_change.py` → `usage: scope_change.py [-h] [--baseline BASELINE] [--requests REQUESTS]`

### `uiowa_rfq_18649_workshare`

Carrier record and evidence-authority boundary for the whole workstream.

```bash
cd revenue/uiowa_rfq_18649_workshare
python3 compiler.py --help
```

- `compiler.py` → `usage: compiler.py [-h] {compile,verify,render} ...`

---

## 2. Evidence collection

### `uiowa_rfq_18649_ai_use_inventory`

Current AI use: active vs informal experiment vs planned.

```bash
cd revenue/uiowa_rfq_18649_ai_use_inventory
python3 interview_guide.py --help
cd revenue/uiowa_rfq_18649_ai_use_inventory
python3 inventory.py --help
```

- `interview_guide.py` → `usage: interview_guide.py [-h] [--guide] [--probes PROBES]`
- `inventory.py` → `usage: inventory.py [-h] --input INPUT [--outdir OUTDIR] [--print]`

### `uiowa_rfq_18649_contractor_transition`

UIOWA-108: staff-role changes, application ownership, service identities and runbook updates as one handoff scenario.

```bash
cd revenue/uiowa_rfq_18649_contractor_transition
python3 transition.py --help
```

- `transition.py` → `usage: transition.py [-h] --input INPUT [--outdir OUTDIR] [--print]`

### `uiowa_rfq_18649_deadline_continuity`

UIOWA-107: research-administration continuity scenario across a hard external deadline.

```bash
cd revenue/uiowa_rfq_18649_deadline_continuity
python3 continuity.py --help
```

- `continuity.py` → `usage: continuity.py [-h] --input INPUT [--outdir OUTDIR] [--print]`

### `uiowa_rfq_18649_document_extraction`

Locator-preserving extraction from PDF/DOCX/text evidence.

```bash
cd revenue/uiowa_rfq_18649_document_extraction
python3 extract.py --help
```

- `extract.py` → `usage: extract.py [-h] [-o OUTPUT] input`

### `uiowa_rfq_18649_handoff`

Development-to-operations handoff packet evidence.

```bash
cd revenue/uiowa_rfq_18649_handoff
python3 handoff.py --help
```

- `handoff.py` → `usage: handoff.py [-h] {validate,render} ...`

### `uiowa_rfq_18649_incident_learning`

Incident timelines, postmortems, corrective-action follow-through.

_No verified command line._ no top-level python modules; this component is documents or data

### `uiowa_rfq_18649_intake_rehearsal`

Intake-to-assessment rehearsal; malformed-input handling.

```bash
cd revenue/uiowa_rfq_18649_intake_rehearsal
python3 rehearse_intake.py --help
```

- `rehearse_intake.py` → `usage: rehearse_intake.py [-h] [--collection COLLECTION] [--out OUT]`

### `uiowa_rfq_18649_knowledge_readiness`

AI knowledge and data readiness evidence.

Not built yet — nothing to run.

### `uiowa_rfq_18649_observability`

Observability and service-objective evidence.

```bash
cd revenue/uiowa_rfq_18649_observability
python3 observability.py --help
```

- `observability.py` → `usage: observability.py [-h] [--out OUT] packet`

### `uiowa_rfq_18649_question_cards`

UIOWA-114: turns one unresolved observation into the follow-up question that would resolve it.

```bash
cd revenue/uiowa_rfq_18649_question_cards
python3 question_cards.py --help
```

- `question_cards.py` → `usage: question_cards.py [-h] [--data DATA] [--observations OBSERVATIONS]`

### `uiowa_rfq_18649_recovery_evidence`

Backup completion vs demonstrated restoration.

```bash
cd revenue/uiowa_rfq_18649_recovery_evidence
python3 assess_recovery.py --help
cd revenue/uiowa_rfq_18649_recovery_evidence
python3 recovery_evidence.py --help
```

- `assess_recovery.py` → `usage: assess_recovery.py [-h] [--json-output JSON_OUTPUT]`
- `recovery_evidence.py` → `usage: recovery_evidence.py [-h] [--estate ESTATE] [--outdir OUTDIR]`

### `uiowa_rfq_18649_release_provenance`

Deployment record traced to artifact digest and approval evidence.

```bash
cd revenue/uiowa_rfq_18649_release_provenance
python3 provenance.py --help
```

- `provenance.py` → `usage: provenance.py [-h] [--case CASE] [--schema] [--format {json,markdown}]`

### `uiowa_rfq_18649_secure_guidance`

Secure-development guidance usability evidence.

```bash
cd revenue/uiowa_rfq_18649_secure_guidance
python3 assess_guidance.py --help
```

- `assess_guidance.py` → `usage: assess_guidance.py [-h] --csv-out CSV_OUT --md-out MD_OUT packet`

### `uiowa_rfq_18649_security_event_review`

Security-event review and ownership evidence.

```bash
cd revenue/uiowa_rfq_18649_security_event_review
python3 assess_security_events.py --help
```

- `assess_security_events.py` → `usage: assess_security_events.py [-h] --json-out JSON_OUT --csv-out CSV_OUT`

### `uiowa_rfq_18649_synthetic_collection`

Fictional AIS evidence corpus; the safe input for every rehearsal.

_No verified command line._ no verified command line: 1 module(s) probed, none answered --help with a usage line

### `uiowa_rfq_18649_test_data_readiness`

Test-data catalog readiness evidence.

_No verified command line._ no top-level python modules; this component is documents or data

### `uiowa_rfq_18649_vocabulary_crosswalk`

Reconciles group and assessment-area vocabulary across components so the same thing has one name.

```bash
cd revenue/uiowa_rfq_18649_vocabulary_crosswalk
python3 reconcile.py --help
```

- `reconcile.py` → `usage: reconcile.py [-h] [--revenue-root REVENUE_ROOT] [--crosswalk CROSSWALK]`

---

## 3. Analysis

### `uiowa_rfq_18649_adoption_readiness`

Organizational adoption readiness; never rates individuals.

```bash
cd revenue/uiowa_rfq_18649_adoption_readiness
python3 readiness.py --help
```

- `readiness.py` → `usage: readiness.py [-h] [--teams TEAMS] [--indicators INDICATORS]`

### `uiowa_rfq_18649_ai_decision_case`

UIOWA-111: connects AI evaluation, lifecycle and economics into one decision case.

```bash
cd revenue/uiowa_rfq_18649_ai_decision_case
python3 ai_decision_case.py --help
```

- `ai_decision_case.py` → `usage: ai_decision_case.py [-h] --case CASE [--format {markdown,json,text}]`

### `uiowa_rfq_18649_ai_eval_kit`

AI usefulness evaluation tasks with known answers.

```bash
cd revenue/uiowa_rfq_18649_ai_eval_kit
python3 eval_kit.py --help
```

- `eval_kit.py` → `usage: eval_kit.py [-h] [--tasks TASKS] [--runs RUNS [RUNS ...]] [--out OUT]`

### `uiowa_rfq_18649_ai_integration`

Integration and portability readiness patterns.

_No verified command line._ no verified command line: 6 module(s) probed, none answered --help with a usage line

### `uiowa_rfq_18649_ai_opportunity_portfolio`

AI task suitability, benefit, integration effort.

```bash
cd revenue/uiowa_rfq_18649_ai_opportunity_portfolio
python3 opportunity_portfolio.py --help
```

- `opportunity_portfolio.py` → `usage: opportunity_portfolio.py [-h] [--candidates CANDIDATES] [--out OUT]`

### `uiowa_rfq_18649_ai_policy_to_workflow`

Policy-to-workflow assessment (NIST AI RMF as reference only).

```bash
cd revenue/uiowa_rfq_18649_ai_policy_to_workflow
python3 policy_matrix.py --help
```

- `policy_matrix.py` → `usage: policy_matrix.py [-h] [--fixtures FIXTURES] [--out OUT]`

### `uiowa_rfq_18649_capacity_benchmark`

Workflow capacity benchmark; measured vs estimated.

```bash
cd revenue/uiowa_rfq_18649_capacity_benchmark
python3 benchmark.py --help
cd revenue/uiowa_rfq_18649_capacity_benchmark
python3 generate_collection.py --help
cd revenue/uiowa_rfq_18649_capacity_benchmark
python3 workflow.py --help
```

- `benchmark.py` → `usage: benchmark.py [-h] [--sizes [{small,medium,large} ...]]`
- `generate_collection.py` → `usage: generate_collection.py [-h] [--profile {large,medium,small}] --out OUT`
- `workflow.py` → `usage: workflow.py [-h] [--mode {baseline,optimized}] [--out OUT] collection`

### `uiowa_rfq_18649_capacity_feasibility`

UIOWA-116: joins resource ranges to roadmap feasibility with real role-capacity arithmetic.

```bash
cd revenue/uiowa_rfq_18649_capacity_feasibility
python3 capacity_roadmap.py --help
```

- `capacity_roadmap.py` → `usage: capacity_roadmap.py [-h] {check,plan,rules} ...`

### `uiowa_rfq_18649_delivery_metrics`

Delivery metric calculation, data dictionary, interpretation notes.

```bash
cd revenue/uiowa_rfq_18649_delivery_metrics
python3 calculator.py --help
```

- `calculator.py` → `usage: calculator.py [-h] --window-start WINDOW_START --window-end WINDOW_END`

### `uiowa_rfq_18649_economics_resource_adapters`

UIOWA-105: joins economics and resource estimates onto the recommendation register, keeping effort, recurring cost, cash cost and released capacity separate.

```bash
cd revenue/uiowa_rfq_18649_economics_resource_adapters
python3 check_contract.py --help
cd revenue/uiowa_rfq_18649_economics_resource_adapters
python3 integrate.py --help
```

- `check_contract.py` → `usage: check_contract.py [-h]`
- `integrate.py` → `usage: integrate.py [-h] [--register REGISTER]`

### `uiowa_rfq_18649_outcome_measurement`

Adoption vs operational outcome, kept separate.

```bash
cd revenue/uiowa_rfq_18649_outcome_measurement
python3 analyze.py --help
```

- `analyze.py` → `usage: analyze.py [-h] {validate,report} ...`

### `uiowa_rfq_18649_prioritization`

Recommendation prioritization with visible weights and sensitivity.

```bash
cd revenue/uiowa_rfq_18649_prioritization
python3 prioritize.py --help
```

- `prioritize.py` → `usage: prioritize.py [-h] [--recommendations RECOMMENDATIONS]`

### `uiowa_rfq_18649_rating_model`

Area rating with an explicit decision table.

```bash
cd revenue/uiowa_rfq_18649_rating_model
python3 rating_model.py --help
```

- `rating_model.py` → `usage: rating_model.py [-h] [--json-out JSON_OUT]`

### `uiowa_rfq_18649_roadmap_dependencies`

UIOWA-115: graph check over recommendation prerequisites; finds cycles, missing prerequisites and phase inversions.

```bash
cd revenue/uiowa_rfq_18649_roadmap_dependencies
python3 depcheck.py --help
```

- `depcheck.py` → `usage: depcheck.py [-h] [--roadmap ROADMAP] [--outdir OUTDIR]`

### `uiowa_rfq_18649_workbench`

Local analyst surface over the workshare compiler.

```bash
cd revenue/uiowa_rfq_18649_workbench
python3 server.py --help
```

- `server.py` → `usage: server.py [-h] [--port PORT]`

---

## 4. Draft review

### `uiowa_rfq_18649_doc_usability`

Reviewer usability method and worksheets.

_No verified command line._ no top-level python modules; this component is documents or data

### `uiowa_rfq_18649_interchange`

CSV/JSON/doc interchange verification for review handoffs.

Not built yet — nothing to run.

### `uiowa_rfq_18649_output_agreement`

UIOWA-117: checks the matrix, recommendation register, executive summary and presentation agree with each other.

```bash
cd revenue/uiowa_rfq_18649_output_agreement
python3 make_bundle.py --help
cd revenue/uiowa_rfq_18649_output_agreement
python3 output_agreement.py --help
```

- `make_bundle.py` → `usage: make_bundle.py [-h] [--out OUT]`
- `output_agreement.py` → `usage: output_agreement.py [-h] [--json] [--regenerate OUT] bundle`

### `uiowa_rfq_18649_qa_kit`

Evidence-backed discussion and Q&A kit.

Not built yet — nothing to run.

### `uiowa_rfq_18649_traceability`

UIOWA-093: statement to finding to citation to source bytes, with drift detection; fails loudly on an orphan at any level.

```bash
cd revenue/uiowa_rfq_18649_traceability
python3 audit_assertions.py --help
cd revenue/uiowa_rfq_18649_traceability
python3 audit_self_sealing.py --help
cd revenue/uiowa_rfq_18649_traceability
python3 trace_check.py --help
```

- `audit_assertions.py` → `usage: audit_assertions.py [-h] [--prefix PREFIX] [--format {text,json}]`
- `audit_self_sealing.py` → `usage: audit_self_sealing.py [-h] [--prefix PREFIX] [--timeout TIMEOUT]`
- `trace_check.py` → `usage: trace_check.py [-h] [--format {text,json,markdown}] [--register]`

### `uiowa_rfq_18649_traceability_rehearsal`

Evidence to finding to recommendation to report-line trace validator.

Takes no arguments, so it has no `--help` interface. Documented runner,
executed by `verify_kit.py`:

```bash
cd revenue/uiowa_rfq_18649_traceability_rehearsal
python3 validate_trace.py
```

---

## 5. Final delivery

### `uiowa_rfq_18649_acceptance_map`

UIOWA-130: delivery acceptance criteria mapped to the artifacts that actually satisfy them.

```bash
cd revenue/uiowa_rfq_18649_acceptance_map
python3 build_index.py --help
```

- `build_index.py` → `usage: build_index.py [-h] [--revenue-root REVENUE_ROOT] [--exhibit EXHIBIT]`

### `uiowa_rfq_18649_closeout`

Evidence lifecycle and 30-day post-completion closeout templates.

```bash
cd revenue/uiowa_rfq_18649_closeout
python3 closeout.py --help
```

- `closeout.py` → `usage: closeout.py [-h] [--as-of AS_OF] [--json-out JSON_OUT]`

### `uiowa_rfq_18649_exec_summary`

UIOWA-081: leadership executive-summary template where every statement is traceable to a finding.

_No verified command line._ no verified command line: 5 module(s) probed, none answered --help with a usage line

### `uiowa_rfq_18649_integration`

Field-name and taxonomy reconciliation across components.

```bash
cd revenue/uiowa_rfq_18649_integration
python3 integrate_tabular.py --help
```

- `integrate_tabular.py` → `usage: integrate_tabular.py [-h] [--repo REPO] --out OUT`

### `uiowa_rfq_18649_milestone_packets`

UIOWA-135: milestone delivery packets; verifies every cited artifact by opening it.

```bash
cd revenue/uiowa_rfq_18649_milestone_packets
python3 milestone_packets.py --help
```

- `milestone_packets.py` → `usage: milestone_packets.py [-h] [--artifact-root ARTIFACT_ROOT]`

### `uiowa_rfq_18649_print_pagination`

UIOWA-123: renders the report to PDF and inspects every page for the defects that ruin a printed deliverable.

```bash
cd revenue/uiowa_rfq_18649_print_pagination
python3 printreport.py --help
```

- `printreport.py` → `usage: printreport.py [-h] [--document DOCUMENT] [--out OUT]`

### `uiowa_rfq_18649_report_structure`

RFQ-aligned final-report structure.

```bash
cd revenue/uiowa_rfq_18649_report_structure
python3 report_structure.py --help
cd revenue/uiowa_rfq_18649_report_structure
python3 scope_guard.py --help
```

- `report_structure.py` → `usage: report_structure.py [-h] [--map MAP] [--schemas SCHEMAS]`
- `scope_guard.py` → `usage: scope_guard.py [-h] [--json] [--show-neutralized] [paths ...]`

### `uiowa_rfq_18649_report_visuals`

Accessible visual language; unassessed stays distinct.

```bash
cd revenue/uiowa_rfq_18649_report_visuals
python3 render_report_visuals.py --help
```

- `render_report_visuals.py` → `usage: render_report_visuals.py [-h] [--data DATA] [--out OUT]`

---

## 6. Optional readout

### `uiowa_rfq_18649_qa_kit`

Q&A answers substantiated from supplied evidence.

Not built yet — nothing to run.

### `uiowa_rfq_18649_qa_refusal_contract`

UIOWA-089C: what the Q&A kit does when the evidence does NOT support an answer.

_No verified command line._ no verified command line: 4 module(s) probed, none answered --help with a usage line

### `uiowa_rfq_18649_readout_deck`

Deck architecture that agrees with the example report.

```bash
cd revenue/uiowa_rfq_18649_readout_deck
python3 deck_architecture.py --help
```

- `deck_architecture.py` → `usage: deck_architecture.py [-h] {check,render,rules} ...`
