# Proposed specialist workshare — internal commercial hypothesis

**Status:** `PROPOSED_NOT_ACCEPTED`  
**Working fixed fee:** **$18,000**  
**Buyer price:** UNKNOWN / not set here  
**Prime:** UNSELECTED  
**Customer data:** NOT AUTHORIZED

This is a bounded subcontract/workshare hypothesis for a qualified ERP prime. It is not a County offer and is not permission to present TokenJunkieLabs as a software vendor, system integrator of record, public-sector ERP reference holder, or bidder.

## Deliverable 1 — conversion reconciliation pack

**Objective:** make migration completeness and exceptions inspectable instead of relying on a single “load succeeded” indicator.

Prime supplies the authorized mapping/rules and approved data extracts or synthetic fixtures. TJLabs produces:

- source-to-target entity/field/control mapping ledger;
- per-generation input/output row and key counts;
- deterministic content/hash receipts where appropriate;
- transformation-rule references and unresolved-assumption register;
- duplicate, orphan, truncation, invalid-value and unmapped-record exceptions;
- rerun/replay evidence proving the same generation does not silently double-apply state;
- reconciliation summary that separates PASS, EXCEPTION_ACCEPTED_BY_PRIME, and HOLD.

**Acceptance target:** every in-scope source record is accounted for exactly once as migrated, explicitly excluded by prime-owned rule, or held with a reason. No unexplained row loss; no silently accepted duplicate logical IDs.

## Deliverable 2 — approval / segregation-of-duties acceptance pack

**Objective:** prove the implemented role/action model behaves as the prime and County specify.

Historical Douglas County audits make purchase-order create/approve separation a useful test hypothesis, but the current RFP/configuration authority must come from the retained packet and prime/County-approved design.

TJLabs produces synthetic-role fixtures and traces for:

- creator attempts to approve own transaction;
- distinct approver approval;
- supervisor / emergency / delegated overrides if the approved design permits them;
- expired/deactivated user;
- cross-department action;
- duplicate approval request;
- amount/threshold boundary cases supplied by the approved design;
- role change between creation and approval;
- audit-trail presence and reason attribution.

**Acceptance target:** every synthetic case resolves exactly as the approved role/control matrix says, with traceable actor, action, result and reason. A control failure stays FAIL; it is never normalized away as a migration exception.

## Deliverable 3 — integration evidence matrix

For each prime-approved interface, bind:

- system owner and technical owner;
- source and target;
- transport/API/file contract generation;
- identity/authorization assumptions;
- record/event identity;
- ordering and duplicate semantics;
- retry policy and unknown-outcome behavior;
- expected reconciliation artifact;
- monitoring/alert evidence;
- cutover dependency;
- rollback/replay implications;
- open gaps.

**Acceptance target:** no production interface is marked READY while owner, contract, failure handling, or reconciliation evidence is unknown.

## Deliverable 4 — cutover / rollback / replay assurance

TJLabs converts the prime's runbook into an evidence ledger containing:

- entry criteria and approval owners;
- data freeze / extraction generation;
- configuration/version identifiers;
- migration/integration checkpoints;
- business reconciliation checkpoints;
- stop/rollback criteria;
- unknown-outcome handling;
- replay idempotency checks;
- post-cutover reconciliation;
- exception ownership and closure evidence.

**Acceptance target:** each checkpoint has a named owner, objective evidence, PASS/HOLD/FAIL state and rollback consequence. Missing evidence cannot produce READY.

## Deliverable 5 — acceptance evidence binder

A prime-owned handoff package that connects:

`buyer/prime criterion -> implementation artifact -> verification receipt -> exception -> owner -> disposition`.

The binder can include conversion, role/control, integration and cutover receipts. It must preserve the difference between:

- TJLabs technical verification;
- prime representation;
- County review/acceptance.

TJLabs never records a County acceptance decision unless the prime supplies buyer-authoritative evidence of that decision.

## Explicit exclusions

Unless a later written agreement changes them, the proposed $18,000 workshare excludes:

- ERP licenses, hosting or product support;
- product configuration ownership;
- project/program management for the overall implementation;
- buyer communications and procurement administration;
- bidder registrations, certifications, insurance or bonding;
- prime references/past-performance claims;
- cybersecurity/compliance attestations owned by the product/prime;
- production access to County PII, payroll, HR or financial data;
- legal, tax, accounting or procurement advice;
- final buyer pricing, contract negotiation, signatures or submission;
- County acceptance authority.

## Responsibility split

### ERP prime owns

Product/implementation solution, bidder eligibility, staffing, public-sector references, County relationship, all buyer representations, official configuration decisions, real-data authorization, implementation schedule, product/integration claims, security/compliance attestations, proposal pricing/submission, signatures, contract and acceptance authority.

### TokenJunkieLabs owns only if contracted

The bounded evidence/reconciliation work above, using prime-authorized sources and explicit rules, with unknowns and exceptions preserved.

## Commercial release gate

No proposal to a prime is sent until:

1. exact RFP/addenda are retained and screened;
2. teaming/subcontract route is actually permitted;
3. selected prime evidence satisfies mandatory gates;
4. selected prime is plausibly pursuing this exact solicitation;
5. opportunity + recipient collision census is fresh;
6. the exact outbound has current designated single-writer authorization.

Until then: `PROPOSED_NOT_ACCEPTED / $0_BOOKED / $0_CASH`.
