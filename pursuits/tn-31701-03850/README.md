# Tennessee RFI 31701-03850 — Statewide Cashiering Response Lab

Internal pursuit carrier for Commons #15882.

**Operation:** `TN-31701-03850-CASHIERING-RFI-RESPONSE-LAB-ZETALEDGER-20260917`  
**Lead-discovery credit:** Z-Sol-Finance-17  
**Response-lab owner:** Zeta Ledger / GPT-5.6 Sol  
**State:** INTERNAL / PARTNER-FIRST / NOT SUBMITTED / $0 BOOKED

## Controlling public sources

1. Tennessee Central Procurement Office listing:
   https://www.tn.gov/generalservices/procurement/central-procurement-office--cpo-/supplier-information/request-for-proposals--rfp--opportunities1.html
2. First-party RFI packet:
   https://www.tn.gov/content/dam/tn/generalservices/documents/cpo/rfi-updates/31701-03850/RFI_31701-03850_Statewide_Edison_Cashiering_System_Final.pdf

Observed 2026-09-17. Re-read the first-party listing and packet before any external action because posted documents may be amended.

## Buyer and schedule

- Buyer: State of Tennessee, Department of Finance & Administration, Strategic Technology Solutions, Edison Resource Planning.
- RFI: **31701-03850 — Statewide Cashiering System**.
- Issued: 2026-09-11.
- Written questions/comments due: **2026-09-25 2:00 PM Central**.
- State answers scheduled: 2026-10-01.
- RFI response due: **2026-10-05 2:00 PM Central**.
- Packet names Rebekah Jenkins, IT Contract Specialist, as the communications contact.
- Only one question submission per vendor.
- RFI response is informational, is not a prerequisite to a future solicitation, creates no contract rights, and the State will not reimburse response costs.

## Submission guardrails

- Maximum 20 pages.
- English, 8.5x11 pages, minimum 12-point font, numbered pages.
- Word or PDF.
- Answer numbering must track the Technical and Cost Informational Forms.
- Embedded links that redirect to landing/static websites are prohibited in the response; necessary evidence needs to be expressed in text or otherwise packaged consistently with the packet.
- Production/state data must remain in the United States; production-data access is limited to U.S.-based resources.
- Code may be developed outside the U.S., but any testing outside the U.S. must use fake data.
- Foreign-adversary software restrictions apply.
- The State may request oral presentations.

## Commercial posture

### Do not prime from unsupported evidence

The packet asks for an existing cashiering solution and evidence that a small specialist shop must not fabricate:

- current PCI DSS v4.0.1 responsibility mapping / AOC where applicable;
- current SOC 2 Type II covering the actual solution environment;
- historical uptime and SLA evidence;
- U.S.-only production/backup/DR data;
- browser/mobile/web product behavior and accessibility;
- payment-processor integration such as Worldpay/FIS;
- Check 21 / RDC and ICL capabilities;
- cash drawers, printers, card readers, credit-card terminals and check scanners;
- broad installed cashiering functionality across 120 business requirements;
- product support, DR, maintenance and release-management evidence.

**Recommended lane:** partner-first paid workshare behind an established cashiering OEM, payments vendor, ERP integrator or public-sector SI.

### Specialist workshare we can credibly offer

1. **Edison integration acceptance** — source/target contracts, field maps, deterministic test packs, exception ledgers and replayable evidence.
2. **Cashier/batch/deposit reconciliation controls** — expected-vs-actual totals, over/short, tender-to-batch conservation, deposit traceability and unresolved-item owner review.
3. **Migration/data-quality acceptance** — bounded retained generations, completeness checks, duplicate/identity controls and source-bound outputs.
4. **Bank/settlement interface validation** — retained BAI2/camt.053/bank/merchant-settlement style fixtures and controls as synthetic demonstrations, not production certification.
5. **UAT / cutover evidence** — scenario matrix, acceptance criteria, rollback fences, parallel-run reconciliation and issue closure receipts.
6. **Audit/control design** — immutable event/evidence concepts, role/period/status controls, reason-code enforcement, exact source provenance.
7. **Reporting acceptance** — batch/detail, variance, deposit, accounting-distribution and reconciliation report contracts.
8. **AI governance boundary** — if the prime includes AI, require U.S.-only AI data, no training/sharing of State data, disablement, dependency inventory and explicit data-flow evidence.

### Existing internal demonstration assets

Use only as **synthetic engineering demonstrations** and only after re-reading current main:

- SMB #1269 — bank statement ↔ GL reconciliation desk.
- SMB #1295 — BAI2 intake/control-total validation.
- SMB #1299 — camt.053 retained-statement intake.
- SMB #1301 — merchant settlement evidence reconciliation.
- SMB #1287 — treasury access/payment-control recertification.
- SMB #1261 / merged #1281 — fixed-asset register ↔ GL reconciliation.
- Other current finance controls may be added only with exact-main verification.

These do **not** prove Tennessee acceptance, PCI/SOC compliance, processor certification, uptime, hardware support, installed statewide cashiering functionality, or production authority.

## Files in this lab

- `requirements_crosswalk.csv` — all 120 Attachment 1 requirements with a conservative response posture.
- `response_lab.md` — architecture, demo, implementation/UAT/cutover, security gap, partner workshare, pricing hypothesis, 20-page outline and go/no-go gates.
- `questions.md` — one consolidated owner-ready vendor question submission candidate. It is a draft only; no send authority.

## Authority fence

No buyer or partner outreach, no question submission, no portal action, no supplier registration, no response submission, no contract representation, no spend, no payment, and no booked revenue.

Any external message requires:
1. fresh exact recipient/purpose dedupe across Slack/Gmail;
2. fresh Muse arbitration;
3. re-read of current first-party packet and amendments;
4. owner-ready copy with unsupported claims removed.

Pricing in this lab is `PROPOSED_NOT_ACCEPTED`.
