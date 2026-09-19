# Framer LMS delivery and acceptance plan

Internal design proposal, 2026-09-19. No platform has been selected, supplier qualification established, delivery capacity committed, or workshare accepted. The scenarios below are proposed acceptance procedures, not executed tests or additional buyer requirements.

Sources: [released September 1 RFP](https://investappalachia.org/wp-content/uploads/2026/08/1.-draft2_RFP_Invest_Appalachia_Framer_Training_LMS.docx.pdf), especially printed pp. 2–4 and 6–10; [September 17 FAQ](https://investappalachia.org/wp-content/uploads/2026/09/final_FAQs_Framer_Training_LMS_RFP_with_TOC_2026-09-17.docx.pdf), Q1–Q29; and the retained [67-row Attachment A inventory](../recovered_20260916/attachment_a_inventory.md). FAQ SHA-256: `1e68dbc5e2c748dbe7ddd24f770554a836ea5d334dfcf15aa7352aed5e74b261`. See [SOURCE_REVIEW.md](SOURCE_REVIEW.md) and [FAQ_DELTA.md](FAQ_DELTA.md) for source provenance and the requirement mapping. Page references below use printed pages.

The original RFP was read before transcribing this schedule. FAQ Q2 confirms that its filename's draft2 text does not make it a draft. The proposal deadline remains September 22, 2026, 5:00 p.m. Eastern Time; this plan does not authorize submission. Refresh the [buyer listing](https://investappalachia.org/framer-rfp/) before relying on the schedule.

## Delivery basis

Use an established, maintainable LMS configuration, selected by the responsible prime with Invest Appalachia (IA). FAQ Q11 rules out treating this as a fully bespoke LMS build. IA provides curriculum; the supplier organizes, configures, adapts and uploads it. FAQ Q10's approximately 10% content organization/design and 90% technical implementation estimate is scope guidance, not a staffing or price formula.

For planning, FAQ Q14 gives 20 participants per cohort, two cohorts per year with a possible third in 2027, three affiliates, six facilitators, 30 speakers and one system administrator. These are estimates, not a contracted capacity ceiling or a count of unique licensed users. Q15 describes an approximately four-month cohort. Confirm concurrency, alumni retention and license-counting rules before sizing. IA expects to operate the system after launch (Q13).

## Milestones and proposed review evidence

Dates are sourced; proposed evidence and decision records are design inferences for discussion. Do not merge adjacent dates or imply that the FAQ cancels an original review.

| Date | Source obligation or clarification | Proposed review evidence and dependency |
|---|---|---|
| October 13, 2026 | RFP p. 6 kickoff/work begins; FAQ Q9 anticipates IA content ready for upload. | Prime/IA confirm selected platform, role map, detailed scope, named owners and content inventory. Record missing material explicitly rather than treating a partial folder as complete. |
| October 28, 2026 | RFP p. 6 early build review. | Demonstrate branded navigation and representative role/cohort journeys using fictional users; record configuration decisions and unresolved requirements. |
| November 17, 2026 | FAQ Q9 anticipates modules 1–9, facilitator material and library uploaded/integrated. | Reconcile the content manifest with the actual course structure; identify broken links, inaccessible content and assets awaiting IA approval. |
| November 18, 2026 | RFP p. 6 mid-build showcase. | Demonstrate live-session setup, reminders, core workflows and exception handling against the configured system. November 17 preparation supports this separate review. |
| December 8, 2026 | RFP p. 6 pre-beta walkthrough. | Run the complete five-role pathway matrix and record defects, impact, owner and retest evidence. |
| December 15, 2026 | RFP p. 6 and FAQ Q9: participant, speaker and facilitator experiences ready for beta. | IA/prime review actual beta readiness, test access, representative content and support routes; readiness is not inferred from account creation alone. |
| January 15, 2027 | RFP p. 6 and FAQ Q9: final prioritized IA change requests. | Preserve the requested change set, distinguish defects from added scope and record disposition, owner and effect on timing/cost. |
| January 31, 2027 | RFP pp. 4, 6 and FAQ Q9: final curriculum, architecture/configuration and revisions complete. | Show resolved required-scope issues, IA-admin handover, usable exports, documentation and acceptance record. A proposed procedure is not a delivered acceptance. |
| February 1–April 30, 2027 | RFP pp. 4, 6: three months of warranty/troubleshooting/defect correction and reasonable technical support. | Maintain an agreed support log, reproduce and resolve covered defects, verify fixes, and transfer outstanding operational records at close. Do not invent response-time SLAs or permanent administration. |

FAQ Q9 describes primarily asynchronous work with regular check-ins; the existing Friday coordination meeting can move. Named staffing and availability still need evidence. A schedule in this document is not capacity proof.

## Proposed acceptance scenarios

All scenario IDs below are local design IDs. Use fictional accounts and approved sample material first, then authorized representative buyer data. Capture configuration version, role, cohort, source asset, steps, expected result, actual result, evidence location and reviewer. IA and the prime approve the actual acceptance terms. The baseline inventory remains 54 required, 12 preferred and one mixed item; FAQ clarifications do not silently reclassify it.

| ID | Scenario and expected observation | Source basis |
|---|---|---|
| DA01 | Configure two fictional affiliates and separate cohorts. Enroll a participant through the intended workflow and confirm correct branding, assigned cohort and appropriate reporting scope; the second affiliate's participant data stays outside that affiliate user's view. | Attachment A enrollment/branding/cohort/reporting/permissions; RFP p. 3; FAQ Q12, Q14. |
| DA02 | Assign two facilitators concurrently, including a backup. Both perform their authorized tasks; removing one assignment does not remove the other's access or corrupt cohort history. Exact scope is approved before configuration. | FAQ Q16; Attachment A facilitator dashboard/participant management/limited administration. |
| DA03 | A participant opens orientation, nine modules, assignments, templates, reminders and permitted recordings across agreed desktop/mobile devices. Identify slow-network failure and recovery behavior through an agreed test profile rather than inventing a bandwidth guarantee. | RFP pp. 3–4; Attachment A participant journeys; FAQ Q15, Q19. |
| DA04 | A former participant becomes a facilitator. Historical assignments/progress remain tied to the completed cohort for administration/reporting; the new role does not automatically promise personal access to all prior learner work. Verify the IA-approved access matrix. | FAQ Q18. |
| DA05 | A speaker opens the allowed roster, profile and session information but cannot view participant email addresses or private contact details through configured screens, ordinary exports or notifications. Use routine role-based acceptance, not penetration testing. | FAQ Q23; Attachment A limited roster/privacy. |
| DA06 | An affiliate adds a local assessment question while required standard questions remain intact. Only the administrator changes the standard set; response exports preserve the distinction and version for longitudinal comparison. | FAQ Q26; Attachment A permitted customization/assessment management. |
| DA07 | An administrator changes a trial numeric application rubric and records its version. Results are reproducible for that version; changes do not silently rewrite past decisions. The exact rubric and historical-recalculation behavior are design decisions for IA. | FAQ Q25; Attachment A application workflows. |
| DA08 | Demonstrate two agreed progression configurations, such as assignment submission plus assessment completion versus a sequential module rule. Record which is approved; exercise incomplete, late and corrected records without inventing final program rules. | FAQ Q27; Attachment A progression/completion. |
| DA09 | Produce an internal program completion record from the agreed rules; correct a record using the approved process. Do not attach an external accreditation/CEU claim or integration. | FAQ Q28; Attachment A completion record. |
| DA10 | A learner and speaker reach the correct live-session link and receive the intended reminders. Demonstrate the agreed breakout/presentation, attendance and recording process; distinguish native/manual steps from integrations. Simple access is not evidence that every required live-session function works. | RFP p. 3; FAQ Q21–Q22; Attachment A live-session/attendance/presentation controls. |
| DA11 | Reschedule a session and inspect recipient groups, timing, canceled reminders and the updated link. Repeat the administrative action and verify the agreed duplicate-handling behavior; neither duplicate-safe implementation nor delivery guarantees are claimed in advance. | Attachment A adjustable timing/communications/automation; FAQ Q22. |
| DA12 | A speaker completes the approved MOU workflow and requests payment. IA receives the internal notification; the LMS stores no sensitive tax or banking document and initiates no financial transfer. Confirm where those documents are handled outside the LMS. | FAQ Q29; Attachment A electronic MOU/payment request indicator. |
| DA13 | Reconcile every admitted asset with the manifest, including revised copies. Check module placement, title, owner, permissions and working links; distinguish editable template copies from the master. Repeating an import must follow an agreed replacement/duplication policy. | FAQ Q19; Attachment A resource/asset management; RFP pp. 2–3. |
| DA14 | Review representative PDFs, documents and video, remediate agreed accessibility issues, and retain the review/resolution record. Check navigation, captions/transcripts and accessible alternatives appropriate to each asset; define applicable criteria with IA before asserting compliance. | FAQ Q20; RFP pp. 3–4; Attachment A accessibility/support. |
| DA15 | Approve a representative edited video before batch work, then verify branding/opening treatment, intelligibility, captions as agreed, permission and playback. Track source duration separately from rendered file size and future recordings. | FAQ Q19, Q20, Q24. |
| DA16 | Export authorized IA course assets, reports and user/program data into agreed usable formats; open the outputs independently and reconcile counts/relationships. Demonstrate backup/recovery arrangements within the selected platform's actual capability. | RFP p. 4 ownership/portability; Attachment A export/storage. |
| DA17 | IA's designated administrator independently creates a cohort, assigns multiple facilitators, manages standard questions and schedules a session using delivered instructions. Record any steps still dependent on a supplier. | FAQ Q13, Q16, Q26; RFP p. 4 training/documentation. |
| DA18 | Review the options for future self-paced delivery, identifying present architectural constraints and later work/cost. Initial acceptance does not require launching the aspirational self-directed program. | FAQ Q17; RFP pp. 3–4. |

These scenarios exercise several requirements each and are not a replacement for all 67 Attachment A rows. The selected prime must maintain a row-by-row fit/exception record, including preferred features not in initial scope and the mixed feedback/completion item. A demonstration must distinguish configuration delivered, capability merely available, and additional licensed/custom work.

## Responsibilities and handover

| Owner | Proposed responsibility |
|---|---|
| IA | Source content and rights, final program rules/rubric, required questions, branding, named reviewers, operational decisions and final acceptance. |
| Qualified prime | Platform recommendation, full scope/budget, staffing and qualification evidence, delivery coordination, configured system, insurance/contract obligations, training and covered support. |
| TJLabs candidate specialist | The existing proposed implementation/acceptance workshare: traceability, bounded configuration/verification and defect evidence as agreed with the prime. No inferred qualification or accepted subcontract. |
| Platform/tool providers | Licensed service capabilities, usage terms, export/storage behavior and support under their actual contracts; no quoted capability or price is assumed here. |

The proposed handover bundle contains configuration and role maps, source-to-course asset inventory, acceptance/exception records, operational instructions, export/backup procedure, third-party dependencies, recurring-cost schedule and covered-support route. Sensitive participant material belongs in authorized delivery storage, not this repository. See [CONTENT_AND_COST_DEPENDENCIES.md](CONTENT_AND_COST_DEPENDENCIES.md) for unresolved inputs and pricing dependencies.
