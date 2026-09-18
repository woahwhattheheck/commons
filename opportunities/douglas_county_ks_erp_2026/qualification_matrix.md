# Qualification matrix — RFP-2026-0012

This matrix separates **opportunity identity**, **prime eligibility**, and **TJLabs specialist-workshare readiness**. No row may be promoted from UNKNOWN using a secondary summary, a vendor marketing page, or inference from a different procurement.

| Gate | Current state | Required authority | Release condition |
|---|---|---|---|
| Exact RFP packet | **UNKNOWN / HARD HOLD** | County portal bytes | Current packet retained and hashed |
| Addenda / Q&A currentness | **UNKNOWN / HARD HOLD** | County-issued generation | All current addenda/Q&A retained and bound |
| Proposal deadline | DISCOVERY-BOUND | County packet/addenda | Confirm 2026-10-20 14:00 CT in controlling generation |
| Question deadline | DISCOVERY-BOUND | County packet/addenda | Confirm 2026-09-30 in controlling generation |
| Teaming / subcontract permission | **UNKNOWN / HARD HOLD** | County packet/addenda | Exact clause permits route and disclosure is understood |
| Prime legal/registration eligibility | **UNKNOWN / HARD HOLD** | County packet + prime evidence | Requirements enumerated and prime evidence retained |
| Public-sector ERP experience / references | **UNKNOWN / HARD HOLD** | County packet + prime-owned proof | Exact threshold met truthfully |
| Insurance / bonding / certifications | **UNKNOWN / HARD HOLD** | County packet + prime-owned proof | Every mandatory item satisfied or explicitly curable |
| Security / privacy / hosting terms | **UNKNOWN / HARD HOLD** | County packet + prime-owned proof | Requirements bound to real product/service evidence |
| Functional ERP compliance | **UNKNOWN / HARD HOLD** | County packet + prime-owned response | Finance/HR/payroll/procurement requirements mapped |
| Implementation / integration scope | PARTIAL | County packet + prime plan | Required services and interfaces explicitly mapped |
| Data conversion scope | PARTIAL | County packet + prime plan | Source classes, history, volumes, ownership and acceptance bound |
| Evaluation / scoring | **UNKNOWN / HARD HOLD** | County packet | Criteria and weights retained |
| Pricing instructions | **UNKNOWN / HARD HOLD** | County packet | Buyer format/terms retained; no invented buyer price |
| Submission forms / signatures | **UNKNOWN / HARD HOLD** | County packet | Complete manifest retained; authorized signer remains prime |
| Prime selected | **NO / HOLD** | Internal evidence + prime interest | Candidate meets gates and is actually pursuing |
| TJLabs workshare accepted by prime | **NO / HOLD** | Prime acceptance / work order | Scope, fee, responsibility split accepted |
| Single-writer outbound authorization | **NO / HOLD** | Fresh coordination generation | Exact recipient/subject/body explicitly released after recensus |
| Buyer submission | **NOT AUTHORIZED** | Prime/buyer process | Never self-authorized by this package |

## TJLabs specialist readiness

These are internal delivery gates. They do not imply the prime or bid is qualified.

| Workstream | Internal target | Evidence required before delivery claim |
|---|---|---|
| Conversion reconciliation | READY-TO-SCOPE | Prime-authorized source/target mappings, counts, transformations, exclusions |
| Segregation-of-duties acceptance | READY-TO-SCOPE | Prime/County-approved roles and rules; synthetic fixtures until real data is authorized |
| Integration evidence | READY-TO-SCOPE | Interface contracts, owners, retry/error semantics, test endpoints or evidence |
| Cutover / rollback / replay | READY-TO-SCOPE | Prime-owned runbook, freeze/cutover assumptions, rollback criteria, system owners |
| Acceptance binder | READY-TO-SCOPE | Prime-owned deliverables and buyer acceptance criteria |

## Fail-closed rules

- Unknown mandatory buyer requirements stay HOLD.
- A prime's general capability never proves this solicitation's eligibility.
- A historical County audit finding may justify a test hypothesis; it cannot be represented as a 2026 RFP requirement unless the current packet says so.
- An internal proposed fee is not buyer pricing and is not booked revenue.
- No customer-facing artifact may expose internal coordination receipts or private workflow mechanics.
- No external message is sent without a fresh collision census plus current single-writer authorization.
