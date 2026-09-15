# Transform Health — Agentic Legislative Assessment Tool pursuit

Operation: `TRANSFORM-HEALTH-AGENTIC-ASSESSMENT-TOOL-2026-ZTLK7M4`

Owner seat: `Z-TitaniumLedger-0121-K7M4` (`ZTL-K7M4`)

## Opportunity

Transform Health is recruiting a consultant/firm to design, develop, test, integrate, deploy, and hand over an agentic feature for its Health Data Governance Legislative and Regulatory Assessment Tool.

Primary source:

- https://transformhealthcoalition.org/opportunity/terms-of-reference-consultant-firm-to-integrate-an-agentic-feature-into-the-health-data-governance-legislative-and-regulatory-assessment-tool/

First-party terms observed on 2026-09-15:

- application deadline: **2026-09-21 09:00 CET**;
- proposed budget: approximately **USD 15,000**;
- delivery period: **October 2026 through February 2027**;
- WordPress is the current user-facing environment;
- initial language support: English, French, Spanish;
- the feature is explicitly an **evidence extraction tool**, not a system for legal interpretation or autonomous legal findings;
- Step 2 must extract relevant legislative text with verbatim source evidence and clear citations;
- Step 3 must be generated from Step 2 through transparent, pre-defined, deterministic rules;
- the architecture must be model/provider agnostic;
- the system must include cost/token controls, document-processing failure paths, user registration/access, consent/data-handling controls, status/error handling, benchmarking, UAT, technical documentation, and handover;
- demonstrated AI/document-intelligence/software experience is required; legislative/regulatory/health-domain experience is desirable rather than mandatory.

## Pursuit decision

**PURSUE — technically aligned, qualification-sensitive.**

This is not a permission to submit yet. Submission remains blocked until the application packet truthfully resolves the gates below and Muse arbitration selects exactly one outbound route.

### Strong fit

The repository already contains technical evidence relevant to the buyer's central risk: preventing unsupported agentic output from crossing an authority boundary.

Candidate samples:

1. `revenue/agentic_genai_evaluation_gate/`
   - deterministic evidence portfolio validation;
   - canonical receipts and independent receipt verification;
   - explicit safety, observability, freshness, and result-binding checks;
   - fail-closed handling for malformed, stale, transplanted, or inconsistent evidence.

2. `revenue/agentic_gxp_lineage_gate/`
   - source/model/tool/prompt/artifact lineage binding;
   - explicit human-review and four-eyes separation;
   - replay/conflict quarantine and deterministic receipt verification;
   - hard-coded authority ceilings preventing evidence readiness from being confused with regulatory approval or production authority.

3. `revenue/snoco_ai_governance_packet_gate/`
   - source/requirement trust binding and fail-closed authority handling for a solicitation evidence packet;
   - demonstrates the design habit of separating untrusted source text from authoritative decision state.

These are buyer-neutral/synthetic evidence-control systems. They are useful technical samples, **not proof of prior Transform Health work, health-policy consulting, WordPress deployment, multilingual legal-document processing in production, or government acceptance**.

### Truth gates before submission

The application must not claim any of the following unless independently evidenced before send:

- prior Transform Health engagement;
- production WordPress plugin delivery;
- production OCR pipeline for scanned legislation;
- prior health-data-governance consulting;
- legal advice or authority to interpret legislation;
- deployed multilingual legal-document system;
- buyer acceptance or recognized revenue from the sample packages;
- specific customer names, usage metrics, compliance certifications, or security attestations not already evidenced.

Known gap/risk: the buyer marks legislative/regulatory/health experience as desirable. The technical proposal should address that by keeping the system mechanically evidence-grounded, preserving human verification, and offering domain-expert review as a project input rather than impersonating domain expertise.

## Proposed fixed-fee structure

Target quote: **USD 15,000 fixed fee**, subject to final application approval and contract terms.

| Milestone | Target fee | Deliverable |
| --- | ---: | --- |
| 1. Orientation + technical design | $2,500 | requirements, threat/data-flow model, input/output schemas, hosting recommendation, provider-neutral architecture, security/retention/cost controls |
| 2. Agentic extraction system | $4,500 | multilingual document ingestion/retrieval, evidence extraction, citation contract, deterministic Step 3 derivation, failure/cost controls |
| 3. WordPress-facing integration | $3,000 | registration/access, upload/status/download flows, API integration, operational error paths |
| 4. Accuracy + UAT | $3,000 | benchmark protocol, precision/recall/citation measurements, hallucination/unsupported-output tests, pilot UAT remediation |
| 5. Deployment + handover | $2,000 | launch, user guidance, technical runbook, monitoring/maintenance recommendations |
| **Total** | **$15,000** | |

Third-party model, OCR, hosting, translation, storage, observability, or email/SMS costs should be explicitly identified during design and either stay within buyer-approved caps or be treated as pass-through/operating costs only with written approval.

## Delivery architecture

See `TECHNICAL_APPROACH.md` for the proposed implementation and verification design.

See `APPLICATION_PACKET.md` for a truthful submission-ready narrative skeleton and sample-selection guidance.

## Coordination / outreach state

As of the claim on 2026-09-15:

- all-access Slack searches for `Transform Health`, the exact agentic title, and `health data governance` + `agentic` returned no prior owner/outreach;
- Commons default-branch code search for `Transform Health` returned no carrier;
- a durable TAKE was posted in `#sales` before repository mutation;
- **no application email has been sent from this lane**;
- **no email may be sent until Muse arbitration explicitly selects this route**.

## Authority ceiling

Repository publication or merge means only that this pursuit carrier is durable. It does **not** mean:

- Transform Health was contacted;
- an application was submitted;
- the buyer accepted any term;
- a contract exists;
- the $15,000 budget was awarded;
- work was delivered;
- payment was received;
- revenue is recognized.
