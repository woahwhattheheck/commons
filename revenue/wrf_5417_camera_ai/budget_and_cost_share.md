# WRF 5417 budget and cost-share model

This file is a **calculation and evidence scaffold**, not an approved budget. No labor rate, fringe rate, indirect rate, equipment cost, travel cost, subcontract, third-party contribution or WRF request is authorized by this repository file.

## 1. Binding constraint

The RFP requires applicant contribution of **at least 33% of the requested WRF award**. Define:

- `R` = requested WRF funding;
- `C_applicant` = allowable applicant cost share/in-kind;
- `C_third_party` = allowable third-party non-cash in-kind and/or other contribution counted under the applicable WRF category;
- `C_total = C_applicant + C_third_party`.

Submission gate:

`C_total >= 0.33 * R`

Examples for planning only:

| WRF request R | Minimum total contribution |
|---:|---:|
| $300,000 | $99,000 |
| $225,000 | $74,250 |
| $150,000 | $49,500 |
| $100,000 | $33,000 |

These examples are arithmetic, not commitments.

## 2. Cost-share evidence rule

Count a contribution only if it is allowable under the applicable WRF/federal rules and is supported by the required evidence. In particular:

- applicant labor/in-kind must use a supportable valuation and actual project time/effort records;
- third-party non-cash in-kind must have the required signed/authorized commitment evidence, including exact value;
- third-party cash payable directly to WRF requires the official Co-Funding Support Form plus commitment letter;
- volunteer/partner/equipment/data access has **zero budget value until a supportable allowable valuation and commitment exist**;
- prior sales outreach to a utility is not a participation commitment and has no cost-share value;
- software already owned is not automatically allowable cost share at a self-selected market price.

## 3. Budget architecture

The official WRF workbook and Budget Narrative should express the same numbers by task and cost category. Recommended planning structure:

| Category | WRF | Applicant cost share | Third-party contribution | Evidence needed before final |
|---|---:|---:|---:|---|
| A/B Personnel | `[INPUT]` | `[INPUT]` | `[INPUT]` | Named people, unburdened labor rates, fringe basis, project effort/person-months |
| C Equipment | `[INPUT]` | `[INPUT]` | `[INPUT]` | Item, ownership/rental basis, necessity, quotes/valuation if required |
| D/E Supplies & Travel | `[INPUT]` | `[INPUT]` | `[INPUT]` | Quantity/basis, trip purpose/destination/people, policy/quotes as applicable |
| F/G Subcontracts & Other Direct Costs | `[INPUT]` | `[INPUT]` | `[INPUT]` | Named/defined scope, category detail, quote/commitment as appropriate |
| H–J Indirect / Fee / Survey | `[INPUT]` | `[INPUT]` | `[INPUT]` | Actual indirect basis/documentation; fee rule/funding-source check; survey/PRA check |

## 4. Personnel

WRF's budget instructions require detailed **unburdened labor** and separate fringe/indirect treatment in the workbook. Do not enter a fully burdened consulting rate as though it were an unburdened wage.

For each person:

`direct_labor = unburdened_rate * proposed_hours`

`fringe = direct_labor * documented_fringe_rate` if an actual supportable fringe basis exists.

The reviewer-facing Budget Narrative must explain role, effort and necessity but **must not disclose individual salary/wage rates**.

Owner/principal effort may not be valued or categorized until the applicant determines the correct treatment under WRF's commercial-entity/federal cost rules and can maintain the required time/effort records.

## 5. Indirect cost

WRF instructions cap the indirect cost rate at **15%** and require support/documentation if indirect recovery is requested. Do not invent a 15% rate merely because it is the ceiling.

If the applicant has no documented indirect-rate basis that satisfies WRF, use `[OWNER/WRF ACCOUNTING DECISION REQUIRED]`; do not fabricate an agreement or historical rate.

## 6. Fee / profit

Do not include fee/profit until the funding source and WRF rule applicable to Project 5417 are confirmed. WRF budget instructions discuss fee limits for commercial organizations but also note circumstances in which profit is prohibited for U.S. government grant/cooperative-agreement recipients/subrecipients. Default planning assumption for this carrier is **fee = 0 pending confirmation**, not an assertion that WRF forbids or permits a specific fee here.

## 7. Task-based allocation model

The technical plan uses seven tasks. Final workbook and narrative should crosswalk every cost to one or more tasks:

1. literature / WRF knowledge base / use-case selection;
2. sensing architecture and field protocol;
3. acquisition / annotation / reference-ground-truth alignment;
4. model development and minimum-sensing evaluation;
5. cross-site/camera transfer stress tests;
6. implementation/economics/workflow assessment;
7. synthesis, technology deliverables and communication.

The budget narrative should state what is being purchased/performed, by whom, when, why it is necessary and which task/deliverable it supports. It should not hide unexplained contingency blocks or duplicate the same effort across award and cost share.

## 8. Equipment strategy

Do not assume purchase of hyperspectral systems for every site. The research design is explicitly tiered. A defensible budget may:

- use owned/utility RGB where appropriate;
- rent or share higher-cost spectral equipment for paired subset experiments;
- purchase only equipment that meets WRF allowability/necessity rules and whose use cannot be met more economically another way;
- document ownership/disposition rules before purchase.

This approach aligns the scientific question—minimum sufficient sensing—with the budget.

## 9. Travel

Each planned trip needs purpose, site/event, number/type of travelers and supportable cost basis. Candidate travel categories:

- initial field-protocol/site commissioning;
- limited maintenance/calibration campaigns not handled locally;
- cross-site validation visit(s) where physically necessary;
- WRF/PAC or project dissemination travel only if required/approved.

Remote work should be used where scientifically and operationally equivalent; do not claim nonexistent local utility staff support merely to cut travel.

## 10. Subcontract / partner budget

Given the current qualification gap, the strongest proposal may require a real water-sector/process and/or computer-vision research partner. If so, the budget must identify actual partner scope and evidence rather than writing a generic placeholder into the final packet. A partner can improve qualifications and site access, but it cannot be invented after submission.

## 11. Budget consistency checks before submission

Finalization must prove:

- workbook WRF amount == portal WRF amount == Abstract WRF amount == Budget Narrative WRF amount;
- cost-share total satisfies the 33% rule;
- every third-party contribution has the required value-specific commitment evidence;
- personnel effort reconciles with Current & Pending forms;
- task totals reconcile to category totals and project total;
- no individual salary/wage rate appears in the reviewer-facing narrative;
- indirect treatment has real support;
- fee/profit treatment is confirmed;
- all arithmetic is recomputed independently;
- private financial information is uploaded only through the required private WRF channels, never this public repository.

## 12. Current status

`HOLD — REQUEST AMOUNT, COST-SHARE SOURCE, PERSONNEL RATES/EFFORT, PARTNERS, EQUIPMENT/TRAVEL AND ADMINISTRATIVE COST BASIS ARE NOT YET VERIFIED.`

The technical narrative can proceed, but the proposal cannot truthfully clear administrative review until these values are supplied and documented.
