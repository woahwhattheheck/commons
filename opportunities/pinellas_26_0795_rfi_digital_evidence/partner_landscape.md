# Production partner landscape — research only / outbound DNR

**No outreach is authorized by this file.** Before contacting any vendor, run fresh Commons/Slack ownership search and provider mailbox history for the exact organization + route. One worker / one route / one live thread. Do not contact multiple people at the same vendor in parallel.

## 1. Thomson Reuters Case Center — strongest primary-platform candidate

Public evidence:

- Product: https://legal.thomsonreuters.com/en/products/case-center
- Indiana Judicial Branch identifies Case Center as the product behind its statewide Digital Evidence Portal: https://www.in.gov/courts/evidence/
- Texas Judicial Branch likewise identifies Case Center as its Digital Evidence Sharing platform: https://www.txcourts.gov/programs-services/digital-evidence-sharing/

Why it maps well to Pinellas 26-0795-RFI:

- purpose-built courts / judges / hearing evidence platform;
- external parties and self-represented litigants can upload through court-invited cases;
- documentary + multimedia evidence, search/indexing, permissions, annotation/redaction, exhibit marking, in-person/remote hearing presentation;
- unusually strong public-sector proof: state judicial branches publicly describe active use.

Open proof needed before any turnkey claim:

- exact Pinellas-required chain-of-custody semantics and all-file-action/view audit;
- physical evidence placeholders/tags;
- approval-based destruction + advance notice/copy workflow;
- current U.S. data residency/hosting details and applicable Florida judicial/criminal-justice security mapping;
- CMS/API support for Pinellas's actual court systems;
- commercial/partner willingness for this RFI.

Suggested route: **first partner to evaluate** if a turnkey response is pursued. Do not contact until deconfliction/provider-history fence is green.

## 2. Omnigo — strongest digital + physical evidence / custody lifecycle candidate

Public evidence:

- Court evidence management: https://www.omnigo.com/industry/courts
- Trial presentation: https://www.omnigo.com/industry/courts-trial-presentation-software

Why it maps well:

- explicitly positions one system of record for digital and physical court evidence;
- digital intake, barcode/physical-item tracking, location/status, chain-of-custody history;
- return/disposal workflows and party notification align unusually closely with Pinellas retention/destruction language;
- presentation capabilities add courtroom-use coverage.

Open proof needed:

- external self-represented-litigant workflow and identity model;
- all-file-action/view logging semantics;
- U.S. hosting/security/DR specifics;
- test/training isolation;
- API/CMS integration specifics for Pinellas;
- deployment references relevant to comparable county/circuit court environments.

Suggested route: **parallel diligence, not parallel outreach**. Compare evidence against Case Center first; contact only after one route is selected/claimed.

## 3. Justice AV Solutions (JAVS) — courtroom capture/presentation complement

Public evidence:

- Digital evidence / court-record integration: https://www.javs.com/2026/07/13/digital-evidence-solutions-court-record/
- CMS integration: https://www.javs.com/case-management-integration/
- Evidence presentation: https://www.javs.com/simplified-evidence-presentations/

Fit:

- courtroom A/V recording, displayed-evidence capture, judge preview, evidence presentation and CMS integration;
- public claim of installations in 10,000+ courtrooms;
- strong complement if Pinellas ultimately wants the evidence repository connected tightly to the official A/V record.

Gap:

- public material is more focused on courtroom record/capture than the complete external-submission -> custody -> retention/destruction repository lifecycle requested by this RFI.

Suggested route: complement/integration partner, not first-choice lifecycle-platform prime.

## 4. For The Record — court-record/cloud complement

Public evidence:

- https://fortherecord.com/
- https://fortherecord.com/solutions/stakeholder/court-it/

Fit:

- courtroom recording, cloud storage, searchable connected records, integration and court-IT focus.

Gap:

- current public evidence recovered here is less directly matched to Pinellas's external evidence submission, physical item tracking and approval-bound destruction workflow than Case Center/Omnigo.

Suggested route: secondary diligence only.

## Partner-selection rule

Do not optimize for a logo. Score candidates against the exact RFI requirements and require evidence for each claimed capability. The best teaming shape may be:

- **platform prime:** proven court evidence/exhibit UX + public-sector deployments;
- **hosting/security owner:** U.S.-resident infrastructure, IAM, scanning, backup/DR/BCP and applicable security evidence;
- **TJLabs specialist:** independent custody/integrity model, integration acceptance tests, deterministic export verification, failure/recovery tests and response-consistency review.

This creates a paid specialist path without pretending TJLabs alone supplies the production SaaS today.
