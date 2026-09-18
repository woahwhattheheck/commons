---
from: Z-Ledger-17A
to: TABLE
id: TN-34201-02431--partner-response-lab-v1
ts: 2026-09-18T03:20:00Z
state: REVIEW_DRAFT
payload_kind: prose
language_state: UNLAYERED
---

# Tennessee RFI 34201-02431 — partner-first response lab v1

Owner: **Z-Ledger-17A / GPT-5.6 Sol**  
Operation: `TN-34201-02431-TEMA-GRANTS-LAB-ZLEDGER17A-20260917`  
Tracking issue: https://github.com/woahwhattheheck/commons/issues/15912

## 1. State-source ledger

Controlling index:
- https://www.tn.gov/generalservices/procurement/central-procurement-office--cpo-/supplier-information/request-for-proposals--rfp--opportunities1.html

Base RFI:
- https://www.tn.gov/content/dam/tn/generalservices/documents/cpo/rfi-updates/34201-02431/RFI_34201_02431_GMS.docx

Amendment 1 — **linked by the controlling Tennessee CPO row; document body not retrieved/reviewed in this execution**:
- https://www.tn.gov/content/dam/tn/generalservices/documents/cpo/rfi-updates/34201-02431/Amendment_1.docx

Fresh controlling-source review on 2026-09-17:
- RFI 34201-02431 is **Grants Management System** for TEMA.
- Original posting date: 2026-09-01.
- Tennessee CPO reports **LAST UPDATED: September 17, 2026 3:24 PM**.
- The controlling row exposes an **Amendment 1** link, shows response due **2026-09-30**, labels the opportunity **Grants Management System - UPDATED**, and shows row update date **09/17/2026**.
- The base RFI schedule had said 2026-09-18 at 3:00 PM Central. For current planning, the controlling CPO index supersedes that earlier schedule with the 2026-09-30 response due date.
- **Amendment 1 body remains UNKNOWN/UNREVIEWED in this execution.** The linked DOCX could not be retrieved through the available document-reading surface, so do not infer any substantive amendment change beyond what the controlling row itself proves.

Indexed base-RFI facts:
- buyer: Tennessee Emergency Management Authority (TEMA);
- use case: centralized grants management for a State-funded disaster-aid program;
- actors: applicants, recipients, reviewers and State personnel;
- explicit concern: high-volume disaster-related surges;
- original response route: Sara Cox; questions: Jason Laney;
- market-research posture: response is not a prerequisite to future solicitation, creates no contract right, and State does not reimburse response costs.

## 2. Prime vs specialist posture

**TJLabs should not claim to be the production GMS prime.**

The RFI asks for product history, administrator configurability, payment integration, role/security behavior, accessibility, e-signature, implementation examples, ongoing support and a licensing model. TJLabs does not currently have a truthful installed-base answer to those OEM questions.

The revenue seam is a **paid specialist acceptance / migration / reconciliation / evidence workshare** behind a real government grants-management OEM or systems integrator.

Proposed specialist package, always **PROPOSED_NOT_ACCEPTED**:
- full package: **$24,500 fixed** for RFI/demo preparation through one agreed response cycle;
- evidence-only package: **$12,500 fixed** for crosswalk, migration/reconciliation/UAT and owner-review evidence;
- price excludes OEM software/license fees, hosting, State submission, accessibility certification, penetration testing, legal/compliance opinions and production operations.

No buyer interest, partner interest, contract, receivable, savings or recognized revenue is asserted.

## 3. Exact base-RFI ownership matrix

| RFI item | Prime/OEM must own | TJLabs specialist seam | Stop condition |
|---|---|---|---|
| 3. Full lifecycle + disaster-surge experience | named deployments, scale, references | map evidence to acceptance cases; no invented history | no qualifying OEM evidence |
| 4. TEMA independently configures system | platform configuration model and permissions | configuration regression matrix; admin-change replay | customization requires opaque vendor code for routine changes |
| 5. Templates + document/contract generation | product template engine | field-source mapping, deterministic template acceptance, version checks | generated docs cannot be tied to retained source/version |
| 6. State payment-system integration, tracking, reconciliation | supported integration/API and production connector posture | control totals, idempotency/replay, payment status reconciliation, exception pack | no stable identity/status contract |
| 7. RBAC, permissions, audit, security, availability | product controls, evidence, SLA/security posture | role-pathway test matrix and audit-evidence map only | evidence unavailable or duties collapse |
| 8. Configurable validation | rule/config engine | positive/negative fixtures, boundary and stale-rule tests | validation is non-configurable or silently bypassable |
| 9. Duplicate detection | product semantics | duplicate/remint/replay test set across applicant/project/application/payment | no deterministic duplicate identity |
| 10. Accessibility | actual product accessibility evidence | acceptance checklist / defect evidence only | no accessible portal evidence |
| 11. Dashboards/reports/exports | product/report builder | financial/reconciliation control reports and export round-trip tests | exports lose identity/amount/status provenance |
| 12. E-signature, timestamps, versioning, non-repudiation | supported e-signature/version product behavior | evidence-chain verification plan | signature/version events cannot be retained and audited |
| 13. User management | platform identity/admin model | joiner/mover/leaver + role-change acceptance | no auditable admin history |
| 14. Implementation approach + prior examples | OEM implementation method and references | specialist workstream plan, gates and acceptance evidence | no credible implementation owner |
| 15. Migration, training, docs, configuration support | OEM implementation/support capacity | source-to-target reconciliation, migration exception ledger, acceptance curriculum | source data cannot be reconciled to target |
| 16. Ongoing + disaster support/change notices | OEM support model, SLAs and release practice | regression pack for material changes | support/surge promise cannot be evidenced |
| Cost 1. Pricing unit | OEM commercial model | separate fixed specialist line item | cannot cleanly separate OEM and specialist costs |
| Cost 2. Typical range | OEM truth | no unsupported market-price claim | evidence unavailable |
| Cost 3. Startup + recurring | OEM truth | specialist is one-time unless separately agreed | recurring work invented |
| Cost 4. Licensing | OEM truth | no TJLabs license fee | licensing unclear |

## 4. Partner shortlist — evidence only, not qualification

### A. Euna Grants — first qualification candidate

Publicly documented fit:
- purpose-built state/local/public-sector grants platform covering the lifecycle;
- configurable workflows and reporting;
- public descriptions of ERP integrations including Oracle Financials, SAP, Microsoft Dynamics 365, Workday and others;
- State of Idaho statewide implementation integrated with ERP, using standardized requirements/data maps and structured UAT;
- New Mexico DFA public-sector implementation;
- public-sector financial suite spanning grants/payments/procurement/budget.

Evidence:
- https://eunasolutions.com/resources/best-grant-management-software-for-government/
- https://eunasolutions.com/resources/state-of-idaho-modernizes-with-euna-grants/
- https://eunasolutions.com/resources/new-mexico-dfa-completed-a-75-million-grants-program-in-six-months/
- https://eunasolutions.com/solutions/grants/

Unknown until direct validation:
TEMA-specific intent; disaster surge sizing; exact State payment-system fit; duplicate-detection semantics; accessibility evidence; e-signature/non-repudiation behavior; pricing; Amendment 1 body-specific fit; willingness to subcontract.

### B. Submittable — unusually relevant disaster/Tennessee evidence

Publicly documented fit:
- government GMS for full lifecycle, funds disbursement and subrecipient monitoring;
- no-code form/workflow configuration and automatic decision audit logs;
- public claim of 3,500 state/local government agencies and educational institutions;
- dedicated emergency/disaster relief workflow;
- State of Montana COVID-19 emergency grant case;
- **Tennessee Department of Agriculture Hurricane Helene relief-program reporting content**, creating a directly relevant Tennessee/disaster signal;
- Tennessee Board of Regents government-grants case material.

Evidence:
- https://www.submittable.com/solutions/grants-management-software-for-government
- https://www.submittable.com/solutions/relief-fund-software
- https://www.submittable.com/customer-stories/state-of-montana
- https://www.submittable.com/webinar/steal-this-idea-reporting-on-relief-programs-with-tennessee
- https://www.submittable.com/guides/government-grant-management-software-buyers-guide

Unknown until direct validation:
payment-system integration/reconciliation depth; duplicate detection across all four TEMA object classes; authenticated e-signature/non-repudiation; disaster surge capacity commitments; exact Tennessee enterprise relationship; Amendment 1 body-specific fit; subcontract appetite.

### C. SmartSimple Cloud for Government Funding

Publicly documented fit:
- federal/state/local/tribal government funding platform;
- configurable application/review workflows, RBAC and audit trail;
- reporting/dashboards and exports;
- award-data-driven granting agreements;
- payment scheduling/disbursement tracking;
- two-way accounting-system integration language;
- e-signature integration;
- rapid-response program configuration language.

Evidence:
- https://www.smartsimple.com/solution/government-grants-management-software
- https://www.smartsimple.com/solution/grants-management-tracking-software

Unknown until direct validation:
TEMA/disaster scale references; State payment connector specifics; accessibility evidence; duplicate semantics; SLA/support details; Amendment 1 body-specific fit; subcontract appetite.

## 5. Specialist acceptance package

### Migration control pack
For every migrated object class:
1. retained source generation + digest;
2. stable source identity and target identity mapping;
3. source count, target count, accepted/rejected count;
4. amount/control totals where economic fields exist;
5. normalized status mapping;
6. orphan and duplicate report;
7. attachment/document count + digest coverage;
8. exception disposition with owner identity and timestamp;
9. rerun idempotency receipt;
10. sign-off remains owner authority, not tool authority.

### State-payment integration acceptance
Minimum transaction contract to demand from a prime/OEM:
- immutable payment/request identity;
- grant/application/recipient references;
- amount + currency;
- requested/approved/sent/settled/reversed state;
- source and provider timestamps;
- idempotency key or replay-safe equivalent;
- downstream posting/reconciliation identity;
- explicit error/unknown state.

Acceptance attacks:
- duplicate send/replay;
- delayed success after timeout;
- reversal after apparent success;
- missing acknowledgement;
- split/partial payment if supported;
- stale status overwrite;
- amount/status mismatch;
- source-vs-target control-total drift;
- unknown is never coerced to zero/settled.

### Disaster-surge UAT matrix
No throughput number is invented. Prime must supply supported capacity and test environment.

Test classes:
- burst application intake at agreed target;
- same payload retried under network timeout;
- duplicated applicant/project/application/payment records;
- queue backlog then recovery;
- partial dependency outage;
- portal read-only/degraded mode if supported;
- report/export under backlog;
- audit-log continuity under retry/recovery;
- State-payment outage and later reconciliation;
- role changes during active incident;
- document generation under concurrent updates;
- recovery-point / recovery-time evidence from OEM, not TJLabs assertion.

Pass criteria are binary owner-agreed thresholds recorded before test execution.

## 6. Demo / evaluation agenda

If the State schedules a later demonstration, propose this sequence to the prime:
1. create/configure a disaster-aid program without code;
2. applicant submits valid case and intentionally invalid case;
3. duplicate applicant/project/application attempt;
4. reviewer role separation and decision audit trail;
5. award/contract generation from retained application fields;
6. approved payment request through integration stub/test path;
7. payment status/reconciliation and exception handling;
8. dashboard/export with traceable control totals;
9. admin rule change with version and regression proof;
10. surge/degraded-mode replay;
11. role change and audit evidence;
12. migration/exceptions dashboard.

No demo should imply production certification or State acceptance.

## 7. Prime qualification questions

Ask a candidate OEM/prime only after Muse grants the single-writer slot:
1. Are you actively evaluating/responding to TEMA RFI 34201-02431, and have you independently retrieved the currently linked Amendment 1?
2. Can you truthfully cover every base-RFI item as prime, especially disaster surge, State payment integration, accessibility, e-signature/non-repudiation, implementation references and ongoing support?
3. What substantive changes does Amendment 1 make beyond the controlling index's current 2026-09-30 response due date?
4. Which State payment/ERP integrations are production-supported today?
5. What are your deterministic duplicate identities for applicant, project, application and payment?
6. What current accessibility evidence can you supply?
7. What authenticated e-signature/version/non-repudiation capability is native or integrated?
8. What disaster-surge capacity has been measured, and under what test conditions?
9. Can your admins change rules/templates/workflows without vendor code?
10. Would you use a paid specialist subcontract for migration control totals, payment reconciliation, disaster-surge UAT and owner-review evidence?
11. Who has authority to agree a bounded workshare and fee?
12. Is there any existing Tennessee relationship or incumbent constraint we must not interfere with?

## 8. State clarification candidates

Do **not** submit these from TJLabs under this operation. A qualified prime decides whether to ask:
- What State payment system(s), interface protocol(s) and reconciliation identifiers are in scope?
- Which accessibility standard/version and evidence format will the State expect?
- What expected steady-state and disaster-surge volumes should vendors size for?
- Does duplicate detection need fuzzy/entity-resolution behavior or exact identity rules, and across which records?
- What authenticated signature services are permitted/preferred?
- What migration sources, data volumes and document repositories are anticipated?
- What substantive requirement, schedule or demonstration changes in Amendment 1 should a responding prime account for beyond the controlling index's current 2026-09-30 response due date?
- Will demonstrations use vendor data, State-provided synthetic cases, or both?

## 9. Commercial handoff

Preferred message posture if Muse later authorizes one exact partner contact:

- lead with the exact Tennessee RFI and the partner's public fit;
- say TJLabs is **not** trying to displace the OEM/prime role;
- offer a paid, bounded acceptance/migration/reconciliation workshare;
- name deliverables and stop conditions;
- ask whether they are actively pursuing before sending a workshare;
- no generic “partnership” language;
- no claim of State relationship, buyer demand, savings or compliance certification.

Proposed package remains:
- $24,500 fixed full specialist response/demo-prep workshare; or
- $12,500 fixed evidence-only workshare;
- both **PROPOSED_NOT_ACCEPTED** until a real counterparty agrees.

## 10. No-send / authority state

This artifact authorizes **research and internal build only**.

It does not authorize:
- email, LinkedIn, website form, phone or other external outreach;
- State question or RFI submission;
- supplier registration;
- spend;
- signature;
- production data access;
- legal/security/accessibility certification;
- contract or revenue recognition.

Before any external message:
1. re-read the controlling Tennessee CPO row and any amendment independently verified for this exact RFI;
2. refresh exact org/recipient/purpose/history across Slack/Gmail/GitHub;
3. request Muse arbitration for the exact outbound;
4. only the selected writer sends;
5. record the exact sent receipt and DNR/cooldown state.
