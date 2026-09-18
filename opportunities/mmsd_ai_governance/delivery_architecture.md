# MMSD AI Governance — Delivery Architecture

## Purpose

This is a delivery design for a public wastewater utility, not a generic corporate AI policy template. It separates **Generative AI** from **Operational AI** and treats any AI adjacent to treatment, infrastructure, telemetry, control, maintenance or physical actuation as a safety-sensitive system. The design remains a proposal-development artifact until current MMSD buyer-controlled RFP bytes are recovered.

## Non-negotiable safety boundary

Discovery does **not** authorize active probing, control changes, production model experiments, PLC/SCADA writes, changes to treatment logic, or testing that can affect water quality, worker safety, service continuity or environmental compliance. Operational-AI discovery defaults to read-only documentation review, asset-owner interviews, vendor evidence and approved passive inventory. Any future technical testing requires buyer authorization and the utility's normal OT change/safety process.

## Workstream 0 — Source and authority lock

Before response finalization, recover the current RFP plus every addendum and Q&A directly from MMSD-controlled publication or written buyer delivery. Hash buyer files, record capture times, identify supersession relationships, and compile a one-line requirement/evidence owner for every mandatory proposal element. Cached buyer pages and procurement indexes may seed the work plan; they never close a submission requirement.

## Workstream 1 — Enterprise AI inventory

Create an inventory across four distinct planes:

1. **Employee/knowledge AI** — chat assistants, document summarization, search, coding, drafting and meeting tools.
2. **Embedded SaaS AI** — AI features added by ERP, HR, finance, asset-management, GIS, collaboration, security and vendor platforms.
3. **Analytical Operational AI** — forecasting, anomaly detection, predictive maintenance, optimization, diagnostics and computer vision that inform operations but do not directly actuate controls.
4. **Actuating / physical AI** — systems able to alter plant, field, infrastructure or safety-relevant behavior directly or through an operator workflow.

Each inventory row should carry: system owner, vendor, purpose, deployment model, AI capability, autonomy level, affected process, data classes, retention location, training-data exposure, external connectors, human review point, logging availability, public-record relevance, vendor model-change mechanism, incident contact, and evidence references. Unknown fields remain unknown rather than being guessed.

## Workstream 2 — Risk tiering

Score each use case on independent dimensions rather than a single opaque risk number:

- physical / environmental safety consequence;
- service-continuity consequence;
- autonomy or actuation authority;
- sensitive/confidential/regulated data exposure;
- public-record / retention / discovery exposure;
- decision impact on people, vendors or public stakeholders;
- model/vendor opacity and update control;
- explainability / contestability need;
- cybersecurity and external-connector exposure;
- dependence on third-party hosted models or training terms.

Proposed policy tiers:

- **T0 — prohibited/unapproved:** unsanctioned tools handling restricted data, bypassing retention/security controls, or uncontrolled actuation.
- **T1 — low-risk assistive:** bounded drafting/search/administrative uses with approved data and mandatory human review.
- **T2 — governed analytical:** models informing business or operational decisions, requiring documented ownership, validation, monitoring and records controls.
- **T3 — high-impact operational:** systems affecting safety, continuity, infrastructure, compliance or consequential decisions; require formal risk assessment, change control, fallback, monitoring and named accountable owner.
- **T4 — safety-critical/actuating:** direct or effectively direct physical actuation; require utility-specific engineering/safety authorization outside ordinary AI-policy approval, with fail-safe manual control and no presumption of acceptability.

## Workstream 3 — Data sovereignty, security and records

Build one control map spanning AI policy, information security, Wisconsin public-record obligations and operational data governance. Minimum control questions:

- Which data may be sent to hosted model providers?
- Where is prompt/output data stored and for how long?
- Can vendor terms use customer data for model training or service improvement?
- Can retention/legal-hold obligations be enforced?
- Can records responsive to public-record requests be reconstructed without relying on end-user memory?
- Are model/version, prompt context, source documents and consequential outputs logged at the level needed for auditability?
- Are cross-border/subprocessor locations and deletion semantics known?
- Can the utility export evidence when a vendor service changes or terminates?

A model-provider privacy statement is not treated as a records-retention control, security assessment, or contractual data-sovereignty guarantee.

## Workstream 4 — Human oversight and Operational-AI change control

For T2+ systems define a named system owner, accountable business/operations owner, review cadence, validation evidence, input/data-quality checks, performance/drift indicators, incident triggers, fallback path and retirement criteria. For T3/T4, integrate with existing OT engineering and change-control procedures rather than creating a parallel AI-only bypass.

No policy language should imply that a model can self-authorize an operational change. Human review must be meaningful: reviewers need access to the basis for a recommendation, sufficient time/authority to reject it, and a safe fallback when confidence is low or telemetry is degraded.

## Workstream 5 — Vendor and procurement controls

Create a reusable AI vendor questionnaire and contract schedule. Request at minimum:

- exact AI functions and whether they can be disabled;
- model/provider/subprocessor chain;
- data-use/training terms;
- hosting and data-residency locations;
- retention/deletion/export semantics;
- security attestations and incident notice;
- model/update/change-notification policy;
- validation/performance evidence relevant to the stated use;
- logging/audit capabilities;
- human-oversight and fallback controls;
- IP/indemnity limitations where applicable;
- exit/portability plan.

Existing vendors should be inventoried for newly introduced AI features so procurement controls address **embedded/shadow AI**, not only new procurements labeled “AI.”

## Workstream 6 — Incident response

AI incidents need a route into existing security, privacy, operational, safety and records-management processes. The AI playbook should define triage for data disclosure, harmful/incorrect consequential output, service outage, drift/performance degradation, unauthorized model/vendor change, prompt/data exfiltration, public-record gap and unsafe operational behavior.

For a suspected T3/T4 incident, containment prioritizes safe operations and established OT/safety procedures over forensic experimentation. Preserve evidence without impeding treatment or emergency response.

## Workstream 7 — Training and AI literacy

Deliver role-based training rather than one slide deck:

- all staff: approved tools, restricted data, records obligations, verification and escalation;
- managers/system owners: use-case approval, risk tiering, vendor ownership, monitoring and incident duties;
- procurement/legal/records/security: evidence checklist and contract controls;
- technical/OT teams: model/data validation, logging, change control, fallback and drift;
- executives/governance body: risk acceptance, exception approval, metrics and review cadence.

Training should include realistic MMSD-style scenarios but must not invent buyer facts or disclose sensitive operational detail.

## Governance operating model

Use a small cross-functional AI governance function rather than a permanent committee for every low-risk use. Proposed decision rights:

- business/operations owner proposes and remains accountable for the use case;
- security/privacy/records/legal functions review their domains;
- OT/safety engineering controls any operational or physical-impact path;
- procurement controls vendor evidence and contract terms;
- AI governance maintains inventory, tiering, exceptions, review cadence and policy versioning;
- executive authority approves high-impact exceptions and residual risk when required.

## Concrete deliverables

1. AI use/governance policy with defined scope and decision rights.
2. AI inventory schema and completed discovery inventory.
3. Risk-tiering rubric and use-case assessment template.
4. Approved/prohibited-use standard and exception workflow.
5. Data sovereignty, records/retention and security control matrix.
6. AI vendor questionnaire + procurement/contract requirements.
7. Incident-response annex and escalation map.
8. Operational-AI / OT oversight annex.
9. Training curriculum and role-specific job aids.
10. Governance charter, metrics and review cadence.
11. Prioritized implementation roadmap with owners/dependencies.

## Outcome measures

Track inventory coverage, percentage of T2+ use cases with accountable owners and validation evidence, unresolved data-residency/retention gaps, vendor-AI disclosure coverage, training completion by role, review timeliness, exception aging, incident closure, and policy/control revisions. Do not use “number of AI tools deployed” as a success metric.
