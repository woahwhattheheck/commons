# WRF 5417 technical proposal draft

**Working title:** From Camera to Utility Evidence: Minimum-Sensing-Tier and Cross-Site Transfer Framework for Water and Wastewater Monitoring

> Draft status: technically developed, administratively incomplete. Replace every `[OWNER INPUT]` or `[PARTNER INPUT]` only with verified facts. Do not submit this Markdown directly; final WRF packet must follow the official page/format/upload rules.

## Project Abstract — one-page content spine

Camera-based AI can lower the cost and increase the spatial and temporal coverage of water-quality and process monitoring, but field adoption is constrained by a practical question: **what is the least complex imaging system that remains reliable when the camera, site, lighting, weather, season, and process conditions change?** Project 5417 should answer that question with a common validation framework rather than a collection of isolated high-accuracy demonstrations.

This project will select **3–5 utility-led use cases spanning drinking water and wastewater**, establish conventional measurements and decision-relevant ground truth for each, and evaluate a staged sensing ladder beginning with commodity RGB and escalating to controlled illumination and spectral imaging only where measured incremental value warrants the additional cost and operational burden. Candidate use cases are: (1) source-water harmful algal bloom / surface-condition screening; (2) intake or treatment turbidity/color/particle-event screening; (3) activated-sludge floc morphology, filament/bulking and settleability screening; (4) foam, scum, spill or visible process-anomaly detection; and (5) a utility-selected camera-observable condition that broadens sector transfer evidence.

The work will use site- and time-blocked experiments that deliberately stress camera model, view geometry, illumination, weather, fouling, compression, and operating regime. Models will be evaluated under **zero-shot transfer, few-shot recalibration, and site-specific retraining**. Performance will be reported with discrimination metrics, calibration, abstention/coverage, false-alarm and miss costs, data completeness, latency, and stability against conventional utility measurements. The project will pre-register acceptance thresholds for each use case before final model selection, preserve an explicit human/utility decision boundary, and document failure envelopes rather than treating low-confidence outputs as operational facts.

The principal research product will be a **Minimum-Sensing and Transferability Framework**: a camera-selection matrix, cross-site/camera benchmark protocol, normalized evidence schema, implementation and QA/QC playbook, and open reference artifacts where licensing and WRF requirements permit. The framework is designed to extend WRF Projects 5154, 5266, 5339, and 5189 by moving from individual sensors/models and broad AI adoption guidance to a reproducible decision rule for sensing sufficiency and transfer risk across both drinking-water and wastewater applications.

**Applicant / PI / requested WRF amount / committed contribution / participating utilities:** `[OWNER INPUT — must match portal, budget and signed support documents exactly]`

---

# Project Description

## 1. Research objectives

The proposed research has six objectives.

### Objective 1 — select high-value, camera-observable utility use cases

Use a structured selection rubric to choose 3–5 use cases across drinking water and wastewater. The rubric scores: operational value; measurability of reference ground truth; frequency/availability of positive and negative cases; camera observability; consequence of false positives/false negatives; expected transfer challenge; field burden; privacy/security implications; and potential for sector-wide reuse.

Candidate use cases are intentionally not pre-committed as if utility participation already existed. Final use cases will be selected with participating utilities after project launch and WRF/PAC input.

### Objective 2 — determine minimum practical camera/sensing requirements

For each use case, evaluate the least complex sensor configuration that satisfies the pre-established utility threshold. The test ladder is:

1. commodity RGB using ambient light;
2. RGB with controlled illumination / fixed geometry and, where useful, optical filtering or polarization;
3. multispectral imaging;
4. hyperspectral imaging only where lower tiers do not provide acceptable performance and incremental utility value justifies the operational burden.

This avoids assuming that more bands are automatically better. The output is a requirements matrix linking task, viewing geometry, lighting control, resolution, frame cadence, environmental protection, calibration burden, bandwidth/storage, and maintenance to measured performance.

### Objective 3 — develop models with transparent evidence and failure handling

Models will be fit to the selected tasks using methods appropriate to each data regime: classification, segmentation, detection, regression, temporal change detection, or a hybrid. The research question is not tied to a single architecture. Every evaluated pipeline will preserve:

- source/site/camera/time provenance;
- preprocessing and calibration metadata;
- model/data version identity;
- confidence/calibration evidence where meaningful;
- explicit invalid-input and insufficient-evidence states;
- reproducible train/validation/test manifests;
- a human/utility review path for outputs below operational confidence or outside the tested envelope.

Direct automatic process control is outside the baseline research claim. Any future control use must be separately validated and governed by the utility.

### Objective 4 — quantify transferability across sites, cameras and operating conditions

The central scientific contribution is a **transfer matrix**, not a single aggregate test score. For every feasible source→target pairing, measure:

- in-domain baseline;
- zero-shot transfer to a held-out site/camera/condition;
- few-shot recalibration using a small, predeclared amount of target data;
- site-specific retraining where justified;
- degradation by domain-shift factor (lighting, season, camera family, geometry, weather/fouling, process regime);
- calibration and abstention behavior under shift.

Site and time identities will be blocked at the split level to prevent leakage. Random-image splitting across near-duplicate frames from the same sequence will not be treated as cross-site validation.

### Objective 5 — validate against conventional measurements and operational relevance

Each use case will define its reference method before model acceptance. Examples, subject to participating-utility confirmation, include chlorophyll-a/phycocyanin or validated bloom observations for HAB screening; turbidity and other conventional water-quality measurements for visible source/treatment changes; settleability/SVI/MLSS and microscopy/operator assessment for activated-sludge morphology; and documented operator/event logs for visible process anomalies.

The study will report not only statistical model quality but also practical decision performance: false-alarm burden, missed-event burden, usable coverage, latency, maintenance/data-loss rate, recalibration burden, and incremental value over the relevant conventional practice.

### Objective 6 — produce a scalable implementation and technology-selection framework

Translate the experiments into a decision process utilities can apply without reproducing the entire research project. The final framework will answer:

1. Is the condition sufficiently camera-observable for this decision?
2. What reference evidence is needed to validate it?
3. What minimum sensor tier meets the threshold?
4. How sensitive is performance to site/camera/lighting/process shift?
5. How much target-site calibration is required?
6. What data, cybersecurity, maintenance, integration and review controls are needed?
7. When should the camera method abstain or defer to conventional measurement?

## 2. Understanding of the problem and relationship to prior WRF work

WRF 5417 sits at the intersection of several strong existing research lines. Project 5154 demonstrated autonomous low-cost HAB monitoring using an in-situ imaging device, machine-learning species identification/quantification, and field deployment. Project 5266 is evaluating hyperspectral/multispectral approaches for algal-bloom early warning across geographically diverse waters and field/laboratory comparisons. Project 5339 is developing a transferable AI HAB warning system combining laboratory, field, weather and satellite information. Project 5189 addresses AI/ML adoption, value and utility performance more broadly.

The proposed work therefore should **not** repeat the question "can AI extract a water-related signal from images?" Instead it should establish how to choose a camera configuration economically, how to validate the signal under realistic utility conditions, and how to know when a model can or cannot transfer.

Published external work reinforces the opportunity and the gap. Satoh et al. (2021, DOI 10.1039/D0EW00908C) collected more than 12,000 activated-sludge microscopy images from two wastewater treatment plants and reported about 95% training accuracy for aggregated/dispersed floc classification, while also demonstrating the need for target-plant retraining when extending to other plants. Recent HAB-camera work has shown continuous RGB-camera detection can be viable, while spectral-imaging studies show that additional bands can improve bloom discrimination in some conditions. Those results support a controlled **incremental-sensing** experiment; they do not justify assuming a single model or camera will transfer across utilities.

The proposal's originality is therefore the combination of:

- a predeclared **minimum-sensing-tier** decision rule;
- explicit multi-factor domain-shift experiments;
- zero-shot/few-shot/site-specific transfer curves;
- calibrated abstention and failure-envelope reporting;
- consistent metrics across drinking-water and wastewater tasks;
- an implementation artifact that links scientific performance to utility cost and operational burden.

## 3. Technical approach and tasks

### Task 1 — literature, WRF knowledge-base and use-case selection

**Months 1–3.** Build a structured evidence table covering WRF projects/resources and current academic/industry camera-AI work. With WRF/PAC and committed utility participants, score candidate use cases and select 3–5. For each selected case, define: intended operational decision; reference measurement; positive/negative event definition; acceptable false-alarm/miss burden; target latency; expected camera location; and safety boundary.

**Deliverables:** literature/evidence synthesis; use-case selection memo; pre-registered success criteria; draft data dictionary.

### Task 2 — sensing architecture and field protocol

**Months 2–6.** Specify camera tiers and deployment test matrix. Document minimum resolution, field of view, frame cadence, illumination/geometry controls, weather/environmental protection, reference targets/calibration procedures, cleaning/fouling checks, local buffering, time synchronization, bandwidth/storage, and cyber/data handling assumptions.

Use the least complex sensor tier feasible at every site; add higher-spectral-resolution equipment at a designed subset sufficient to estimate incremental value. This creates paired evidence rather than confounding site differences with camera differences.

**Deliverables:** sensing requirements matrix; installation/data-collection protocol; QA/QC checklist.

### Task 3 — dataset acquisition, annotation and reference-ground-truth alignment

**Months 4–15.** Collect time-synchronized imagery and reference measurements. Sampling will deliberately include normal conditions, transitions, low-frequency events, day/night and seasonal ranges, and known nuisance conditions such as glare, rain/snow where relevant, occlusion, dirty optics, compression and connectivity loss.

Annotation methods will be use-case specific and documented with inter-rater or reference-method agreement where relevant. Data will be partitioned by site/time/event sequence before model tuning. Raw utility data will remain under agreed data controls; public/open derivatives will include only material allowed by utility and WRF agreements.

**Deliverables:** versioned data manifest; annotation/reference-method SOP; data-quality report; approved shareable dataset subset where feasible.

### Task 4 — model development and minimum-sensing analysis

**Months 7–18.** Train fit-for-purpose baseline and advanced models for each use case and sensing tier. Compare performance at matched examples when multiple sensor tiers are available. Model selection will consider discrimination/regression quality, calibration, inference burden, data requirement, maintainability and utility decision cost.

The minimum tier for a use case is the least complex configuration that satisfies its pre-registered decision threshold with an uncertainty margin under the required validation conditions. If no tier satisfies the threshold, the correct output is that camera-only monitoring is not validated for that use case.

**Deliverables:** model benchmark; sensor-ablation report; minimum-sensing recommendation by use case.

### Task 5 — cross-site/camera transfer stress tests

**Months 12–22.** Execute leave-one-site-out and leave-one-camera/configuration-out evaluations. Factor domain shifts where the dataset supports it. Produce transfer curves at zero target labels and increasing small calibration sets, then compare with full target-specific training.

For each target, report performance loss from source baseline, target coverage at calibrated confidence, required target examples to recover threshold performance, and failure modes. Use bootstrap confidence intervals or other appropriate uncertainty methods; use paired analyses when observations are genuinely paired.

**Deliverables:** cross-site/camera transfer matrix; calibration burden curves; failure-envelope catalog.

### Task 6 — implementation, economics and utility workflow assessment

**Months 18–25.** Convert technical results to operational choices. Estimate camera/sensor cost class, installation/maintenance burden, cleaning/calibration frequency, compute/storage/network needs, integration pattern, expected operator review burden, and dependence on conventional measurements. Compare incremental benefit of advanced sensing tiers to the added lifecycle burden.

Develop reference architecture that treats the camera/model as an **evidence producer** feeding a utility-approved monitoring/review workflow. The architecture will distinguish: sensor capture; validation/preprocessing; inference; quality/confidence/abstention; evidence/logging; integration; and any downstream operator decision. No generic model output becomes a control command by implication.

**Deliverables:** camera/implementation decision matrix; lifecycle burden model; reference integration architecture.

### Task 7 — synthesis, transfer framework and dissemination

**Months 23–30.** Produce WRF report and utility-facing implementation guidance. Prepare open reference schemas, benchmark/evaluation code and/or example data where permitted by technology/IP/data agreements. Conduct webcast and conference/peer-reviewed dissemination consistent with WRF communication requirements.

**Deliverables:** final report; Minimum-Sensing and Transferability Framework; utility field checklist; technology deliverables accepted under WRF guidance; open-access publication manuscript; webcast/presentation materials.

## 4. Evaluation framework

Use-case-specific primary metrics will be selected before final model choice. The common evaluation layer includes:

- classification/detection: sensitivity/recall, specificity, precision, F1, AUROC/AUPRC where appropriate;
- segmentation: IoU/Dice plus event-level utility metric;
- regression: MAE/RMSE/bias and agreement against reference method;
- calibration: Brier score / expected calibration error or task-appropriate equivalent;
- abstention: risk-vs-coverage curves and invalid-input rejection rate;
- operations: false alarms per operating period, misses, usable-data coverage, latency, data-loss rate;
- transfer: absolute and relative degradation from source/in-domain baseline; examples or person-hours needed for recalibration;
- reproducibility: exact data/model/configuration version and deterministic evaluation manifest.

Confidence intervals and hypothesis tests will be selected to match the sampling unit; frames from the same event/sequence will not be falsely treated as independent observations.

## 5. Application potential

The practical output is a procurement-and-validation decision aid rather than a vendor-specific model. A utility should be able to use the framework to determine whether a camera is appropriate, how sophisticated the camera needs to be, what ground truth must be collected before operational reliance, how much local recalibration is expected, how to detect domain shift, and what failure conditions require conventional measurement or human review.

The cross-sector design allows the project to identify which findings generalize and which remain use-case specific. A drinking-water source camera and a wastewater microscopy camera may use different optics and reference measurements, yet both can share a disciplined method for sensing sufficiency, held-out transfer, confidence calibration, provenance, abstention and lifecycle burden.

## 6. Communication plan — one-page content spine

**Audiences:** utility operations/engineering/laboratory staff; utility IT/OT and data teams; consultants/integrators; camera/sensor and software vendors; researchers; regulators where appropriate.

**During project:** concise periodic WRF/PAC updates tied to decisions; participating-utility working sessions at use-case selection, field-protocol approval, preliminary transfer results and implementation synthesis; website/project updates per WRF requirements.

**Final:** WRF final report; utility field checklist/decision matrix; webcast; conference presentation; at least one open-access peer-reviewed manuscript; technology artifacts (schemas/benchmark/reference code/data where permitted) packaged under WRF technology-deliverable requirements.

The communication plan will distinguish tested evidence from exploratory results and will publish negative/failure findings that materially affect safe adoption.

## 7. Management plan — content that cannot be finalized without actual people

Proposed roles, subject to `[OWNER INPUT]` and verified commitments:

- **Principal Investigator:** accountable for scientific scope, WRF/PAC interface, budget/schedule and final deliverables. Eligibility must be resolved before submission.
- **Computer Vision / ML Lead:** experimental design, model/evaluation implementation, transfer analysis.
- **Water Utility / Process Lead(s):** operational use-case definition, reference-method design, interpretation, field constraints.
- **Field/Data Lead:** camera installation, time synchronization, manifests, data quality and site protocols.
- **QA/QC Lead:** independent protocol/data/evaluation audit and deviation tracking.
- **Utility site leads:** local access, reference data, event interpretation, operational review.

Do not name a person or organization in these roles until their participation, qualifications and time commitment are documented.

## 8. Schedule summary

A 30-month planning baseline preserves the RFP's 24–30 month window and leaves review margin:

| Months | Work |
|---|---|
| 1–3 | Task 1: knowledge base, utility use-case selection, pre-registered thresholds |
| 2–6 | Task 2: sensing architecture, field/QA protocol |
| 4–15 | Task 3: multi-site data/reference acquisition |
| 7–18 | Task 4: model and sensing-tier evaluation |
| 12–22 | Task 5: transferability stress tests |
| 18–25 | Task 6: implementation/economics/workflow |
| 23–30 | Task 7: synthesis, deliverables, publication/outreach |

Final schedule must include WRF/PAC review/revision windows and committed site availability.

## 9. References — starter set

Public WRF sources:

- WRF Project 5154, *Autonomous in situ Monitoring of Harmful Algal Blooms*: https://www.waterrf.org/research/projects/autonomous-situ-monitoring-harmful-algal-blooms
- WRF Project 5266, *Determining the role of spectral imaging as an Early Warning System for presence/significance of algal blooms*: https://www.waterrf.org/research/projects/determining-role-spectral-imaging-early-warning-system-presencesignificance-algal
- WRF Project 5339, *Artificial Intelligence-Based Early-Warning & Mitigation System for Harmful Algal Blooms*: https://www.waterrf.org/research/projects/artificial-intelligence-based-early-warning-mitigation-system-harmful-algal-0
- WRF Project 5189, *Artificial Intelligence Adoption Framework for Water and Wastewater Utilities*: https://www.waterrf.org/research/projects/artificial-intelligence-adoption-framework-water-and-wastewater-utilities
- WRF ML Toolkit / Data-Driven Process Control program: https://www.waterrf.org/research/projects/MLToolkit

Selected external evidence:

- Satoh, H., Kashimoto, Y., Takahashi, N., Tsujimura, T. (2021). Deep learning-based morphology classification of activated sludge flocs in wastewater treatment plants. *Environmental Science: Water Research & Technology*, 7, 298–305. https://doi.org/10.1039/D0EW00908C
- `[FINAL PACKET: verify and add full bibliographic records for the current RGB HAB-camera, spectral HAB-classification, activated-sludge transfer/settleability and other literature cited in narrative before submission.]`

## 10. Explicit limitations in this draft

This draft establishes a credible method; it does **not** establish that the current applicant has already performed water-sector field research, owns required camera hardware, has a committed participating utility, has a qualified PI under WRF's definition, possesses a federal-grant-compliant accounting system, or has the 33% contribution. Those are proposal eligibility/qualification facts and must be supplied truthfully or the bid should not be submitted.
