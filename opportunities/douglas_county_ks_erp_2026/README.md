# Douglas County, Kansas ERP — specialist acceptance workshare

**Opportunity:** Douglas County, Kansas RFP-2026-0012 — Enterprise Resource Planning (ERP) System  
**Internal operation:** `DOUGLAS-KS-ERP-ACCEPTANCE-SOLZ-20260917`  
**Current state:** `PARTNER_FIRST / PRIME_UNSELECTED / CONTROLLING_PACKET_HOLD / OUTBOUND_HOLD / PROPOSED_NOT_ACCEPTED / $0_BOOKED / $0_CASH`

This directory is an internal pursuit carrier. It is not a bid, a representation that TokenJunkieLabs is an ERP prime, a County submission, or authority to contact a buyer or partner.

## Current source truth

Douglas County's first-party Purchasing page says the County publishes public RFPs/RFBs and accepts electronic bid submissions through bids&tenders, with vendor registration required for submission:

- https://www.dgcoks.gov/administration/purchasing
- indexed tender route: https://douglascountyks.bidsandtenders.net/Module/Tenders/en/Tender/Detail/75e76acb-87a3-4199-9fae-d5736d38e590

A current public index for the exact tender reports RFP-2026-0012 was posted 2026-09-15, questions are due 2026-09-30, and proposals are due 2026-10-20 at 2:00 PM Central. It describes a modern integrated ERP replacing legacy finance, HR, payroll, procurement, and administrative systems, including implementation services and ongoing support.

**The exact controlling RFP packet and addenda are not retained in this carrier.** Indexed facts help identify the opportunity; they do not establish bidder qualifications, teaming permission, insurance, references, evaluation, price instructions, forms, integrations, data volumes, security terms, or final submission mechanics.

## Why this is commercially interesting

Douglas County's historical first-party audit reports repeatedly documented a segregation-of-duties weakness in the incumbent ERP: in some small departments the same person could enter and approve purchase orders, and auditors recommended separating entry and approval functions.

Examples:

- https://www.dgcoks.gov/sites/default/files/2024-07/FS%2021%20Final.pdf
- https://www.dgcoks.gov/sites/default/files/2023-08/2021-single-audit.pdf

That history does **not** prove the 2026 RFP scores segregation of duties. It does make a technically specific specialist seam credible: conversion and configuration acceptance should prove approval authority, auditability, reconciliation, and exception handling instead of merely asserting that a migration completed.

## Proposed specialist seam

Working commercial hypothesis: **$18,000 fixed / PROPOSED_NOT_ACCEPTED**, contingent on a qualified ERP prime, controlling-packet compatibility, and an agreed work order.

1. Legacy conversion reconciliation.
2. Approval / segregation-of-duties acceptance on synthetic or prime-authorized evidence.
3. Integration evidence matrix and failure/retry reconciliation.
4. Cutover / rollback / replay assurance.
5. Prime-owned acceptance evidence binder.

See `paid_workshare.md` and `acceptance_plan.md`.

## Required order of operations

1. Recover and hash the exact current RFP packet plus all addenda from the County portal.
2. Bind every mandatory bidder/subcontract/team/evaluation/submission requirement in `qualification_matrix.md`.
3. Select a real ERP prime candidate only from evidence that it can satisfy the solicitation.
4. Establish whether subcontracting/teaming is permitted and how it must be disclosed.
5. Re-run connected-source collision checks for the exact opportunity and selected recipient.
6. Obtain a fresh designated single-writer authorization for the exact proposed outbound.
7. Only that current authorization can release one external message.

Unknowns remain HOLD. A deadline alone never authorizes acceleration around missing eligibility evidence.

## Authority ceiling

Allowed here: public-source recovery, internal qualification, internal scope/pricing hypothesis, code/docs/tests, coordination, PR/review/merge.

Not authorized here: County questions/contact, portal registration/terms acceptance, proposal submission, signatures, bidder or qualification claims, references/certifications/insurance assertions, final buyer pricing, customer-data access, spend, contract acceptance, award, payment, cash, or revenue recognition.
