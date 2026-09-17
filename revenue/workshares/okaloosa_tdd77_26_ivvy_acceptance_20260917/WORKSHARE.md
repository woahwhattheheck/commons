# Okaloosa TDD 77-26 — iVvy migration/integration acceptance workshare

**State:** `PROPOSED_NOT_ACCEPTED`  
**Buyer opportunity:** Okaloosa County Tourism Department RFP TDD 77-26  
**Potential prime/platform context:** iVvy — topical fit only; this packet does **not** assert iVvy is bidding, qualified, selected, or interested  
**Commercial hypothesis:** USD 35,000 fixed fee  
**Delivery target:** 15 business days after complete, approved inputs and prime/customer authorization  
**Owner:** Token Junkie Labs (TJLabs)  
**Publication state:** NOT SENT — any external publication requires a separate current Muse single-writer decision plus immediate Slack/Gmail/relationship recensus.

## 1. Purpose

This packet defines one bounded paid specialist workshare for migration, integration acceptance, cutover-readiness, and audit/security evidence associated with the current Okaloosa TDD 77-26 venue/event-management procurement.

Current public evidence establishes a plausible technical adjacency only. Public solicitation summaries describe a multi-venue/event-management SaaS requirement, buyer-named integration needs involving Workday, DocuSign, and BluePay/Bluepay, and a ten-year migration from Ungerboeck/Momentus-family source data. iVvy publicly describes cloud venue/event-management software, a broad integration ecosystem, a developer API, and migration support from Momentus. Those facts justify preparing a partner-ready technical slice; they do **not** prove that iVvy is bidding, that any named buyer integration exists natively, that iVvy satisfies the RFP, or that either iVvy or the County wants TJLabs involved.

The workshare is therefore deliberately evidence-first and prime-subordinate. A qualified prime/platform provider retains the buyer relationship, response, platform, compliance, architecture, commercial, signature, and submission authority. TJLabs supplies a reviewer-verifiable acceptance product inside a frozen slice.

## 2. Bounded work package

At kickoff, the prime/customer freezes one scope key covering:

- the exact RFP/version/addenda set controlling the slice;
- one approved legacy/source export family and migration generation;
- one approved target export/read-only evidence family;
- the closed set of buyer-named integration paths admitted to the slice;
- the closed security/audit acceptance requirement set;
- one cutover/rehearsal generation and decision owner;
- the approved evidence and data-handling boundary.

No additional system, venue, dataset, historical archive, integration, requirement, or operational responsibility is silently included.

### A. Source-export profiling and migration reconciliation

For the approved Ungerboeck/Momentus-family export evidence, TJLabs will produce a deterministic source profile and migration-reconciliation pack covering, where the supplied evidence permits:

1. object/table/file population inventory and generation identity;
2. stable record/business-key inventory and approved remapping rules;
3. field/type/requiredness profile and explicitly admitted transforms;
4. attachment/document/reference inventory where relevant;
5. duplicate, orphan, unmapped, truncated, and malformed-record findings;
6. source-to-target population and key reconciliation;
7. bounded field-level spot checks selected from a documented rule;
8. exception references for every unresolved mismatch;
9. explicit `PASS`, `HOLD`, or `NOT_TESTABLE_FROM_SUPPLIED_EVIDENCE` per acceptance rule.

Aggregate counts, screenshots, filenames, operator assurances, or a successful import job do not by themselves prove migration acceptance when the rule requires stronger evidence. A ten-year requested history does not imply that all ten years are available, clean, legally transferable, or semantically compatible; missing or contradictory source evidence remains a HOLD.

### B. Buyer-named integration contract and acceptance harnesses

For each admitted Workday, DocuSign, and BluePay/Bluepay path — or an owner-approved substitute if the final buyer packet differs — TJLabs will prepare an explicit acceptance contract before claiming integration readiness. The contract records:

- source and target system ownership;
- direction of data/control flow;
- exact admitted business objects and identifiers;
- schema or semantic field contract;
- authentication/secret custody boundary without copying credentials into this repository;
- allowed test environment and data class;
- correlation/idempotency identity;
- retry/duplicate/reversal behavior where applicable;
- ordering and clock/timezone assumptions that materially affect outcomes;
- expected positive and negative-path behavior;
- reconciliation and exception evidence requirements;
- owner-controlled actions required for a conclusive result.

The public iVvy API and integration catalog establish extensibility adjacency only. They are **not** evidence that native Workday, DocuSign, or BluePay connectors exist or satisfy TDD 77-26. The acceptance harness validates the integration pattern actually selected and evidenced by the prime/customer; it does not invent one.

No destructive production replay is authorized by this workshare.

### C. Cutover rehearsal, drift, and rollback/readiness evidence

For one owner-approved rehearsal generation, TJLabs will produce:

- frozen source/target/evidence generation identifiers;
- pre-cutover dependency and owner checklist;
- rehearsal sequence and observable checkpoints;
- migration/integration reconciliation thresholds supplied or approved by the owner;
- source/target drift detection between rehearsal and final generation;
- explicit abort/HOLD triggers;
- retry/re-run evidence rules;
- rollback prerequisites and owner-controlled rollback decision points;
- post-rehearsal exception ledger;
- go/no-go evidence summary separating proven facts from owner assertions.

TJLabs will not invent RTO/RPO, outage windows, rollback guarantees, data-loss tolerances, or final go-live authority. If those requirements are material, they must come from the buyer/prime-approved source set.

### D. Security/audit acceptance evidence and exception ledger

For the closed security/audit requirement set, TJLabs will map each admitted requirement to retained evidence or an explicit HOLD. Evidence classes may include owner-supplied configuration exports, access/role evidence, audit-event samples, API/security documentation, redacted logs, transfer-path evidence, retention/backup evidence, or owner-run test outputs.

Every unresolved finding records at minimum:

- stable exception id;
- requirement/system/migration/integration reference;
- evidence references;
- observed result and expected result;
- severity/disposition supplied or approved by the owner;
- responsible owner and next action;
- closure-evidence requirement;
- state: `OPEN`, `HOLD`, `RETEST_READY`, or `CLOSED_WITH_EVIDENCE`.

This is acceptance evidence, not an independent SOC, PCI, legal, privacy, cybersecurity, or regulatory certification. Missing evidence never becomes a PASS because a deadline arrives.

### E. Reviewer-verifiable final acceptance pack

The final work product contains:

1. frozen scope and source/version manifest;
2. evidence/digest inventory for retained bytes;
3. migration source profile and reconciliation results;
4. integration-contract/acceptance matrices;
5. cutover/rehearsal and rollback-readiness evidence;
6. security/audit requirements-to-evidence matrix;
7. exception/HOLD ledger;
8. approved retest/closure evidence;
9. residual blocker/risk list;
10. concise handoff stating what is proven, what is owner-asserted, and what remains unproven.

## 3. Required inputs

The 15-business-day target begins only after the designated owner confirms a complete approved input set. Expected inputs are:

- current official TDD 77-26 packet and all controlling addenda supplied or authenticated by the prime/customer;
- exact response/acceptance requirements relevant to the TJLabs slice;
- prime/platform architecture and the actual selected approach for each buyer-named integration;
- approved legacy export samples/data dictionary and source-generation identity;
- approved target export or read-only evidence;
- approved integration specifications, sandbox fixtures, or owner-run replay outputs;
- security/audit requirements and acceptable evidence classes;
- cutover/rehearsal window, owner-provided thresholds, and decision owners;
- data-handling, redaction, transfer, environment, and retention constraints;
- owner-approved severity/disposition vocabulary and named reviewers.

If a required input is unavailable or contradictory, the affected conclusion remains a HOLD and the pack identifies the exact missing owner-controlled evidence or decision.

## 4. Data and environment boundary

Default delivery posture:

- no production credentials or standing privileged account;
- no production mutation, deployment, or direct database write;
- no County portal or procurement-account action;
- no end-customer submission, signature, certification, or representation;
- no independent platform-selection or final architecture decision;
- no handling of secrets in repository artifacts;
- synthetic, redacted, owner-approved exports, sandbox fixtures, logs, screenshots, or read-only evidence wherever sufficient;
- no independent legal, privacy, PCI, SOC, regulatory, or security-compliance certification;
- no need for attendee/customer/person identity when stable opaque identifiers are sufficient.

If regulated, payment, identity, or other sensitive data is unavoidable, work on that material does not begin until the owner supplies the governing terms and approved transfer/access path.

## 5. Responsibility split

### iVvy / qualified prime / County retains

- bidder/prime qualification and buyer relationship;
- County forms, certifications, references, attestations, insurance/licensing, and addenda compliance;
- platform licensing and platform feature commitments;
- final architecture and exact integration implementation choice;
- customer-specific security/compliance representations;
- production access, configuration, deployment, cutover, rollback, and go-live authority;
- migration source authorization and data-transfer approval;
- user training and ongoing support commitments;
- final customer pricing and commercial terms;
- proposal signatures and procurement submission authority;
- final acceptance, risk acceptance, and release decision.

### TJLabs owns inside the frozen slice

- migration source profiling and deterministic reconciliation rules;
- requirements/evidence traceability;
- integration acceptance-contract and evidence harness design;
- approved replay/reconciliation evidence analysis;
- cutover/rehearsal readiness evidence structure;
- security/audit acceptance evidence mapping;
- exception/HOLD ledger maintenance;
- reviewer-verifiable acceptance-pack assembly;
- concise handoff separating proven, owner-asserted, and unresolved claims.

## 6. Acceptance criteria

The fixed-fee work package is delivery-complete only when all of the following are true:

1. **Controlling sources frozen:** exact buyer packet/addenda and prime-approved source identities for the slice are recorded.
2. **Scope frozen:** migration generation, target evidence family, integration set, security/audit requirement set, and rehearsal generation are enumerated.
3. **Evidence inventory complete:** each material conclusion has stable evidence references; retained bytes are digested where byte custody exists.
4. **Migration reconciliation complete:** every agreed migration rule has `PASS`, `HOLD`, or `NOT_TESTABLE_FROM_SUPPLIED_EVIDENCE` with traceable evidence.
5. **Integration contracts complete:** every admitted path has an explicit contract and either acceptance evidence or an owner-visible HOLD.
6. **No connector inference:** public iVvy extensibility is never substituted for evidence of a native or compliant Workday, DocuSign, or BluePay integration.
7. **Cutover evidence complete:** rehearsal checkpoints, drift, abort/HOLD triggers, rollback prerequisites, and residual blockers are explicit.
8. **Security/audit traceability complete:** each admitted requirement maps to retained evidence or an explicit HOLD without TJLabs self-certification.
9. **Exceptions explicit:** every finding is closed with evidence or remains visible; nothing is silently waived.
10. **Authority truth preserved:** the pack does not represent TJLabs as bidder, platform authority, buyer, final architect, compliance certifier, signatory, submitter, production operator, or commercial acceptance authority.

A packet may be delivery-complete while still containing owner-controlled HOLDs. Delivery completion means the bounded evidence product is complete and truthful, not that every buyer/prime condition has been cleared.

## 7. Schedule

Target delivery is 15 business days after complete approved inputs:

- days 1–2: controlling-source verification, input inventory, scope freeze, traceability skeleton;
- days 3–6: migration source profiling and first reconciliation pass;
- days 5–9: integration-contract/harness evidence pass;
- days 8–11: rehearsal/cutover and security/audit evidence mapping;
- days 10–13: exception triage, owner questions, approved reruns/retests;
- days 14–15: final pack assembly, traceability audit, reviewer handoff.

Owner-caused access delays, changing buyer requirements, new integrations, materially different source generations, or additional venues/datasets pause affected acceptance items and may require a separately approved scope change.

## 8. Commercial assumptions

Commercial hypothesis: **USD 35,000 fixed / 15 business days / PROPOSED_NOT_ACCEPTED**.

The fixed fee assumes:

- one TDD 77-26 specialist acceptance slice;
- one closed legacy source/export family and one approved target evidence family;
- the closed buyer-named Workday, DocuSign, and BluePay/Bluepay integration set, subject to confirmation against the current official packet;
- one owner-approved cutover rehearsal generation;
- one closed security/audit acceptance requirement set;
- owner-provided approved inputs and owner-controlled environment actions;
- no production operations, travel, platform licensing, infrastructure spend, or County procurement response authored/signed by TJLabs;
- no unbounded historical-data remediation or bespoke middleware implementation program;
- no independent certification, penetration test, or ongoing support obligation.

Material expansion requires an explicit written scope change before work is represented as included.

## 9. Out of scope

Unless separately agreed, this workshare excludes:

- serving as prime or bidder;
- full TDD 77-26 response production or submission;
- platform replacement or platform feature development;
- licensing/procurement of iVvy or third-party systems;
- enterprise middleware implementation beyond the bounded acceptance slice;
- production deployment, cutover execution, or rollback execution;
- exhaustive ten-year data cleansing/remediation;
- end-user training delivery or long-term support;
- SOC/PCI/legal/privacy/regulatory certification;
- penetration testing or broad performance/load testing;
- customer pricing, contracting, award, invoicing, collection, or accounting activity.

## 10. Kickoff decisions

A productive scoping discussion can be reduced to eight decisions:

1. What exact official TDD 77-26 packet/addenda control this slice?
2. What legacy export generation and target evidence family are admitted?
3. What data classes and historical ranges are actually available and authorized?
4. What exact integration implementation is selected for each buyer-named external system?
5. What security/audit requirements and evidence classes govern acceptance?
6. What rehearsal/cutover generation, thresholds, and owner decision points apply?
7. Who owns ambiguity, severity, architecture, compliance, and final acceptance decisions?
8. What owner-controlled evidence/actions must occur for a HOLD to clear?

## 11. Public-source provenance used for fit qualification

Current public sources used only to establish topical fit are recorded in `source_ledger.json`. They include a public solicitation summary for TDD 77-26 plus iVvy product, integration, developer-API, and migration materials.

The public-source boundary is intentionally narrow: a secondary solicitation summary is not a substitute for the official current packet/addenda, and iVvy marketing/developer materials are not proof of buyer-specific connector availability, bidder qualification, RFP compliance, interest, or acceptance.

## 12. Authority / truth ledger

At repository publication:

- `external_send_authorized = false`
- `muse_selected = false`
- `ivvy_interest_known = false`
- `ivvy_bid_intent_known = false`
- `ivvy_qualified_for_rfp = false`
- `prime_relationship_exists = false`
- `proposal_delivered = false`
- `proposal_accepted = false`
- `contract_exists = false`
- `work_authorized = false`
- `submission_authorized = false`
- `county_submission_made = false`
- `invoice_exists = false`
- `payment_received = false`
- `receivable_exists = false`
- `booked_revenue = false`
- `recognized_revenue = false`

A repository merge is product/readiness evidence only. It is not a bid, buyer submission, partner acceptance, contract, receivable, payment, or revenue event.
