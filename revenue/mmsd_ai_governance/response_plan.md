# MMSD Comprehensive AI Use & Governance Policy — truth-bound response plan

**Opportunity:** `MMSD-AI-GOVERNANCE-RFP-20260913`  
**Buyer:** Madison Metropolitan Sewerage District  
**Current internal posture:** `HOLD_QUALIFICATION_GATES` until the official PDF submission requirements and company evidence are resolved.  
**Purpose of this file:** a substantive technical response skeleton. It is not a submitted proposal, quote, contract, award, reference claim, or authorization to contact the District.

## 1. Published buyer objective

The District is seeking a qualified consulting firm to produce a comprehensive and actionable AI Use and Governance Policy that covers both:

- **Generative AI** used for administrative workflows, drafting, analysis, and knowledge work; and
- **Operational AI** used in or around wastewater treatment processes, infrastructure analytics, and plant upgrades.

The published objective combines innovation/upskilling with strict electronic-data safeguards, data sovereignty, public-records compliance, transparency, vendor governance, incident response, and staff literacy. The public solicitation index additionally identifies a shadow-AI audit and stakeholder interviews.

This plan therefore treats AI governance as an **operating system for decisions**, not a generic acceptable-use memo.

## 2. Proposed outcome architecture

The engagement should leave the District with a policy plus operational artifacts that make the policy executable:

1. **AI system/use-case inventory** — current, planned, embedded, vendor-provided, Generative AI, and Operational AI.
2. **Four-tier risk model** — determines intake, review, evidence, approval, monitoring, and incident requirements.
3. **Acceptable-use standard** — employee rules for public, internal, sensitive, regulated, and operational data.
4. **Operational-AI safety boundary** — separates advisory analytics from actions that can affect treatment, equipment, process control, environmental compliance, or safety.
5. **Data sovereignty + records map** — where prompts, inputs, outputs, logs, derived records, and vendor telemetry may flow and what must be retained.
6. **Public-records playbook** — acquisition, retention, discoverability, redaction/escalation ownership, and approved use of transient-chat features.
7. **Vendor procurement control set** — required disclosures, data-use terms, retention, model training, subprocessors, security, incident reporting, audit/export, portability, and exit.
8. **Shadow-AI audit method** — discovery without turning the audit itself into employee surveillance.
9. **Incident-response runbook** — data exposure, unsafe output, unauthorized automation, model/provider change, integrity failure, and Operational-AI anomaly.
10. **Training + role curriculum** — all staff, managers, procurement, IT/security/data, records/legal, and operational/engineering roles.
11. **Governance charter** — named decision rights and exception workflow.
12. **90-day implementation roadmap** — converts policy approval into operating cadence.

## 3. Risk-tier model

### Tier 0 — Prohibited / hold

Examples to validate with District stakeholders:

- autonomous changes to treatment or safety-critical process controls without separately approved engineering controls;
- uploading restricted/sensitive District data to unapproved AI services;
- AI-only final legal, regulatory, hiring, discipline, procurement-award, or other consequential decisions;
- undocumented tools that cannot meet required records, security, or data-sovereignty controls.

**Gate:** `HOLD` until a designated authority explicitly approves an alternative control path; some uses may remain prohibited.

### Tier 1 — Low-risk assistive

Examples: public-information drafting, ideation, style assistance, approved translation support, or non-sensitive summarization.

**Minimum controls:** approved tool, user review, data classification check, accuracy/source expectations, required disclosure/records handling.

### Tier 2 — Business / internal consequential support

Examples: internal analysis, procurement support, operational planning, code assistance, vendor or asset analysis where outputs can influence material decisions.

**Additional controls:** documented purpose, named owner, approved data classes, validation criteria, human decision point, logging/retention, material-change review.

### Tier 3 — High-impact / operational

Examples: AI/ML connected to wastewater treatment analytics, infrastructure condition/risk models, maintenance prioritization, process optimization, safety/environmental compliance support, or systems whose erroneous output could materially affect operations.

**Additional controls:** explicit technical owner + business/operations owner; safety and failure-mode analysis; authoritative-data lineage; test/validation evidence; human or deterministic interlock before external effect; rollback/degraded mode; monitoring thresholds; model/data drift review; vendor-change notification; incident exercises; periodic reauthorization.

## 4. Shadow-AI audit method

The audit should answer “what AI is actually used, for what, with what data, under whose authority?” without presuming wrongdoing.

### Discovery sources

- stakeholder interviews by department/function;
- approved SaaS/application inventory and procurement records;
- IT/security telemetry already lawfully available to the District;
- browser/extension/application inventory where policy and labor/privacy constraints allow;
- survey of recurring work where employees may be seeking unofficial AI assistance;
- vendor feature inventory for systems that introduced embedded AI after original procurement.

### Audit record

For each candidate use/system: `owner`, `department`, `purpose`, `provider/product`, `AI capability`, `data classes`, `inputs`, `outputs`, `decision/effect`, `records generated`, `retention`, `integration`, `risk tier`, `approval state`, `vendor evidence`, `next action`.

### Findings taxonomy

- `APPROVED_CURRENT`
- `APPROVED_NEEDS_CONTROL_UPDATE`
- `UNKNOWN_REVIEW_REQUIRED`
- `UNAPPROVED_HOLD`
- `PROHIBITED`
- `RETIRE_OR_REPLACE`

The assessment should report systemic patterns and remediation queues; it should not make unsupported misconduct claims about individual employees.

## 5. Stakeholder interview plan

A final schedule should be confirmed with the District. Proposed groups:

- executive sponsor / administration;
- IT, security, data/platform owners;
- legal/records/public affairs;
- procurement/vendor management;
- HR/training;
- engineering, treatment operations, maintenance/reliability;
- planning/capital-project and infrastructure analytics owners;
- representative administrative end users;
- internal audit/risk if applicable.

### Core questions

1. Which decisions/workflows are already using AI or AI-enabled vendor features?
2. What data crosses the tool boundary, and what is authoritative vs derived?
3. What can the AI recommend, decide, trigger, or change?
4. Where is a human review actually meaningful rather than ceremonial?
5. What record must exist to reconstruct the decision/work product later?
6. What failure would matter most: confidentiality, integrity, availability, safety, environmental compliance, fairness, public trust, cost, or service continuity?
7. What existing policy/control already governs the risk?
8. What operational burden would make a proposed governance control fail in practice?

## 6. Data sovereignty and electronic-data safeguards

Each approved AI use should have a documented data-flow answer for:

- origin and classification of input data;
- transmission regions/endpoints;
- provider storage/retention;
- provider training or secondary-use rights;
- subprocessors and cross-border handling;
- encryption and access controls;
- administrative/support access;
- derived data, embeddings, caches, logs, and telemetry;
- deletion/export/portability capability;
- breach/incident notice;
- model/vendor change notification;
- District exit procedure.

A policy should distinguish **“provider promises not to train on prompts”** from the broader questions of retention, telemetry, abuse monitoring, subprocessors, administrative access, and derived artifacts.

## 7. Wisconsin public-records operating playbook

The policy should be drafted with District counsel/records authority rather than treating the technical consultant as legal counsel. The technical operating model should nevertheless make records obligations executable:

- identify which AI inputs/outputs/logs are District records under the District's approved interpretation;
- map systems to retention schedules and legal holds;
- require export/search capability where records must be retained;
- prohibit or constrain ephemeral modes when they defeat required retention;
- record model/tool identity and material source context when necessary to reconstruct work;
- define employee duty to transfer a required record out of a transient vendor surface;
- establish escalation for sensitive/confidential/redaction questions;
- test retrieval with sample records before approving a high-risk tool.

No response should promise a legal conclusion about Wisconsin records law without designated District legal review.

## 8. Vendor procurement framework

For AI-capable vendors, require a scored disclosure that covers at least:

| Domain | Required evidence | Fail/hold examples |
|---|---|---|
| Capability | exact AI features, models, automation/effect boundary | material feature cannot be disabled or scoped |
| Data use | training/secondary use, retention, telemetry, subprocessors | undisclosed secondary use or incompatible retention |
| Sovereignty | processing/storage locations and support access | cannot meet District-approved location/control requirement |
| Security | auth, encryption, tenant isolation, incident process | missing essential control/evidence |
| Records | export, search, retention, deletion, legal hold support | required records cannot be preserved/retrieved |
| Change control | model/provider change notification, release notes | silent material changes to high-risk capability |
| Reliability | evaluation, monitoring, degraded mode, rollback | no credible failure handling for high-impact use |
| Transparency | limitations, human oversight, documentation | marketing-only claims with no usable evidence |
| Exit | portable export + deletion verification | lock-in prevents required transition |

Procurement should not award or reject solely on a self-generated “AI risk score”; human procurement authority remains intact.

## 9. Operational-AI controls for wastewater/infrastructure

This is where a generic office-AI policy is insufficient.

For Tier-3 Operational AI, require:

- clear separation between **measurement/source data**, model-derived features, prediction/recommendation, operator decision, and physical/digital effect;
- authoritative sensor/data-quality checks and stale/missing/implausible-data handling;
- documented operating envelope and out-of-distribution behavior;
- deterministic interlocks or human authorization for effects that can alter treatment, safety, compliance, or equipment state;
- safe degraded/manual mode;
- model + data version traceability;
- change/retraining validation before promotion;
- baseline and acceptance performance by operational condition, not one aggregate metric;
- alert/false-positive/false-negative burden reviewed with operators;
- post-deployment drift, incident, and override monitoring;
- emergency disable/rollback path tested on a defined cadence.

The governance policy should never imply that an AI consultant assumes licensed engineering, operator, environmental-compliance, or safety authority.

## 10. Incident-response framework

Proposed incident classes:

- sensitive-data exposure or unauthorized data transfer;
- material hallucination/inaccuracy used downstream;
- prompt injection / malicious content affecting tool behavior;
- unauthorized agent/tool action;
- vendor/model change invalidating prior approval;
- records-retention/export failure;
- discriminatory or unfair consequential output;
- integrity/availability event;
- Operational-AI anomaly, unsafe recommendation, control-boundary breach, or unexplained model behavior.

Every incident path needs: detection source, severity, containment owner, preserve-evidence instruction, system/data owner, records/legal/security escalation, vendor notification path, decision on suspension, recovery/validation, corrective action, and approval to return to service.

## 11. Staff AI-literacy plan

### All staff

- what counts as AI (including embedded vendor features);
- approved vs unapproved tools;
- data classification and prompt/input boundaries;
- verification and source discipline;
- public records/retention responsibilities;
- incident/reporting path;
- when human review is mandatory.

### Managers and system owners

- risk-tier intake;
- decision rights and exception requests;
- measuring actual benefit and failure burden;
- documentation and periodic review.

### Procurement / IT / security / data / records

- vendor questionnaire;
- data-flow and retention review;
- model/tool change governance;
- records and exit tests;
- evidence requirements.

### Operations / engineering

- Operational-AI boundary;
- data quality, drift, degraded mode, interlocks;
- override and incident logging;
- reauthorization after material change.

Training should include role-specific scenarios and a short comprehension/decision exercise, not just attendance.

## 12. Six-month delivery shape

This is a proposed work plan, subject to the actual PDF and buyer agreement.

### Month 1 — discover and baseline

- kickoff, document request, stakeholder map;
- current policy/control inventory;
- shadow-AI discovery;
- initial system/use inventory;
- risk and records assumptions log.

### Month 2 — classify and design

- risk-tier workshop;
- data sovereignty / records / vendor-control mapping;
- Operational-AI workshop;
- initial gaps and quick controls.

### Month 3 — draft operating artifacts

- policy v0.5;
- acceptable-use standard;
- intake/risk assessment;
- procurement questionnaire;
- incident-response draft;
- governance charter.

### Month 4 — validate against scenarios

- administrative GenAI scenarios;
- embedded/vendor AI scenario;
- procurement scenario;
- public-record request/retention scenario;
- Operational-AI anomaly/change scenario;
- incident tabletop.

### Month 5 — train and revise

- role-based training;
- stakeholder review;
- policy/control revision;
- implementation backlog and owners.

### Month 6 — finalize and operationalize

- final policy package;
- governance artifacts and training materials;
- approved inventory/risk-register starting point;
- 90-day implementation roadmap;
- executive/board-style briefing as requested;
- handoff and update cadence.

## 13. Acceptance framework

A strong engagement should be accepted on observable outputs, for example:

1. all identified AI uses have an owner, purpose, risk tier, approval state, data-class entry, and next action;
2. every Tier-3 use has an explicit effect boundary, safe/degraded mode, change-control path, and incident owner;
3. approved AI vendors have a completed minimum vendor-control record or an explicit exception;
4. selected records scenarios can be retrieved/exported under the approved procedure;
5. staff training completion + scenario results are measurable by role;
6. a tabletop produces an actionable incident timeline and identified control improvements;
7. policy exceptions have expiration, owner, compensating control, and review date;
8. the final policy and operating artifacts identify owners and update cadence rather than ending at publication.

Metrics must be finalized with the District; this plan does not fabricate baseline or target percentages.

## 14. Proposal-public-record boundary

The official landing page says proposal responses and their contents are public record. Therefore a final submission package should exclude:

- secrets, API keys, credentials, private repository links, proprietary customer datasets;
- confidential client evidence that lacks explicit permission for disclosure;
- unnecessary personal data;
- internal-only threat detail that creates security exposure;
- unsupported claims about certifications, insurance, clients, outcomes, or current District systems.

Use public-safe reference descriptions only after confirming authorization and exact RFP requirements.

## 15. Qualification gaps that block a prime submission today

These are **unknown**, not failed:

- exact five required submission items;
- evaluation criteria/weights;
- reference requirements and whether team references count;
- insurance requirements/timing;
- company/entity forms and certifications;
- required price format;
- named staff availability for six months;
- owner-approved price;
- actual eligible reference evidence.

Until resolved, this package supports technical readiness but status remains `HOLD_QUALIFICATION_GATES`.

## 16. Sources used for current public facts

- Official landing page: https://www.madsewer.org/contracting-center/comprehensive-artificial-intelligence-ai-use-and-governance-policy-request-for-proposal/
- Public solicitation index used to corroborate question deadline, term, and source-document name: https://publicbidsearch.com/bids/comprehensive-artificial-intelligence-ai-use-and-governance-madison-wi-d08042

The source document is named `FINAL-RFP-Comprehensive-AI-Policy-Development-1.pdf`; its bytes were not retrievable through the research harness used for this package. Any later official PDF or addendum supersedes indexed summaries and this plan must be reconciled before proposal submission.
