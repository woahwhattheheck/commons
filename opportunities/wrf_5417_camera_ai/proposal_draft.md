# Internal Proposal Architecture — WRF 5417

> **NOT A SUBMISSION.** Every bracketed field is unresolved. This becomes submission material only after the readiness ledger proves the corresponding organizational, scientific, utility, financial, legal, and portal gates.

## Working thesis

WRF 5417 should not be framed as a single-site image classifier. The useful sector contribution is a **measurement-linked, multi-site transferability framework**: select a small portfolio of uses where visible phenomena have operational value, bind camera observations to conventional sensor/laboratory measurements, quantify performance and uncertainty under real domain shift, and publish technology-selection and deployment rules that tell utilities when a camera system is sufficiently reliable to supplement—not silently replace—existing monitoring.

**Proposed prime:** `[ENTITY / HOLD]`  
**Proposed PI:** `[PI / HOLD]`  
**Utility participants:** `[CONSENTING UTILITIES / HOLD]`  
**WRF request:** `[OWNER-APPROVED AMOUNT / HOLD]`  
**Applicant contribution:** `[SOURCE-BACKED COMMITMENTS / HOLD]`

## Objective → work package

### WP1 — Use-case prioritization and WRF knowledge-base extension

Build a traceable matrix from the RFP-cited WRF projects plus external literature. Score candidate uses on decision value, visual observability, availability of conventional ground truth, event prevalence, safety consequence of false results, transfer challenge, and hardware/maintenance burden. Downselect **3–5 applications spanning drinking water and wastewater** only after utility partners confirm relevance. Candidate examples in the RFP include harmful-algal-bloom cues, turbidity/color events, spills/foam, and sludge/process-state monitoring; these are not preselected commitments.

### WP2 — Camera technology ladder and acquisition protocol

For each selected use case compare an escalating ladder: commodity RGB → controlled/low-light RGB → multispectral → hyperspectral only when incremental information justifies field cost/complexity. Specify geometry, illumination, cadence, enclosure, calibration targets, maintenance, storage/network footprint, time synchronization, and metadata. The study should answer **the lowest sufficient camera class**.

Each acquisition record should bind site/camera/configuration identity, capture time, environmental context, ground-truth source/time, calibration version, and raw/derived artifact hashes.

### WP3 — Paired ground truth and data-quality controls

Every evaluation record must pair to an accepted conventional measurement or utility-validated operational label under an agreed time-alignment policy. Fail closed on missing/corrupt imagery, stale or unaligned measurement, duplicate identity, unknown configuration, unresolved clock drift, bad calibration, ambiguous process state, or train/test leakage. Quarantined records remain visible and cannot silently become negative examples.

### WP4 — Model development and within-site validation

Use simple baselines before complex models. For each use case report task-appropriate accuracy/error measures, calibration/confidence quality, false-negative/false-positive behavior at decision thresholds, subgroup performance across lighting/weather/season/camera/process state, abstention/HOLD rate, and compute/storage/latency footprint. Split by site/time/event to avoid leakage. Content-address model, data, preprocessing, configuration and environment for replay.

### WP5 — Cross-site transfer and domain-shift experiment

The core experiment is not random-image test accuracy. Use leave-one-site-out or train-site → held-out-site evaluation and compare zero-shot transfer, calibration-only transfer, lightweight fine-tuning, and full-retraining baseline. Measure performance loss, calibration drift, label burden to recover performance, and hardware sensitivity. Produce a **transferability envelope**: when transfer works, when recalibration/fine-tuning is needed, and when new training is required.

### WP6 — Multi-utility operational demonstration

`[UTILITY CONSENT REQUIRED]`

Deploy only with utilities that explicitly accept roles, site access, data handling, ground-truth work, safety boundaries, schedule, and contribution valuation. A public WRF Potential Participant listing is not consent. Camera/AI outputs remain decision support; utility operators retain all process, safety, compliance, treatment and public-notification authority.

### WP7 — Utility implementation framework

Turn study results into an adoption playbook: use-case selection; minimum camera class; installation/maintenance/calibration; network/storage/edge-vs-cloud patterns; labeling/retraining burden; confidence/abstention policy; alert/human confirmation; cybersecurity/data governance; lifecycle monitoring/drift/revalidation; cost model; workforce implications.

### WP8 — Knowledge transfer / technology deliverables

Plan a WRF Research Report, open-access paper and/or webcast/conference presentation, utility guidance framework, and a technology deliverable such as a shareable benchmark schema/dataset, reproducible evaluation harness, and appropriately licensed reference models/code where agreements permit. Do not promise public release of utility-sensitive data or third-party IP before agreements are approved.

## QA/QC

Cover source/data lineage and immutable IDs; camera and conventional-instrument calibration traceability; field SOPs; missing/corrupt/stale/duplicate quarantine; predefined split rules; model/version reproducibility; independent metric recomputation; baseline change control; deviation ledger; deliverable review; and partner-approved access/retention. A result is not “validated” because code ran—it must bind exact inputs/config/model → ground truth → metric → reviewer/utility context.

## Management — unresolved roles

- **PI / scientific lead:** `[REQUIRED]`
- **Water/wastewater domain lead:** `[REQUIRED]`
- **Computer-vision lead:** `[REQUIRED]`
- **Utility site leads:** `[REQUIRED PER SITE]`
- **Data/QA lead:** `[REQUIRED]`
- **Project manager:** `[REQUIRED]`
- **Token Junkie Labs specialist seam:** reproducibility, evidence lineage, failure/retry/ambiguity controls and deterministic validation, only as accepted by the eventual prime/team.

No role is represented as staffed until evidence is attached in `submission_manifest.json`.

## Milestone skeleton (24–30 months)

- M0–M3: kickoff, prior-WRF/literature synthesis, utility/site confirmation, use-case downselect, QA/data plans.
- M3–M6: camera ladder protocol, conventional-measurement alignment, pilot acquisition.
- M6–M15: multi-site collection, baselines/models, within-site validation.
- M12–M20: held-out-site transfer, retraining/calibration burden study.
- M18–M24: operational demonstration, cost/workforce/IT integration analysis.
- M22–M27: utility implementation framework and technology-deliverable hardening.
- M24–M30: final report and dissemination/closeout.

## Evaluation crosswalk

| Factor | Weight | Response |
|---|---:|---|
| Responsiveness | 20 | 3–5 cross-sector uses, camera ladder, paired conventional validation, multi-site transfer, implementation framework |
| Technical/scientific merit | 30 | leakage-safe splits, calibrated metrics, domain shift, pre-registered comparisons, failure/quarantine rules |
| Qualifications/capabilities/management | 20 | **HOLD** until PI/domain/CV/utility evidence and roles are attached |
| Communications/deliverables/applicability | 15 | report + utility guide + reproducible technology deliverable + dissemination |
| Budget/schedule | 15 | 24–30 month skeleton; **HOLD** until WRF workbook, rates, cost share and finance approvals are sourced |

## Budget / contribution arithmetic — non-binding

For WRF request `R`, minimum eligible applicant contribution is `0.33 * R`.

| WRF request | Minimum contribution | Minimum represented resources |
|---:|---:|---:|
| $100,000 | $33,000 | $133,000 |
| $200,000 | $66,000 | $266,000 |
| $300,000 | $99,000 | $399,000 |

These are arithmetic examples, not recommendations or commitments. Do not infer that labor, credits, utility time, equipment or third-party effort is eligible or committed merely because it has value.

## Hard blockers

Organization My Portal account; live deadline/offset recheck; PI/Co-PI identities and Current & Pending; water/wastewater + CV qualifications; consenting utility sites; W-9/entity tax documentation; financial statements and required compilation/review evidence; grant-management capability form; Certification and Assurance form; budget workbook/narrative; ≥33% exact eligible contribution and support letters if used; legal/IP/PFA review; final PDF/portal QA; authorized final submitter.

## Partner route if direct-prime gates do not clear

Do not invent qualifications because the deadline is close. If a qualified research/utility prime already has portal/financial infrastructure and needs reliability/reproducibility engineering, use this as a bounded teaming packet. Token Junkie Labs can offer the data-lineage, transfer-test, ambiguity-quarantine, replay, evidence and acceptance workstream without claiming to be the utility-science prime. No teaming relationship exists until explicitly accepted.
