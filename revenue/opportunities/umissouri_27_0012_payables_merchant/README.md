# University of Missouri RFP 27-0012 — Payables / Merchant Finance Pursuit

Operation: `UMO-27-0012-PAYABLES-MERCHANT-WORKSHARE-ZQ2132-20260917`  
Owner/source/finalizer: **Z-Quarryline-2132 / GPT-5.6 Sol**  
Commercial state: **PARTNER-FIRST / DIRECT-PRIME HOLD / PROPOSED_NOT_ACCEPTED / $0 booked**

This carrier turns a live finance-sector procurement into a bounded specialist workshare and a deterministic reconciliation evidence package. It does **not** represent Token Junkie Labs as a bank, merchant acquirer, card issuer, PCI/SOC certifier, University bidder of record, or authorized prime.

## Live opportunity

Public procurement indexes currently identify:

- buyer: University of Missouri System;
- RFP: **27-0012 — Payables Program and Merchant Services**;
- issued: 2026-08-25;
- close: **2026-09-25 14:00 CT**;
- question cutoff: 2026-09-10 14:00 CT (already passed);
- submission route: University electronic bidding platform;
- buyer of record: Carla Gilzow;
- indexed attachments: University terms/instructions, insurance, data-protection addendum, annual transaction volume, AP spend file, merchant questionnaire, IdP questionnaire, HECVAT, Merchant Financial Proposal Template, and Payables Financial Proposal Template.

Research sources retained as links, not buyer-authoritative bytes:

- <https://www.governmentcontracts.us/government-contracts/opportunity-details/80633382558814146.htm>
- <https://app.govly.com/public/opportunities/17012722>
- <https://www.highergov.com/sl/contract-opportunity/mo-payables-program-and-merchant-services-73151679/>

The secondary public scope descriptions include merchant acquiring, commercial card/ePayables, current PeopleSoft integration, future-ERP support, reconciliation/reporting, fraud/liability controls, security questionnaires, and accessibility evidence.

**Important:** the exact current buyer packet is not retained in this carrier. `validate_manifest()` therefore emits `HOLD_BUYER_PACKET_REQUIRED`. Secondary summaries can justify research/build activity but cannot promote submission authority.

## Commercial wedge

Reference workshare, deliberately not accepted or booked:

**Payables and Merchant Reconciliation Acceptance Workshare — $18,000 fixed — PROPOSED_NOT_ACCEPTED**

Optional, separately accepted after a prime/customer decision:

**Cutover / Evidence-Pack Extension — $6,000 — PROPOSED_NOT_ACCEPTED**

A qualified prime keeps every regulated/commercial responsibility: acquiring/banking/card-network relationships, product pricing, PCI/SOC and other certifications, audited financials, buyer forms, portal access, implementation commitments, signatures, submission, and contract acceptance.

TJLabs' bounded workshare is test/evidence tooling around:

1. requirement-to-evidence mapping;
2. PeopleSoft/current-ERP and future-ERP interface acceptance;
3. merchant-ID, settlement, fee and daily-file reconciliation;
4. commercial-card / virtual-card / ePayables supplier exception handling;
5. chargeback and fraud exception evidence;
6. GL mapping and audit-chain verification;
7. security/accessibility evidence indexing without independent certification;
8. synthetic/redacted finalist-demo evidence.

No cardholder data, bank-account secrets, credentials, production ERP writes, payment mutation, or buyer data is required.

## Partner research — no winner selected

`fixtures.json` contains research-only candidates. The compiler refuses to turn public evidence into selection/contact authority.

Current evidence leads:

- **J.P. Morgan** — University public treasury material identifies JPMorgan Chase Bank in the current internet merchant-account path: <https://www.umsystem.edu/departments-staff/finance/investments-treasury/treasury/e-commerce-credit-cards>. J.P. Morgan also publicly documents commercial-card ERP/accounting file exports: <https://www.jpmorgan.com/payments/solutions/commercial-cards/program-management>.
- **Commerce Bank** — publicly exposes corporate merchant services, virtual/commercial cards, integrated payables and ERP-facing reconciliation: <https://www.commercebank.com/corporate/payments-treasury>, <https://www.commercebank.com/corporate/payments-treasury/receivables/merchant-services>, <https://www.commercebank.com/corporate/payments-treasury/payables/payment-hub>.
- **U.S. Bank** — publicly markets higher-education payables and commercial-card solutions: <https://www.usbank.com/corporate-and-commercial-banking/industry-expertise/public-sector/higher-education-payment-solutions.html>.

These links establish research leads only. RFP participation, complete merchant/payables scope, PeopleSoft/current-generation integration, certifications, commercial terms, and willingness to team remain unconfirmed unless separately evidenced.

Before **any** external partner contact: fresh Slack + Gmail collision fence, then Muse arbitration for the exact org × route × purpose. This repository cannot authorize the send.

## Deterministic finance evidence

`umissouri_27_0012.py` strictly validates JSON and emits SHA-256 receipts.

The hostile reconciliation matrix covers every terminal:

- `EVIDENCE_READY`;
- `REJECT_SENSITIVE_DATA`;
- `HOLD_MISSING_SETTLEMENT`;
- `HOLD_MERCHANT_TOTAL_MISMATCH`;
- `HOLD_GL_MAPPING`;
- `HOLD_CHARGEBACK_EXCEPTION`;
- `HOLD_PAYABLES_SUPPLIER`;
- `HOLD_FUTURE_ERP`;
- `HOLD_AUDIT_CHAIN`;
- `HOLD_STALE_EVIDENCE`.

One-cent processor/ERP mismatch is a hold. Boolean/integer aliasing, duplicate JSON keys, non-finite values, future evidence, unknown keys, duplicate case IDs, source deadline drift, commercial self-acceptance, and authority promotion are rejected.

Partner candidates receive only evidence states; even a candidate that clears public-fit + ERP evidence is merely `QUALIFIED_FOR_HUMAN_PARTNER_REVIEW`, never auto-selected.

## Authority ceiling

The compiled pursuit and evidence bundle preserve all of these as false:

- buyer / partner contact;
- submission;
- contract acceptance;
- banking;
- merchant acquiring;
- card issuance;
- payment;
- production ERP writes;
- compliance certification;
- revenue recognition.

The bundle additionally emits `HOLD_MUSE_ARBITRATION_REQUIRED` for partner outreach and `HOLD_BUYER_PACKET_REQUIRED` while exact buyer packet bytes are absent.

## Verify

From this directory:

```bash
python -m py_compile umissouri_27_0012.py test_umissouri_27_0012.py
python -m unittest -v test_umissouri_27_0012.py
python -O -m unittest -v test_umissouri_27_0012.py
```

Hosted CI repeats compile + semantic suites on Python 3.11 and 3.13. A queued, absent, cancelled, or stale workflow run is **UNKNOWN**, never green by inference.
