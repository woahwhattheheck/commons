# Recovery evidence matrix (UIOWA-068)

> SYNTHETIC / FICTIONAL. Every service, backup job, exercise, date and measurement in this file was invented for artifact review. Nothing here describes the University of Iowa, any real estate, or any real incident. Do not cite any figure in this file as a finding.

Generated from records as of **2026-09-15**. All ages are computed against that declared date, never the wall clock, so this output is reproducible.

## What this matrix does and does not claim

A rung is a statement about **evidence on file**, not a maturity rating and not a judgement of any team. `UNKNOWN` means the evidence was not supplied; it is never converted into a zero, a pass, or a score. Owners are recorded as roles, never as individuals.

- **R0 NO_EVIDENCE** - Nothing on record for this service.
- **R1 CONFIGURED** - A backup exists but is not currently completing.
- **R2 BACKUP_COMPLETING** - The backup job succeeds on its schedule.
- **R3 RESTORE_DEMONSTRATED** - A restoration actually completed.
- **R4 FUNCTION_VERIFIED** - The restored service performed its business function.

Two rules do most of the work: **a tabletop exercise never lifts a service above R2**, and **R4 requires a business-function check that was performed, passed, and carries an evidence reference**.

## Position

9 services. By rung: R0=1, R1=2, R2=2, R3=2, R4=2.

- **2** service(s) have a verified business function after restoration (R4).
- **4** service(s) have any demonstrated restoration at all (R3 or better).
- **7** service(s) have an UNKNOWN chain recovery time.
- **2** service(s) have a stated RTO that the evidence already shows is exceeded.

## Evidence matrix

| Service | Tier | Rung | Backup health | Own measured | Chain recovery | Stated RTO | RTO status |
|---|---|---|---|---|---|---|---|
| Backup Control Plane (SVC-BKP-CTL) | 1 | R3 RESTORE_DEMONSTRATED | COMPLETING | 140 min | UNKNOWN (>= 140 min) | 240 min | UNKNOWN |
| Directory Synchronization Service (SVC-DIRSYNC) | 2 | R0 NO_EVIDENCE | NO_RECORD | UNKNOWN | UNKNOWN | 480 min | UNKNOWN |
| Grade Submission Service (SVC-GRADE) | 2 | R1 CONFIGURED | STALE | UNKNOWN | UNKNOWN (>= 320 min) | 480 min | UNKNOWN |
| Identity Provider (SSO) (SVC-IDP) | 1 | R4 FUNCTION_VERIFIED | COMPLETING | 95 min | UNKNOWN (>= 95 min) | 120 min | UNKNOWN |
| LMS Integration Bridge (SVC-LMS-INT) | 3 | R1 CONFIGURED | FAILING | UNKNOWN | UNKNOWN | 1440 min | UNKNOWN |
| Course Registration Portal (SVC-REG) | 1 | R2 BACKUP_COMPLETING | COMPLETING | UNKNOWN | UNKNOWN (>= 320 min) | 240 min | EXCEEDED |
| Student Records Database (SVC-SIS-DB) | 1 | R4 FUNCTION_VERIFIED | COMPLETING | 320 min | 320 min | 180 min | EXCEEDED |
| Shared Object Store (SVC-STORE) | 1 | R3 RESTORE_DEMONSTRATED | COMPLETING | 210 min | 210 min | 360 min | WITHIN_STATED_RTO |
| Backup Vault and Catalog (SVC-VAULT) | 1 | R2 BACKUP_COMPLETING | COMPLETING | UNKNOWN | UNKNOWN (>= 140 min) | 240 min | UNKNOWN |

`UNKNOWN (>= N min)` is a lower bound, not an estimate. It means the chain contains at least one measured link of N minutes and at least one link nobody has measured.

### Worked restoration scenario: Course Registration Portal (`SVC-REG`)

**Business function that must come back:** A student can complete a course add/drop and receive a written confirmation.

**Stated objective:** RTO 240 minutes, RPO 15 minutes. **Owning role:** Enterprise Applications team.

**Restoration chain** (every service that must be back before this one can do its job):

| Step | Service | Rung | Own measured restore | What is missing |
|---|---|---|---|---|
| self | `SVC-REG` Course Registration Portal | R2 | UNKNOWN | no measured restoration |
| dep | `SVC-DIRSYNC` Directory Synchronization Service | R0 | UNKNOWN | no measured restoration; no current backup evidence |
| dep | `SVC-IDP` Identity Provider (SSO) | R4 | 95 min | - |
| dep | `SVC-SIS-DB` Student Records Database | R4 | 320 min | - |
| dep | `SVC-STORE` Shared Object Store | R3 | 210 min | business function unverified |

**Where this stalls.** No measured restoration for SVC-DIRSYNC, SVC-REG. The chain time is unknown; the figure below is a lower bound, not an estimate.

**Measured recovery time:** the slowest *measured* link in this chain is 320 minutes. That is a **lower bound on the whole chain**, not an estimate of it: the unmeasured links can only push the real figure higher.

**Against the stated objective:** EXCEEDED -- At least 320 minutes of measured restoration in the chain against a stated 240-minute objective. Conclusive despite the remaining unknowns -- the true figure can only be higher.

**Backup completion is not the same claim.** Backup health for this service is `COMPLETING` (Job BK-REG-01 succeeded 1 day(s) ago on a daily schedule.). That establishes that a job exited successfully. It establishes nothing about restoration, and nothing about whether a restored instance could satisfy its business function: *A student can complete a course add/drop and receive a written confirmation.*

**Evidence notes for this service:**

- EX-2026-05-REG (2026-05-08) is a tabletop: it does not demonstrate restoration and cannot lift this service above R2.

## Findings

| ID | Severity | Service | Finding |
|---|---|---|---|
| RF-001 | high | `SVC-BKP-CTL` | Backup Control Plane sits in a circular recovery dependency (SVC-BKP-CTL <-> SVC-VAULT). Each side's measured restoration assumed the other was already available. |
| RF-002 | medium | `SVC-BKP-CTL` | Backup Control Plane has a completed restoration but no passing business-function check. The data came back; whether the service can do its job with it is unestablished. |
| RF-003 | medium | `SVC-BKP-CTL` | Backup Control Plane: The densest recorded data-scope schedule implies up to 1440 minutes of loss against a stated 60-minute objective. If a continuous or log-shipping mechanism exists it is not in these records -- ask for it rather than assuming either way. |
| RF-004 | high | `SVC-BKP-CTL` | Backup Control Plane: EX-2026-06-BKPCTL restored the service and the business-function check RAN AND FAILED: Control plane started, but could not enumerate backup sets: the catalog it reads lives in SVC-VAULT, which was not available. |
| RF-005 | high | `SVC-DIRSYNC` | Directory Synchronization Service has no backup record and no restoration evidence of any kind. |
| RF-006 | high | `SVC-GRADE` | Grade Submission Service: Job BK-GRADE-01 reports success but ran 19 day(s) ago against a daily schedule (tolerance 3 day(s)). |
| RF-007 | medium | `SVC-GRADE` | Grade Submission Service: The densest recorded data-scope schedule implies up to 1440 minutes of loss against a stated 60-minute objective. If a continuous or log-shipping mechanism exists it is not in these records -- ask for it rather than assuming either way. |
| RF-008 | medium | `SVC-GRADE` | Grade Submission Service: EX-2026-01-GRADE (2026-01-30) was attempted and did not complete (outcome=failed). An attempt is not a demonstrated capability. |
| RF-009 | high | `SVC-IDP` | Identity Provider (SSO) reaches R4, but depends on SVC-DIRSYNC, which sits at R1 or below. The proven service rests on an unproven foundation. |
| RF-010 | medium | `SVC-IDP` | Identity Provider (SSO): The densest recorded data-scope schedule implies up to 1440 minutes of loss against a stated 60-minute objective. If a continuous or log-shipping mechanism exists it is not in these records -- ask for it rather than assuming either way. |
| RF-011 | medium | `SVC-LMS-INT` | LMS Integration Bridge depends on SVC-GHOST-API, for which no record exists in the estate. Recovery time cannot be established. |
| RF-012 | high | `SVC-LMS-INT` | LMS Integration Bridge: Most recent recorded job for BK-LMS-01 is 'failed'. |
| RF-013 | high | `SVC-REG` | Course Registration Portal: At least 320 minutes of measured restoration in the chain against a stated 240-minute objective. Conclusive despite the remaining unknowns -- the true figure can only be higher. |
| RF-014 | high | `SVC-SIS-DB` | Student Records Database: At least 320 minutes of measured restoration in the chain against a stated 180-minute objective. Conclusive despite the remaining unknowns -- the true figure can only be higher. |
| RF-015 | medium | `SVC-SIS-DB` | Student Records Database: The densest recorded data-scope schedule implies up to 1440 minutes of loss against a stated 15-minute objective. If a continuous or log-shipping mechanism exists it is not in these records -- ask for it rather than assuming either way. |
| RF-016 | medium | `SVC-STORE` | Shared Object Store has a completed restoration but no passing business-function check. The data came back; whether the service can do its job with it is unestablished. |
| RF-017 | medium | `SVC-STORE` | Shared Object Store: The densest recorded data-scope schedule implies up to 10080 minutes of loss against a stated 60-minute objective. If a continuous or log-shipping mechanism exists it is not in these records -- ask for it rather than assuming either way. |
| RF-018 | low | `SVC-STORE` | Shared Object Store: whether the backup copy leaves the primary facility was not established. Left UNKNOWN rather than assumed either way. |
| RF-019 | high | `SVC-VAULT` | Backup Vault and Catalog sits in a circular recovery dependency (SVC-BKP-CTL <-> SVC-VAULT). Each side's measured restoration assumed the other was already available. |
| RF-020 | medium | `SVC-VAULT` | Backup Vault and Catalog: The densest recorded data-scope schedule implies up to 1440 minutes of loss against a stated 60-minute objective. If a continuous or log-shipping mechanism exists it is not in these records -- ask for it rather than assuming either way. |

## Next exercises, ranked

Ranking formula, stated so it can be argued with: `tier_weight x evidence_gap x (1 + blast_radius)`, where `tier_weight` is 3/2/1 for tiers 1/2/3, `evidence_gap` is how many rungs short of R4 the service sits, and `blast_radius` is how many other services transitively depend on it. Ties break on blast radius, then service id. A high rank is a claim about where evidence is cheapest to gain, not a claim that the service is failing.

| Rank | Service | Rung | Score | Formula | Recommended exercise |
|---|---|---|---|---|---|
| 1 | Directory Synchronization Service (`SVC-DIRSYNC`) | R0 | 32 | tier_weight(2) x evidence_gap(4) x (1 + blast_radius(3)) = 32 | Establish a backup record and a named owning role first. An exercise has nothing to restore from until that exists. |
| 2 | Shared Object Store (`SVC-STORE`) | R3 | 12 | tier_weight(3) x evidence_gap(1) x (1 + blast_radius(3)) = 12 | Repeat the restoration and add a business-function check: Stored objects are retrievable and byte-identical to what was written. Record the evidence reference. |
| 3 | Backup Vault and Catalog (`SVC-VAULT`) | R2 | 12 | tier_weight(3) x evidence_gap(2) x (1 + blast_radius(1)) = 12 | Run a restoration exercise and measure wall-clock time to a running service. Record the figure even if it is unflattering. |
| 4 | Backup Control Plane (`SVC-BKP-CTL`) | R3 | 6 | tier_weight(3) x evidence_gap(1) x (1 + blast_radius(1)) = 6 | Repeat the restoration and add a business-function check: Backup and restore jobs can be scheduled, launched and monitored. Record the evidence reference. |
| 5 | Grade Submission Service (`SVC-GRADE`) | R1 | 6 | tier_weight(2) x evidence_gap(3) x (1 + blast_radius(0)) = 6 | Repair the backup job, then restore the first completing set into an isolated environment. |
| 6 | Course Registration Portal (`SVC-REG`) | R2 | 6 | tier_weight(3) x evidence_gap(2) x (1 + blast_radius(0)) = 6 | Run a restoration exercise and measure wall-clock time to a running service. Record the figure even if it is unflattering. |
| 7 | LMS Integration Bridge (`SVC-LMS-INT`) | R1 | 3 | tier_weight(1) x evidence_gap(3) x (1 + blast_radius(0)) = 3 | Repair the backup job, then restore the first completing set into an isolated environment. |

## Interview prompts

- **Separating completion from restoration.** Show me the most recent restore you actually performed for Directory Synchronization Service, not the backup job log. What was the wall-clock time from decision to a running service?
- **Function, not process.** After that restore, what did someone do to confirm this held true -- *Account attribute and group-membership changes propagate to downstream consumers.* -- and where is that recorded?
- **Dependency reality.** If Directory Synchronization Service had to be rebuilt today, what has to be back first? Walk me down the chain until you reach something nobody has ever restored.
- **The unrecorded mechanism.** Several stated RPOs are denser than the recorded backup schedules support. Is there a continuous or log-shipping mechanism that is not in these records?
- **Circularity.** If the backup control plane and its catalog were both unavailable, what is the documented order of operations to get either one back?
- **Ownership as a role.** Which role -- not which person -- is accountable for deciding a restoration is complete, and what do they check before saying so?
- **The exercise that was not run.** What restoration exercise has been deferred most often, and what has blocked it each time?
- **Evidence retention.** Where do restoration exercise records live, how long are they kept, and who can produce one from two years ago?

## What is still UNKNOWN

Every `UNKNOWN` above is an open evidence request, not a deficiency score. Nothing in this document is a certification, a compliance determination, or a comparison against any peer institution.
