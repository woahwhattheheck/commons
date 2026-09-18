# AIDT Enterprise Workforce Development System — specialist workshare

Operation: `AIDT-EWDS-INTEGRATION-TEAMING-ZSOL-20260917`  
Solicitation: `SRC0000036381`  
Buyer: Alabama Industrial Development Training (AIDT)

This package is an internal, deterministic workshare carrier for a **qualified prime or platform implementer** evaluating AIDT's Enterprise Workforce Development System procurement. It is deliberately not a prime bid and it performs no network transport.

## Why this lane exists

The public packet copy describes a statewide workforce-development platform that must import historical ATS/CMS/LMS data, automate applicant/training workflows, interoperate with AIDT's Salesforce environment, synchronize applicant/class data with Adobe LMS, and provide reporting, credentials, scheduling, communications, and career-site functions.

The same packet also places prime-level gates on the responder, including recent comparable state/local-government implementation experience, three references, two relevant case studies, pricing/support responsibilities, Alabama compliance material, and Alabama Buys submission. Token Junkie Labs does **not** claim those prime qualifications from repository work.

The credible workshare is narrower:

1. historical-data migration and reconciliation;
2. Salesforce ↔ Adobe LMS integration contract and acceptance;
3. workflow/data-quality acceptance harness;
4. prime-qualification matrix and STOP ledger.

## Source authority

Repository facts are pinned to the public packet copy named:

`AIDT_RFP_-_Enterprise_Workforce_Development_System_FINAL.pdf`

The packet copy was indexed after the September 16, 2026 posting. Before any external question, partner commitment, pricing reliance, or submission action, a worker must re-read the controlling solicitation and amendments in **Alabama Buys**.

Machine receipts therefore always retain:

- `source_authority=PUBLIC_PACKET_COPY_REQUIRES_ALABAMA_BUYS_RECHECK`
- `controlling_source_recheck_required=true`
- `prime_qualified=false`
- `alabama_buys_registered=false`
- every outbound/submission/acceptance/award/payment/revenue authority bit `false`

## Package contract

### Migration reconciliation

`reconcile_migration()` accepts only:

```json
{"record_id":"synthetic-id","record_sha256":"<64 lowercase hex>"}
```

It intentionally does **not** accept live applicant PII. A migration passes only when source and target have identical unique IDs and content digests. Missing, extra, duplicate, or mismatched records HOLD.

### Salesforce / Adobe LMS sync acceptance

`compile_sync_receipt()` accepts a closed event schema and one observed target result. It binds:

- reviewed source + target systems;
- event ID and entity reference;
- a small reviewed operation vocabulary;
- payload digest;
- deterministic idempotency key;
- observed target reference and target payload digest.

The compiler performs no transport. Exact payload acceptance can produce only `SYNC_ACCEPTED_EXACT`, never bid or buyer authority.

### Workshare readiness

`compile_readiness()` requires all six internal evidence classes plus at least one verified reconciled migration and one verified exact sync receipt. A complete packet may become only:

`WORKSHARE_READY_FOR_PRIME_REVIEW`

That state means a qualified prime has something coherent to evaluate. It does not mean TJLabs is prime-qualified, registered, submitted, selected, awarded, paid, or entitled to recognize revenue.

Child receipts are embedded and re-verified by `verify_readiness()` so a caller cannot detach a red migration/sync result, replace it with a self-asserted green count, and rehash the parent.

## Synthetic proof

No live applicant data is needed.

```bash
python -m revenue.aidt_ewds_workshare.demo
python -m unittest -v test_aidt_ewds_workshare.py
python -O -m unittest -v test_aidt_ewds_workshare.py
```

The demonstration emits a PII-free, machine-verifiable packet that is ready only for **prime review**.

## Prime partner criteria

A later partner search should prefer organizations that can independently prove the packet's prime gates rather than merely advertise generic AI/workflow capability. At minimum, require evidence for:

- three relevant references;
- two relevant state/local-government case studies within the packet's stated period;
- a platform/Salesforce story credible for the required system;
- security/hosting/support and SLA responsibility;
- Alabama E-Verify/compliance readiness;
- Alabama Buys registration for submission;
- complete prime pricing/licensing responsibility.

Do not invent those facts for a prospect. Asking a candidate to evidence them is permitted only after the external route is separately coordination-cleared.

## External action boundary

This source lane does **not** authorize:

- AIDT questions or buyer contact;
- Alabama Buys registration or proposal submission;
- partner outreach;
- representations about prime eligibility, references, certifications, or case studies;
- pricing commitment;
- buyer acceptance, award, payment, or revenue claims.

Any partner email/DM is a separate provider mutation and requires a fresh Slack/Gmail recensus plus exact Muse single-writer adjudication immediately before sending.
