# Proposal skeleton — public-record-safe draft architecture

This is a response **structure**, not a submitted proposal. Replace every bracketed field only with verified business evidence.

## 1. Executive response

MMSD needs one policy system that governs two very different AI surfaces: administrative/generative tools and operational/embedded AI touching wastewater, infrastructure and plant modernization. Our recommended approach is to produce a policy plus an operating toolkit that staff can actually use: inventory, risk tier, decision authority, allowed data, vendor controls, recordkeeping, incident path, review cadence and role-based training.

State the proposed outcome in one sentence:

> A repeatable MMSD AI governance system that permits useful low-risk adoption while requiring progressively stronger evidence, human authority, data safeguards and operational review as AI risk increases.

Then state only verified qualifications: `[legal entity]`, `[named lead]`, `[comparable engagements/references]`, `[insurance status]`.

## 2. Understanding of MMSD’s problem

Frame the work around five connected constraints:

1. **Mixed AI modalities.** GenAI drafting assistants and operational/process AI cannot share one blunt control regime.
2. **Critical-utility consequences.** Operational use must account for availability, safety, environmental/process integrity, manual fallback and change control—not just privacy or hallucination risk.
3. **Public-record reality.** AI prompts, outputs, decision logs, vendor records and policy artifacts need intentional records treatment and counsel/custodian validation.
4. **Data sovereignty and vendors.** Governance must follow data through hosted models, subprocessors, support channels, telemetry, retention/training settings and exit/deletion.
5. **Adoption.** Staff need an understandable allowed/prohibited/escalate model; a policy that requires lawyers/security to interpret every ordinary use will drive shadow AI rather than control it.

## 3. Method — six phases

### Phase 0 — kickoff and evidence map

- confirm decision owners, legal/records/security/IT/operations/procurement stakeholders;
- inventory existing policies, architecture, vendor-risk and records artifacts;
- agree definitions, project controls, interview/sample plan and acceptance criteria;
- establish an issue/decision register so unresolved policy choices are explicit.

**Outputs:** evidence request, stakeholder map, decision register, project calendar.

### Phase 1 — AI inventory and current-state assessment

Build a normalized register for:

- owner/business process;
- AI type and purpose;
- vendor/product/model where known;
- inputs/data classes;
- outputs/actions;
- integration/system access;
- level of autonomy / human approval;
- records generated;
- operational dependency and fallback;
- vendor data use/residency/retention/subprocessors;
- current controls and known gaps.

Use interviews plus a bounded shadow/embedded-AI discovery method. The inventory is a governance baseline, not a promise of exhaustive forensic detection unless the RFP specifically requires it.

**Outputs:** current-state inventory, shadow/embedded-AI observations, gap heat map.

### Phase 2 — risk taxonomy and tiering

Propose a risk model mapped to NIST AI RMF functions but tuned to MMSD. Score at least:

- consequence to treatment/infrastructure/environment/safety;
- data sensitivity and sovereignty;
- external/public impact;
- decision/action autonomy;
- model uncertainty / verifiability;
- vendor and change-control exposure;
- records/transparency implications;
- recoverability/manual fallback.

Illustrative tiers:

- **Tier 0 — prohibited:** uses that violate law/policy or delegate nondelegable authority.
- **Tier 1 — routine assistive:** low-consequence drafting/analysis using approved data/tools and required human review.
- **Tier 2 — controlled business:** material internal decisions, sensitive data, integrated workflows, or externally visible outputs requiring documented owner/review controls.
- **Tier 3 — high impact / operational:** systems affecting infrastructure/treatment/safety, regulated determinations, or autonomous actions; require formal assessment, technical validation, human authority, monitoring, rollback and incident controls.

Final tier names/rules belong to MMSD and must align to its existing policies and legal advice.

### Phase 3 — policy + operating controls

Draft policy and companion standards covering:

- scope/definitions and approved/prohibited/escalate use;
- roles and governance body/accountability;
- use-case intake and approval;
- data classification, sovereignty, prompt/input/output handling;
- records creation/retention/disclosure workflow;
- human review and nondelegable authority;
- model/vendor procurement due diligence;
- subprocessors, retention, training-use, residency and deletion requirements;
- testing/validation for operational/high-risk AI;
- monitoring, material-change review and periodic recertification;
- incident reporting, containment, rollback and evidence preservation;
- access controls, secrets and system integration;
- transparency/disclosure where required;
- exception and emergency process;
- employee responsibilities and enforcement;
- policy/version/change governance.

**Outputs:** policy draft, standards/control catalog, vendor questionnaire/contract-control checklist, use-case assessment, incident playbook, exception form.

### Phase 4 — scenario validation

Run tabletop / walkthrough cases across both GenAI and Operational AI, for example:

- employee drafts public communication with GenAI using internal material;
- SaaS AI feature silently changes retention/training terms;
- AI-assisted analysis informs an engineering recommendation;
- embedded ML alarms/drift conflict with operator observations;
- agent/workflow attempts an action beyond delegated authority;
- public-record request reaches AI prompts/outputs/decision logs;
- vendor materially changes model/subprocessor;
- sensitive information is accidentally entered into an unapproved tool.

Each scenario should produce the same things staff will need in reality: owner, tier, allowed/prohibited state, evidence, human decision, record, incident path and closeout.

### Phase 5 — training, adoption and handoff

Create role-specific training for at least:

- general staff;
- managers/use-case owners;
- IT/security/data;
- procurement/vendor management;
- records/legal stakeholders;
- engineering/operations/lab staff where scope confirms.

Leave MMSD with a maintainable toolkit: AI register, assessments, vendor checklist, decision templates, incident/evidence forms, training materials, policy-update cadence and a 30/60/90-day adoption backlog.

## 4. Quality and acceptance

Propose measurable acceptance rather than “deliver report”:

- inventory fields populated to agreed coverage/sample threshold;
- every identified use has owner + tier + disposition;
- control requirements trace to each tier;
- policy language passes designated MMSD legal/records/security/operations review;
- tabletop cases produce deterministic decision routes;
- vendor questionnaire covers agreed data/model/change fields;
- training artifacts delivered and agreed sessions completed;
- final policy + toolkit incorporate comment matrix and are version controlled;
- unresolved owner decisions are explicitly listed, never silently guessed.

## 5. Team and relevant evidence

Only insert evidence that can survive public scrutiny:

- `[named project lead + role + availability]`
- `[public-sector AI governance reference]`
- `[utility/wastewater/critical-infrastructure reference]`
- `[data governance/security/public-records experience]`
- `[training/change-management experience]`
- `[technical AI/agent governance artifacts]`

Internal prototypes may support technical capability but are **not** customer references.

## 6. Schedule

If the secondary six-month term is confirmed, propose a schedule such as:

- Weeks 1–2: kickoff/evidence map;
- Weeks 2–6: inventory/interviews/current state;
- Weeks 5–9: taxonomy/tiering/control design;
- Weeks 8–14: policy/toolkit drafts;
- Weeks 13–18: review/scenario validation;
- Weeks 17–22: revisions/training;
- Weeks 21–24: final adoption/handoff.

Adapt to official milestones; do not commit dates until named staff availability is confirmed.

## 7. Pricing

Use only the official requested format. Internally model price from:

- PM/governance lead hours;
- AI technical/operational specialist hours;
- security/data/vendor-risk hours;
- records/legal liaison effort (not unauthorized legal services);
- interviews/workshops/training;
- policy/toolkit drafting and revision rounds;
- travel/on-site assumptions;
- subcontractor costs;
- insurance/administrative burden;
- contingency for scope that the bid document actually requires.

State assumptions and optional services separately. Do not lowball the engagement by pretending the inventory, stakeholder process and training are a memo-writing exercise.

## 8. Exceptions / assumptions

Include an explicit table for contract exceptions, scope assumptions, client dependencies and excluded activities. Examples: legal advice remains with MMSD counsel; penetration testing or process-control certification is excluded unless expressly included; MMSD provides timely access to stakeholders/policies/vendor records; implementation of third-party technical controls is separate unless priced.

## 9. Public-record hygiene before submission

Final red-team review must remove:

- secrets/tokens/private URLs;
- unnecessary customer-confidential detail;
- internal Slack or agent-coordination text;
- unsupported revenue/performance claims;
- unapproved personal information;
- hidden comments/revision history;
- invented qualifications, certifications, references or insurance statements.