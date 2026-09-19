# Framer LMS: evidence readiness after the September 17 FAQ

Internal decision worksheet, 2026-09-19. The newly recovered FAQ changes the way a proposed team may substantiate experience. It supplies no evidence that this team has that experience, insurance, staffing, or a committed partner. The retained proposal remains on hold.

Sources: [FAQ Q1-Q8, printed pp.3-4](https://investappalachia.org/wp-content/uploads/2026/09/final_FAQs_Framer_Training_LMS_RFP_with_TOC_2026-09-17.docx.pdf#page=3), [official RFP page](https://investappalachia.org/framer-rfp/), and the existing source-bound [proposal packet](../current_packet.json). See [SOURCE_REVIEW.md](SOURCE_REVIEW.md) for the exact FAQ digest and observation date. Existing packet statuses below are retained historical evidence states; this work did not repeat private credential, calendar, email or document searches.

## What changes in the qualification discussion

| Topic | Current source meaning | Evidence needed before a positive finding |
|---|---|---|
| Prime entity and tax form | Q1 requires a U.S.-registered prime able to provide a completed W-9; W-8BEN-E is not a substitute. | Actual proposed legal entity, registration basis and authorized private W-9 custody. A trading name or teammate's form does not establish the prime's fact. |
| At least two LMS platforms | Q6 permits collective experience across named key personnel, including a named specialist subcontractor. Neither one individual nor the applicant company must have delivered both. | Name each platform and the person who performed hands-on implementation/configuration; document their role, responsibilities, evidence, planned project contribution and subcontractor involvement. |
| Comparable role | Q5 allows experience as consultant, subcontractor or technical lead. | Attribute work honestly to the actual role. Obtain an appropriate reference able to discuss it; do not present subcontract work as a prime engagement. |
| Unselected specialist | Q7 permits describing an unfilled role's required qualifications and anticipated costs. | Keep that role visibly unfilled. A job description or budget allowance is not Q6's named-person implementation history. |
| Insurance limits | Q4 describes roughly $1 million as a preference rather than a universal mandatory floor; final requirements are resolved before contract execution. | Current coverage in each category, explanation of any lower level, ability to obtain additional coverage if required, and cost implications. The FAQ does not waive the underlying insurance documentation or let this worksheet certify adequacy. |
| Availability | Q8 retains the September 22, 5:00 PM ET deadline and anticipates October 13 kickoff. | Named staff capacity and commitments across the delivery period. A prior empty calendar interval establishes neither staffing nor availability. |

The broader RFP requirements for adult-learning packaging, relevant examples, references and documentation still apply. A clarification about eligible experience changes the evidence route; it does not mark any existing missing item as verified.

## Retained gate reconciliation

The existing `current_packet.json` at Git blob `8e24ca9ea6adb91213180c49972a07585740ed4c` records the following. These are reported as that generation's state, not a new private evidence audit.

| Existing field | Retained state | What a later reviewed generation must resolve |
|---|---|---|
| two_lms_platform_implementations | MISSING | Apply Q5/Q6 to a named delivery team, supported work history and references. Preserve platform and role attribution. |
| adult_learning_packaging | HOLD | Attributable adult-learning packaging work and the responsible team member; a demonstration is not completed client work. |
| start_capacity_2026_10_13 | HOLD | Delivery commitments and workload; supersede the earlier no-calendar-conflict observation with actual capacity evidence. |
| w9_available | HOLD | Q1-compliant prime entity and private evidence of form readiness. |
| general_liability_available | HOLD | Actual coverage, any lower-limit rationale under Q4, and unresolved contracting requirements. |
| professional_liability_available | HOLD | Actual E&O/professional-liability coverage and any cost/coverage gap. |
| cybersecurity_insurance_available | HOLD | Actual coverage and any cost/coverage gap. |
| two_relevant_project_examples | MISSING | Two shareable, relevant examples with ownership and role attribution. |
| two_prior_client_references | MISSING | Two appropriate references with current details and permission for intended use. |

No row is upgraded by this dossier. No private forms, policy certificates, client contact details or reference letters belong in this public repository.

## Team evidence register to prepare privately

Record one row per proposed person and qualifying platform: legal contracting relationship; named role; implementation dates; platform and project; actual hands-on responsibilities; evidence locator; reference basis; anticipated project involvement; availability; and reviewer conclusion. Keep source and observation dates separate. Cross-reference the same evidence rather than counting one project repeatedly under different role labels.

The reviewer should distinguish **supported**, **missing**, **conflicting**, and **not yet attributable** evidence. These are suggested working-paper labels, not buyer acceptance. No numerical score can substitute for a missing mandatory fact. An unnamed potential subcontractor remains an open staffing dependency even if an allowance has been budgeted.

## Regenerating the retained packet safely

The existing `carrier.py` and `workshare.py` bind their data to a retained source generation. The proposed $24,000 workshare in `partner_workshare.json` is also bound to that generation and remains `PROPOSED_NOT_ACCEPTED`; it is not a complete buyer budget. Its wording that the qualified prime must own the two-platform evidence predates Q6. Preserve that historical object and reconcile it explicitly when preparing a new generation.

A future implementation should update the source bundle, changed qualification meanings, actual evidence references, proposal assumptions and dependent digests together; then run the existing carrier and workshare verification against the entire new generation. It must keep missing evidence and unpriced categories blocked. This document neither changes those runtime artifacts nor claims their old metadata incorporates the new FAQ.

## Decision and next owner

Source recovery is complete. Qualification, named-team commitments, final platform selection, a full priced budget, proposal completeness and outbound authority remain unresolved. The next internal owner can use this worksheet to collect evidence and decide whether to prepare a later reviewed proposal generation. The source permits a potentially useful team structure; no actual team has been established by this work.

Existing Synegen/Raccoon Gang contact history and DNR remain in force. Do not treat a new public FAQ as an invitation to repeat outreach. No contact, submission, signature, scheduling, spending, award or revenue action is performed by this dossier.
