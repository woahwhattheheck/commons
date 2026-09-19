# Demonstrated sample run

Verbatim capture. Nothing below was retyped, summarised, or tidied.

## How this run was invoked

This lane was not yet committed when the run was taken, so the survey used an
assembled view: a scratch directory of symlinks to every live lane **plus this lane
as it will exist once landed**. That is the only reason `--root` is a temp path.
After landing, the plain default is correct and `sh sample_run.sh` needs no arguments.

```bash
# assemble the view (only needed because this lane was still uncommitted)
M=$(mktemp -d)
for d in /home/user/commons/revenue/uiowa_rfq_18649_*; do ln -s "$d" "$M/$(basename "$d")"; done
ln -s "$PWD" "$M/uiowa_rfq_18649_operator_handoff"

sh sample_run.sh "$M" /home/user/commons

# after landing, from revenue/uiowa_rfq_18649_operator_handoff, this is all you need:
sh sample_run.sh
```

`--repo-root /home/user/commons` is passed because one component runner
(`integrate_tabular.py --repo …`) resolves its inputs from the repository root, which
is not the parent of an assembled survey root.

## Captured output

```text
== 1/5 self-test: does the verifier itself still behave? ==
Ran 24 tests in 2.760s

OK

== 2/5 deterministic demo on the synthetic fixture (known ground truth) ==
   expect: alpha WORKING, bravo DRAFT, charlie DRAFT, delta MISSING, echo UNMAPPED
survey root : /home/user/fleet/staging/OP5-SLATE/revenue/uiowa_rfq_18649_operator_handoff/fixtures/minikit
generated   : 2026-09-19T14:01:57Z (python 3.11.15)
counts      : WORKING 1 | DRAFT 2 | MISSING 1 | UNMAPPED 1

PHASE        COMPONENT                                      STATUS    EVIDENCE
kickoff      uiowa_rfq_18649_alpha                          WORKING   2 tests passed
kickoff      uiowa_rfq_18649_bravo                          DRAFT     check executed and did not pass: 1 of 1 test file(s) fai
analysis     uiowa_rfq_18649_charlie                        DRAFT     document component: 2 document/data files and no executa
analysis     uiowa_rfq_18649_delta                          MISSING   no directory for this component exists under the survey 
unassigned   uiowa_rfq_18649_echo                           UNMAPPED  lane found on disk but not placed in any phase by the ma

== 3/5 real survey of the live lane tree at /tmp/claude-0/-home-user/6e551c41-37c5-5a0b-95f1-fb4584e151a7/scratchpad/mergedrgzE ==
survey root : /tmp/claude-0/-home-user/6e551c41-37c5-5a0b-95f1-fb4584e151a7/scratchpad/mergedrgzE
generated   : 2026-09-19T14:02:06Z (python 3.11.15)
counts      : WORKING 24 | DRAFT 7 | MISSING 7 | UNMAPPED 0

PHASE        COMPONENT                                      STATUS    EVIDENCE
kickoff      uiowa_rfq_18649_operator_handoff               WORKING   24 tests passed
kickoff      uiowa_rfq_18649_mobilization                   DRAFT     document component: 2 document/data files and no executa
kickoff      uiowa_rfq_18649_workshare                      WORKING   34 tests passed
kickoff      uiowa_rfq_18649_build_board                    DRAFT     document component: 3 document/data files and no executa
evidence_col uiowa_rfq_18649_synthetic_collection           WORKING   5 tests passed
evidence_col uiowa_rfq_18649_intake_rehearsal               WORKING   30 tests passed
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
analysis     uiowa_rfq_18649_rating_model                   WORKING   7 tests passed
analysis     uiowa_rfq_18649_prioritization                 WORKING   48 tests passed
analysis     uiowa_rfq_18649_delivery_metrics               WORKING   6 tests passed
analysis     uiowa_rfq_18649_outcome_measurement            WORKING   6 tests passed
analysis     uiowa_rfq_18649_workbench                      DRAFT     check executed and did not pass: 1 of 2 test file(s) fai
analysis     uiowa_rfq_18649_capacity_benchmark             MISSING   no directory for this component exists under the survey 
analysis     uiowa_rfq_18649_ai_opportunity_portfolio       WORKING   39 tests passed
analysis     uiowa_rfq_18649_ai_policy_to_workflow          MISSING   no directory for this component exists under the survey 
analysis     uiowa_rfq_18649_adoption_readiness             WORKING   49 tests passed
analysis     uiowa_rfq_18649_ai_integration                 MISSING   no directory for this component exists under the survey 
analysis     uiowa_rfq_18649_ai_eval_kit                    WORKING   29 tests passed
draft_review uiowa_rfq_18649_traceability_rehearsal         WORKING   documented runner exited 0
draft_review uiowa_rfq_18649_doc_usability                  DRAFT     document component: 6 document/data files and no executa
draft_review uiowa_rfq_18649_qa_kit                         MISSING   no directory for this component exists under the survey 
draft_review uiowa_rfq_18649_interchange                    MISSING   no directory for this component exists under the survey 
final_delive uiowa_rfq_18649_report_structure               WORKING   55 tests passed
final_delive uiowa_rfq_18649_report_visuals                 WORKING   60 tests passed
final_delive uiowa_rfq_18649_integration                    WORKING   documented runner exited 0
final_delive uiowa_rfq_18649_closeout                       WORKING   7 tests passed
readout      uiowa_rfq_18649_readout_deck                   WORKING   56 tests passed
readout      uiowa_rfq_18649_qa_kit                         MISSING   no directory for this component exists under the survey 

== 4/5 regenerate the operator guide from that survey ==
wrote OPERATOR_GUIDE.md (22551 bytes, 38 components, 24 UNKNOWN university inputs)

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

> The committed `OPERATOR_GUIDE.md` was regenerated from a *later* survey than the one
> captured above (WORKING 25 · DRAFT 7 · MISSING 6 · UNMAPPED 2, taken immediately before
> commit). Both are real; they differ because four minutes passed and other authors landed
> work. That is the point of the next paragraph.

**Step 3 is a snapshot, not a standing fact.** Its counts moved three times during the
build of this lane as other authors landed work (`recovery_evidence` went from 7 to 57
collected tests, `prioritization` from 5 to 48, and six components went MISSING →
WORKING). Re-run it; do not quote it.

## Locating the right artifact for each engagement step

| engagement step | open this |
|---|---|
| all six phases, in order, with commands | `OPERATOR_GUIDE.md` |
| one row per component, for a spreadsheet | `sample/component_status.csv` |
| the verbatim stdout of every command the survey ran | `sample/verification_log.md` |
| the full machine-readable survey including per-run exit codes | `sample/component_status.json` |
| what the University still has to give us | `university_inputs.csv` (all `UNKNOWN`) |
| which component serves which phase, and why | `kit_manifest.json` |
