# UIOWA-020 — Framework adaptation memo

## Objective

Use primary NIST frameworks to make the RFQ 18649 assessment more repeatable and auditable **without** converting the engagement into a certification exercise, a compliance audit, a procurement review, or an invented maturity-scoring program.

The framework crosswalk supplies a shared vocabulary for four RFQ assessment areas:

- software development
- security
- deployment and operations
- AI readiness

It is an assessment aid. University evidence remains the basis for findings.

## Evidence model

Each conclusion should preserve the distinction between these evidence states:

| Evidence state | Meaning | Examples |
|---|---|---|
| **Documented intent** | A policy, standard, procedure, or role states what should happen. | security standard, SDLC policy, RACI, AI-use policy |
| **Demonstrated implementation** | A sampled artifact or workflow shows the practice operating. | repository rule, review record, deployment pipeline, access review |
| **Measured outcome** | A defined measure shows a result over a stated population and period. | restore success rate, change failure measure, remediation distribution |
| **Contradictory evidence** | Sources disagree or sampled practice differs materially from stated intent. | policy requires review but sampled emergency path bypasses it without recorded exception |
| **Unknown / not established** | Available evidence cannot support a conclusion. | missing denominator, inaccessible logs, unverified ownership |

Do not silently promote documented intent into demonstrated implementation or measured outcome.

## Crosswalk use

### 1. Software development

Use SSDF as the main secure-development practice reference, supported by CSF where development intersects governance, dependencies, identity, platform security, and improvement.

Questions should test actual operating behavior, for example:

- How are development security requirements established and changed?
- Which repositories and delivery paths are subject to review, testing, or release criteria?
- How are exceptions authorized and later revisited?
- How are third-party components inventoried and updated?
- What evidence shows that findings feed back into design, coding, and release practices?

**Boundary:** SSDF is a secure-software-development framework. It does not by itself define the full quality, product-management, architecture, accessibility, or service-management practices needed by the engagement.

### 2. Security

Use CSF 2.0 Core outcomes as the primary organizing vocabulary, with SSDF for software-producing teams and AI RMF where AI systems or AI-assisted workflows are actually present.

Useful assessment moves include:

- establish the service and stakeholder context before judging controls;
- separate policy from sampled implementation;
- connect identity/access, asset/service knowledge, monitoring, incident handling, and recovery to specific services;
- retain denominators and time periods for any quantitative claim;
- record exceptions and risk acceptance instead of treating variance as automatic failure.

**Boundary:** CSF outcomes are non-prescriptive. This work does not assert certification or a single correct technical implementation.

### 3. Deployment and operations

Use CSF categories such as PR.PS, PR.IR, DE.CM, DE.AE, RS.MA, RS.AN, RS.MI, RC.RP, and RC.CO to structure service reliability/security evidence. Use SSDF PS and RV practices where release integrity and vulnerability response cross into operations.

Potential evidence includes:

- service ownership and dependency maps;
- environment and deployment controls;
- change/release records;
- telemetry coverage and alert definitions;
- incident and recovery records;
- restore or continuity tests;
- vulnerability intake and remediation records.

**Boundary:** Raw counts—alerts, incidents, deployments, vulnerabilities—are not comparable measures without definitions, scope, severity mix, service scale, and denominator.

### 4. AI readiness

Use AI RMF 1.0 to assess whether AI-enabled workflows, where present, have bounded purposes, ownership, evaluation, oversight, monitoring, and stop/rollback paths.

The assessment should first establish the use case:

1. Is an AI capability actually used, piloted, or proposed in the workflow?
2. What purpose, users, data, decisions, and dependencies are in scope?
3. Who owns approval, operation, evaluation, monitoring, and retirement?
4. What evidence supports fitness for that particular use?
5. What happens when evidence no longer supports continued use?

**Boundary:** Public University AI guidance is not evidence that ESS, RIS, or IAM uses AI. AI RMF should not create a presumption of adoption.

## Calibration across ESS, RIS, and IAM

Framework mappings must not erase local operating context. The assessment should:

- evaluate ESS, RIS, IAM, and shared services separately before drawing cross-cutting conclusions;
- preserve service criticality, academic/research calendar constraints, data sensitivity, stakeholder population, and externally managed dependencies;
- distinguish a common enterprise expectation from a local implementation choice;
- treat a single team's sample as evidence about that sample, not automatically about AIS or the University as a whole;
- record contradictory evidence and unresolved questions rather than forcing consensus.

## Profiles and target state

CSF 2.0 Organizational Profiles can support a useful **Current → Target → Action** structure:

- **Current:** what evidence shows now;
- **Target:** the outcome the University chooses to pursue;
- **Gap:** the difference, with context;
- **Action:** a practical improvement, owner, dependency, and sequencing note.

This structure is descriptive and decision-oriented. It must **not** be translated into “Level 1–5,” percentages, percentiles, or a TJLabs-created maturity ranking unless the parties separately agree to a validated scoring methodology.

## CSF Tiers

CSF Tiers may be used, if useful to the University, as contextual language about the rigor of cybersecurity risk governance and management. They are not treated here as:

- empirical benchmarks;
- certification levels;
- a vendor-neutral “maturity score”;
- a basis for ranking ESS, RIS, IAM, or peer institutions.

If Tiers are discussed in a report, the cited CSF 2.0 definition and the local evidence supporting the characterization must be visible.

## Quantitative evidence

A metric is reportable only when its interpretation can be reconstructed. Capture at minimum:

- definition;
- numerator and denominator, when applicable;
- population/scope;
- period;
- source system;
- exclusions;
- whether it is a target, observation, or externally published benchmark.

If one of those is missing, state the limitation. Do not invent a denominator or infer a trend from a single point.

## Framework-to-finding trace

For each material assessment finding, maintain a trace that can answer:

1. **What University evidence supports the statement?**
2. **What evidence state is it—intent, implementation, outcome, contradictory, or unknown?**
3. **Which service/team/population and period does it apply to?**
4. **Which framework locator, if any, helps interpret it?**
5. **What part of the conclusion is NIST source language versus TJLabs/Clark's proposed assessment design?**
6. **What practical improvement follows, and what local constraint affects it?**

The framework citation is never a substitute for the University evidence.

## Recommended artifact request patterns

| Assessment area | High-value artifacts |
|---|---|
| Software development | SDLC standards; repository/change-control configuration; peer-review samples; test/scan records; dependency inventories; build/release records; exception records |
| Security | service/asset inventories; IAM lifecycle/access-review evidence; risk records; vulnerability records; monitoring coverage; incident/recovery records |
| Deployment/operations | service maps; deployment/change records; environment controls; SLO/SLA definitions where used; telemetry/alert coverage; incident retrospectives; restore/continuity tests |
| AI readiness | use-case inventory; ownership/approval records; data/model/provider inventories; evaluation plans/results; human-oversight design; monitoring; incident/rollback/retirement procedures |

## Freshness rule

The source register records the versions used to design the assessment. NIST states in 2026 that AI RMF 1.0 is undergoing revision, so the team should recheck the primary publication pages:

- at kickoff,
- before final evidence synthesis,
- before the final report/readout.

A new release should trigger an explicit version-impact note, not a silent framework swap.

## What this deliverable enables

The crosswalk and memo can now be used to build:

- interview guides with source-linked prompts;
- evidence-request lists;
- finding templates that separate evidence from interpretation;
- a Current/Target action register;
- QA checks that reject unsupported certification, compliance, or maturity claims;
- final-report appendices showing exactly how external framework concepts were adapted.
