# UIOWA-020 — Primary framework reference crosswalk adaptation memo

**Status:** assessment-design reference; not a compliance determination, certification, benchmark score, or finding about University of Iowa practice  
**Scope:** RFQ 18649 assessment areas — software development, security, deployment/operations, and AI readiness — across ESS, RIS, and IAM  
**Access/review date:** 2026-09-19

## Purpose

This package gives the RFQ 18649 workbench a source-controlled way to use primary NIST frameworks without pretending that those sources supply a validated maturity model for the University. The companion `20-framework-crosswalk.csv` maps selected framework elements to the four assessment areas and proposes evidence questions; `20-source-version-register.csv` records the publication/version status used for the mapping.

The existing workbench renders a 12-cell ESS/RIS/IAM × four-dimension inspection surface. These references are therefore **inputs to discovery and evidence interpretation**, not authority to mark a cell READY, assign a buyer-facing score, certify compliance, or infer current University practice from public material.

## Source semantics that must stay distinct

### NIST SP 800-218 — SSDF 1.1

SSDF is a set of high-level **secure software development practices and tasks** intended to be integrated into SDLC implementations. It is strongest for the software-development dimension and contributes specific evidence questions to security and deployment/operations.

Use it to ask whether practices such as security requirements, secure-development roles, toolchains, software-security checks, secure build environments, release integrity, secure design/coding/testing, vulnerability response, and root-cause learning are defined and evidenced.

Do **not** call the result an “SSDF maturity score.” SSDF 1.1 does not define a maturity ladder for the Iowa assessment.

Currentness note: NIST published SP 800-218 Rev.1 / SSDF 1.2 as an **Initial Public Draft** on 2025-12-17. As of this review, NIST's SSDF publications page still lists SP 800-218 v1.1 as Final and v1.2 as Draft. Use v1.1 as the stable baseline; track v1.2 as a version watch item only.

### NIST CSF 2.0

CSF 2.0 provides a taxonomy of high-level **cybersecurity outcomes**. NIST explicitly says the Core outcomes are not a checklist and that the CSF does not prescribe how outcomes are achieved. That makes CSF useful for assessment questions about governance, asset/risk understanding, identity/data/platform protection, monitoring, incident handling, recovery, and improvement without dictating a particular toolchain.

For this engagement, use CSF categories as outcome lenses, then ask for local evidence and context.

**CSF Tiers guardrail:** Section 3 and Appendix B describe Tiers 1–4 and Appendix B calls its table a **notional illustration**. The Tiers characterize the rigor of an organization's cybersecurity risk governance and management practices. They should not be imported as the four-dimension ESS/RIS/IAM maturity scale, treated as empirical percentiles, or used to imply NIST validated a service-level scoring method.

NIST SP 1347 (final 2026-08-25) is useful method support because it describes Informative References as relationships between elements of different source documents. That supports maintaining an explicit crosswalk like this one while keeping each source's semantics intact.

### NIST AI 100-1 — AI RMF 1.0

AI RMF 1.0 organizes AI risk work into **GOVERN, MAP, MEASURE, and MANAGE**, with categories and subcategories. It is the primary reference for AI-readiness discovery: inventories and ownership, use-case context, requirements and human oversight, TEVV/measurement, monitoring, third-party AI risk, deployment decisions, incident handling, deactivation, and continual improvement.

AI RMF is voluntary, use-case agnostic, and risk-based. Its Section 6 Profiles describe current and target states for specific contexts. Profiles are useful for organizing gaps and desired outcomes, but they are **not a universal maturity ladder**.

Currentness note: NIST's AI RMF site states that **AI RMF 1.0 is being revised**. Recheck the NIST publication page before the final client-facing methodology is frozen.

### Targeted AI companions

Two final NIST companions are relevant only when facts justify their use:

- **NIST SP 800-218A** augments SSDF 1.1 with secure-development practices for generative AI and dual-use foundation models.
- **NIST AI 600-1** is a cross-sectoral Generative AI profile for AI RMF 1.0.

Do not use either companion as evidence that AIS develops models, uses generative AI in production, or has a particular vendor architecture. Confirm the actual AI lifecycle role first.

## Proposed use by RFQ assessment area

| RFQ area | Primary reference | Supporting references | Evidence-oriented use |
|---|---|---|---|
| Software development | SSDF 1.1 | CSF 2.0; AI RMF where AI is actually in scope | Requirements, roles, design review, secure coding/testing, build controls, component governance, release integrity, vulnerability learning |
| Security | CSF 2.0 | SSDF 1.1; AI RMF security/resilience elements | Governance, IAM, data/platform protection, risk assessment, monitoring, incident analysis/mitigation, recovery |
| Deployment / operations | CSF 2.0 | SSDF PS/PW/RV; AI RMF post-deployment elements | Release integrity, secure defaults, observability, event analysis, incident handling, recovery, change/deactivation, continual improvement |
| AI readiness | AI RMF 1.0 | SSDF 1.1 / 800-218A when applicable; CSF 2.0; AI 600-1 when GenAI applies | Inventory/ownership, context and limits, human oversight, TEVV, metrics, production monitoring, third-party/model risk, residual-risk and deployment decisions |

## Assessment-design rules

1. **Framework mapping is not a finding.** A mapped framework element only tells the team what evidence or questions may be useful.
2. **Public information is context, not implementation evidence.** University policy or strategy pages cannot establish ESS/RIS/IAM operating practice without corroborating engagement evidence.
3. **Separate policy, implementation, and outcome.** A policy can exist without consistent execution; an implemented process can still have poor outcomes; an outcome can be produced by multiple different practices.
4. **Keep source constructs native.** SSDF practices remain practices; CSF outcomes remain outcomes; AI RMF functions/categories/subcategories remain risk-management constructs.
5. **Do not source-wash a local rubric.** If the engagement uses a local maturity or capability scale, label it as a proposed assessment design, document the evidence rules and calibration method, and never imply NIST validated the score.
6. **No certification/compliance claims.** This RFQ work is an evidence-based assessment, not a NIST certification, legal compliance audit, or assurance engagement.
7. **No peer-percentile claims without comparable data.** Public peer descriptions can inform questions, but cannot justify percentile placement without comparable definitions, periods, populations, and denominators.
8. **Record applicability.** For each source element, note why it is relevant to the service and what evidence would show it is not applicable.
9. **Revalidate versions at methodology freeze.** SSDF 1.2 is draft and AI RMF 1.0 is under revision as of this review.

## Suggested evidence record shape

For each ESS/RIS/IAM × assessment-area cell, retain or export fields equivalent to:

- service/group
- assessment area
- framework source + exact element
- applicability rationale
- evidence source and observation date
- observed practice / outcome
- implementation evidence
- outcome evidence
- exception or counter-evidence
- unresolved question
- assessor interpretation
- local rubric level, **if any**, explicitly labeled as local/proposed
- reviewer and review date

This preserves the Commons workbench's evidence-authority boundary while making framework adaptation reconstructable.

## Key discovery questions enabled by the crosswalk

### Software development
- Which security requirements must each service satisfy, and how are changes and exceptions tracked?
- What evidence shows design/code/test/release security checks are consistently used?
- How are third-party components selected, tracked, updated, and retired?
- What happens after a vulnerability or escaped defect: only remediation, or root-cause/process change as well?

### Security
- Who owns cybersecurity risk decisions for each service and supporting platform?
- How are identities, access, data, platform configurations, and suppliers governed and reviewed?
- What monitoring coverage exists, how are events prioritized, and how do incidents drive improvement?
- Which resilience/recovery objectives are defined and tested for each service?

### Deployment / operations
- Can a release be traced from approved change through build artifact to deployment?
- What release-integrity, configuration, rollback, and recovery controls are evidenced?
- How are monitoring, incident response, change management, and post-incident learning connected?
- Which measures have stable definitions and denominators suitable for trend or peer comparison?

### AI readiness
- What AI-enabled capabilities actually exist in AIS workflows, if any, and who owns them?
- What are the intended uses, users, limits, data dependencies, human-oversight expectations, and risk tolerances?
- What TEVV, security/resilience evaluation, production monitoring, and feedback mechanisms exist?
- How are third-party/pre-trained models or services monitored, and what are the stop/deactivate paths when behavior departs from intended use?

## Source register

See `20-source-version-register.csv`. The reviewed primary sources are NIST publications/pages only; no certification, compliance status, empirical benchmark, or University implementation claim is created by this crosswalk.
