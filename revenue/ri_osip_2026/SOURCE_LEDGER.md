# Source ledger - Rhode Island OSIP 2026

## Controlling buyer source

- Buyer: Rhode Island Office of the General Treasurer / State Investment Commission.
- Document: `REQUEST FOR PROPOSAL FOR INVESTMENT MANAGEMENT, RECORDKEEPING, OPERATIONAL AND ADMINISTRATIVE SERVICES FOR THE OCEAN STATE INVESTMENT POOL (OSIP)`.
- Official URL: https://treasury.ri.gov/media/2171/download?language=en
- RFP issued: 2026-09-15.
- Questions due: 2026-09-25, 4:00 PM Eastern.
- Proposals due: 2026-10-20, 4:00 PM Eastern.
- Observed during build: 2026-09-17.

This build parsed the buyer-hosted issued RFP through the available public retrieval surface. It did **not** successfully retain/download the exact PDF bytes into the build container, so `candidate_prime.example.json` correctly marks the RFP row `METADATA_ONLY`; its SHA-256 is a fixture identity, **not** a hash of the buyer PDF.

## Buyer-first-party facts used as source literals

### Prime minimums

- >= 5 years in business as an investment-management organization managing institutional assets in the subject or similar strategy.
- authorized to conduct investment-management services in Rhode Island;
- ability to accommodate transactions through 3:00 PM ET for same-day credit;
- directly involved investment professionals with >= 5 years relevant experience;
- >= $5 billion institutional AUM in the subject/similar strategy;
- >= 1 institutional public client in the subject/similar strategy;
- equal-opportunity employer.

### Scope relevant to a specialist workshare

- participant-level books, accounts and transaction histories;
- participant earnings calculation/allocation;
- fund accounting and reconciliation;
- participant and Treasury reporting;
- records sufficient for Rhode Island statutory reporting;
- audit data/support and auditor/custodian coordination;
- participant contributions/withdrawals, confirmations and backup transaction methods;
- information security, internal controls, business continuity and disaster recovery;
- custom/ad-hoc reporting and data extracts.

### Evaluation

- Investment Management: 25 points.
- Administration and Operations: 25 points.
- Organization and Experience: 20 points.
- Participant Services, Marketing, and Distribution: 15 points.
- Fees: 15 points.

### Subcontracting signal

The questionnaire asks the respondent to identify and describe subcontractors intended for aspects of fund administration and separately asks about outsourced/subcontracted custodial services. That supports investigating a specialist workshare; it does **not** by itself prove a subcontract award, prime interest, or acceptance of TokenJunkieLabs.

## Contact boundary

The RFP identifies `Cash_RFPs@treasury.ri.gov` as the sole point of contact and prohibits procurement-related contact with other Treasurer/State personnel. No buyer contact occurred from this build.
