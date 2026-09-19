# Integrated release-and-recovery case — SYN-109-ESS-RELEASE-01

> SYNTHETIC / FICTIONAL. Every service, environment, release, digest, date and measurement in this file was invented for artifact review. Nothing here describes the University of Iowa, any real service, any real release, or any real incident. Do not cite any figure in this file as a finding.

**Cross-component status: `GAPS`** · 0 contradiction(s), 3 gap(s) · as of `2026-09-18T12:00:00+00:00`

`AGREED` means the supplied records do not contradict each other. It is not a release approval, a recovery certification, or a statement that the release was safe. No maturity score, confidence score or individual rating is produced.

## 1. Provenance chain (UIOWA-057 view)

- Chain: `DEP-1 -> ART-1 -> ART-1 -> BLD-1 -> BLD-1 -> SRC-1`
- Fully linked: **yes**

## 2. Environment view

- Deployed `fictional-2.3.0` to **`ess-prod`**
- Verifications passed in: `ess-stage`
- Environment difference: **YES**

| Verification | Environment | Version | Outcome | Covers deployed env |
|---|---|---|---|---|
| `VER-STAGE` | `ess-stage` | `fictional-2.3.0` | **PASSED** | no |
| `VER-PROD` | `ess-prod` | `fictional-2.3.0` | **FAILED** | yes |

## 3. Recovery evidence (UIOWA-068 ladder)

| Service | Backup | Restoration | Observed RPO | Observed RTO (to business verification) | Technical restore | Dependencies | Business function |
|---|---|---|---|---|---|---|---|
| `SVC-ESS` | EVIDENCED | **DEMONSTRATED** | 50 min (MEETS_TARGET) | 65 min (MEETS_TARGET) | 50 min | EVIDENCED | EVIDENCED |
| `SVC-IAM` | PARTIAL | **NOT_DEMONSTRATED** | UNKNOWN | UNKNOWN | UNKNOWN | NOT_APPLICABLE | NOT_EVIDENCED |
| `SVC-RIS` | EVIDENCED | **PARTIAL** | 80 min (EXCEEDS_TARGET) | UNKNOWN | 80 min | PARTIAL | NOT_EVIDENCED |

**`SVC-IAM` evidence gaps**

- backup completion not evidenced: source 'EV-SYN-IAM-BACKUP' is interview evidence; without artifact corroboration it remains UNKNOWN
- no restoration exercise recorded; restoration is NOT_DEMONSTRATED, which is an absence of evidence and not a failed exercise

**`SVC-RIS` evidence gaps**

- business-function verification was not attempted in the records; it stays NOT_EVIDENCED
- observed RTO cannot be computed: it runs to business-function verification, which is not recorded here. The technical restore time is reported separately and is NOT an RTO
- dependency SVC-ESS verification claimed but unsupported: no observed verification time

## 4. Timeline agreement

- Events in the shared register: **17** (16 with a known time)
- **Unorderable (UNKNOWN time, excluded from ordering):** `EVT-RIS-DEPVERIFY`
- Component assertions checked: **18** · disagreements: **0**
- Ordering constraints: **0** violated, **0** UNKNOWN (an unknown endpoint is neither a pass nor a violation)

## 5. Findings

| Class | Code | Subject | Component | Detail |
|---|---|---|---|---|
| gap | `ENVIRONMENT_DIFFERENCE` | `ess-prod` | environment | every PASSED verification ran in ['ess-stage'], but the release was deployed to 'ess-prod'; a pass in another environment is not evidence about the environment that actually ran the release |
| gap | `UNORDERABLE_EVENT` | `EVT-RIS-DEPVERIFY` | cross-component | event 'EVT-RIS-DEPVERIFY' (dependency_verification) has no observed timestamp; it stays UNKNOWN and is excluded from ordering checks. It is NOT placed at the start of the timeline and NOT treated as satisfied |
| gap | `UNSUPPORTED_RECOVERY_CLAIM` | `SVC-RIS:dependency:SVC-ESS` | recovery | service 'SVC-RIS' claims dependency 'SVC-ESS' was verified, but the claim is not carried by a verification record (no observed verification time); the claim is reported unsupported and does not raise the status |

