# Exeter CA RFP 2026-06 — municipal finance implementation-evidence workshare

Status: **PROPOSED_NOT_ACCEPTED**  
Commercial hypothesis: **USD 24,000 fixed**  
Reference delivery window: **12 business days after agreed input readiness**  
Operation: `EXETER-CA-2026-06-MUNICIPAL-FINANCE-ACCEPTANCE-ZSOL-20260917`

## Positioning

This is a bounded specialist subcontract for a qualified municipal-finance/ERP prime pursuing City of Exeter RFP 2026-06. It is not an ERP software proposal and does not represent TJLabs as meeting the solicitation's prime-vendor minimum qualifications.

The qualified prime retains software/product authority, California municipal references, implementation staffing, hosting/security/compliance claims, buyer communications, proposal pricing, insurance/legal terms, submission, production access, go-live decisions, award and payment authority.

## Paid workshare

### 1. Migration-generation custody and crosswalk integrity

Prime supplies frozen source/target extract-generation identities, mapping rules, approved transformations, and bounded synthetic/de-identified or otherwise authorized evidence.

TJLabs supplies:
- content-addressed source/target generation manifest;
- account/fund, vendor, customer and employee crosswalk checks;
- duplicate/conflicting-source mapping detection;
- explicit exception ledger rather than silent row loss;
- deterministic replay receipt.

Acceptance: every admitted source identity has one declared terminal mapping/disposition; contradictory mappings or unbound generations are HOLD.

### 2. GL/fund and subledger reconciliation

Buyer-scope seams covered:
- general ledger / fund accounting;
- AP and AR;
- payroll;
- utility billing;
- cashiering / cash management;
- bank reconciliation;
- financial reporting controls.

TJLabs supplies:
- integer-cent control-total comparisons;
- trial-balance and fund/control-account reconciliation;
- source/target record-count reconciliation;
- explicit, separately evidenced approved conversion deltas;
- subledger-to-GL control evidence;
- unresolved-exception ledger.

Acceptance: unexplained amount/count drift is never rounded away or converted into PASS.

### 3. Bank-reconciliation evidence

Prime defines the City-approved reconciliation model and evidence boundaries. TJLabs checks that statement-side and book-side adjustments reconcile to the same declared terminal amount, with retained evidence IDs for adjustments.

TJLabs does not move money, clear transactions, connect to a bank, certify cash balances, or substitute for City/prime accounting judgment.

### 4. Interface / integration acceptance

For every admitted interface, prime supplies source, target, contract/format and bounded evidence.

TJLabs supplies:
- interface manifest and digest;
- required-interface completeness check;
- duplicate interface-ID detection;
- verified/failed/HOLD evidence state;
- replay/duplicate-effect assertions where evidence permits.

No network call or production integration is performed by the acceptance harness.

### 5. UAT traceability

Mandatory evidence surfaces for this workshare:
- GL/fund accounting;
- AP;
- AR;
- payroll;
- cashiering;
- bank reconciliation;
- utility billing;
- financial reporting;
- integrations;
- data conversion.

TJLabs supplies stable evidence IDs and rejects caller-authored PASS states lacking retained evidence digests. Human UAT/business acceptance remains prime/City authority.

### 6. Cutover / rollback / replay

TJLabs supplies:
- source-freeze receipt check;
- rollback-evidence receipt check;
- replay-evidence receipt check;
- unresolved cutover exception gate;
- deterministic final report digest.

A READY report means only the bounded evidence packet satisfied this workshare's rules. It cannot mint go-live or buyer acceptance.

## Delivery sequence

- **Days 1–2:** source/evidence inventory, generation freeze, mappings, authority gaps.
- **Days 3–5:** control totals, AP/AR/payroll/utility/cashiering reconciliation.
- **Days 6–7:** bank/interface acceptance and hostile exception passes.
- **Days 8–9:** UAT traceability and evidence retention.
- **Days 10–11:** cutover/rollback/replay binder and rerun.
- **Day 12:** prime review, gap disposition, reproducible final evidence package.

Clock starts only after input-readiness passes. Missing/contradictory evidence produces HOLD rather than fabricated PASS.

## Commercial truth

The USD 24,000 / 12-business-day figure is a working commercial hypothesis only. It is not a contract, accepted quote, receivable or revenue. No external offer is authorized until the target relationship is independently qualified, Slack/Gmail are re-censused, and Muse selects exactly one writer/recipient/purpose generation.
