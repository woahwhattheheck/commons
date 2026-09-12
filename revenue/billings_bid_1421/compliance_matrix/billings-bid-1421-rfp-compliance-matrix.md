# City of Billings Bid 1421 - Truthful RFP Compliance Matrix

Working product name: AquaTrace. The City RFP itself does not use that name.

Receipt slug: `billings-bid-1421-rfp-compliance-matrix-20260831-01`  
Claim retained: [Slack claim at 2026-08-30 23:15:49 EDT](https://tokenjunkielabs.slack.com/archives/C0BTTA66TK3/p1788146149800119?thread_ts=1788145616.353679&cid=C0BTTA66TK3)  
Prepared: 2026-08-30 EDT  
Decision: **HOLD / NO SUBMISSION**

## Evidence boundary

Requirements were transcribed from the [official City bid page](https://www.billingsmt.gov/bids.aspx?bidID=1421) and the [official City RFP DOCX](https://www.billingsmt.gov/DocumentCenter/View/56340/2026-LIMS-RFP). The DOCX was downloaded directly, opened read-only, rendered by Microsoft Word to 17 pages, and checked against the document-order table extraction. No third-party RFP summary was used.

Current positive evidence is deliberately narrow:

- `EVIDENCE_NOW`: Attachment E Intent to Respond has a provider-read-back `SENT` receipt, Gmail message `1a055c181593fa52`, thread `1a0558834f38f75d`; [Slack receipt](https://tokenjunkielabs.slack.com/archives/C0BTTA66TK3/p1788145165307049). This is not a proposal, price, award, compatibility claim, or proof of any product capability.
- `PROTOTYPE_EVIDENCE`: an internal operations-package draft exists with implementation discovery, training, support/escalation, DR-test, and RBAC-boundary outlines; [terminal receipt and SHA-256](https://tokenjunkielabs.slack.com/archives/C0BTA20SU95/p1788146472325639?thread_ts=1788146230.392879&cid=C0BTA20SU95). It is planning evidence only, not proof of a deployed system, staffing capacity, security compliance, or contractual performance.
- No validated product build, production deployment, reference, customer, certification, insurance, instrument-compatibility result, independent security assessment, or approved price evidence was available to this lane at the cutoff.

Status meanings:

- `EVIDENCE_NOW`: a current, specific artifact supports the requirement.
- `PROTOTYPE_EVIDENCE`: a bounded internal draft/test artifact exists, but does not establish production or contractual compliance.
- `PLANNED_AFTER_AWARD`: the RFP expressly places performance after selection/award and a pre-award claim is not being made.
- `CANNOT_CLAIM`: evidence is absent, incomplete, unsigned, buyer-dependent, or not authorized for use.

## Source defects and conservative treatment

- The table of contents contains broken bookmarks and numbering that does not match the body. This matrix cites the body heading plus rendered page.
- Attachment E says both “at least five days prior” (page 4) and “within five days” (page 15). The stricter reading is used; the sent receipt is the only compliance evidence asserted.
- Attachment F omits methods for Paint Filter Test and Volatile Acids and prints an incomplete method string for Metals (AA), Total. Those items require City/lab clarification before any method-support claim.
- The RFP gives a proposal deadline and contract term, but no standalone implementation schedule. “Implementation Timeline” is an evaluation criterion; the proposer must supply the plan.

## A. Administrative, submission, legal, and security requirements

| ID | RFP locator | Requirement | Status | Exact evidence/artifact needed | Owner | Blocking note |
|---|---|---|---|---|---|---|
| A01 | Sec. 1, p. 3 | Proposal received by 5:00 PM MST on 4 September 2026. | CANNOT_CLAIM | Final submission receipt showing timestamp, destination, and exact attachment hashes. | Proposal Operations + authorized sender | No proposal submission is authorized or performed by this lane. |
| A02 | Sec. 1, p. 3 | Respond in detail to every RFP element. | CANNOT_CLAIM | Final crosswalk with every row cleared and reviewer sign-off. | Proposal Operations | This matrix exposes unresolved rows; it does not clear them. |
| A03 | Sec. 1 and body Sec. 6, pp. 3, 6 | Email the proposal to the contact listed in Section 1. | CANNOT_CLAIM | Authorized send plan plus provider receipt after owner-approved submission. | Authorized sender | External contact/submission is outside this lane. |
| A04 | Sec. 1 and body Sec. 6, pp. 3, 6 | Email pricing separately with subject “LIMS RFP Confidential Pricing.” | CANNOT_CLAIM | Approved Attachment B price matrix, separate-message package, and provider receipt. | Finance + authorized signer/sender | No pricing was supplied, calculated, or sent. |
| A05 | Sec. 2 and Att. E, pp. 4, 15 | Complete, sign, and email Intent to Respond within the required advance window. | EVIDENCE_NOW | Provider receipt `1a055c181593fa52` with read-back `SENT`; preserve completed form and message hash in the bid file. | Proposal Operations + authorized signer | Evidence supports intent only, not proposal compliance. |
| A06 | Sec. 4 and Att. D, pp. 5, 14 | If questions are submitted, use Master Q&A, include identity/contact, clear question, and RFP reference, before the five-business-day cutoff. | CANNOT_CLAIM | Owner-approved Attachment D and email receipt, or written decision that no question is required. | Proposal Operations + Legal/Product reviewers | No City question/contact is authorized in this lane. |
| A07 | Body Sec. 6, p. 6 | Proposal maximum is 20 pages including signed Conditions and Non-Collusion; pricing is excluded. | CANNOT_CLAIM | Final paginated PDF plus page-count QA showing 20 pages or fewer. | Proposal Operations | No final response package exists. |
| A08 | Body Sec. 6, p. 6 | A one-page cover letter may be included in addition to the 20-page proposal. | CANNOT_CLAIM | Final one-page cover letter and pagination audit. | Proposal Operations + authorized signer | Optional artifact not prepared in this lane. |
| A09 | Body Sec. 6, p. 6 | Submission acknowledges all information is accurate and complete. | CANNOT_CLAIM | Signed representation plus evidence review checklist and claim-owner approvals. | Authorized signer + Legal + Proposal Operations | Unsupported rows prevent this representation. |
| A10 | Body Sec. 7, p. 7 | Include all forms provided in the RFP; omission may cause rejection. | CANNOT_CLAIM | Final package manifest showing Attachments A and C in response and Attachment B under separate cover; Att. D/E handled as applicable. | Proposal Operations | Forms are not compiled or signed for proposal submission. |
| A11 | Body Sec. 7, p. 7 | Honor prices and proposal terms for at least 90 days after the due date. | CANNOT_CLAIM | Finance-approved price validity statement and authorized-signature approval. | Finance + Legal + authorized signer | No pricing or term approval exists. |
| A12 | Body Sec. 7, p. 7 | Certify independent proposal and no collusion. | CANNOT_CLAIM | Fully executed Attachment C by an authorized representative. | Legal + authorized officer | No signed certification is available to this lane. |
| A13 | Body Sec. 7 and Att. A, pp. 7-8, 11 | State ability to meet workers compensation, CGL, auto, notice, additional-insured, and waiver requirements. | CANNOT_CLAIM | Broker letter or policy schedule mapped to every RFP limit/endorsement, reviewed by Legal/Risk. | Risk/Insurance + Legal | Do not claim insurance readiness without broker/policy evidence. |
| A14 | Body Sec. 7 and Att. A, pp. 8, 11 | Successful proposer purchases City business license and completes vendor forms before payment/contract execution. | PLANNED_AFTER_AWARD | Post-award license/vendor onboarding checklist and assigned owner. | Corporate Operations + Finance | Explicitly not required with proposal; willingness still needs authorized approval. |
| A15 | Body Sec. 7, p. 8 | Provide reasonable security proof aligned to City categorization, latest NIST SP 800-53, federal and Montana requirements. | CANNOT_CLAIM | Independent audit/scans, City-approved FIPS 199 categorization, control mapping, remediation record, and assessor report. | Security Lead + independent assessor | Internal planning is not reasonable proof and no assessment was evidenced. |
| A16 | Body Sec. 7, p. 8 | Deliver annual assurance statements as NIST SAR or FedRAMP SAR. | CANNOT_CLAIM | Current qualifying SAR/FedRAMP SAR and annual delivery commitment approved by Security/Legal. | Security Lead + independent assessor | No qualifying report or certification is evidenced. |
| A17 | Body Sec. 7, pp. 8-9 | Do not probe, scan, intrude, spoof City/State identities, or forge billingsmt.gov/mt.gov email. | PROTOTYPE_EVIDENCE | Internal nonproduction security boundary and denial-test plan; before claim, add approved policy, product controls, test results, and staff attestation. | Security Lead + Legal | Draft boundary exists; operating controls and attestations are unverified. |
| A18 | Body Sec. 7, p. 9 | Acknowledge proposal materials may become public records after award. | CANNOT_CLAIM | Legal public-records review and redaction/secrets checklist for final package. | Legal + Proposal Operations | No final package has been reviewed for disclosure. |
| A19 | Sec. 3, p. 4 | Accept a five-year term with options for up to five one-year renewals. | CANNOT_CLAIM | Legal/commercial approval of term and renewal language. | Legal + Finance + authorized signer | No commercial approval is evidenced. |

## B. Section 3 scope and functional requirements

| ID | RFP locator | Requirement | Status | Exact evidence/artifact needed | Owner | Blocking note |
|---|---|---|---|---|---|---|
| S3-01 | Sec. 3, p. 4 | Provide a LIMS meeting all RFP requirements. | CANNOT_CLAIM | Completed matrix, versioned product evidence index, and signed technical review. | Product Lead + Proposal Operations | Aggregate claim cannot clear while any mandatory row lacks evidence. |
| S3-02 | Sec. 3, p. 4 | Configure and implement the system. | PROTOTYPE_EVIDENCE | Existing discovery/configuration outline; add implementation schedule, migration plan, roles, acceptance plan, and resourcing. | Implementation Lead | Draft plan exists; no delivery history or committed schedule is evidenced. |
| S3-03 | Sec. 3, p. 4 | Train laboratory personnel. | PROTOTYPE_EVIDENCE | Existing nine-module outline; add audience map, materials, trainer qualifications, attendance, assessments, and completion records. | Training Lead + Implementation Lead | Outline is not delivered training evidence. |
| S3-04 | Sec. 3, p. 4 | Provide ongoing technical support and updates. | PROTOTYPE_EVIDENCE | Existing escalation runbook; add staffed support model, hours, SLAs, release policy, sample tickets, and service metrics. | Support Lead + Product Operations | Capacity and contractual service levels are not evidenced. |
| S3-05 | Sec. 3, p. 4 | Fully web-based UI plus field app for collection, field entry, electronic chain of custody, and offline operation. | CANNOT_CLAIM | Runnable build; offline-sync protocol; synthetic end-to-end tests including reconnect, conflicts, duplicates, custody receipts, and role denial. | Product Engineering + QA | No runnable build or verified tests are available to this lane. |
| S3-06 | Sec. 3, p. 4 | Laboratory management, scheduling, and forecasting. | CANNOT_CLAIM | Feature build, data model, demo script, and deterministic scheduling/forecast test results. | Product Engineering + QA | No feature evidence located. |
| S3-07 | Sec. 3, p. 4 | Intuitive, user-friendly interface with minimal training requirements. | CANNOT_CLAIM | Usability protocol, representative lab-user sample, task success/time/error results, and findings. | Product Design/Research + QA | “Intuitive” cannot be asserted from a specification. |
| S3-08 | Sec. 3, p. 4 | Complete sample lifecycle traceability and chain of custody, including custody and disposition events. | CANNOT_CLAIM | Immutable event model, sample/custody fixture set, audit export, and end-to-end trace/reconciliation results. | Product Engineering + QA | No executed traceability corpus is evidenced. |
| S3-09 | Sec. 3, p. 4 | Track analyst demonstration of capability, training, and certification status by method. | CANNOT_CLAIM | Analyst-method authorization model, expiry/history controls, role tests, and synthetic records. | Product Engineering + QA + Lab SME | No implemented/evaluated module evidence located. |
| S3-10 | Sec. 3, p. 4 | Centralized secure storage with redundancy and disaster recovery. | PROTOTYPE_EVIDENCE | Existing DR test-evidence outline; add architecture, encryption/key controls, backups, restore execution, reconciled RTO/RPO results, and independent review. | Security/Platform Lead | Plan exists; operating service and successful restore are not evidenced. |
| S3-11 | Sec. 3, p. 4 | Role-based access control preserving integrity and accountability. | PROTOTYPE_EVIDENCE | Existing RBAC boundary/test outline; add role matrix, implementation, denial tests, privileged-access logs, and approval. | Security Lead + Product Engineering | Design/test plan is not implemented-control evidence. |
| S3-12 | Sec. 3, p. 4 | Real-time audit trails and system logs for data changes and activity history. | CANNOT_CLAIM | Append-only event schema, actor/time/reason fields, tamper controls, export, and executed mutation/retry tests. | Product Engineering + Security + QA | No build or test record is evidenced. |
| S3-13 | Sec. 3 and Att. F, pp. 4, 17 | Integrate laboratory instruments for automated acquisition and processing. | CANNOT_CLAIM | Exact device/model/protocol matrix, vendor interface proof, adapter implementation, synthetic fixtures, and witnessed tests on City-equivalent devices. | Integration Engineering + QA | Attachment F lacks exact models/protocols for several devices; compatibility must not be inferred. |
| S3-14 | Sec. 3, p. 4 | Tools for documenting and charting QC/QA processes. | CANNOT_CLAIM | QC rule/config model, charts, exception workflow, retest/release controls, and deterministic test evidence. | Product Engineering + Lab QA SME | No feature evidence located. |
| S3-15 | Sec. 3, p. 4 | Upload and store certificates of analysis for chemical inventory. | CANNOT_CLAIM | COA object model, upload/virus-scan/retention/access controls, retrieval audit, and tests. | Product Engineering + Security + QA | No feature evidence located. |
| S3-16 | Sec. 3, p. 5 | Customizable reports for regulatory, client, and internal use. | CANNOT_CLAIM | Template/version model, sample CMDP/netDMR/internal outputs, field mapping, validation, and reconciliation tests. | Reporting Engineering + Lab SME + QA | No report conformance evidence located. |
| S3-17 | Sec. 3, p. 5 | Comprehensive training materials and ongoing user support. | PROTOTYPE_EVIDENCE | Training/support outlines exist; add complete materials, role-based labs, knowledge checks, support catalog, and staffing proof. | Training Lead + Support Lead | Drafts do not establish comprehensive or ongoing delivery. |
| S3-18 | Sec. 3, p. 5 | Built-in help or knowledge base for self-service troubleshooting. | CANNOT_CLAIM | Searchable KB build, article inventory, in-product links, ownership/update process, and user test. | Product/Documentation Lead + Support | No built-in help evidence located. |
| S3-19 | Sec. 3, p. 5 | Dedicated technical support for updates and issue resolution. | PROTOTYPE_EVIDENCE | Escalation runbook exists; add named support function, coverage, SLAs, update policy, ticket evidence, and continuity plan. | Support Lead + Product Operations | Staffing/capacity and contractual terms are unverified. |

## C. Evaluation and demonstration requirements

| ID | RFP locator | Requirement | Status | Exact evidence/artifact needed | Owner | Blocking note |
|---|---|---|---|---|---|---|
| E01 | Body Sec. 5 Phase I, p. 5 | Adhere to instructions. | CANNOT_CLAIM | Final submission checklist with owner/sign-off for every instruction. | Proposal Operations | Final package absent. |
| E02 | Body Sec. 5 Phase I, p. 5 | Be complete and timely. | CANNOT_CLAIM | Cleared matrix, form manifest, pagination check, and timely provider receipt. | Proposal Operations | Unresolved capability and corporate evidence rows remain. |
| E03 | Body Sec. 5 Phase II, p. 5 | Ability to meet Section 3 requirements - 25 points. | CANNOT_CLAIM | Section 3 evidence pack with runnable demos/tests and honest gaps. | Product Lead + QA | Specification text is not evidence. |
| E04 | Body Sec. 5 Phase II, p. 5 | Experience and references - 25 points. | CANNOT_CLAIM | Three qualifying, permission-cleared reference records matching Attachment A categories and project evidence. | Corporate Operations + Legal | No verified qualifying references are available. |
| E05 | Body Sec. 5 Phase II, p. 5 | Implementation timeline - 10 points. | CANNOT_CLAIM | Dated implementation schedule with dependencies, resources, milestones, migration, training, acceptance, and risk buffer. | Implementation Lead | Discovery outline is not a timeline; City inputs are still unknown. |
| E06 | Body Sec. 5 Phase II, p. 5 | Post-implementation support and maintenance - 25 points. | PROTOTYPE_EVIDENCE | Support/escalation draft exists; add staffed model, maintenance cadence, SLAs, metrics, and contractual approval. | Support Lead + Product Operations | Prototype planning evidence only. |
| E07 | Body Sec. 5 Phase II, p. 5 | Cost competitiveness and value - 15 points. | CANNOT_CLAIM | Authorized cost model and completed Attachment B, separately packaged. | Finance + authorized signer | No price is available or authorized. |
| E08 | Body Sec. 5, p. 6 | Be prepared for a software demonstration if the City requests one. | CANNOT_CLAIM | Runnable demo environment, scripted scenarios mapped to Section 3, synthetic data, operator, and fallback plan. | Product Lead + Sales Engineering + QA | No demo-readiness evidence is available to this lane. |

## D. Attachment A - validation questions

| ID | RFP locator | Requirement | Status | Exact evidence/artifact needed | Owner | Blocking note |
|---|---|---|---|---|---|---|
| AA01 | Att. A General 1, p. 11 | Company name, address, contact, phone, email, and website. | CANNOT_CLAIM | Corporate registry/profile record and authorized proposal contact approval. | Corporate Operations + Legal | Do not infer legal entity or authority from an email identity. |
| AA02 | Att. A General 2, p. 11 | Number and list of U.S. facilities/locations. | CANNOT_CLAIM | Verified facility list. | Corporate Operations | No verified list supplied. |
| AA03 | Att. A General 3, p. 11 | Years doing business under the company name. | CANNOT_CLAIM | Formation/registry evidence and history statement. | Corporate Operations + Legal | No evidence supplied. |
| AA04 | Att. A General 4, p. 11 | Total full-time employees. | CANNOT_CLAIM | Current HR-certified headcount. | People Operations | No evidence supplied. |
| AA05 | Att. A General 5, p. 11 | SBA status and documentation if applicable. | CANNOT_CLAIM | Current SBA determination/certificate or truthful “No” approved by Legal. | Corporate Operations + Legal | No status evidence supplied. |
| AA06 | Att. A General 6, p. 11 | Standard payment terms. | CANNOT_CLAIM | Finance-approved payment terms. | Finance + Legal | No terms approved for this bid. |
| AA07 | Att. A General 7, p. 11 | At least three references: new (under 12 months), retained (3+ years), and former (terminated within 2 years), with contact information. | CANNOT_CLAIM | Three category-matching, permission-cleared references with dates, scope, outcomes, and contact data. | Corporate Operations + Legal | No qualifying references or permissions are evidenced. |
| AA08 | Att. A General 8, p. 11 | State ability to meet minimum insurance and additional-insured requirement. | CANNOT_CLAIM | Broker/policy evidence and authorized answer. | Risk/Insurance + Legal | Cannot claim willingness/capacity without review. |
| AA09 | Att. A Functionality 1, p. 11 | Provide certificate of insurance before contract signing and commencement. | CANNOT_CLAIM | Broker confirmation, bindable coverage, and pre-contract checklist. | Risk/Insurance + Legal | No insurance evidence. |
| AA10 | Att. A Functionality 2, p. 11 | Instruct carrier to notify City if coverage changes. | CANNOT_CLAIM | Broker/carrier endorsement or written commitment approved by Risk. | Risk/Insurance | No commitment evidence. |
| AA11 | Att. A Functionality 3, p. 11 | Purchase City business license and complete vendor forms if selected. | PLANNED_AFTER_AWARD | Authorized willingness statement and post-award onboarding checklist. | Corporate Operations + Finance | Performance is post-award; approval still required before answering “Yes.” |
| AA12 | Att. A Quality 1, p. 11 | State whether a QA program exists and attach it if yes. | CANNOT_CLAIM | Current approved QA program or truthful “No” response authorized by Legal/Product. | Quality Lead + Legal | No QA program artifact supplied. |
| AA13 | Att. A Quality 2, p. 11 | State whether employees take mandatory drug tests. | CANNOT_CLAIM | HR policy and authorized response consistent with law and actual practice. | People Operations + Legal | No policy evidence supplied. |
| AA14 | Att. A Legal 1, p. 11 | Disclose pending lawsuits, if any. | CANNOT_CLAIM | Current legal representation approved by counsel. | Legal | No litigation certification supplied. |

## E. Attachment B - separate price matrix

| ID | RFP locator | Requirement | Status | Exact evidence/artifact needed | Owner | Blocking note |
|---|---|---|---|---|---|---|
| AB01 | Att. B, p. 12 | Send Attachment B separately under Section 1 instructions. | CANNOT_CLAIM | Separately approved/sent package and provider receipt. | Finance + Proposal Operations + authorized sender | No pricing or sending authorized. |
| AB02 | Att. B, p. 12 | Price implementation. | CANNOT_CLAIM | Cost model, assumptions, approval, and completed price cell. | Finance + Implementation Lead | No price supplied. |
| AB03 | Att. B, p. 12 | Price staff training. | CANNOT_CLAIM | Training scope/cost model and approved price. | Finance + Training Lead | No price supplied. |
| AB04 | Att. B, p. 12 | Price instrument integration. | CANNOT_CLAIM | Device-by-device scope/assumptions and approved price. | Finance + Integration Engineering | Compatibility and exact integration scope are unknown. |
| AB05 | Att. B, p. 12 | Price yearly maintenance. | CANNOT_CLAIM | Maintenance scope, term assumptions, and approved annual price. | Finance + Product Operations | No price supplied. |
| AB06 | Att. B, p. 12 | Price ongoing technical support. | CANNOT_CLAIM | Support coverage/SLA assumptions and approved price. | Finance + Support Lead | No price supplied. |
| AB07 | Att. B, p. 12 | Acknowledge addenda and complete company/date/contact/title/signature fields with authorized signer. | CANNOT_CLAIM | Final addenda log and fully executed Attachment B. | Proposal Operations + Legal + authorized signer | Addenda must be rechecked immediately before any submission. |

## F. Attachment C - Conditions and Non-Collusion

| ID | RFP locator | Requirement | Status | Exact evidence/artifact needed | Owner | Blocking note |
|---|---|---|---|---|---|---|
| AC01 | Att. C, p. 13 | Form signed in full by a responsible authorized representative. | CANNOT_CLAIM | Fully completed form plus proof of signing authority. | Legal + authorized officer | No signed form or authority evidence available. |
| AC02 | Att. C, p. 13 | Agree to RFP conditions and referenced Standard Terms and Conditions. | CANNOT_CLAIM | Legal review of all incorporated terms and written approval. | Legal | The packet text available to this lane does not include a separate attached Standard Terms document; do not assume acceptance. |
| AC03 | Att. C, p. 13 | Agree to furnish services at stated prices/location/date. | CANNOT_CLAIM | Approved scope, price, delivery commitments, and authorized signature. | Finance + Legal + Delivery Lead | No price or delivery commitment approved. |
| AC04 | Att. C, p. 13 | Certify no agreement/collusion, no inducement, independent arrival, and no premature disclosure. | CANNOT_CLAIM | Authorized officer certification after conflict/communication review. | Legal + authorized officer | Must be a truthful human/legal certification, not an inferred system claim. |

## G. Attachment D - conditional question form

| ID | RFP locator | Requirement | Status | Exact evidence/artifact needed | Owner | Blocking note |
|---|---|---|---|---|---|---|
| AD01 | Att. D, p. 14 | Prepare questions on the provided template if questions are submitted. | CANNOT_CLAIM | Owner-approved Attachment D or written no-question decision. | Proposal Operations | No external contact authorized. |
| AD02 | Att. D, p. 14 | Give a date and RFP reference for each question. | CANNOT_CLAIM | Completed row-level question log. | Proposal Operations + requirement owner | Conditional; no question package exists. |
| AD03 | Att. D, p. 14 | Include requester/company/email fields. | CANNOT_CLAIM | Verified identity/contact and authorized form. | Corporate Operations + Proposal Operations | Identity/authority evidence not supplied to this lane. |
| AD04 | Sec. 4 and Att. D, pp. 5, 14 | Submit before cutoff and preserve City answer/addendum. | CANNOT_CLAIM | Authorized email receipt and addendum reconciliation log. | Proposal Operations | No question was sent; deadline may already be inside the five-business-day window. |

## H. Attachment F - analysis and method coverage

Every row below is a separate City-listed analyte/method target. `CANNOT_CLAIM` means no validated method configuration, calculation, unit/reporting rule, QC rule, or regression result was available. The repeated owner is Reporting/Methods Engineering with Lab SME and QA review.

| ID | RFP locator | Analysis / source method | Status | Exact evidence/artifact needed | Owner | Blocking note |
|---|---|---|---|---|---|---|
| AF-A01 | Att. F, p. 16 | Alkalinity - SM 2320 B | CANNOT_CLAIM | Versioned method configuration and synthetic calculation/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A02 | Att. F, p. 16 | Biochemical Oxygen Demand - SM 5210 B | CANNOT_CLAIM | Versioned method configuration and synthetic lifecycle/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A03 | Att. F, p. 16 | Bromide - EPA 300.0 | CANNOT_CLAIM | Versioned method configuration and synthetic instrument/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A04 | Att. F, p. 16 | Chemical Oxygen Demand - HACH 8000 | CANNOT_CLAIM | Versioned method configuration and synthetic calculation/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A05 | Att. F, p. 16 | Chloride - EPA 300.0 | CANNOT_CLAIM | Versioned method configuration and synthetic instrument/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A06 | Att. F, p. 16 | Chlorine, Free - SM 4500-Cl G | CANNOT_CLAIM | Versioned method configuration and synthetic calculation/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A07 | Att. F, p. 16 | Chlorine, Total Residual - SM 4500-Cl G | CANNOT_CLAIM | Versioned method configuration and synthetic calculation/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A08 | Att. F, p. 16 | Coliform, E. coli - SM 9223B | CANNOT_CLAIM | Versioned method configuration and synthetic result/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A09 | Att. F, p. 16 | Coliform, Total - SM 9223B | CANNOT_CLAIM | Versioned method configuration and synthetic result/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A10 | Att. F, p. 16 | Dissolved Oxygen - source prints “SM 450-O G” | CANNOT_CLAIM | Buyer-confirmed method identifier, versioned configuration, and synthetic test. | Methods Engineering + City/Lab SME + QA | Source identifier must be confirmed; do not silently correct it. |
| AF-A11 | Att. F, p. 16 | Fluoride - EPA 300.0 | CANNOT_CLAIM | Versioned method configuration and synthetic instrument/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A12 | Att. F, p. 16 | Hardness, Total/Calcium - Calc | CANNOT_CLAIM | Buyer-approved formula/rounding/units and synthetic calculation tests. | Methods Engineering + City/Lab SME + QA | Formula is not supplied. |
| AF-A13 | Att. F, p. 16 | Heterotrophic Plate Count - SM 9215 B | CANNOT_CLAIM | Versioned method configuration and synthetic result/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A14 | Att. F, p. 16 | Metals (AA), Total - source prints “EPA 200.9, SM” | CANNOT_CLAIM | Buyer-confirmed complete method citation, configuration, and synthetic instrument/QC test. | Methods Engineering + City/Lab SME + QA | Source method text is incomplete. |
| AF-A15 | Att. F, p. 16 | Metals (AA), Dissolved - EPA 200.9 | CANNOT_CLAIM | Versioned method configuration and synthetic instrument/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A16 | Att. F, p. 16 | Nitrogen, Ammonia - SM 4500-NH3 B/C | CANNOT_CLAIM | Versioned method configuration and synthetic calculation/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A17 | Att. F, p. 16 | Nitrogen, NO2 - EPA 300.0 | CANNOT_CLAIM | Versioned method configuration and synthetic instrument/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A18 | Att. F, p. 16 | Nitrogen, NO3 - EPA 300.0 | CANNOT_CLAIM | Versioned method configuration and synthetic instrument/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A19 | Att. F, p. 16 | Nitrogen, NOX - EPA 353.2 | CANNOT_CLAIM | Versioned method configuration and synthetic calculation/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A20 | Att. F, p. 16 | Nitrogen, TKN - SM 4500-N B | CANNOT_CLAIM | Versioned method configuration and synthetic calculation/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A21 | Att. F, p. 16 | Nitrogen, Total - Calc | CANNOT_CLAIM | Buyer-approved formula/rounding/units and synthetic calculation tests. | Methods Engineering + City/Lab SME + QA | Formula is not supplied. |
| AF-A22 | Att. F, p. 16 | Organic Carbon, Dissolved - SM 5310 B | CANNOT_CLAIM | Versioned method configuration and synthetic instrument/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A23 | Att. F, p. 16 | Organic Carbon, Total - SM 5310 B | CANNOT_CLAIM | Versioned method configuration and synthetic instrument/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A24 | Att. F, p. 16 | Paint Filter Test - method blank | CANNOT_CLAIM | Buyer-confirmed method, configuration, and synthetic test. | Methods Engineering + City/Lab SME + QA | Method is absent from source. |
| AF-A25 | Att. F, p. 16 | pH - SM 4500-H+ B | CANNOT_CLAIM | Versioned method configuration and synthetic instrument/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A26 | Att. F, p. 16 | Phosphate, Ortho - EPA 300.0 | CANNOT_CLAIM | Versioned method configuration and synthetic instrument/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A27 | Att. F, p. 16 | Phosphorus, Total - EPA 365.4/365.1 | CANNOT_CLAIM | Versioned method configuration and synthetic calculation/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A28 | Att. F, p. 16 | Solids, Total - SM 2540 B | CANNOT_CLAIM | Versioned method configuration and synthetic calculation/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A29 | Att. F, p. 16 | Solids, Total Dissolved - SM 2540 C | CANNOT_CLAIM | Versioned method configuration and synthetic calculation/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A30 | Att. F, p. 16 | Solids, Total Suspended - SM 2540 D | CANNOT_CLAIM | Versioned method configuration and synthetic calculation/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A31 | Att. F, p. 16 | Solids, Volatile - SM 2540 E | CANNOT_CLAIM | Versioned method configuration and synthetic calculation/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A32 | Att. F, p. 16 | Solids, Volatile Suspended - SM 2540 D | CANNOT_CLAIM | Versioned method configuration and synthetic calculation/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A33 | Att. F, p. 16 | Specific Conductance - SM 2510 B | CANNOT_CLAIM | Versioned method configuration and synthetic instrument/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A34 | Att. F, p. 16 | Sulfate - EPA 300.0 | CANNOT_CLAIM | Versioned method configuration and synthetic instrument/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A35 | Att. F, p. 16 | Turbidity - SM 2310 B | CANNOT_CLAIM | Versioned method configuration and synthetic instrument/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |
| AF-A36 | Att. F, p. 16 | Volatile Acids - method blank | CANNOT_CLAIM | Buyer-confirmed method, configuration, and synthetic test. | Methods Engineering + City/Lab SME + QA | Method is absent from source. |
| AF-A37 | Att. F, p. 16 | UV254 - SM 5910 B | CANNOT_CLAIM | Versioned method configuration and synthetic instrument/QC/report test. | Methods Engineering + Lab SME + QA | No validated method evidence. |

## I. Attachment F - instrument integration targets

| ID | RFP locator | Instrument target | Status | Exact evidence/artifact needed | Owner | Blocking note |
|---|---|---|---|---|---|---|
| AF-I01 | Att. F, p. 17 | pH meters (5) | CANNOT_CLAIM | Exact makes/models/firmware/protocols, interface documentation, adapter fixture, and witnessed ingest/reconciliation tests. | Integration Engineering + City/Lab SME + QA | “pH meters” is insufficient for a compatibility claim. |
| AF-I02 | Att. F, p. 17 | Analytical balances (3) | CANNOT_CLAIM | Exact makes/models/firmware/protocols, interface documentation, adapter fixture, and witnessed tests. | Integration Engineering + City/Lab SME + QA | Exact devices/interfaces are not supplied. |
| AF-I03 | Att. F, p. 17 | PerkinElmer Furnace AA | CANNOT_CLAIM | Exact model/software/export protocol, vendor documentation, adapter fixture, and witnessed tests. | Integration Engineering + City/Lab SME + QA | Brand/family is not exact compatibility evidence. |
| AF-I04 | Att. F, p. 17 | Metrohm Ion Chromatograph | CANNOT_CLAIM | Exact model/software/export protocol, vendor documentation, adapter fixture, and witnessed tests. | Integration Engineering + City/Lab SME + QA | Brand/family is not exact compatibility evidence. |
| AF-I05 | Att. F, p. 17 | Sievers TOC Analyzer | CANNOT_CLAIM | Exact model/software/export protocol, vendor documentation, adapter fixture, and witnessed tests. | Integration Engineering + City/Lab SME + QA | Brand/family is not exact compatibility evidence. |
| AF-I06 | Att. F, p. 17 | Seal Discrete Analyzer | CANNOT_CLAIM | Exact model/software/export protocol, vendor documentation, adapter fixture, and witnessed tests. | Integration Engineering + City/Lab SME + QA | Brand/family is not exact compatibility evidence. |

## J. Attachment F - required reporting targets

| ID | RFP locator | Reporting target | Status | Exact evidence/artifact needed | Owner | Blocking note |
|---|---|---|---|---|---|---|
| AF-R01 | Att. F, p. 17 | CMDP drinking water reporting | CANNOT_CLAIM | Current City-required schema/template, field mapping, validated synthetic output, rejection handling, and reconciliation test. | Reporting Engineering + City/Lab SME + QA | No format/version or conformance evidence supplied. |
| AF-R02 | Att. F, p. 17 | netDMR reporting | CANNOT_CLAIM | Current City-required schema/template, field mapping, validated synthetic output, rejection handling, and reconciliation test. | Reporting Engineering + City/Lab SME + QA | No format/version or conformance evidence supplied. |
| AF-R03 | Att. F, p. 17 | Operations dashboards, internal or linked externally (for example Power BI) | CANNOT_CLAIM | Dashboard requirements, role/metric definitions, data lineage, sample dashboard, access tests, and refresh reconciliation. | Reporting/Data Engineering + City/Lab SME + QA | Buyer metrics and implementation evidence are absent. |

## Submission gate and exact blockers

Do not call the response compliant or submit it until all mandatory `CANNOT_CLAIM` rows are either supported by dated evidence, answered with an owner-approved truthful limitation where the RFP allows it, or explicitly accepted as a bid risk by the authorized owner.

The present hard blockers are:

1. No runnable, validated AquaTrace build or executed Section 3 acceptance evidence is available to this lane.
2. No verified new/retained/former references, deployment history, customer permission, or experience evidence.
3. No verified legal entity/profile packet, authorized signer, insurance readiness, QA program, SBA status, HR statements, payment terms, litigation statement, or commercial approvals.
4. No qualifying independent security proof, NIST/FedRAMP SAR, scan/audit report, or annual-assurance capability.
5. Attachment F lacks exact instrument models/interfaces and has incomplete method entries; there is no device compatibility or regulatory-report conformance evidence.
6. No authorized implementation timeline, support staffing/SLA, maintenance commitment, or price matrix.
7. No final response, cover letter, signed Attachment C, addenda log, 20-page QA, or submission authorization/receipt.

No City/prospect contact, question, proposal, form, price, payment, or bid submission was made by this compliance-matrix lane. No capability, customer, reference, insurance, certification, instrument compatibility, security compliance, or pricing claim was invented.
