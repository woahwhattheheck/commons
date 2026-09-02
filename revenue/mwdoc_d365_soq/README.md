# MWDOC RFQ FIN. 2026-001 — compliance/readiness review

**Commons ID:** `mwdoc-d365-partner-soq-packet-20260902-01`  
**Observed:** 2026-09-02  
**Decision:** **NO-GO AS PRIME / CONDITIONAL SUBCONTRACTOR ONLY**

This is an internal evidence review, not an SOQ, legal opinion, partner recommendation, customer reference, bid, submission, award, or qualification claim.

## Executive finding

TokenJunkieLabs/Commons should **not submit as prime on current evidence**. The official RFQ says a response is nonresponsive unless the firm demonstrates: (1) Microsoft partner status in good standing with a D365 F&O practice, (2) ability to operate in MWDOC's GCC Moderate tenant, and (3) two public-agency D365 F&O support references. None is evidenced for TokenJunkieLabs.

Commons does evidence deterministic synthetic regression, replay, reconciliation, explicit HOLD states, hash receipts, Power BI-shaped export-contract tests, and fail-closed connector behavior. Those are supportive engineering patterns only—not D365, GCC, governmental-accounting, public-agency, customer, or production evidence.

## Dates and source status

- Official RFQ: [PDF](https://www.mwdoc.com/wp-content/uploads/2026/08/RFQ_FIN_2026-08-01_D365_Post_Go-Live_Support.pdf); [opportunity page](https://www.mwdoc.com/opportunities/rfps-rfqs/).
- Base-RFQ questions closed August 31, 2026 at 5:00 p.m. Pacific.
- MWDOC's mass notice says the Q&A addendum is delayed until/by September 4; [internal notice receipt](https://tokenjunkielabs.slack.com/archives/C0BTURDA3PW/p1788309831051499). It was not on the official opportunity page when observed.
- SOQ: September 25, 2026 at 5:00 p.m. Pacific; electronic only, attachment under 25 MB.
- Start target: October 26, 2026.
- Addendum check: Required Content says ability to begin October 26, while Evaluation says September 21 (before SOQ submission). Do not silently choose one.

## Requirement-to-evidence matrix

| RFQ requirement | Commons/TokenJunkieLabs evidence | Readiness |
|---|---|---|
| Microsoft partner in good standing; demonstrated D365 F&O practice | None located | **GAP — prime nonresponsive** |
| GCC Moderate provisioning/operation; disclose commercial-only history | None located | **GAP — prime nonresponsive** |
| Two public-agency D365 F&O support references | Both slots empty | **GAP — prime nonresponsive** |
| D365 functional support across GL, AP, AR, cash/bank, fixed assets, budgeting, procurement | No D365 engagement evidence | **GAP** |
| Financial Reporting, Power BI, Excel/Power Query within GCC constraints | [Synthetic Power BI contract](./readiness.json), explicitly non-D365/non-live | **SUPPORTING PATTERN ONLY** |
| Administrator and end-user training; written guides; knowledge transfer | No D365 training delivery evidence | **GAP** |
| Non-production update testing, regression library, MWDOC sign-off before production | Deterministic synthetic tests and HOLD patterns exist; no D365/tenant/update evidence | **SUPPORTING PATTERN ONLY** |
| Roles, segregation of duties, licensing, provisioning/access reviews | None located | **GAP** |
| Paylocity, ACH/NACHA, Positive Pay, DMF, OData/BYOD, Power Platform automation | None located | **GAP** |
| Pacific-time support model and 2-business-hour Severity-1 response | No named bench or coverage commitment | **GAP** |
| Named staff, October 26 availability, conflicts, resumes | Not assembled/authorized | **GAP** |
| Fully burdened rates and prepaid blocks; no fixed fee/NTE | Template only; no authorized rates | **GAP** |
| Standard agreement and insurance | No executed review or certificates located | **GAP** |

## Non-deceptive prime/subcontractor structure

**Prime:** a separately verified Microsoft partner that itself demonstrates D365 F&O, GCC Moderate/PPAC unified environments, public-sector fund accounting, two qualifying public-agency references, a named functional/technical/reporting/training bench, required response coverage, insurance, and agreement acceptance.

**TokenJunkieLabs as optional narrow subcontractor:** non-production AP-to-report regression/reconciliation controls only—test-case design, deterministic replay, exception/HOLD logic, totals reconciliation, evidence receipts, and documentation—under the prime's architecture, GCC security/onboarding, change control, production authority, and MWDOC sign-off.

The prime must retain all claims and accountability for RFQ responsiveness, Microsoft status, GCC tenant work, D365 configuration/reporting/security/licensing/integrations/update operations, staffing, references, SLA, rates/prepaid blocks, insurance, conflicts, contract, signatures, submission, and production validation.

Never present Commons synthetic artifacts as D365 experience, customer work, GCC validation, production readiness, or a public-agency reference. No production access or autonomous deployment/release is proposed.

## Partner screen

| Candidate | Role | Verified mandatory gates | Score | Status |
|---|---|---:|---:|---|
| TokenJunkieLabs / Commons | Narrow subcontractor only | 0/3 | 0% | Not prime-eligible on current evidence |
| Qualified D365 F&O GCC public-sector firm (not identified) | Prime template | 0/3 | 0% | Unverified |

No external firm was researched, named, contacted, or recommended in this lane.

## Go/no-go actions

- [ ] Read and acknowledge every official addendum after publication.
- [ ] Require the prime to supply documentary proof for all three mandatory responsiveness gates.
- [ ] Apply MWDOC's answer to the already-submitted subcontractor question; do not assume subcontractor credentials cure prime eligibility.
- [ ] Name staff covering every D365 discipline and confirm October 26 availability/short-notice response.
- [ ] Obtain consent and verify two qualifying references with the required contact details.
- [ ] Authorize entity, signer, conflicts statement, rates, prepaid blocks, agreement revisions, and cover letter.
- [ ] Have broker/counsel verify applicable CGL, auto, workers compensation, professional liability, technology/cyber liability, endorsements, indemnity, confidentiality, IP, public-record, transition, and seven-year record terms.
- [ ] Keep SOQ at 10 pages excluding resumes/rates/agreement revisions; resumes at 2 pages each; PDF under 25 MB.
- [ ] Use exact subject `SOQ — MWDOC RFQ FIN. 2026-001` and confirm receipt.
- [ ] **NO-GO** if any mandatory gate, reference, authorized rate, signer, insurance/contract acceptance, or addendum acknowledgement remains unsupported.

## Package

- [Machine-readable readiness](./readiness.json)
- [Fail-closed rate template](./rate-sheet-template.csv)
- [No-login summary](./readiness.html)
