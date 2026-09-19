# RFQ 18649 — operator handoff

> **Preparation kit for an assessment that has not been awarded.** Nothing in this
> repository is a University of Iowa finding, and every example input is synthetic
> and labelled as fiction. The kit is what an operator runs; the University's real
> inputs are listed at the end and are all **UNKNOWN** until supplied.

**Read this first.** You are picking up work built by many hands. The status
column below is not a promise from the people who wrote each component — it is the
result of `verify_kit.py` actually executing them, in an isolated copy, at the
timestamp shown. Regenerate it before you trust it.

- survey root: `/tmp/claude-0/-home-user/6e551c41-37c5-5a0b-95f1-fb4584e151a7/scratchpad/finalBBWi`
- snapshot taken (UTC): **2026-09-19T14:02:46Z** · python 3.11.15
- **WORKING 25 · DRAFT 7 · MISSING 6 · UNMAPPED 2**

## Refresh the status table before you rely on it

```bash
cd revenue/uiowa_rfq_18649_operator_handoff
python3 verify_kit.py --root ../ \
    --out-json sample/component_status.json \
    --out-csv  sample/component_status.csv \
    --out-md   sample/verification_log.md
python3 render_guide.py --status sample/component_status.json --out OPERATOR_GUIDE.md
```

`verify_kit.py` copies every lane to a temporary directory before running anything,
so it cannot modify work owned by another author. The copies are deleted afterwards.

## Status legend

| status | what it means here | how it was decided |
|---|---|---|
| **WORKING** | the operator can run this today | `verify_kit.py` executed the component's own unittest suite (or its documented runner) in an isolated copy and saw it pass |
| **DRAFT** | exists, but do not assume it runs | no automated check ships with it, or the check failed, timed out, or needs a dependency this offline environment does not have |
| **MISSING** | a phase needs it and it is not built yet | no directory for it exists under the survey root |
| **UNMAPPED** | found on disk, not yet placed in a phase | lanes land continuously; this is a bookkeeping signal, not a quality judgement |

No status in this table was taken from a component's README. A README is its
author's claim; the status column is an execution result.

## The six phases at a glance

| # | phase | components | WORKING | DRAFT | MISSING |
|---|---|---|---|---|---|
| 1 | [Kickoff and mobilization](#1-kickoff) | 4 | 2 | 2 | 0 |
| 2 | [Evidence collection](#2-evidence-collection) | 13 | 9 | 3 | 1 |
| 3 | [Analysis](#3-analysis) | 11 | 8 | 1 | 2 |
| 4 | [Draft review](#4-draft-review) | 4 | 1 | 1 | 2 |
| 5 | [Final delivery](#5-final-delivery) | 4 | 4 | 0 | 0 |
| 6 | [Optional readout](#6-readout) | 2 | 1 | 0 | 1 |

---

## 1. Kickoff and mobilization

Stand the engagement up: scope confirmation, contacts, schedule shape, coordination forms, and the assessment context the whole kit is built against.

**What the operator does in this phase**

- Read the mobilization plan and hold the scope-confirmation conversation with the University sponsor.
- Fill the coordination forms with real named contacts (all currently UNKNOWN).
- Record the agreed kickoff date; every date in the kit is relative to it.

| component (directory under `revenue/`) | status | what it is for |
|---|---|---|
| `uiowa_rfq_18649_operator_handoff` | **WORKING** | This handoff: the six-phase guide, the component verifier, and the UNKNOWN register. Start here. |
| `uiowa_rfq_18649_workshare` | **WORKING** | Carrier record and evidence-authority boundary for the whole workstream. |
| `uiowa_rfq_18649_build_board` | DRAFT | Assessment context notes used to brief the team. |
| `uiowa_rfq_18649_mobilization` | DRAFT | Eight-week and six-week plan shapes, coordination forms, scope-confirmation agenda. |

**Commands that were executed for this phase in the snapshot above**

```bash
(cd revenue/uiowa_rfq_18649_operator_handoff && python3 -m unittest test_verify_kit)
(cd revenue/uiowa_rfq_18649_workshare/methodology && python3 -m unittest test_validate_23_evidence_register)
(cd revenue/uiowa_rfq_18649_workshare && python3 -m unittest test_compiler)
```

**What is not ready in this phase, and why**

- `uiowa_rfq_18649_mobilization` — **DRAFT**: document component: 2 document/data files and no executable code; completeness of prose is not machine-checkable and needs a human read
- `uiowa_rfq_18649_build_board` — **DRAFT**: document component: 3 document/data files and no executable code; completeness of prose is not machine-checkable and needs a human read

---

## 2. Evidence collection

Gather what the University actually supplies, register it with stable IDs and exact locators, and rehearse the intake path before real documents arrive.

**What the operator does in this phase**

- Run the intake rehearsal against the synthetic corpus first, so malformed input handling is observed, not assumed.
- Register each supplied artifact with a stable evidence ID and an exact locator.
- Use the per-area interview worksheets to collect evidence for each assessment area.
- Anything not supplied stays UNKNOWN in the register. Never enter a zero for an absent input.

| component (directory under `revenue/`) | status | what it is for |
|---|---|---|
| `uiowa_rfq_18649_ai_use_inventory` | **WORKING** | Current AI use: active vs informal experiment vs planned. |
| `uiowa_rfq_18649_handoff` | **WORKING** | Development-to-operations handoff packet evidence. |
| `uiowa_rfq_18649_intake_rehearsal` | **WORKING** | Intake-to-assessment rehearsal; malformed-input handling. |
| `uiowa_rfq_18649_observability` | **WORKING** | Observability and service-objective evidence. |
| `uiowa_rfq_18649_recovery_evidence` | **WORKING** | Backup completion vs demonstrated restoration. |
| `uiowa_rfq_18649_release_provenance` | **WORKING** | Deployment record traced to artifact digest and approval evidence. |
| `uiowa_rfq_18649_secure_guidance` | **WORKING** | Secure-development guidance usability evidence. |
| `uiowa_rfq_18649_security_event_review` | **WORKING** | Security-event review and ownership evidence. |
| `uiowa_rfq_18649_synthetic_collection` | **WORKING** | Fictional AIS evidence corpus; the safe input for every rehearsal. |
| `uiowa_rfq_18649_document_extraction` | DRAFT | Locator-preserving extraction from PDF/DOCX/text evidence. |
| `uiowa_rfq_18649_incident_learning` | DRAFT | Incident timelines, postmortems, corrective-action follow-through. |
| `uiowa_rfq_18649_knowledge_readiness` | MISSING | AI knowledge and data readiness evidence. |
| `uiowa_rfq_18649_test_data_readiness` | DRAFT | Test-data catalog readiness evidence. |

**Commands that were executed for this phase in the snapshot above**

```bash
(cd revenue/uiowa_rfq_18649_synthetic_collection/tests && python3 -m unittest test_collection)
(cd revenue/uiowa_rfq_18649_intake_rehearsal && python3 -m unittest test_rehearsal)
(cd revenue/uiowa_rfq_18649_secure_guidance && python3 -m unittest test_assess_guidance)
(cd revenue/uiowa_rfq_18649_security_event_review && python3 -m unittest test_assess_security_events)
(cd revenue/uiowa_rfq_18649_observability && python3 -m unittest test_observability)
(cd revenue/uiowa_rfq_18649_recovery_evidence && python3 -m unittest test_assess_recovery)
(cd revenue/uiowa_rfq_18649_recovery_evidence && python3 -m unittest test_recovery_evidence)
(cd revenue/uiowa_rfq_18649_release_provenance && python3 -m unittest test_provenance)
(cd revenue/uiowa_rfq_18649_handoff/tests && python3 -m unittest test_handoff)
(cd revenue/uiowa_rfq_18649_ai_use_inventory && python3 -m unittest test_inventory)
```

**What is not ready in this phase, and why**

- `uiowa_rfq_18649_document_extraction` — **DRAFT**: check could not run offline: missing dependency 'pypdf' (declared: pypdf>=6,<7)
- `uiowa_rfq_18649_test_data_readiness` — **DRAFT**: check executed and did not pass: 1 of 2 test file(s) failed
- `uiowa_rfq_18649_incident_learning` — **DRAFT**: document component: 2 document/data files and no executable code; completeness of prose is not machine-checkable and needs a human read
- `uiowa_rfq_18649_knowledge_readiness` — **MISSING**: no directory for this component exists under the survey root

---

## 3. Analysis

Turn registered evidence into findings and prioritized recommendations with visible weights and explicit units.

**What the operator does in this phase**

- Apply the rating model to each assessment area using only supplied evidence.
- Run the prioritization calculator; inspect the sensitivity output before accepting an order.
- Keep every finding pointed at the evidence ID it came from — the traceability rehearsal is the check.

| component (directory under `revenue/`) | status | what it is for |
|---|---|---|
| `uiowa_rfq_18649_adoption_readiness` | **WORKING** | Organizational adoption readiness; never rates individuals. |
| `uiowa_rfq_18649_ai_eval_kit` | **WORKING** | AI usefulness evaluation tasks with known answers. |
| `uiowa_rfq_18649_ai_opportunity_portfolio` | **WORKING** | AI task suitability, benefit, integration effort. |
| `uiowa_rfq_18649_ai_policy_to_workflow` | **WORKING** | Policy-to-workflow assessment (NIST AI RMF as reference only). |
| `uiowa_rfq_18649_delivery_metrics` | **WORKING** | Delivery metric calculation, data dictionary, interpretation notes. |
| `uiowa_rfq_18649_outcome_measurement` | **WORKING** | Adoption vs operational outcome, kept separate. |
| `uiowa_rfq_18649_prioritization` | **WORKING** | Recommendation prioritization with visible weights and sensitivity. |
| `uiowa_rfq_18649_rating_model` | **WORKING** | Area rating with an explicit decision table. |
| `uiowa_rfq_18649_ai_integration` | MISSING | Integration and portability readiness patterns. |
| `uiowa_rfq_18649_capacity_benchmark` | MISSING | Workflow capacity benchmark; measured vs estimated. |
| `uiowa_rfq_18649_workbench` | DRAFT | Local analyst surface over the workshare compiler. |

**Commands that were executed for this phase in the snapshot above**

```bash
(cd revenue/uiowa_rfq_18649_rating_model && python3 -m unittest test_rating_model)
(cd revenue/uiowa_rfq_18649_prioritization && python3 -m unittest test_prioritize)
(cd revenue/uiowa_rfq_18649_delivery_metrics && python3 -m unittest test_calculator)
(cd revenue/uiowa_rfq_18649_outcome_measurement/tests && python3 -m unittest test_analyze)
(cd revenue/uiowa_rfq_18649_ai_opportunity_portfolio && python3 -m unittest test_opportunity_portfolio)
(cd revenue/uiowa_rfq_18649_ai_policy_to_workflow && python3 -m unittest test_policy_matrix)
(cd revenue/uiowa_rfq_18649_adoption_readiness && python3 -m unittest test_readiness)
(cd revenue/uiowa_rfq_18649_ai_eval_kit && python3 -m unittest test_eval_kit)
```

**What is not ready in this phase, and why**

- `uiowa_rfq_18649_workbench` — **DRAFT**: check executed and did not pass: 1 of 2 test file(s) failed
- `uiowa_rfq_18649_capacity_benchmark` — **MISSING**: no directory for this component exists under the survey root
- `uiowa_rfq_18649_ai_integration` — **MISSING**: no directory for this component exists under the survey root

---

## 4. Draft review

Prove the draft is followable back to source and usable by its readers, and capture feedback without flattening disagreement.

**What the operator does in this phase**

- Run the traceability validator; a broken trace is a blocker, not a footnote.
- Run the documentation usability method against the draft with a real reviewer task.
- Record unresolved disagreements as unresolved. Do not resolve them by deletion.

| component (directory under `revenue/`) | status | what it is for |
|---|---|---|
| `uiowa_rfq_18649_traceability_rehearsal` | **WORKING** | Evidence to finding to recommendation to report-line trace validator. |
| `uiowa_rfq_18649_doc_usability` | DRAFT | Reviewer usability method and worksheets. |
| `uiowa_rfq_18649_interchange` | MISSING | CSV/JSON/doc interchange verification for review handoffs. |
| `uiowa_rfq_18649_qa_kit` | MISSING | Evidence-backed discussion and Q&A kit. |

**Commands that were executed for this phase in the snapshot above**

```bash
(cd revenue/uiowa_rfq_18649_traceability_rehearsal && python3 validate_trace.py)
```

**What is not ready in this phase, and why**

- `uiowa_rfq_18649_doc_usability` — **DRAFT**: document component: 6 document/data files and no executable code; completeness of prose is not machine-checkable and needs a human read
- `uiowa_rfq_18649_qa_kit` — **MISSING**: no directory for this component exists under the survey root
- `uiowa_rfq_18649_interchange` — **MISSING**: no directory for this component exists under the survey root

---

## 5. Final delivery

Assemble the RFQ-aligned final report, check its accessible visual language, and close the evidence lifecycle.

**What the operator does in this phase**

- Assemble the report against the RFQ-aligned structure.
- Check the visual language reads without color alone and that unassessed cells stay visibly distinct from assessed ones.
- Run the closeout validator. It validates disposition records; it deletes nothing.

| component (directory under `revenue/`) | status | what it is for |
|---|---|---|
| `uiowa_rfq_18649_closeout` | **WORKING** | Evidence lifecycle and 30-day post-completion closeout templates. |
| `uiowa_rfq_18649_integration` | **WORKING** | Field-name and taxonomy reconciliation across components. |
| `uiowa_rfq_18649_report_structure` | **WORKING** | RFQ-aligned final-report structure. |
| `uiowa_rfq_18649_report_visuals` | **WORKING** | Accessible visual language; unassessed stays distinct. |

**Commands that were executed for this phase in the snapshot above**

```bash
(cd revenue/uiowa_rfq_18649_report_structure && python3 -m unittest test_report_structure)
(cd revenue/uiowa_rfq_18649_report_visuals && python3 -m unittest test_report_visuals)
(cd revenue/uiowa_rfq_18649_closeout && python3 -m unittest test_closeout)
(cd revenue/uiowa_rfq_18649_integration && python3 integrate_tabular.py --repo /home/user/commons --out /tmp/verify_kit_out_b8truv0b/integration.json)
```

---

## 6. Optional readout

Optional leadership readout. The deck must agree with the delivered report; detail lives in the appendix.

**What the operator does in this phase**

- Build the deck from the delivered report, not from a parallel narrative.
- Rehearse Q&A only against evidence that is actually in the report.

| component (directory under `revenue/`) | status | what it is for |
|---|---|---|
| `uiowa_rfq_18649_readout_deck` | **WORKING** | Deck architecture that agrees with the example report. |
| `uiowa_rfq_18649_qa_kit` | MISSING | Q&A answers substantiated from supplied evidence. |

**Commands that were executed for this phase in the snapshot above**

```bash
(cd revenue/uiowa_rfq_18649_readout_deck && python3 -m unittest test_deck_architecture)
```

**What is not ready in this phase, and why**

- `uiowa_rfq_18649_qa_kit` — **MISSING**: no directory for this component exists under the survey root

---

## Lanes discovered on disk but not yet placed in a phase

These landed after `kit_manifest.json` was last written. Assign each one to a
phase in the manifest; nothing is dropped silently.

| component | underlying observation |
|---|---|
| `uiowa_rfq_18649_acceptance_map` | lane found on disk but not placed in any phase by the manifest; underlying observation: check executed and did not pass: 1 of 1 test file(s) failed |
| `uiowa_rfq_18649_traceability` | lane found on disk but not placed in any phase by the manifest; underlying observation: executed 1 test file(s) here, 34 tests ran, all passed |

---

## University inputs still needed — all UNKNOWN

Every row below is an input the kit cannot manufacture. None of them has been
supplied, and none of them is being approximated, defaulted, or scored as zero.
A component that needs one of these cannot produce a real result until it arrives.

| id | phase | input needed | why the kit needs it | blocks | status |
|---|---|---|---|---|---|
| UNK-01 | kickoff | Confirmed kickoff date | Every date in the mobilization plan is expressed relative to kickoff; without it no schedule in the kit resolves to a calendar | `uiowa_rfq_18649_mobilization` | **UNKNOWN** |
| UNK-02 | kickoff | Named engagement sponsor and day-to-day University point of contact | The coordination forms have contact slots that cannot be filled by the kit; escalation path is undefined without them | `uiowa_rfq_18649_mobilization` | **UNKNOWN** |
| UNK-03 | kickoff | Authoritative list of AIS teams in scope and the services each one runs | Determines how many evidence sets exist and which assessment areas apply to each; the kit currently exercises three fictional teams | `uiowa_rfq_18649_synthetic_collection` | **UNKNOWN** |
| UNK-04 | kickoff | Written scope boundary: which systems and data are explicitly out of scope | Prevents the assessment from collecting evidence it has no authorization to hold | `uiowa_rfq_18649_workshare` | **UNKNOWN** |
| UNK-05 | kickoff | Access method and approval for any University system the team is permitted to view | The kit is offline by construction and connects to nothing; any read access is a separate University decision | `uiowa_rfq_18649_workshare` | **UNKNOWN** |
| UNK-06 | evidence_collection | Interview participant list with roles and availability windows | Determines interview scheduling and which worksheets are used; no scheduling is performed by the kit | `uiowa_rfq_18649_mobilization` | **UNKNOWN** |
| UNK-07 | evidence_collection | Real SDLC and change-management documentation | The analysis components read supplied documents; today they read a fictional corpus only | `uiowa_rfq_18649_document_extraction` | **UNKNOWN** |
| UNK-08 | evidence_collection | Incident records for an agreed lookback window including postmortems and corrective-action status | Incident learning needs at least one overdue action and one completed action to be assessable; the synthetic set supplies those only as fiction | `uiowa_rfq_18649_incident_learning` | **UNKNOWN** |
| UNK-09 | evidence_collection | Backup job records AND at least one documented restoration exercise | The kit deliberately separates backup completion from demonstrated restoration; only the University can supply evidence of the second | `uiowa_rfq_18649_recovery_evidence` | **UNKNOWN** |
| UNK-10 | evidence_collection | Monitoring and alerting configuration exports or screenshots and any service objectives in force | Observability assessment reads supplied evidence and connects to no monitoring system | `uiowa_rfq_18649_observability` | **UNKNOWN** |
| UNK-11 | evidence_collection | Security-event review records with ownership and disposition | Security-event assessment evaluates supplied records only; it reads no SIEM or identity system | `uiowa_rfq_18649_security_event_review` | **UNKNOWN** |
| UNK-12 | evidence_collection | Deployment records for a sample of releases with artifact identifiers and approval evidence | Release provenance traces a deployment to an artifact digest; without real records the trace is fictional | `uiowa_rfq_18649_release_provenance` | **UNKNOWN** |
| UNK-13 | evidence_collection | Current test-data catalog including ownership refresh cadence and retention rules | Test-data readiness assesses a supplied catalog; it cannot enumerate datasets itself | `uiowa_rfq_18649_test_data_readiness` | **UNKNOWN** |
| UNK-14 | evidence_collection | Inventory of AI tools currently in use separated into active use informal experimentation and planned | The AI-use inventory is a collection instrument; the University holds the only accurate answer and informal use is easy to under-report | `uiowa_rfq_18649_ai_use_inventory` | **UNKNOWN** |
| UNK-15 | evidence_collection | Any existing AI or acceptable-use policy text in force | Policy-to-workflow assessment compares written policy against observed workflow; it needs the actual policy text | `uiowa_rfq_18649_ai_policy_to_workflow` | **UNKNOWN** |
| UNK-16 | analysis | Delivery volume and timing data for an agreed measurement window | Delivery metrics require stated workload sizes and a defined environment; estimates must be labelled as estimates not measured | `uiowa_rfq_18649_delivery_metrics` | **UNKNOWN** |
| UNK-17 | analysis | Staffing counts and role mix available for improvement work | Resource and adoption estimates separate one-time from recurring effort and cannot be produced without a real capacity figure | `uiowa_rfq_18649_prioritization` | **UNKNOWN** |
| UNK-18 | analysis | The University's own weighting of what matters most among quality security reliability and speed | The prioritization weights are visible and adjustable on purpose; the defaults are placeholders not a recommendation | `uiowa_rfq_18649_prioritization` | **UNKNOWN** |
| UNK-19 | analysis | Constraints that rule options out such as budget freezes procurement rules or union agreements | A recommendation the University cannot act on is not a recommendation; the kit cannot infer these | `uiowa_rfq_18649_adoption_readiness` | **UNKNOWN** |
| UNK-20 | draft_review | Named draft reviewers and the review window | Documentation usability is measured from a real reviewer performing a real task; a synthetic reviewer proves only that the method runs | `uiowa_rfq_18649_doc_usability` | **UNKNOWN** |
| UNK-21 | draft_review | University corrections and disagreements on the draft | Unresolved disagreements are preserved rather than edited away; that requires the University to state them | `uiowa_rfq_18649_qa_kit` | **UNKNOWN** |
| UNK-22 | final_delivery | Required final-report format accessibility requirements and delivery channel | The report structure and visual-language checks target a format the University has not yet specified | `uiowa_rfq_18649_report_structure` | **UNKNOWN** |
| UNK-23 | final_delivery | Evidence disposition instruction for the RFQ's 30-day post-completion period | The closeout kit validates a disposition record and deliberately deletes nothing; the instruction is the University's to give | `uiowa_rfq_18649_closeout` | **UNKNOWN** |
| UNK-24 | readout | Whether the optional readout is wanted and who attends | The deck architecture exists but its audience and depth are undetermined | `uiowa_rfq_18649_readout_deck` | **UNKNOWN** |

---

## Limits of this handoff

- The status table is a snapshot. It is true for the timestamp printed at the top
  and for this machine's Python; re-run `verify_kit.py` rather than trusting it.
- WORKING means *the component's own check passed*. It does not mean the component
  is correct for the University's real evidence, and it is not a maturity rating.
- DRAFT on a document component means only that prose cannot be machine-checked. It
  is not a claim that the document is bad; it needs a human read.
- No component here certifies compliance, scores an individual, or ranks the
  University against peers, and this handoff does not add such a capability.
