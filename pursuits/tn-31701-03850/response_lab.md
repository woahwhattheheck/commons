# Response Lab — Tennessee RFI 31701-03850

Internal drafting and partner-workshare artifact. **Not a State response and not send authority.**

## 1. Positioning

The credible commercial lane is not “TJLabs already operates a statewide cashiering SaaS.” It is:

> **Independent integration, migration-acceptance, reconciliation and UAT workshare behind a qualified cashiering OEM / public-sector SI.**

The prime owns the production cashiering platform, certifications, hosting, hardware, processor relationships, SLAs and support. TJLabs owns a bounded acceptance/control layer that makes interfaces and financial outcomes testable and reviewable.

### Why this posture fits the packet

The RFI combines:
- product qualification and operating evidence (PCI, SOC 2, uptime, support, DR);
- broad cashiering/UI/hardware functionality;
- Edison and payment-processor integration;
- high-value accounting and reconciliation controls.

The first two categories require an established product owner. The latter two are where a specialist acceptance/reconciliation workshare can add leverage without inventing product history.

## 2. Target workshare

### A. Interface contract and Edison acceptance

Deliver:
- source/target field catalog;
- accounting-distribution / ChartField mappings;
- deterministic interface fixtures;
- success/failure/retry semantics;
- idempotency and duplicate handling;
- batch/payment/deposit lineage;
- exact exception ledger;
- replayable acceptance receipts.

RFI anchors: 37-42, 70, 111-115.

### B. Cashier/batch/deposit reconciliation

Acceptance invariants:
1. every retained transaction belongs to exactly one accepted batch generation;
2. tender totals equal the batch total (Req. 110);
3. expected, actual and variance are independently represented;
4. drawer variance and deposit variance remain distinct (Req. 109);
5. over/short has exact minor-unit arithmetic (Req. 106);
6. threshold exceptions require retained reason evidence (Req. 107);
7. approvals bind the exact variance generation (Req. 108);
8. a reopened batch is a new authorized state with reason/audit lineage (Req. 101);
9. finalized batches reject unauthorized mutation (Req. 102);
10. deposit construction preserves batch membership and partition criteria (Reqs. 97-98).

RFI anchors: 54-55, 64, 66, 68, 83-89, 92, 95-118.

### C. Migration acceptance

Do not assume “database migrated” means “business state migrated.”

Inventory separately:
- active/inactive users and groups;
- office/location/collection-point structure;
- tenders and payment types;
- allocations/accounting distributions;
- effective-dated configuration;
- receipt/payment forms;
- open and historical batches;
- transaction/document links;
- exception queues;
- processor/interface configuration;
- audit history and retention state.

For every migration generation:
- retained source digest / export identity;
- record-count and amount controls;
- reject/exception inventory;
- normalized mapping version;
- target-load receipt;
- post-load reconciliation;
- owner approval / HOLD.

Historical public iNovah documentation shows Draft/Current/Last Current deployment state, effective-dated allocation configuration, configurable interface types and offline batch-exception behavior. Treat that as **architecture context only**; re-verify the actual current State environment before external use.

### D. Parallel run / cutover evidence

For each pilot cohort:
- same-day source snapshot;
- incumbent result;
- proposed-system result;
- exact difference set;
- tender/batch/deposit/accounting totals;
- processor settlement outcome;
- Edison posting outcome;
- unresolved HOLD queue;
- rollback decision.

No “go live” recommendation while unresolved material differences remain.

## 3. Reference architecture

```text
[Cashier / Agency users]
          |
          v
[Qualified prime cashiering platform]
  |       |        |        |
  |       |        |        +--> receipt / document / reporting
  |       |        +-----------> hardware / Check21 / RDC
  |       +--------------------> card / ACH processor integration
  +----------------------------> Edison / agency interfaces
          |
          v
[Acceptance & evidence sidecar — TJLabs workshare]
  - source/target contract
  - replay fixtures
  - control totals
  - exception ledger
  - batch/deposit/accounting reconciliation
  - immutable acceptance receipts
  - UAT / cutover evidence pack
          |
          v
[Owner review / prime / State acceptance authority]
```

### Authority boundaries

The sidecar:
- may observe retained test/export evidence;
- may calculate deterministic differences and controls;
- may emit review artifacts;
- may never post to Edison;
- may never move money;
- may never authorize refunds, voids, deposits, batches or close;
- may never claim State acceptance;
- may never replace prime security/compliance evidence.

## 4. Synthetic demonstration plan

All demonstrations use synthetic/fake data.

### Demo 1 — tender to batch conservation
Cash + check + card + ACH lines -> split tenders -> exact batch total -> deliberate one-cent mismatch -> HOLD.

Anchors: 60-61, 68, 104, 106, 110.

### Demo 2 — batch to deposit lineage
Multiple batches -> authorized consolidation -> separate card/check deposits -> retained membership -> deliberate duplicate batch -> HOLD.

Anchors: 97-109.

### Demo 3 — accounting distribution / Edison bridge
Payment type -> multiple allocations -> Company/BU/Department/ChartField mapping -> amount/percentage split -> invalid combination -> HOLD.

Anchors: 95, 111-115.

### Demo 4 — bank reconciliation
Synthetic bank statement/retained statement intake -> deposit expectation -> matched/unmatched items -> exact exception queue.

Anchor: 117. Reuse current SMB bank/GL, BAI2 or camt.053 control patterns only after exact-main readback.

### Demo 5 — refund/reversal lineage
Original payment -> partial refund -> reversal/adjustment -> original-document reference -> audit chain.

Anchors: 66, 85, 118.

### Demo 6 — effective-dated configuration
Current allocation/payment rule -> future-dated change -> pre/post-boundary transaction -> rollback generation.

Anchors: 83, 91, 94-96.

### Demo 7 — offline/reconnect exception
Synthetic offline batch -> reconnect -> duplicate/reordered replay -> explicit exception rather than silent double acceptance.

Anchor: 72 plus reconciliation controls.

### Demo 8 — AI hard-disable boundary
If prime includes AI: demonstrate “AI disabled” path and prove core cashiering/reconciliation continues without model calls or State-data egress.

Anchors: 24-28, 32.

## 5. Implementation / UAT / rollout

### Phase 0 — partner qualification and proof inventory
Before proposal claims:
- prime product/version;
- legal entity / contract vehicle;
- SOC 2 report date/scope;
- PCI posture/AOC;
- cyber insurance;
- hosting/subprocessors/data regions;
- uptime/SLA history;
- accessibility evidence;
- processor/Check21/hardware certifications;
- comparable references.

Any missing mandatory evidence remains a GAP, not optimistic prose.

### Phase 1 — discovery and interface contract
- agency/location inventory;
- transaction/tender/batch volumes;
- current interfaces and file/API formats;
- Edison posting and lookup boundaries;
- processor and bank dependencies;
- historical/configuration migration scope;
- retention requirements;
- cutover constraints.

### Phase 2 — sandbox / acceptance harness
- synthetic data only unless State authorizes an onshore environment;
- build replay fixtures;
- verify mapping/control totals;
- classify expected exceptions;
- lock acceptance criteria.

### Phase 3 — migration dry runs
Run at least two repeatable exports/loads with:
- count controls;
- amount controls;
- identity/duplicate controls;
- config parity;
- open-batch treatment;
- history/document treatment;
- issue burn-down.

### Phase 4 — UAT + training
UAT roles:
- cashier;
- supervisor;
- agency administrator;
- accounting/reconciliation;
- security administrator;
- central F&A / ERP;
- support/operations.

Test classes:
- happy path;
- threshold/boundary;
- authorization denial;
- offline/reconnect;
- processor/interface failure;
- duplicate/replay;
- effective-date;
- period close/reopen;
- cross-location;
- accessibility;
- recovery/rollback.

State resources requested: product owners, Edison interface SMEs, agency cashier supervisors, central accounting/reconciliation SMEs, identity/security staff, processor/bank SMEs and UAT coordinators.

### Phase 5 — pilot + parallel run
Prefer a deliberately bounded agency/location cohort covering multiple tenders and real accounting shapes. Require reconciled parallel evidence before expansion.

### Phase 6 — wave rollout + hypercare
- wave entry criteria;
- no unresolved material controls;
- explicit rollback window;
- daily reconciliation scorecard;
- defect severity/ownership;
- cutover decision log;
- hypercare exit criteria.

## 6. Security / certification gap statement

| Evidence | Current TJLabs proof | Required before prime response claim |
| --- | --- | --- |
| SOC 2 Type II for production cashiering environment | NONE | prime current report/scope |
| PCI DSS v4.0.1 responsibility/AOC | NONE | prime/processor evidence |
| Historical cashiering uptime/SLA | NONE | prime production history |
| Cyber liability insurance for prime solution | UNKNOWN | certificate / limits |
| CONUS-only prod/backup/DR + onshore access | UNKNOWN | architecture + subprocessors + contract |
| Worldpay/FIS or current processor certification | NONE | prime/processor evidence |
| Check21/RDC/ICL production certification | NONE | prime/bank evidence |
| Cashiering hardware compatibility | NONE | prime certification/support matrix |
| WCAG 2.1 AA | NONE for a statewide cashiering product | prime accessibility evidence |
| RTO/RPO and recent DR test | NONE for a statewide cashiering product | prime DR evidence |
| Cooperative contract availability | UNKNOWN | prime vehicle evidence |
| Comparable statewide cashiering references | NONE | prime references |

This table is a **stop against fabrication**, not a negative capability claim about a future partner.

## 7. Proposed commercial workshare

All numbers are internal hypotheses: **PROPOSED_NOT_ACCEPTED / $0 BOOKED**.

### Option A — capture + response engineering
**$28,000 fixed**
- requirements partition;
- response architecture;
- integration narrative;
- synthetic control demo;
- owner-ready question consolidation;
- technical red-team / claim scrub.

### Option B — post-award Edison integration acceptance
**$180,000–$320,000 fixed**
depending on number of interface families / agencies / migration generations:
- field/interface contracts;
- migration acceptance;
- reconciliation harness;
- UAT evidence;
- parallel-run controls;
- cutover decision pack.

### Option C — rollout assurance / hypercare
**$18,000/month**, separately accepted
- daily evidence/reconciliation scorecard;
- exception burn-down;
- rollout-wave readiness;
- regression/UAT support.

Pricing excludes prime software licenses, hosting, processor fees, hardware, State portal fees, travel and third-party certifications.

## 8. Twenty-page response skeleton

If responding through a qualified prime, adapt the prime's identity/history rather than TJLabs pretending to be the OEM.

1. Cover + executive response posture.
2. Technical 1-3: legal/contact + comparable experience.
3. Technical 4: implementation approach/timeline.
4. Technical 5-6: contract vehicles + product/architecture/workflow material.
5. Technical 6 continued: interface/data-flow narrative.
6. Technical 7: UAT/training/resources.
7. Technical 8: continuity / rollout / parallel-run / rollback.
8. Technical 9-11: support, SLA, uptime.
9. Technical 12-13: release management + sustainability.
10. Technical 14-15: differentiators + DR/RTO/RPO.
11. Cost 1-4: units, implementation ranges, models, support tiers.
12. Additional considerations / migration and acceptance recommendations.
13. Attachment 1 requirements 1-15.
14. Requirements 16-30.
15. Requirements 31-45.
16. Requirements 46-60.
17. Requirements 61-75.
18. Requirements 76-90.
19. Requirements 91-105.
20. Requirements 106-120 + assumptions/gap legend.

The 15-row/page matrix is a target; final pagination must be verified at 12-point font before submission.

## 9. Go / no-go gate

Do not authorize an external response until all are true:

- [ ] current first-party packet/amendments re-read;
- [ ] exact legal respondent identified;
- [ ] prime/OEM owns the product being described;
- [ ] mandatory security/certification evidence inventoried;
- [ ] comparable experience/references are real and permissioned;
- [ ] hosting/data-residency/subprocessor facts are verified;
- [ ] processor/Check21/hardware boundaries are verified;
- [ ] response answers Technical/Cost numbering exactly;
- [ ] 120-requirement matrix is reviewed by prime;
- [ ] no unsupported TJLabs-as-prime language;
- [ ] 20-page/12-point/no-external-link formatting verified;
- [ ] one-question-submission rule respected;
- [ ] external message/submission has fresh dedupe + Muse selection;
- [ ] owner approves final recipient/file generation.

## 10. Context sources to verify, not controlling procurement terms

- Public State iNovah administration guide pages under https://in.edison.tn.gov/iNovah2/Help/
- Tennessee fiscal-review archive material describing prior iNovah/Edison and payment-processing arrangements.

These help formulate migration questions. They do **not** override the 2026 RFI and must not be quoted as current contractual truth without fresh verification.
