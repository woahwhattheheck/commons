# WRF 5417 QA/QC and validation plan

This is a proposal draft. Final QA/QC must be reconciled to actual participating sites, reference methods, laboratories, instruments, software and WRF requirements.

## 1. Quality objectives

The QA/QC system is designed to make five classes of error visible rather than allowing them to collapse into a single model score:

1. **capture failure** — unusable image, blocked/dirty lens, glare, lighting or synchronization failure;
2. **reference failure** — missing, delayed, ambiguous or non-comparable conventional measurement;
3. **data/annotation failure** — provenance, labeling or split contamination;
4. **model failure** — misclassification/regression error, miscalibration or unrecognized out-of-distribution condition;
5. **transfer failure** — acceptable source-site performance that does not survive a new site/camera/season/process regime.

The project will report these separately.

## 2. Quality records and provenance

Every retained observation or sequence will bind, as applicable:

- utility/site and sampling location using project-approved identifiers;
- camera/sensor model and stable device ID;
- lens/optics/filter/illumination configuration;
- resolution, exposure and acquisition settings needed to reproduce the image stream;
- timestamp and time-synchronization status;
- calibration/reference-target status where relevant;
- environmental/process context approved for research use;
- reference sample/measurement identity and timing window;
- annotation version and annotator/reviewer identity or method;
- preprocessing pipeline and code/configuration version;
- dataset release/manifest version;
- model/evaluation version;
- exclusion/deviation reason when a record is not used.

Raw PII, credentials and unnecessary utility-sensitive metadata are not research-quality fields and should not be copied into public artifacts.

## 3. Camera and field QA

Before deployment, each camera configuration will have a documented acceptance check covering image integrity, focus/field of view, clock synchronization, storage/network path, expected illumination regime, and reference target or scene check where appropriate.

During deployment, quality controls will include:

- periodic fixed-scene/reference-target checks where feasible;
- dirty/occluded lens detection and cleaning log;
- missing-frame and timestamp-gap monitoring;
- configuration drift detection;
- exposure/saturation/blur statistics;
- event/deviation log for maintenance, repositioning, firmware or camera replacement;
- deliberate nuisance-condition collection rather than silently excluding hard conditions.

A replaced/repositioned camera creates a new configuration stratum for transfer analysis; it is not treated as if the data source were unchanged.

## 4. Reference-method QA

Each use case will identify the conventional measurement or operational evidence against which the imaging method is evaluated. Final methods must be site- and analyte-specific. General requirements are:

- use standard/certified utility or laboratory methods where applicable;
- record method, instrument, calibration/QC status and sample timing;
- define maximum allowed image↔reference timing offset before analysis;
- preserve raw and transformed units;
- flag censored/below-detection/invalid values explicitly;
- do not use operator impressions as quantitative ground truth unless the task itself is a structured operator classification and agreement is measured;
- use duplicate/reference samples or repeated readings at a frequency appropriate to the method and WRF/site QA requirements.

If reference quality is insufficient for a planned endpoint, the correct QA disposition is `HOLD/INSUFFICIENT_REFERENCE`, not a forced label.

## 5. Annotation QA

For human-annotated tasks:

- create a written annotation protocol with edge-case examples;
- train annotators on a common seed set;
- double-annotate a predeclared fraction of records;
- quantify inter-rater agreement with a metric appropriate to the task;
- resolve material disagreements by a defined adjudication process;
- blind annotators to model predictions on benchmark/test data;
- version annotations; never overwrite a released label set without a recorded change reason.

## 6. Dataset split and leakage controls

The benchmark unit is not necessarily an image frame. Consecutive frames, bursts, repeated microscope fields, samples from the same bottle/event, and observations from the same operating episode can be highly dependent.

Therefore:

- partition by site, time block and event/sequence before tuning;
- keep all near-duplicate/related frames in the same partition;
- reserve at least one site/camera/configuration for true transfer testing when the design permits;
- prevent statistics, normalization parameters, reference labels or manual selections derived from held-out data from entering training;
- hash/version manifests and record every exclusion;
- rerun a similarity/duplicate screen across train/test partitions before final scoring.

Random frame-level splits may be used only for a clearly labeled exploratory within-domain experiment and never presented as cross-site generalization.

## 7. Pre-specified acceptance thresholds

Before selecting the final model for a use case, the research team and participating utility will establish:

- intended monitoring/review decision;
- minimum useful sensitivity/recall and/or quantitative error;
- acceptable false-alarm burden;
- acceptable miss burden and any high-consequence miss class;
- minimum usable coverage after abstention/quality rejection;
- maximum latency where relevant;
- expected target-site calibration burden;
- conditions in which conventional measurement remains mandatory.

Thresholds will be documented before final model comparison to reduce post-hoc goal shifting.

## 8. Statistics and uncertainty

Analysis will use the correct independent sampling unit. Frames nested within the same event/site are not counted as thousands of independent events.

As appropriate:

- report confidence intervals using site/event-aware bootstrap or model-based methods;
- use paired comparisons for paired sensor tiers/camera settings;
- report class/event prevalence alongside precision/recall;
- report absolute counts in addition to percentages for rare events;
- publish confusion matrices / residual distributions and subgroup/domain-shift slices;
- distinguish exploratory from confirmatory analyses;
- document all multiple-comparison or model-selection procedures material to inference.

## 9. Calibration, abstention and invalid inputs

A model score is not automatically a calibrated probability. Where confidence is used operationally, evaluate calibration on held-out data and under transfer.

The pipeline will define explicit states for:

- valid model output;
- low-confidence output requiring review;
- invalid/unusable input;
- unsupported configuration/domain;
- missing/late reference evidence;
- model/data/configuration mismatch.

Performance with abstention will be reported as risk/quality versus coverage. Low-confidence or out-of-domain cases are not relabeled as normal to keep uptime high.

## 10. Transferability protocol

For each feasible source→target pair:

1. freeze the source model and preprocessing;
2. evaluate **zero-shot** target performance;
3. expose predeclared small target calibration sets and evaluate **few-shot** recalibration/fine-tuning;
4. where data permit, fit a target-specific model as an upper comparison;
5. report performance, calibration, coverage and operational burden at each step.

Stratify by camera family, geometry, lighting, season/weather, site and process regime where sample size supports it. Transfer success is use-case specific; one successful target does not establish universal transfer.

## 11. Sensing-tier comparison

Advanced sensing must earn its complexity. RGB, controlled illumination/filtering and spectral tiers will be compared on matched data where feasible. Report:

- task performance and uncertainty;
- incremental improvement over lower tier;
- acquisition and calibration burden;
- data/compute/storage/network burden;
- maintenance/cleaning/environmental burden;
- failure modes;
- target-site transfer behavior.

The recommendation is the **lowest tier meeting the operational threshold with adequate margin**, not the technically most elaborate sensor.

## 12. Software reproducibility

Research code and benchmark artifacts will, where contract/licensing/data rules permit:

- pin dependencies and runtime assumptions;
- use versioned, machine-readable dataset/evaluation manifests;
- record immutable input/model/config digests for published benchmark runs;
- separate training from evaluation code paths;
- make metric definitions executable and unit-tested;
- preserve negative/failed experiments material to final conclusions;
- provide a minimal reproduction command for each published table/figure generated by code.

For technology deliverables, packaging/licensing/documentation will follow WRF's applicable Technology Deliverables Guidance and Project Funding Agreement rather than assuming that every utility dataset or dependency can be open-sourced.

## 13. Deviation and corrective-action process

Material deviations—camera replacement, missed reference sampling, protocol change, annotation defect, corrupted data, target leakage, metric defect—will be logged with discovery date, affected records/results, root cause, correction and re-analysis decision. Results invalidated by a deviation will not remain in the final evidence table merely because they were favorable.

## 14. Independent review gates

Before each major external deliverable:

- verify dataset/manifest and code versions;
- re-run focused benchmark tests;
- verify table/figure provenance;
- reconcile narrative claims to generated results;
- inspect excluded-data/deviation logs;
- confirm that field/utility claims are supported by actual site records;
- check that public release contains no restricted data, credentials or unauthorized third-party material.

## 15. Safety / operational authority boundary

The baseline research output is monitoring and decision support. A camera/model result will not directly operate dosing, treatment, pumping, discharge or other process controls as an undocumented consequence of the research pipeline. Any control application requires a separately designed, utility-approved validation and safety case.
