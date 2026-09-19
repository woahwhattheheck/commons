# Framer LMS content and cost dependencies

Internal planning analysis, 2026-09-19. This document identifies inputs needed to scope and price delivery; it is not a quote, selected architecture, priced proposal, qualification determination or accepted workshare.

Sources: [September 1 RFP](https://investappalachia.org/wp-content/uploads/2026/08/1.-draft2_RFP_Invest_Appalachia_Framer_Training_LMS.docx.pdf), printed pp. 2–4, 6 and 8–10; [September 17 FAQ](https://investappalachia.org/wp-content/uploads/2026/09/final_FAQs_Framer_Training_LMS_RFP_with_TOC_2026-09-17.docx.pdf), especially Q4–Q7, Q9–Q29; retained [Attachment C inventory](https://github.com/woahwhattheheck/commons/blob/main/opportunities/invest_appalachia_framer_lms/recovered_20260916/attachment_c_budget_fields.md); and [existing specialist workshare](https://github.com/woahwhattheheck/commons/blob/main/opportunities/invest_appalachia_framer_lms/partner_workshare.json). FAQ SHA-256: `1e68dbc5e2c748dbe7ddd24f770554a836ea5d334dfcf15aa7352aed5e74b261`. See [SOURCE_REVIEW.md](SOURCE_REVIEW.md) for retained source identities and [FAQ_DELTA.md](FAQ_DELTA.md) for the 67-row mapping.

## Commercial facts that remain separate

| Item | Current source-bound status |
|---|---|
| Buyer contract cap | RFP pp. 2, 8: $60,000 all-in for the required initial scope, including implementation, SMEs, Year 1 software/hosting, required third-party tools and the three-month support period. |
| TJLabs specialist offer | Existing partner_workshare.json proposes $24,000 fixed, with status PROPOSED_NOT_ACCEPTED and budget integration unresolved. Its Git blob at review is `04b072fa272f0ed2c3902c9fbfbfb1931b902ae6`. |
| Offer binding | The existing workshare binds to qualification-generation SHA-256 `13018ee1b2fe14b3b8171acc734e0ea57a52006a5e96f095600e88bcbca63a02`. These new documents do not alter that generation or revalidate its dependent artifacts. |
| Prime proposal | The retained current packet is unpriced; zero placeholders and blank budget-template cells are not evidence of affordability. This analysis provides no replacement total. |
| Platform/license costs | No platform, reseller arrangement or actual provider quote has been selected or accepted here. |
| Future recurring costs | RFP p. 8 requires separate estimates after Year 1. They are outside the initial amount unless specifically included, but matter to long-term value. |

The $24,000 offer is a potential component of a prime's complete budget, not an addition automatically permitted above $60,000. Its existence neither establishes remaining spendable headroom nor demonstrates that all other scope fits. A qualified prime must reconcile overlapping work, every required cost and actual commercial terms before asserting budget compliance. FAQ source recovery does not cure absent experience, references, insurance, staffing or agreement.

## Content intake and preparation

FAQ Q19 provides the planning envelope: fewer than 200 source files and approximately 20–30 hours of recorded video, across a nine-module curriculum. Files are primarily MP4, PDF, Google Docs and Google Sheets, presently in Drive rather than another LMS. There are no existing SCORM, H5P or HTML interactive packages to migrate. These statements describe the buyer's current material; they are not fixed-price guarantees of uniform asset complexity or future volume.

The following preparation approach is a **design inference**, to be scoped with IA and the prime.

| Input/dependency | What must be established | Proposed preparation/acceptance evidence | Cost consequence to resolve |
|---|---|---|---|
| Source manifest | IA-approved source set, stable identity/version, module/role, owner, rights, current location and intended use. | Reconcile manifest to admitted files and course placements; retain missing/duplicate/revised-item exceptions. | Actual file count, revisions and review rounds drive handling effort. |
| Google Docs/templates | Which items remain editable copies, which become fixed documents, and who owns the reusable master. | Verify learner copy behavior and permissions with representative documents; maintain a link/export decision per asset. | Conversion, link maintenance and dependency on existing Workspace licensing. |
| Google Sheets | Separate learning templates from operational lists and private contact information. | Confirm role-appropriate fields and handling; migrate only the agreed data, not entire administrative workbooks by default. | Data cleaning, mapping and repeat-update work; avoid assuming a full CRM integration. |
| PDFs/presentations | Accessibility condition, permitted edits, source originals and approved alternative formats. | Review, remediate agreed issues and record exceptions requiring IA's decision. | Remediation effort is unknown until sampled and inventoried; no blanket compliance guarantee. |
| Recorded video | Source duration, file size, segments, ownership, audio quality and target delivery format. | Approve one representative basic editing treatment, then verify consistent opening/branding/formatting and playback. | FAQ Q24 adds real basic editing work; duration alone does not price editing, encoding or review effort. |
| Captions/transcripts and other accessibility work | What exists, its accuracy and applicable acceptance criteria. | Retain review and reasonable-remediation records; agree alternatives where an original asset cannot be readily adapted. | Vendor/service quotes or labor estimates needed; do not infer all material is already accessible (FAQ Q20). |
| Asset storage | Initial bytes and formats, future cohort recordings, retention, backup, egress and playback needs. | Confirm storage/streaming limits and usable export; distinguish original, processed and backup copies. | Storage, video delivery, processing and overage terms need actual quotes. Video hours are not storage gigabytes. |
| Content sign-off | Named IA reviewers, turnaround and final approved source version. | Track approved, superseded and pending assets; record effects on upload/review dates. | Late or materially revised content changes effort and schedule; do not invent an automatic surcharge. |

FAQ Q10 estimates predominantly technical implementation with limited organization/design support. It does not eliminate the RFP's adult-learning packaging responsibility or Q20/Q24 accessibility and basic-video work. IA creates the curriculum; the supplier still needs to make supplied content usable in the LMS. Creating a new curriculum or interactive package library is not inferred from the current source inventory.

## Cost dependency register

Rows below are planning dependencies, not priced line items. Use Attachment C's six categories and its separate recurring-cost schedule when actual prices are available. Avoid counting the same specialist labor twice under both implementation and SMEs.

| Dependency | Buyer/source basis | Required owner input before pricing | Attachment C allocation and boundary |
|---|---|---|---|
| Prime delivery and coordination | RFP pp. 3–4, 6; FAQ Q9–Q13. | Named staffing, actual availability, platform configuration effort, review cadence and subcontract scope. | Vendor Implementation Services; do not infer capacity from an empty calendar. |
| Existing $24,000 candidate workshare | Retained partner_workshare.json. | Prime/specialist agree included tasks, dependencies, acceptance and terms; distinguish offered scope from FAQ-driven scope needing reconciliation. | Allocate once to the appropriate category with a clear breakdown. Remains unaccepted and does not include an invented license allowance. |
| Instructional design/SMEs | RFP pp. 2–3; FAQ Q10, Q24. | Actual adult-learning expertise, content-review responsibility and estimated contribution. | SMEs and/or implementation as agreed; no claimed credentials absent evidence. |
| LMS subscription/license | RFP pp. 4, 8; FAQ Q11, Q14. | Established-platform fit review and dated provider quote; active/registered/concurrent user definition, role pricing and account retention. | Year 1 LMS/software category. Estimate later annual cost separately. No provider price or platform choice is supplied here. |
| Hosting, video and backup | RFP pp. 4, 8; FAQ Q19. | Architecture-specific service terms, measured bytes, retention and future cohort estimate. | License/software or required service category, clearly itemized so hosting is not omitted or double-counted. |
| Content intake/editing/remediation | FAQ Q19, Q20, Q24. | Approved inventory and representative review, basic video treatment, remediation assumptions and review rounds. | Implementation and/or specialist services; include required work inside the cap rather than treating it as automatically optional. |
| Live training | RFP p. 3; FAQ Q21–Q22. | IA's actual existing Zoom or comparable approved account/plan, permissions, selected connector and any required feature limits. | Required integration/tool costs inside the initial cap. Simple links/reminders do not remove Attachment A attendance/presentation obligations. |
| Applications/scoring/forms | FAQ Q25; Attachment A applications. | IA rubric, selected native/configured workflow, moderation/history behavior and any external-tool need. | Implementation plus required tool cost if selected. No required applicant-tracking vendor or fixed rubric exists in the FAQ. |
| Speaker MOU | FAQ Q29; Attachment A agreements. | Decide whether to use existing DocuSign or an approved alternative; verify users, envelopes, retention and existing contract coverage. | Third-party cost only if required by the selected approach; do not assume existing use means free additional capacity. |
| Payment-request notification | FAQ Q29. | IA recipient and minimal operational information; outside-LMS route for W-9/banking documents. | Configuration/notification cost as needed. No direct finance/payment integration or payment-execution budget is implied. |
| Other existing tools | FAQ Q21. | Confirm any real scope needing Salesforce, Workspace, Asana or Slack integration. | List only selected required dependencies. Direct Salesforce integration is not currently required; neither is every listed tool. |
| Permissions, affiliates and cohorts | FAQ Q14, Q16, Q18, Q23, Q26. | Account overlap, simultaneous cohorts, multi-facilitator assignment, protected standard questions and role-change retention rules. | Configuration and validation effort; compare platform licensing/features without inventing a bespoke security subsystem. |
| Accessibility and low-connectivity testing | RFP pp. 3–4; FAQ Q20. | Agreed criteria, representative devices/content and review responsibility. | Required implementation/verification work and any selected tool fees; no compliance certification or SLA invented. |
| Training/documentation/handover | RFP p. 4; FAQ Q13. | IA administrator availability and required operating tasks, export/backup ownership and documentation format. | Include in implementation; IA's ongoing administration is not permanent supplier staffing. |
| Required support | RFP pp. 4, 6, 8. | Coverage boundaries, defect triage, named support capacity and agreed response arrangements. | Three-Month Post-Implementation Support, February 1–April 30, 2027; no unsupported service-level promises. |
| Support after April 30 | Attachment C optional ongoing-support field; FAQ Q13. | Whether IA wants optional assistance and its scope. | Separate optional proposal and recurring estimate; do not silently add permanent administration. |
| Insurance | RFP p. 8; FAQ Q4. | Current policy evidence, exclusions and actual cost of any additional coverage requested during contracting. | Explain relevant cost assumptions; approximately $1 million is a preference, not a universal absolute floor. No insurance quote or qualification is asserted. |
| Future self-paced learning | FAQ Q17. | Compare present architecture choices with later conversion effort and cost. | Clearly distinguish optional preparation from launch requirements; no full self-directed launch charge is silently included or excluded. |
| Taxes/other necessary charges | RFP p. 8 all-known-cost requirement. | Actual quotes and responsible prime's determination of applicable fees/taxes. | Other or appropriate stated category; blank does not equal zero and no tax treatment is concluded here. |

## Budget completion procedure

This is a proposed preparation process, not executed commercial work:

1. Confirm the source version and update the complete requirement/exception mapping before platform comparison. Preserve all 54 required, 12 preferred and one mixed inventory item.
2. Obtain dated comparable configurations and actual costs for the selected established-platform options, including limitations, minimum terms, renewal, export and overage conditions. Select nothing solely from this document.
3. Scope content handling from representative buyer material and the manifest; identify assumptions and any unresolved remediation/video work.
4. Map every task and license/service to Attachment C once. Separate the $24,000 specialist proposal from the prime's other responsibilities and resolve any overlap; keep commercial status unchanged until agreement exists.
5. Include all required implementation, SMEs, Year 1 licenses/hosting/tools and three-month support in the proposed contract total. If the sourced total exceeds the cap, resolve scope/approach with the responsible parties before claiming compliance; do not hide required work in a later-year line.
6. Present after-Year-1 recurring estimates separately, plus any optional post-support services and future self-paced work. Distinguish an estimate from a guaranteed renewal price.
7. Have the responsible prime review assumptions, terms and certification. A newly priced proposal generation must reconcile source/evidence dependencies and bindings together; do not mutate one number in the old packet and call it current.

The FAQ permits collective two-platform experience across named key personnel and a specialist (Q5–Q7). This changes how evidence may be assembled, not whether evidence exists. The prime must still establish the actual team's roles, hands-on work, references, qualifications and anticipated involvement. U.S.-registered/W-9 eligibility and insurance readiness remain separate matters. No partner or buyer contact is performed by these documents.

See [DELIVERY_AND_ACCEPTANCE.md](DELIVERY_AND_ACCEPTANCE.md) for proposed review scenarios and source-grounded dates. Remaining unknowns are explicit decision inputs, not silent contingency allowances or proof of a viable total price.
