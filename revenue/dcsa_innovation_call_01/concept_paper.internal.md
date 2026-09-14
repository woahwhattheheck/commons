# Mission Access Fabric — Unified Application Access and Integration Prototype

> INTERNAL WORKING DRAFT — NOT AUTHORIZED FOR EXTERNAL CONTACT OR SUBMISSION. Current qualification state: HOLD.

Qualification operation: `DCSA-INNOVATION-CALL-01-20260914`  
Source generation: `df3af195338f8a5abdb70a12f5deab8bec4076796f53db105607facd1558877c`  
Concept-paper deadline: `2026-09-18T13:00:00Z`

## 1. Problem Understanding

DCSA's personnel-vetting, industrial-security, counterintelligence, and insider-threat missions depend on multiple applications with separate navigation, authentication patterns, user experiences, and sustainment seams. The modernization problem is therefore not a portal-only redesign. It is a continuity-constrained integration program: existing Individual Engagement applications must remain operational while workflows, identity context, interfaces, security evidence, and user experience are incrementally unified.

The decision-quality objective is to prove that a modular application layer can provide a common entry point without transferring hidden coupling into a new monolith. The prototype must expose where identity, business rules, data ownership, application responsibilities, and operational support boundaries live. It must also produce evidence that DCSA can onboard additional applications through repeatable contracts rather than one-off rewrites.

The pursuit remains on HOLD. The architecture below is reusable technical preparation, not a representation that the organization possesses required clearances, staffing, eligibility, past performance, price approval, or submission authority.

## 2. Proposed Concept and Vision

The concept is a **Mission Access Fabric**: a thin, modular experience and policy layer over existing mission applications. A common shell presents role-appropriate work, alerts, status, and navigation. A policy decision service evaluates user, role, attribute, resource, and mission context. Identity-provider adapters normalize approved authentication and MFA assertions without replacing Government identity authorities. Workflow and application adapters route each transaction to the system that remains authoritative for that function.

The design follows a strangler and hub-and-spoke pattern. Legacy applications continue to perform assigned work while the common shell progressively absorbs navigation, cross-application context, and reusable workflow coordination. Every onboarding increment has a rollback boundary, a continuity canary, and an observable contract. No migration step depends on a wholesale cutover.

Strategic value comes from converting each prototype phase into reusable assets: interface contracts, policy mappings, onboarding checklists, synthetic and Government-provided test suites, operational dashboards, issue-disposition evidence, and production-transition estimates. Those assets reduce the cost and risk of later application onboarding even when the underlying systems differ.

## 3. High-Level Technical Approach

**Experience shell and workflow continuity.** A component-based web shell provides common navigation, assigned-work views, alerts, announcements, and deep links. Route decisions are explicit and observable. A continuity canary exercises representative legacy and integrated paths before and after every release. User-context transfer occurs only through approved, scoped tokens and contracts; failure falls back visibly to the existing application rather than producing silent partial success.

**Identity, credential, and access management.** Identity adapters support multiple approved providers and MFA patterns, including CAC/PIV and ECA where required. The shell does not mint identity. It consumes signed provider assertions, maps them into a canonical subject/context envelope, and submits authorization questions to a policy decision layer. Least privilege, attribute-aware decisions, session boundaries, step-up requirements, and denial reasons are testable artifacts.

**Integration plane.** API adapters provide synchronous request/response integration where appropriate; event adapters provide durable asynchronous integration and decouple workflow timing. Each adapter declares owner system, schema version, idempotency key, timeout, retry ceiling, ambiguity behavior, audit fields, and rollback route. Business rules remain outside presentation components and are retained with their authoritative service or an explicitly governed rules component.

**Sustainment and transition.** During Phase 1, the performer establishes an application and interface inventory, known-issue baseline, release calendar, operational risk register, and transition-of-responsibility plan for the identified IE applications. The prototype backlog is sequenced around mission continuity, not visual novelty. Existing incident, patch, release, and authorization obligations remain visible beside modernization work.

**DevSecOps and infrastructure as code.** Environments, policies, observability, deployment gates, and rollback procedures are versioned. Builds are reproducible; promoted artifacts are content-addressed; deployment evidence binds exact source, configuration, test, scan, approval, and environment generations. Pipeline success cannot substitute for Government authorization or operational acceptance.

**Security authorization.** The authorization package evolves from the first phase. Control implementation evidence, data flows, boundary diagrams, inventories, scan findings, POA&M/remediation status, test evidence, and decision records are produced as the system changes. The prototype cannot claim success while ATO-critical evidence remains deferred to the end.

**Acceptance evidence.** Phase gates use executable and reviewable evidence: workflow continuity, GAT, UAT, regression, integration, performance, reliability, accessibility, and security results; disposition of defects and findings; and exact production-transition assumptions. Evidence distinguishes observed results from planned work and from owner decisions.

Declared capability set:

- `mission_workflow_discovery`
- `unified_experience_shell`
- `multi_idp_icam`
- `policy_attribute_access`
- `api_event_integration`
- `legacy_ie_sustainment`
- `devsecops_iac`
- `security_authorization_ato`
- `test_acceptance_evidence`
- `production_transition_rom`

## 4. Intellectual Property and Data Rights

This draft assumes Government ownership and control of Government data and does not authorize using enterprise data to train, evaluate, or enhance external commercial foundation models or proprietary algorithms. Data remains inside approved environments and approved processing boundaries. Any AI-assisted feature must identify its model, data path, retention behavior, evaluation method, human authority, failure mode, and rollback path before use.

Background intellectual property asserted for owner review:

- Deterministic evidence compilation and replay patterns, subject to owner rights review
- Fail-visible integration and workflow verification patterns, subject to owner rights review

Third-party dependencies requiring separate license, security, data-rights, and continuity review:

- Existing IE application APIs, data dictionaries, business rules, and sustainment artifacts
- Government-approved identity providers and MFA services
- Government-provided AWS GovCloud environments and operational toolchain

Foreground interface contracts, configuration, test artifacts, onboarding patterns, and deployment evidence should be delivered in forms that support Government operation and follow-on competition. Final rights assertions and markings require counsel and owner approval; this working draft makes no legal conclusion.

## 5. Risk and Opportunity Spotlight

The primary program risk is assuming that a common interface removes integration and sustainment complexity. It can instead hide incompatible identity semantics, duplicated business rules, ambiguous ownership, and silent fallback behavior. The mitigation is evidence-first onboarding: each application integration begins with authority maps, workflow traces, failure contracts, continuity canaries, and a reversible cutover plan.

A second risk is an over-ambitious sustainment transition during the first 30 days. The transition plan must identify exact applications, repositories, pipelines, environments, unresolved incidents, release obligations, access dependencies, and staffing assumptions. Unknowns remain explicit HOLDs rather than being buried in schedule contingency.

A major opportunity is to make onboarding itself a product of the prototype. A standard adapter contract, policy-mapping workbook, test harness, observability pack, and authorization-evidence checklist can turn later application integration into a repeatable bounded process.

Candidate risk register:

- A portal-only implementation could hide rather than remove integration and workflow discontinuities
- ATO evidence deferred to Phase 4 would create a late authorization failure
- Active Top Secret Facility Clearance and personnel clearance evidence is not retained in this repository
- Identity and role semantics may differ across IE applications and cannot be normalized by presentation-layer assumptions
- The first-30-day sustainment transition can dominate prototype risk if application and operational custody is incomplete

Questions drafted for owner review only; no transmission is authorized:

- Does the active Top Secret Facility Clearance requirement apply only to the prime performer, or must every significant subcontractor possess an FCL at Solution Concept Paper submission?
- What Government decision criteria distinguish a successful common-entry prototype from a portal that only deep-links to existing applications?
- What ROM granularity and cost-share treatment does DCSA expect by phase in the six-page Concept Paper?
- What exact source repositories, pipelines, environment inventories, unresolved incident backlogs, and authorization artifacts will be available for the required first-30-day IE sustainment transition?
- Which applications and forms are authoritative for PVQ and required-form scope in Phase 3, and what user-context continuity is permitted across those boundaries?
- Which identity providers and assertion protocols are in the approved baseline, and which CAC/PIV, ECA, and other MFA flows must be demonstrated during Phase 2?

## 6. Rough Order of Magnitude

ROM state: **OWNER_DECISION_REQUIRED**.

No price, cost share, staffing commitment, or schedule commitment is invented in this draft. A submission-quality ROM requires the controlling template and call bytes, a validated participation route, cleared-prime/workshare structure if applicable, staffing and sustainment assumptions, Government-furnished environment assumptions, phase acceptance criteria, data-rights treatment, and owner-approved risk reserve.

The ROM should be organized by the four prototype phases and should separately identify: sustainment transition and operations; discovery and user research; common shell and ICAM/policy integration; application adapters and onboarding; DevSecOps/IaC; testing and accessibility; security authorization and remediation; program management; travel/site activity; and production-transition planning. Any cost-share representation must be bound to the selected OTA eligibility path and owner authority.

---

**Authority ceiling:** this artifact authorizes no email, Q&A submission, concept-paper submission, signature, clearance representation, personnel commitment, price commitment, Government-system access, contract acceptance, spend, award claim, payment claim, or revenue recognition.
