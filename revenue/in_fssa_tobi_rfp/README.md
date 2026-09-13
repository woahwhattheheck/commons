# Indiana FSSA Tobi RFP readiness rail

Offline evidence gate for **Indiana FSSA RFP 26-86873 / event 004100000086873**, the CMHW Case Management System (Tobi) solicitation.

This package does **not** submit a bid, contact the buyer, quote a price, or claim an award. It decides whether supplied evidence is sufficient to treat a prime or bounded-subcontract pursuit as internally ready. Missing evidence is a `HOLD`.

Controlling public board: https://www.in.gov/idoa/procurement/current-business-opportunities/

Verified public facts encoded by the gate: proposal deadline 2026-09-16 15:00 ET; four-year base plus two one-year options; cloud case-management operations/enhancement/training; bidirectional CMHW Portal/DARMHA/COREMMIS interfaces; PMA provider-management capability; phone/virtual/onsite training; Jira help desk with a 48-business-hour response target; three client references; 3% IVOSB participation goal. The controlling RFP/addenda always override this package and must be rechecked before reliance.

Run:

```bash
python -m revenue.in_fssa_tobi_rfp.cli < evidence.json
```

Decisions are `PRIME_READY`, `SUBCONTRACT_READY`, `HOLD`, and `NO_BID`.

Every receipt hard-codes `may_contact_buyer=false`, `may_submit_bid=false`, `may_quote_price=false`, and `revenue_status=UNREALIZED`; the rail is pursuit-readiness evidence, not external-action authority.

For a prime pursuit the gate requires current official-source evidence, Indiana/bidder registration evidence, two-fiscal-year financial-stability evidence, an evidence-backed 3%+ IVOSB plan, all proposal components, and three unique permission-confirmed relevant references. For a subcontract pursuit it instead requires a confirmed named prime plus a bounded technical/QA/training scope and forbids representing prime qualifications.
