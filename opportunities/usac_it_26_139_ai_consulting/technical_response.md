# Volume 2 working draft — Technical Capability

**Internal draft only.** This is a response architecture for USAC IT-26-139. It must be reconciled against the latest buyer generation and real company/team evidence before proposal use. No statement below invents past performance, named staff, certifications, approvals, or buyer acceptance.

## 1. Technical approach

### 1.1 Engagement objective

Deliver a decision-grade AI operating framework that lets USAC move from its current early-adoption posture to a controlled three-year implementation program. The engagement will not build or deploy production AI. It will establish the evidence, governance, operating model, portfolio sequence, risk controls, economics and pilot recommendation required for later implementation decisions.

The work is organized around five questions:

1. **Where is USAC actually ready?** Establish evidence across strategy, policy, governance, workforce, data, technology, privacy/security and decision rights.
2. **What should be done first?** Rank initiatives by mission value, feasibility, risk, prerequisite maturity and measurable outcome rather than novelty.
3. **How should AI be governed?** Turn existing committees/policies into a lifecycle with intake, classification, review, approval, monitoring, escalation and retirement.
4. **How should traditional, generative and agentic AI differ?** Match oversight depth and controls to consequence, autonomy, data sensitivity and failure mode.
5. **How can USAC measure progress?** Define decision gates, outcome metrics, risk indicators, cost allocation and portfolio reporting that survive individual tool/vendor changes.

### 1.2 Workstream A — current-state evidence baseline

#### A1. Evidence intake and document review

Create a structured inventory of current AI strategy, policies, standards, committee charters, risk inventory, vendor/software review process, privacy/security controls, applicable FCC/USAC obligations, project-management practices and current Copilot adoption evidence.

Every observation is tagged as one of:

- documented current control;
- observed operating practice;
- stakeholder-reported practice requiring validation;
- unresolved gap;
- dependency outside the engagement.

This prevents stated policy from being confused with deployed operating capability.

#### A2. Stakeholder discovery

Use a bounded interview/workshop plan spanning USAC program divisions and enterprise support functions. Sessions focus on mission outcomes and high-friction processes; current analytics/automation; sensitive data and decision boundaries; approval/oversight paths; workforce capability; technology constraints; measurable success criteria; and failure/exception patterns.

Buyer Q&A says foundational work already exists, so discovery should validate and deepen existing material rather than recreate it.

#### A3. Readiness model

Score readiness across six dimensions:

1. governance and decision rights;
2. workforce and change absorption;
3. data quality/access/classification;
4. technology/integration/observability;
5. privacy/security/regulatory controls;
6. measurement, financial governance and operational ownership.

Each dimension produces an evidence-backed maturity score, confidence level, blocking dependency and near-term corrective action. A low score identifies prerequisites for a use case rather than automatically recommending against AI.

### 1.3 Workstream B — use-case portfolio and risk segmentation

Build a portfolio of candidate initiatives from stakeholder evidence using one scoring model:

- mission/public value;
- staff-efficiency value;
- customer-experience value;
- implementation effort;
- data readiness;
- integration complexity;
- privacy/security sensitivity;
- regulatory/control burden;
- explainability/auditability requirement;
- human-review feasibility;
- failure consequence;
- recurring operating cost and consumption uncertainty.

Classify initiatives into bounded archetypes such as traditional/statistical analytics; staff knowledge/retrieval assistance; summarization/drafting with human approval; workflow triage/recommendation; process automation with deterministic guardrails; externally facing generative interaction; and tool-using/agentic workflows. The archetypes drive control requirements rather than prescribe a vendor.

### 1.4 Workstream C — three-year implementation roadmap

Construct a sequenced roadmap with prerequisites and decision gates.

#### Horizon 0: foundation

- close priority governance/control gaps;
- formalize use-case intake and risk tiering;
- define data/tool approval boundaries;
- establish evaluation and measurement templates;
- define AI inventory and ownership;
- establish cost tracking and program-line allocation;
- establish workforce enablement and communications.

#### Horizon 1: lower-risk controlled adoption

- prioritize internal efficiency use cases;
- use bounded human-in-the-loop workflows;
- establish baseline/benchmark measurements before rollout;
- validate tool, security, privacy and data boundaries;
- capture adoption, quality, exception, cost and risk telemetry.

#### Horizon 2: scaled workflow integration

- expand only use cases that clear measured value and control thresholds;
- deepen business-process integration;
- standardize reusable evaluation/control patterns;
- mature portfolio funding and lifecycle ownership;
- strengthen cross-division governance and reporting.

#### Horizon 3: selective higher-autonomy evaluation

- consider agentic or externally consequential workflows only where prerequisites are demonstrably mature;
- require explicit action authority, human intervention, traceability, monitoring, rollback and cost controls;
- preserve an option to reject agentic adoption where economics or failure risk does not justify it.

Every roadmap initiative includes owner, prerequisite, dependency, decision gate, indicative resourcing, cost category, measurable outcome and control class.

### 1.5 Workstream D — target operating model and governance

Convert the existing governance structure into an operating lifecycle.

#### Intake

Each proposed use case should capture business owner/accountable executive, intended outcome/affected population, data classes/systems, model/tool class, autonomy, external/internal interaction, material decision impact, integrations, and success metrics/baseline.

#### Risk tiering

Risk classification considers data sensitivity, decision consequence, external exposure, scale, autonomy/tool authority, reversibility, human-review quality, regulatory/audit relevance, model/vendor opacity and failure-detection latency.

#### Review and approval

Define which bodies make which decisions, required evidence, and escalation points. A practical lifecycle is:

`INTAKE -> SCREEN -> EVALUATE -> APPROVE/PILOT -> MONITOR -> REASSESS -> RETIRE`

Each transition has named evidence and decision ownership, avoiding committees that are advisory in theory but ambiguous in operational authority.

#### Inventory and reporting

Maintain one inventory of AI-enabled software/use cases with owner, risk tier, approval status, data boundary, vendor/tool class, evaluation evidence, monitoring metrics, renewal/review date and material incidents/exceptions.

Executive/Board reporting summarizes portfolio value/spend, adoption by risk tier, approved vs pending use cases, material control exceptions, outcome realization, model/tool/vendor concentration, and emerging agentic/autonomy exposure.

### 1.6 Workstream E — agentic AI evaluation

Treat agentic AI as an exploratory design domain, consistent with the RFP.

Evaluate candidate agentic patterns across action authority/scope, tool/API permissions, identity/credential handling, output validation, planning/retry/loop behavior, memory/state boundaries, instruction injection, cross-system data movement, audit trace, human interruption/approval, rollback/compensation, model/tool failure, vendor/model drift and usage/consumption cost.

Where agentic systems are later considered, preserve a bounded control stack:

1. explicit task intent and scope;
2. least-authority tool access;
3. deterministic policy gates around protected actions;
4. evidence capture for actions and external state;
5. independent validation before material side effects where practical;
6. spend/action budgets;
7. loop/retry caps;
8. human escalation for ambiguity or high consequence;
9. replayable audit records;
10. kill/disable capability.

The engagement describes these as governance/design requirements; it does not build an agent.

### 1.7 Workstream F — pilot recommendation

Select a lower-risk candidate traceable to current-state findings. The recommendation packet includes:

- problem statement and user population;
- current baseline/cost/friction;
- value or return hypothesis;
- required data and systems;
- privacy/security/regulatory dependencies;
- required governance approvals;
- proposed human-review boundary;
- success metrics and stopping criteria;
- risk profile and mitigations;
- prerequisites;
- indicative resources and operating cost;
- high-level implementation plan;
- reasons not to proceed if prerequisites fail.

Candidate selection prioritizes feasibility and measurable value over novelty.

### 1.8 Workstream G — executive synthesis

Deliver a presentation-ready readout that lets the AI Executive Committee answer what is ready now, what is blocked and why, where value is most credible, what must change in governance/organization, which initiatives should be sequenced first, how much uncertainty remains, what should be measured next, and which decisions require executive/Board ownership.

## 2. Four-month work plan

### Phase 1 — mobilize and current state (Weeks 1–3)

- kickoff and evidence request;
- document/control inventory;
- targeted stakeholder discovery;
- readiness scoring;
- initial findings and control-gap log.

Outputs: current-state evidence map, readiness matrix, prioritized gaps, confirmed interview findings.

### Phase 2 — portfolio and operating model (Weeks 3–7)

- candidate use-case inventory;
- value/risk/feasibility scoring;
- governance lifecycle design;
- role/decision-right model;
- agentic evaluation framework;
- initial cost/measurement model.

Outputs: portfolio scorecard, governance operating model, control taxonomy, preliminary target-state structure.

### Phase 3 — roadmap and pilot recommendation (Weeks 7–12)

- three-year sequence;
- dependency/decision-gate model;
- indicative resourcing;
- cost tracking / allocation framework;
- workforce/change plan;
- pilot downselection and business-case package.

Outputs: roadmap, pilot recommendation, economics/control assumptions, implementation prerequisites.

### Phase 4 — validation and executive readout (Weeks 12–16)

- cross-functional review;
- contradiction/gap closure;
- scenario testing;
- final deliverable revision;
- executive briefing.

Outputs: accepted deliverables and executive synthesis, subject to USAC's Deliverable Acceptance Form process.

## 3. Quality and acceptance method

For each deliverable:

1. map every claim to source evidence or mark it recommendation/assumption;
2. maintain an unresolved-questions register;
3. run consistency checks across readiness findings, roadmap, governance and pilot;
4. test the roadmap against people/data/technology/control/time/cost constraints;
5. present material tradeoffs, not only a preferred answer;
6. preflight against buyer acceptance criteria before delivery;
7. incorporate buyer rejection comments within the contractual cure window.

## 4. Capabilities evidence slots

The final proposal must replace these placeholders with actual organization/team evidence:

- `[EVIDENCE: enterprise AI strategy / governance delivery]`
- `[EVIDENCE: regulated environment / federal oversight or comparable reporting]`
- `[EVIDENCE: privacy/security governance]`
- `[EVIDENCE: executive roadmap / operating-model transformation]`
- `[EVIDENCE: agentic evaluation / safe automation]`
- `[EVIDENCE: change-management / workforce enablement]`
- `[EVIDENCE: cost model / ROI / portfolio governance]`

No placeholder may become an asserted capability without retained support.

## 5. Key personnel design

Buyer-required baseline: one named AI SME, at least one additional named Key Person, no more than three additional Key People (four total maximum).

A credible team shape to validate against real available people might include AI SME/engagement strategy lead; AI governance/privacy/risk lead; operating-model/change-management lead; and data/technology readiness/economics lead.

This is role design only. Names, employers and resumes must come from real committed personnel. Buyer Q&A permits team/subcontractor employees but they must already be employed by that firm when the proposal is submitted.

## 6. With-AI and without-AI performance variants

### Without-AI variant

Perform research, evidence extraction, interview synthesis, scoring, roadmap development, quality review and presentation using conventional approved productivity tools and human-authored analytical methods.

### With-AI variant — only after USAC written approval

Potentially use approved AI for bounded internal draft summarization of non-prohibited source material, structured comparison of policy/control text, drafting alternatives for human review, qualitative coding support, and consistency checking across draft artifacts.

Controls: only buyer-approved tool/service/model; no USAC data in unapproved systems; human authorship/approval of deliverables; verify source/claim correspondence; no autonomous external actions; no hidden deployment/production integration; capture material AI-assisted steps if buyer policy requires it.

The alternate price scenario includes contractor-provided tool/subscription cost. No AI use is assumed approved at proposal time.

## 7. Explicit exclusions

This strategy engagement does not include production model development/deployment, operating an AI service for USAC, direct automation of USF program decisions, production agent execution, software procurement on USAC's behalf, bypassing USAC security/privacy/tool approval, interpreting unclear FCC policy, or legal advice.

## 8. Proposal red-team questions

1. Does every methodological statement say **how**, rather than merely restate the SOW?
2. Is every claimed capability linked to real evidence?
3. Are agentic recommendations exploratory rather than predetermined adoption?
4. Is the pilot demonstrably lower-risk and feasible within current constraints?
5. Are all programs/divisions addressed without inventing access to buyer data?
6. Are governance roles compatible with USAC's existing committees rather than assuming replacement?
7. Are cost tracking, forecasting and program-line allocation explicitly handled?
8. Are privacy/security/FCC neutrality constraints visible throughout the method?
9. Does the AI-use section separate consulting content from AI tools used to perform the engagement?
10. Can the engagement still be delivered if USAC approves **no AI tools** for contractor use?
11. Does the four-month schedule contain all major deliverables?
12. Are deliverable acceptance/rework windows represented in the delivery plan?
