"""Deterministic internal Solution Concept Paper and question-draft renderer."""

from __future__ import annotations

from typing import Any, Mapping

from .gate import REQUIRED_CAPABILITIES, normalize_candidate, verify_report_shape
from .strict import ValidationError

SECTION_ORDER = (
    "1. Problem Understanding",
    "2. Proposed Concept and Vision",
    "3. High-Level Technical Approach",
    "4. Intellectual Property and Data Rights",
    "5. Risk and Opportunity Spotlight",
    "6. Rough Order of Magnitude",
)
MAX_BODY_WORDS = 3300


def _words(text: str) -> int:
    return len([part for part in text.split() if part])


def render_concept(candidate_value: Any, report_value: Any) -> str:
    candidate = normalize_candidate(candidate_value)
    report = verify_report_shape(report_value)
    if report["subject_id"] != candidate["subject_id"]:
        raise ValidationError("concept candidate and report subject do not match")
    if report["operation_id"] != candidate["operation_id"]:
        raise ValidationError("concept candidate and report operation do not match")

    route = report["state"]
    banner = (
        "INTERNAL WORKING DRAFT — NOT AUTHORIZED FOR EXTERNAL CONTACT OR SUBMISSION. "
        f"Current qualification state: {route}."
    )
    if route == "TEAMING_REQUIRED":
        route_paragraph = (
            "The proposed participation model is a bounded specialist workshare beneath an "
            "independently qualified cleared prime. The specialist scope is integration architecture, "
            "acceptance evidence, reusable onboarding patterns, observability, and rollback design. "
            "Prime responsibility for clearance, submission, sustainment transition, staffing, and "
            "Government commitments remains outside this draft until separately evidenced."
        )
    elif route == "DIRECT_READY":
        route_paragraph = (
            "The internal gate found the evidence needed for owner review of a direct route. This is "
            "not submission authority: current source bytes, personnel assignments, cost, markings, "
            "and owner release must still be rechecked immediately before any external action."
        )
    else:
        route_paragraph = (
            "The pursuit remains on HOLD. The architecture below is reusable technical preparation, "
            "not a representation that the organization possesses required clearances, staffing, "
            "eligibility, past performance, price approval, or submission authority."
        )

    risks = "\n".join(f"- {risk}" for risk in candidate["risks"]) or "- No candidate risks supplied."
    dependencies = (
        "\n".join(f"- {item}" for item in candidate["third_party_dependencies"])
        or "- No third-party dependency has been approved."
    )
    background_ip = (
        "\n".join(f"- {item}" for item in candidate["background_ip"])
        or "- No background intellectual property is asserted by this draft."
    )
    questions = (
        "\n".join(f"- {item}" for item in candidate["question_drafts"])
        or "- No question draft is authorized for transmission."
    )

    sections = [
        f"""# {candidate['concept_title']}

> {banner}

Qualification operation: `{candidate['operation_id']}`  
Source generation: `{report['source_generation_sha256']}`  
Concept-paper deadline: `{report['concept_deadline']}`

## 1. Problem Understanding

DCSA's personnel-vetting, industrial-security, counterintelligence, and insider-threat missions depend on multiple applications with separate navigation, authentication patterns, user experiences, and sustainment seams. The modernization problem is therefore not a portal-only redesign. It is a continuity-constrained integration program: existing Individual Engagement applications must remain operational while workflows, identity context, interfaces, security evidence, and user experience are incrementally unified.

The decision-quality objective is to prove that a modular application layer can provide a common entry point without transferring hidden coupling into a new monolith. The prototype must expose where identity, business rules, data ownership, application responsibilities, and operational support boundaries live. It must also produce evidence that DCSA can onboard additional applications through repeatable contracts rather than one-off rewrites.

{route_paragraph}

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

{chr(10).join(f'- `{capability}`' for capability in REQUIRED_CAPABILITIES)}

## 4. Intellectual Property and Data Rights

This draft assumes Government ownership and control of Government data and does not authorize using enterprise data to train, evaluate, or enhance external commercial foundation models or proprietary algorithms. Data remains inside approved environments and approved processing boundaries. Any AI-assisted feature must identify its model, data path, retention behavior, evaluation method, human authority, failure mode, and rollback path before use.

Background intellectual property asserted for owner review:

{background_ip}

Third-party dependencies requiring separate license, security, data-rights, and continuity review:

{dependencies}

Foreground interface contracts, configuration, test artifacts, onboarding patterns, and deployment evidence should be delivered in forms that support Government operation and follow-on competition. Final rights assertions and markings require counsel and owner approval; this working draft makes no legal conclusion.

## 5. Risk and Opportunity Spotlight

The primary program risk is assuming that a common interface removes integration and sustainment complexity. It can instead hide incompatible identity semantics, duplicated business rules, ambiguous ownership, and silent fallback behavior. The mitigation is evidence-first onboarding: each application integration begins with authority maps, workflow traces, failure contracts, continuity canaries, and a reversible cutover plan.

A second risk is an over-ambitious sustainment transition during the first 30 days. The transition plan must identify exact applications, repositories, pipelines, environments, unresolved incidents, release obligations, access dependencies, and staffing assumptions. Unknowns remain explicit HOLDs rather than being buried in schedule contingency.

A major opportunity is to make onboarding itself a product of the prototype. A standard adapter contract, policy-mapping workbook, test harness, observability pack, and authorization-evidence checklist can turn later application integration into a repeatable bounded process.

Candidate risk register:

{risks}

Questions drafted for owner review only; no transmission is authorized:

{questions}

## 6. Rough Order of Magnitude

ROM state: **{candidate['rom_state']}**.

No price, cost share, staffing commitment, or schedule commitment is invented in this draft. A submission-quality ROM requires the controlling template and call bytes, a validated participation route, cleared-prime/workshare structure if applicable, staffing and sustainment assumptions, Government-furnished environment assumptions, phase acceptance criteria, data-rights treatment, and owner-approved risk reserve.

The ROM should be organized by the four prototype phases and should separately identify: sustainment transition and operations; discovery and user research; common shell and ICAM/policy integration; application adapters and onboarding; DevSecOps/IaC; testing and accessibility; security authorization and remediation; program management; travel/site activity; and production-transition planning. Any cost-share representation must be bound to the selected OTA eligibility path and owner authority.

---

**Authority ceiling:** this artifact authorizes no email, Q&A submission, concept-paper submission, signature, clearance representation, personnel commitment, price commitment, Government-system access, contract acceptance, spend, award claim, payment claim, or revenue recognition.
"""
    ]
    text = "".join(sections)
    body_words = _words(text)
    if body_words > MAX_BODY_WORDS:
        raise ValidationError(
            f"compiled concept exceeds the internal {MAX_BODY_WORDS}-word ceiling: {body_words}"
        )
    for heading in SECTION_ORDER:
        if text.count(f"## {heading}") != 1:
            raise ValidationError(f"compiled concept is missing unique section {heading}")
    return text
