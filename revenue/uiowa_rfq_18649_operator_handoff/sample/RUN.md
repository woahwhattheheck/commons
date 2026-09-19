# Demonstrated sample run

Verbatim capture. Nothing below was retyped, summarised, or tidied.

## How this run was invoked

The lane's updated manifest was not yet committed when this run was taken, so the survey
used an assembled view: a scratch directory of symlinks to every live lane, with this
lane's working copy in place of its committed one. That is the only reason `--root` is a
temp path. From the committed location the plain default is correct and `sh sample_run.sh`
needs no arguments at all.

```bash
# assemble the view (only needed while this lane's own changes are uncommitted)
M=$(mktemp -d)
for d in /home/user/commons/revenue/uiowa_rfq_18649_*; do ln -s "$d" "$M/$(basename "$d")"; done
rm "$M/uiowa_rfq_18649_operator_handoff"; ln -s "$PWD" "$M/uiowa_rfq_18649_operator_handoff"

sh sample_run.sh "$M" /home/user/commons

# from the committed location, this is all you need:
sh sample_run.sh
```

`--repo-root /home/user/commons` is passed because one component runner
(`integrate_tabular.py --repo …`) resolves its inputs from the repository root, which is
not the parent of an assembled survey root.

## Captured output

```text
== 1/5 self-test: does the verifier itself still behave? ==
Ran 30 tests in 3.248s

OK

== 2/5 deterministic demo on the synthetic fixture (known ground truth) ==
   expect: alpha WORKING, bravo DRAFT, charlie DRAFT, delta MISSING, echo UNMAPPED
survey root : /home/user/fleet/staging/OP5-SLATE/revenue/uiowa_rfq_18649_operator_handoff/fixtures/minikit
generated   : 2026-09-19T14:10:08Z (python 3.11.15)
counts      : WORKING 1 | DRAFT 2 | MISSING 1 | UNMAPPED 1

phases      : 1 kickoff=partial | 2 analysis=blocked

!! STALE MANIFEST !! MANIFEST IS BEHIND THE BOARD: 1 lane(s) exist on disk that kit_manifest.json does not place in any phase (uiowa_rfq_18649_echo). Treat this guide as incomplete until they are placed.

PHASE        COMPONENT                                      STATUS    EVIDENCE
kickoff      uiowa_rfq_18649_alpha                          WORKING   2 tests passed
kickoff      uiowa_rfq_18649_bravo                          DRAFT     check executed and did not pass: 1 of 1 test file(s) fai
analysis     uiowa_rfq_18649_charlie                        DRAFT     document component: 2 document/data files and no executa
analysis     uiowa_rfq_18649_delta                          MISSING   no directory for this component exists under the survey 
unassigned   uiowa_rfq_18649_echo                           UNMAPPED  lane found on disk but not placed in any phase by the ma

== 3/5 real survey of the live lane tree at /tmp/claude-0/-home-user/6e551c41-37c5-5a0b-95f1-fb4584e151a7/scratchpad/m2oyBj ==
survey root : /tmp/claude-0/-home-user/6e551c41-37c5-5a0b-95f1-fb4584e151a7/scratchpad/m2oyBj
generated   : 2026-09-19T14:10:22Z (python 3.11.15)
counts      : WORKING 38 | DRAFT 8 | MISSING 4 | UNMAPPED 0

phases      : 1 kickoff=partial | 2 evidence_collection=partial | 3 analysis=partial | 4 draft_review=partial | 5 final_delivery=partial | 6 readout=partial

PHASE        COMPONENT                                      STATUS    EVIDENCE
kickoff      uiowa_rfq_18649_operator_handoff               WORKING   30 tests passed
kickoff      uiowa_rfq_18649_mobilization                   DRAFT     document component: 2 document/data files and no executa
kickoff      uiowa_rfq_18649_workshare                      WORKING   34 tests passed
kickoff      uiowa_rfq_18649_build_board                    DRAFT     document component: 3 document/data files and no executa
kickoff      uiowa_rfq_18649_capability_appendix            WORKING   39 tests passed
kickoff      uiowa_rfq_18649_scope_change                   WORKING   48 tests passed
kickoff      uiowa_rfq_18649_bid_pack                       WORKING   35 tests passed
evidence_col uiowa_rfq_18649_synthetic_collection           WORKING   5 tests passed
evidence_col uiowa_rfq_18649_intake_rehearsal               WORKING   34 tests passed
evidence_col uiowa_rfq_18649_document_extraction            DRAFT     check could not run offline: missing dependency 'pypdf' 
evidence_col uiowa_rfq_18649_test_data_readiness            DRAFT     check executed and did not pass: 1 of 2 test file(s) fai
evidence_col uiowa_rfq_18649_secure_guidance                WORKING   8 tests passed
evidence_col uiowa_rfq_18649_security_event_review          WORKING   9 tests passed
evidence_col uiowa_rfq_18649_observability                  WORKING   5 tests passed
evidence_col uiowa_rfq_18649_recovery_evidence              WORKING   57 tests passed
evidence_col uiowa_rfq_18649_incident_learning              DRAFT     document component: 2 document/data files and no executa
evidence_col uiowa_rfq_18649_release_provenance             WORKING   34 tests passed
evidence_col uiowa_rfq_18649_handoff                        WORKING   6 tests passed
evidence_col uiowa_rfq_18649_ai_use_inventory               WORKING   43 tests passed
evidence_col uiowa_rfq_18649_knowledge_readiness            MISSING   no directory for this component exists under the survey 
evidence_col uiowa_rfq_18649_contractor_transition          WORKING   34 tests passed
evidence_col uiowa_rfq_18649_question_cards                 WORKING   35 tests passed
analysis     uiowa_rfq_18649_rating_model                   WORKING   7 tests passed
analysis     uiowa_rfq_18649_prioritization                 WORKING   48 tests passed
analysis     uiowa_rfq_18649_delivery_metrics               WORKING   6 tests passed
analysis     uiowa_rfq_18649_outcome_measurement            WORKING   6 tests passed
analysis     uiowa_rfq_18649_workbench                      DRAFT     check executed and did not pass: 1 of 2 test file(s) fai
analysis     uiowa_rfq_18649_capacity_benchmark             WORKING   36 tests passed
analysis     uiowa_rfq_18649_ai_opportunity_portfolio       WORKING   39 tests passed
analysis     uiowa_rfq_18649_ai_policy_to_workflow          WORKING   36 tests passed
analysis     uiowa_rfq_18649_adoption_readiness             WORKING   49 tests passed
analysis     uiowa_rfq_18649_ai_integration                 WORKING   46 tests passed
analysis     uiowa_rfq_18649_ai_eval_kit                    WORKING   29 tests passed
analysis     uiowa_rfq_18649_economics_resource_adapters    WORKING   45 tests passed
analysis     uiowa_rfq_18649_roadmap_dependencies           WORKING   47 tests passed
draft_review uiowa_rfq_18649_traceability_rehearsal         WORKING   documented runner exited 0
draft_review uiowa_rfq_18649_doc_usability                  DRAFT     document component: 6 document/data files and no executa
draft_review uiowa_rfq_18649_qa_kit                         MISSING   no directory for this component exists under the survey 
draft_review uiowa_rfq_18649_interchange                    MISSING   no directory for this component exists under the survey 
draft_review uiowa_rfq_18649_traceability                   WORKING   44 tests passed
draft_review uiowa_rfq_18649_output_agreement               WORKING   41 tests passed
final_delive uiowa_rfq_18649_report_structure               WORKING   55 tests passed
final_delive uiowa_rfq_18649_report_visuals                 WORKING   90 tests passed
final_delive uiowa_rfq_18649_integration                    WORKING   documented runner exited 0
final_delive uiowa_rfq_18649_closeout                       WORKING   7 tests passed
final_delive uiowa_rfq_18649_acceptance_map                 DRAFT     check executed and did not pass: 1 of 1 test file(s) fai
final_delive uiowa_rfq_18649_milestone_packets              WORKING   55 tests passed
readout      uiowa_rfq_18649_readout_deck                   WORKING   56 tests passed
readout      uiowa_rfq_18649_qa_kit                         MISSING   no directory for this component exists under the survey 
readout      uiowa_rfq_18649_qa_refusal_contract            WORKING   57 tests passed

== 4/5 regenerate the operator guide from that survey ==
wrote OPERATOR_GUIDE.md (26729 bytes, 50 components, 24 UNKNOWN university inputs)

== 5/5 where to go next ==
   OPERATOR_GUIDE.md          the six phases, per-phase commands, per-component status
   sample/component_status.csv one row per component (open in a spreadsheet)
   sample/verification_log.md  the verbatim output of every command that was run
   university_inputs.csv       the University inputs still needed; all UNKNOWN
```

## What this run demonstrates

**Step 2 is the proof the classifier is not guessing.** The fixture has known answers:
`alpha` is built to pass, `bravo` is built to fail *and ships a README asserting
"production ready, all checks green"*, `charlie` is documents only, `delta` is named by
the manifest and was never built, `echo` exists on disk and is absent from the manifest.
The verifier returned WORKING / DRAFT / DRAFT / MISSING / UNMAPPED — including
contradicting bravo's README. This part is deterministic and should reproduce exactly.

**Step 3 is a snapshot, not a standing fact, and the numbers move fast.** Measured during
the build of this lane:

| time (UTC) | lanes on disk | WORKING | DRAFT | MISSING | UNMAPPED |
|---|---|---|---|---|---|
| 13:54 | 22 | 15 | 9 | 13 | 0 |
| 14:02 | 30 | 25 | 7 | 6 | 2 |
| 14:08 | 41 | 35 | 8 | 4 | 2 |
| 14:10 | 43 | 38 | 8 | 4 | 0 |

Eleven components went `MISSING → WORKING` in sixteen minutes as other authors landed
work, and individual suites grew underneath us (`recovery_evidence` 7 → 57 collected
tests, `prioritization` 5 → 48). Re-run it; do not quote it.

**The `UNMAPPED` column is the reason the staleness banner exists.** Between 14:02 and
14:08 nine new lanes appeared that the manifest did not place in any phase, and two more
arrived while those nine were being placed. Every one of them was caught and named rather
than silently omitted. Expect the banner to fire again — that is the design. When it does,
place the named lanes in `kit_manifest.json` and regenerate; do not suppress it.

## Locating the right artifact for each engagement step

| engagement step | open this |
|---|---|
| can I run this phase today? | `OPERATOR_GUIDE.md`, the "Can I run this phase today?" table |
| all six phases, in order, with commands | `OPERATOR_GUIDE.md` |
| one row per component, for a spreadsheet | `sample/component_status.csv` |
| the verbatim stdout of every command the survey ran | `sample/verification_log.md` |
| the full machine-readable survey, per-run exit codes, staleness and phase readiness | `sample/component_status.json` |
| what the University still has to give us | `university_inputs.csv` (all `UNKNOWN`) |
| which component serves which phase, and why | `kit_manifest.json` |
