# University of Iowa RFQ 18649 — prime fee narrative template

**ILLUSTRATIVE PLANNING DRAFT — NOT AN ACCEPTED OFFER OR BID SUBMISSION.** The prospective prime chooses final prices, delivery assumptions, and terms. Numeric examples are model scenarios, not verified quotations, actual staffing availability, or commitments. Paste blocks are University-facing language for adaptation; preparation notes and model assumptions are internal.

## 1. Attribute 9 pricing excerpt — editable template

This is only the pricing portion of Attribute 9. The complete response must also address methodology/framework/interviews, schedule and deviations, named team and qualifications, comparable references, and assumptions/dependencies/constraints. Attribute 9 allows 4,000 characters total. This excerpt has **985 characters**, including paragraph breaks and current placeholders, leaving **3015 characters** for other content. Recount the assembled field after substitution.

<!-- ATTRIBUTE_9_PRICING_START -->
The fixed price for the base engagement is ${{BASE_FIXED_FEE_USD}}, inclusive of all work described in the Statement of Work and all expected expenses. It covers kickoff and discovery, interviews and artifact review, analysis and synthesis, draft report and review, and the final written report across ESS, RIS, and IAM. Expected travel and other expenses needed for the proposed delivery approach are included; no separate expense reimbursement is requested.

Follow-on readout/discussion options, outside the base engagement, are separately priced: one remote session of up to 60 minutes at ${{OPTION_ONE_SESSION_FEE_USD}}, or a package of up to two remote sessions of up to 60 minutes each at ${{OPTION_TWO_SESSION_FEE_USD}}. Each option includes preparation, supporting materials, and expected expenses. These are alternative packages, not cumulative charges. The supplier bears parking fees, citations, and permit costs; none will be submitted to the University for reimbursement.
<!-- ATTRIBUTE_9_PRICING_END -->

The remote format, one/two-session alternatives, and 60-minute limits are proposed UIOWA004 design assumptions, not RFQ-mandated quantities or confirmed availability.

## 2. Attribute 9 pricing excerpt — worked LOCAL example

**Illustrative LOCAL base scenario with REMOTE follow-on options; not an accepted offer.** This worked excerpt has **928 characters**, leaving **3072 characters** for the other required Attribute 9 content.

<!-- LOCAL_ATTRIBUTE_9_PRICING_START -->
The fixed price for the base engagement is $46,576.50, inclusive of all work described in the Statement of Work and all expected expenses. It covers kickoff and discovery, interviews and artifact review, analysis and synthesis, draft report and review, and the final written report across ESS, RIS, and IAM. Expected travel and other expenses needed for the proposed delivery approach are included; no separate expense reimbursement is requested.

Follow-on readout/discussion options, outside the base engagement, are separately priced: one remote session of up to 60 minutes at $5,125.00, or a package of up to two remote sessions of up to 60 minutes each at $5,500.00. Each option includes preparation, supporting materials, and expected expenses. These are alternative packages, not cumulative charges. The supplier bears parking fees, citations, and permit costs; none will be submitted to the University for reimbursement.
<!-- LOCAL_ATTRIBUTE_9_PRICING_END -->

## 3. Bid Line 1 — Fee for Services / Item Attribute 1, Fee Details

The default example places **$46,576.50** as the base Fee for Services price. Optional readout prices are separate, not included in the base bid line. The printed invitation supplies Price and Total blanks but does not establish an assumed quantity multiplier; the prime should inspect the actual eBid entry and calculated total. This template creates no additional bid line.

The editable Fee Details block below has **1899 characters**, within that field's 4,000-character limit before substitution.

<!-- FEE_DETAILS_START -->
BASE ENGAGEMENT — FIXED PRICE: ${{BASE_FIXED_FEE_USD}}.

The base fee covers all Statement of Work services and expected expenses for the assessment of ESS, RIS, and IAM: kickoff and discovery; interviews and artifact review; analysis and synthesis; draft report preparation and review; and final written report delivery. Assessment coverage includes software development practices, security, deployment, and AI readiness. It includes the prime's management, professional assessment, coordination, and final deliverable responsibilities, together with any subcontracted production services used to perform the proposed work.

INCLUDED EXPENSES / REIMBURSABLE ITEMS: All expected expenses needed for the proposed delivery approach, including expected travel and onsite attendance costs, are included in the fixed base fee. No separate reimbursable expense line is proposed for this scope. The supplier bears parking fees, citations, and parking permit costs and will not seek University reimbursement for them. Patient facility parking ramps will not be used.

SEPARATELY PRICED FOLLOW-ON OPTIONS: One remote readout/discussion session of up to 60 minutes: ${{OPTION_ONE_SESSION_FEE_USD}}. Alternatively, a package of up to two remote readout/discussion sessions of up to 60 minutes each: ${{OPTION_TWO_SESSION_FEE_USD}}. Each option includes preparation, supporting materials, the stated sessions, and all expected expenses. These optional follow-on services are outside the base fee and are alternative packages; the two-session package is not added to the one-session price. The base-plus-option total is ${{BASE_PLUS_ONE_SESSION_USD}} if the one-session option is selected, or ${{BASE_PLUS_TWO_SESSION_USD}} if the two-session package is selected.

The descriptions explain which services each fixed price covers; they do not establish installment amounts or new payment or acceptance conditions.
<!-- FEE_DETAILS_END -->

For the worked LOCAL/REMOTE example, substitute the field values in Section 4. That produces a **1802-character** Fee Details response. A pricing description does not establish University payment terms.

## 4. Model-to-text field contract

Values are USD numbers only, with two decimal places and thousands separators; the paste blocks supply the dollar sign.

| Placeholder | Meaning | Worked LOCAL base / REMOTE option |
|---|---|---:|
| `BASE_FIXED_FEE_USD` | Prime's whole all-inclusive base bid; not merely the TJLabs workshare | 46,576.50 |
| `OPTION_ONE_SESSION_FEE_USD` | Entire separately priced one-session follow-on package | 5,125.00 |
| `OPTION_TWO_SESSION_FEE_USD` | Entire package of up to two follow-on sessions; not a per-session rate | 5,500.00 |
| `BASE_PLUS_ONE_SESSION_USD` | Base + one-session option | 51,701.50 |
| `BASE_PLUS_TWO_SESSION_USD` | Base + two-session package | 52,076.50 |

If only one readout option is offered, remove the unused alternative and combined-total sentence from both blocks. A zero-session selection leaves the base alone. An unpriced placeholder or omitted option is not a zero-dollar quotation. If an onsite option is selected, replace “remote” consistently and use the matching model price; do not mix remote language with onsite prices.

## 5. Illustrative base-price build

The 134 prime work hours come from the eight-week UIOWA002 staffing candidate pinned to `aaff1e3e196dcd9dddf15484fb7a5d74f9c5ba50`. The candidate is a planning input, not a verified current-main deliverable, actual availability, or assignment. The illustrative pricing baseline uses **$150/hour as an assumed prime billing rate**, not a measured labor cost. Prime onsite work is already within the 134 work hours; do not add it again. Travel hours are additional.

| Base component | LOCAL illustration | REGIONAL illustration |
|---|---:|---:|
| TJLabs proposed technical workshare | $24,000.00 | $24,000.00 |
| Prime work hours | 134 | 134 |
| Prime travel hours | 3 visits × 4 h = 12 | 3 visits × 6 h = 18 |
| Prime hours priced at assumed $150/h | 146 h × $150 = $21,900.00 | 152 h × $150 = $22,800.00 |
| Direct expected travel expenses | 3 × $205 = $615.00 | 3 × $640 = $1,920.00 |
| Expense contingency, assumed 10% of direct expenses | $61.50 | $192.00 |
| **Illustrative fixed base price** | **$46,576.50** | **$48,912.00** |

LOCAL visit assumption: 200 miles × $0.75 + one day × $35 meals + $20 parking = $205 direct expenses; four prime travel hours. REGIONAL visit assumption: 400 miles × $0.75 + one $180 hotel night + two days × $60 meals + two days × $20 parking = $640 direct expenses; six prime travel hours. Mileage, meal, hotel, parking, visit, and travel-time inputs are editable planning assumptions, not policy entitlements, verified quotes, or named-person availability.

The total is the **prime's complete proposed service price**, not profit earned. The assumed billing rate may need to support labor cost, overhead, and profit; those costs have not been measured here. No profit, margin, award, invoice, or revenue recognition is established by this model.

The workbook separately exposes **additional prime work hours**, initially an explicit illustrative zero. The candidate's 134-hour total is a valid planning calculation, but does not itself prove that every University-facing obligation has enough effort assigned. Before adopting a final price, map methodology/professional judgment, complete written-report assembly, review and final delivery into the prime work plan, or add the missing effort. Candidate activities A09 (draft synthesis), A12 (prime review), A14 (reconciliation) and A15 (final artifact QA) support that mapping; their names alone do not establish exhaustive report-production coverage. Do not relabel required base work as a paid follow-on option.

Ten additional prime work hours add $1,500 to either base scenario at the illustrative rate. A blank additional-hours input means unknown, not zero. The baseline keeps the displayed 134 hours and an explicit zero only to make the arithmetic inspectable.

The six-week source plan has capacity warnings for Clark in week 3, TJLabs in weeks 2-3, and University participants in weeks 1-2. Its 131-hour prime total must not be read as a proven feasible compressed schedule. The eight-week source plan has no capacity warning under its own assumptions, but neither source scenario includes the travel time or additional work introduced by pricing. Recheck actual weekly capacity after choosing visit timing and the final work split; these models establish no person's availability.

## 6. Illustrative follow-on option prices

Each row is an alternative separately priced package outside the base. The TJLabs proposed $4,000 optional support package covers up to two sessions if separately authorized; do not multiply that package by the session count. Model prime effort is five common preparation hours plus 2.5 hours per session, at the assumed $150/h billing rate. Onsite versions add one visit per session, prime travel time, direct expenses, and the assumed 10% expense contingency.

| Option delivery assumption | One session | Up to two sessions |
|---|---:|---:|
| REMOTE | $5,125.00 | $5,500.00 |
| ONSITE — LOCAL prime visits | $5,950.50 | $7,151.00 |
| ONSITE — REGIONAL prime visits | $6,729.00 | $8,708.00 |

REMOTE arithmetic: $4,000 + (5 + 2.5 × sessions) × $150. LOCAL onsite adds per session 4 travel hours × $150 + $205 expenses + $20.50 contingency. REGIONAL onsite adds per session 6 travel hours × $150 + $640 expenses + $64 contingency.

These onsite variants model **prime** attendance with TJLabs technical support remote. A TJLabs onsite attendance/travel quote is unknown and is not included or authorized by these assumptions. If the chosen work split requires TJLabs onsite work, establish the internal scope and quote and update the prime's all-inclusive option before final pricing. Do not use this scenario to represent a confirmed staffed trip.

## 7. Expense and subcontract reconciliation

TJLabs' **$24,000** proposal buys a bounded technical production workshare, not the whole University engagement. Its separately authorized **$4,000** support option is an internal input, not automatically the University's complete option price. The prime remains responsible for its own professional assessment, management, staffing, onsite approach, final deliverables, and proposal authority.

TJLabs excludes travel from its internal workshare and has not committed travel. Attribute 9 nevertheless requires the prime's University-facing fixed fee to include all expected expenses. The prime must decide who performs each onsite activity and include the expected cost in its fixed bid, including any separately agreed internal subcontract travel cost if needed. Do not pass the internal exclusion through as “travel billed separately,” “actual expenses additional,” or “TJLabs travel reimbursable.”

The RFQ's hybrid approach includes reasonable onsite kickoff/key workshops/readout and remote interviews/routine work (p. 7, Attribute 5). The base model must cover the proposed delivery approach; optional follow-on prices must not separately charge for work already required and priced in the base.

**Parking:** Budget expected lawful parking/permit costs internally. The supplier bears parking fees, citations, and permit costs; the University does not reimburse them. Actual parking/permit availability is not established. Patient facility parking ramps must not be used. Citations remain supplier responsibility rather than a University expense claim.

**Payment:** The TJLabs internal proposal remains 40%/$9,600 on written authorization/kickoff, 40%/$9,600 on draft technical package delivery, and 20%/$4,800 on final technical package acceptance. These are subcontract planning terms, not University payment terms. They are absent from the University-facing paste blocks. This template introduces no new payment trigger, acceptance gate, expense entitlement, or automatic change charge.

## 8. Prime decisions needed to finalize pricing

- Select the delivery approach and number of expected onsite visits; confirm whether LOCAL or REGIONAL assumptions match the proposed work.
- Confirm the prime/TJLabs work split, including who performs onsite work and whether an additional internal TJLabs onsite quote is needed.
- Adopt or revise the 134-hour staffing basis, assumed $150/h billing rate, travel hours, expense inputs, and 10% expense contingency; verify staffing availability independently.
- Select one or both separately priced readout alternatives and the intended remote/onsite format. Preserve all-inclusive pricing for the chosen option.
- Confirm the preferred final price and terms, align the complete Attribute 9 proposal and Fee Details entry, and verify bid-line totals. These preparation decisions create no contact, scheduling, or spending authority.

## 9. Source register and reading coverage

| ID | Source / exact location | Requirement or distinction used |
|---|---|---|
| R1 | Current official RFQ 18649 invitation, p. 9, Attribute 9 “Project Proposal,” fully read | Fixed-price base includes all Statement of Work work and expected expenses; separately priced follow-on options; other required proposal contents; 4,000-character field. |
| R2 | Same invitation, p. 16, Attribute 36 “Supplier Parking,” fully read | Supplier bears parking/permit/citation costs; no University reimbursement; limited availability; no patient facility ramps. |
| R3 | Same invitation, p. 16, Bid Line 1 and Item Attribute 1 “Fee Details,” fully read | Detailed fees, reimbursable/non-reimbursable items, connection to services, 4,000-character field. Page 17 is supplier information/signature-authority certification, not a continuation of fee requirements. |
| R4 | Same invitation, p. 6 Attribute 4 §4.4, p. 7 Attribute 5 hybrid approach, pp. 7–8 schedule phases, read during mobilization review | Follow-on services outside base; hybrid delivery and base phases must be reflected in pricing. |
| E1 | [Acceptance exhibit](https://github.com/woahwhattheheck/commons/blob/a02f7faaf428afaca7e4ca621bd229921fa0c58f/revenue/uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md), entire document read; §§2, 4.4, 7, 9 | Proposed/not accepted $24,000 base, 40/40/20 internal triggers, separate $4,000 option, scope/travel boundary, prime authority. Live main read on 2026-09-19 exactly matched this pinned content. |
| C1 | [Commercial handoff](https://github.com/woahwhattheheck/commons/blob/a02f7faaf428afaca7e4ca621bd229921fa0c58f/revenue/uiowa_rfq_18649_workshare/COMMERCIAL.md), entire document read | Internal workshare and payment hypothesis; travel excluded/uncommitted; prime responsibilities. |
| D1 | UIOWA002 staffing candidate `aaff1e3e196dcd9dddf15484fb7a5d74f9c5ba50`; verified UIOWA002 candidate execution and UIOWA010 pricing assumptions | 134 prime work hours. Other rates, travel inputs, contingency, and option labor are explicit UIOWA010 design assumptions. The exact model was read and executed in memory; no current-main or availability claim is made here. |
| D2 | UIOWA004 current working design | Proposed one/two remote readout alternatives and up-to-60-minute sessions. These are prime-selectable design assumptions, not RFQ requirements. |

RFQ identity: 17-page current official invitation, response deadline September 29, 2026, 3:00 PM Central. PDF SHA-256: `908d9104a56cd19fa4ff8496fe731c57262830302a11069234a11cda66745a44`. Readable extraction SHA-256: `c10de6479bfb2db9745235cabb240960295c9ebacd3ea6d0e1e448154c264563`.

Read this pass: full Attribute 9, full Attribute 36, full Bid Line 1/Fee Details, page 17 context, current full acceptance exhibit, and full pinned commercial handoff. Staffing candidate hours were independently reproduced from the pinned model; the exact source and returned task/role totals are preserved in prime-staffing-source.json. Source-derived requirements, supplied model assumptions, and new narrative design are identified separately.

