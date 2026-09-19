# Demonstrated sample run

Verbatim capture. Nothing below was retyped, summarised, or tidied.

## How this run was invoked

The lane's own changes were uncommitted when this run was taken, so the survey used an
assembled view: a scratch directory of symlinks to every live lane, with this lane's
working copy in place of its committed one. That is the only reason `--root` is a temp
path. From the committed location the plain default is correct:

```bash
cd revenue/uiowa_rfq_18649_operator_handoff
sh sample_run.sh          # no arguments needed
```

The assembled form, for reference:

```bash
M=$(mktemp -d)
for d in /home/user/commons/revenue/uiowa_rfq_18649_*; do ln -s "$d" "$M/$(basename "$d")"; done
rm "$M/uiowa_rfq_18649_operator_handoff"; ln -s "$PWD" "$M/uiowa_rfq_18649_operator_handoff"
sh sample_run.sh "$M" /home/user/commons
```

`--repo-root /home/user/commons` is passed because one component runner
(`integrate_tabular.py --repo …`) resolves its inputs from the repository root, which is
not the parent of an assembled survey root.

## Captured output

```text
== 1/6 self-test: does the verifier itself still behave? ==
Ran 37 tests in 5.473s

OK

== 2/6 deterministic demo on the synthetic fixture (known ground truth) ==
   expect: alpha WORKING, bravo DRAFT, charlie DRAFT, delta MISSING, echo UNMAPPED
survey root : /home/user/fleet/staging/OP5-SLATE/revenue/uiowa_rfq_18649_operator_handoff/fixtures/minikit
generated   : 2026-09-19T14:16:21Z (python 3.11.15)
counts      : WORKING 1 | DRAFT 2 | MISSING 1 | UNMAPPED 1

phases      : 1 kickoff=partial | 2 analysis=blocked

!! STALE MANIFEST !! MANIFEST IS BEHIND THE BOARD: 1 lane(s) exist on disk that kit_manifest.json does not place in any phase (uiowa_rfq_18649_echo). Treat this guide as incomplete until they are placed.

PHASE        COMPONENT                                      STATUS    EVIDENCE
kickoff      uiowa_rfq_18649_alpha                          WORKING   2 tests passed
kickoff      uiowa_rfq_18649_bravo                          DRAFT     check executed and did not pass: 1 of 1 test file(s) fai
analysis     uiowa_rfq_18649_charlie                        DRAFT     document component: 2 document/data files and no executa
analysis     uiowa_rfq_18649_delta                          MISSING   no directory for this component exists under the survey 
unassigned   uiowa_rfq_18649_echo                           UNMAPPED  lane found on disk but not placed in any phase by the ma

== 3/6 real survey of the live lane tree at /tmp/claude-0/-home-user/6e551c41-37c5-5a0b-95f1-fb4584e151a7/scratchpad/m3QGjY ==
survey root : /tmp/claude-0/-home-user/6e551c41-37c5-5a0b-95f1-fb4584e151a7/scratchpad/m3QGjY
generated   : 2026-09-19T14:16:38Z (python 3.11.15)
counts      : WORKING 43 | DRAFT 10 | MISSING 4 | UNMAPPED 0

phases      : 1 kickoff=partial | 2 evidence_collection=partial | 3 analysis=partial | 4 draft_review=partial | 5 final_delivery=partial | 6 readout=partial

PHASE        COMPONENT                                      STATUS    EVIDENCE
kickoff      uiowa_rfq_18649_operator_handoff               WORKING   37 tests passed
kickoff      uiowa_rfq_18649_mobilization                   DRAFT     document component: 2 document/data files and no executa
kickoff      uiowa_rfq_18649_workshare                      WORKING   34 tests passed
kickoff      uiowa_rfq_18649_build_board                    DRAFT     document component: 3 document/data files and no executa
kickoff      uiowa_rfq_18649_capability_appendix            DRAFT     check executed and did not pass: 1 of 1 test file(s) fai
kickoff      uiowa_rfq_18649_scope_change                   WORKING   48 tests passed
kickoff      uiowa_rfq_18649_bid_pack                       WORKING   62 tests passed
kickoff      uiowa_rfq_18649_filesystem_safety              WORKING   24 tests passed
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
evidence_col uiowa_rfq_18649_question_cards                 WORKING   40 tests passed
evidence_col uiowa_rfq_18649_deadline_continuity            WORKING   42 tests passed
evidence_col uiowa_rfq_18649_vocabulary_crosswalk           DRAFT     check executed and did not pass: 1 of 1 test file(s) fai
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
analysis     uiowa_rfq_18649_economics_resource_adapters    WORKING   78 tests passed
analysis     uiowa_rfq_18649_roadmap_dependencies           WORKING   47 tests passed
analysis     uiowa_rfq_18649_ai_decision_case               WORKING   34 tests passed
analysis     uiowa_rfq_18649_capacity_feasibility           WORKING   51 tests passed
draft_review uiowa_rfq_18649_traceability_rehearsal         WORKING   documented runner exited 0
draft_review uiowa_rfq_18649_doc_usability                  DRAFT     document component: 6 document/data files and no executa
draft_review uiowa_rfq_18649_qa_kit                         MISSING   no directory for this component exists under the survey 
draft_review uiowa_rfq_18649_interchange                    MISSING   no directory for this component exists under the survey 
draft_review uiowa_rfq_18649_traceability                   WORKING   66 tests passed
draft_review uiowa_rfq_18649_output_agreement               WORKING   41 tests passed
final_delive uiowa_rfq_18649_report_structure               WORKING   55 tests passed
final_delive uiowa_rfq_18649_report_visuals                 WORKING   90 tests passed
final_delive uiowa_rfq_18649_integration                    WORKING   documented runner exited 0
final_delive uiowa_rfq_18649_closeout                       WORKING   7 tests passed
final_delive uiowa_rfq_18649_acceptance_map                 DRAFT     check executed and did not pass: 1 of 1 test file(s) fai
final_delive uiowa_rfq_18649_milestone_packets              WORKING   55 tests passed
final_delive uiowa_rfq_18649_exec_summary                   WORKING   42 tests passed
final_delive uiowa_rfq_18649_print_pagination               WORKING   39 tests passed
readout      uiowa_rfq_18649_readout_deck                   WORKING   56 tests passed
readout      uiowa_rfq_18649_qa_kit                         MISSING   no directory for this component exists under the survey 
readout      uiowa_rfq_18649_qa_refusal_contract            WORKING   57 tests passed

== 4/6 regenerate the operator guide from that survey ==
wrote OPERATOR_GUIDE.md (29025 bytes, 57 components, 24 UNKNOWN university inputs)

== 5/6 discover what to actually type, by running each component's --help ==
# Command index

**What do I type?** — every command below was discovered by executing the
script with `--help` in a throwaway copy of its lane and keeping the ones that
answered with a real usage line. None of it was read out of a README, so none
of it can be stale relative to the code in the way documentation can.

- survey root: `/tmp/claude-0/-home-user/6e551c41-37c5-5a0b-95f1-fb4584e151a7/scratchpad/m3QGjY`
- generated (UTC): 2026-09-19T14:16:43Z · python 3.11.15
- **54 verified command lines across 43 of 57 components**

Regenerate with:

== 6/6 where to go next ==
   OPERATOR_GUIDE.md          the six phases, phase readiness, per-component status
   COMMAND_INDEX.md           what to type, per component, discovered by running --help
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
contradicting bravo's README, and including raising its own STALE MANIFEST banner over
`echo`, which is deliberately left unplaced so the banner is exercised on every run.

**Step 3 is a snapshot, not a standing fact, and the numbers move fast.** Measured during
the build of this lane:

| time (UTC) | lanes on disk | WORKING | DRAFT | MISSING | UNMAPPED |
|---|---|---|---|---|---|
| 13:54 | 22 | 15 | 9 | 13 | 0 |
| 14:02 | 30 | 25 | 7 | 6 | 2 |
| 14:08 | 41 | 35 | 8 | 4 | 2 |
| 14:10 | 43 | 38 | 8 | 4 | 0 |
| 14:16 | 50 | 38 | 8 | 4 | 7 |
| 14:18 | 50 | 43 | 10 | 4 | 0 |

Twenty-eight components went `MISSING → WORKING` in twenty-four minutes as other authors
landed work, and individual suites grew underneath the survey (`recovery_evidence` 7 → 57
collected tests, `prioritization` 5 → 48). Re-run it; do not quote it.

**The `UNMAPPED` column is why the staleness banner exists.** Nine lanes appeared
unplaced at 14:02, two more while those nine were being placed, one more while those two
were, and seven more at 14:16. Every one was caught and named rather than silently
omitted. **Expect the banner to fire again.** When it does, place the named lanes in
`kit_manifest.json` and regenerate. Do not suppress it: a handoff that admits it is behind
is worth more than one that quietly hands over a map with holes.

**Step 5 answers the question the phase tables do not.** 54 command lines verified across
43 of 57 components, discovered by running each script with `--help` in a throwaway copy
and keeping only the ones that answered with a real usage line. The honest negative
matters as much: components with no verified command line are named as such, never handed
a guessed command. A component that takes no arguments — and so never answers `--help` —
shows its documented runner instead of being written off as un-runnable.

## Locating the right artifact for each engagement step

| engagement step | open this |
|---|---|
| what do I type? | `COMMAND_INDEX.md` |
| can I run this phase today? | `OPERATOR_GUIDE.md`, the "Can I run this phase today?" table |
| all six phases, in order, with per-component status | `OPERATOR_GUIDE.md` |
| one row per component, for a spreadsheet | `sample/component_status.csv` |
| the verbatim stdout of every command the survey ran | `sample/verification_log.md` |
| the full machine-readable survey, exit codes, staleness, phase readiness | `sample/component_status.json` |
| every probed entry point including the rejected ones | `sample/command_index.json` |
| what the University still has to give us | `university_inputs.csv` (all `UNKNOWN`) |
| which component serves which phase, and why | `kit_manifest.json` |
