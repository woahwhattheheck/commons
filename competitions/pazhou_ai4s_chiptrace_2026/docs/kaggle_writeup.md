# Kaggle Writeup draft — ChipTrace

## Title

**ChipTrace: evidence-first multimodal drift intelligence for organ-on-chip experiments**

## One-sentence pitch

ChipTrace is a reproducible research-QC engine that tells an organ-on-chip team *why* a run may no longer be comparable to its baseline—across level, dynamics, sampling, replicates, and cross-sensor structure—and binds every finding to exact input bytes.

## Why this problem matters

AI for organ-on-chip should not begin with the most glamorous downstream prediction. It should begin by asking whether the experiment being interpreted is trustworthy enough to compare with its reference. OoC systems increasingly combine several time-varying modalities, and simple aggregation can hide sensor drift, missing samples, divergent replicates, or altered relationships between channels.

ChipTrace makes that precondition explicit. It is a narrow, inspectable layer that can sit before phenotype, dose-response, toxicity, digital-twin, or experiment-planning models.

## What we built

A dependency-free Python system with:

- strict non-sensitive experiment schema;
- robust median/MAD reference envelopes;
- seven independent quality signals: level shift, within-run change, trend, robust outliers, cadence missingness, replicate divergence, and cross-sensor correlation shift;
- transparent weighted risk plus hard evidence thresholds;
- `SUPPORTED`, `REVIEW`, and `INSUFFICIENT_EVIDENCE` states;
- explicit uncertainty;
- exact input hashes and a canonical SHA-256 replay receipt;
- a standalone HTML judge report;
- a deterministic synthetic demo and hostile tests.

The implementation uses only the Python standard library. A judge can clone the public repository and run the entire demo without network access, an API key, or package installation.

## Demo result

The synthetic candidate contains several deliberate experiment-quality faults. ChipTrace returns `REVIEW` with max quality-risk score `69.869`.

- `barrier_index`: level shift, within-run change, replicate divergence, elevated robust outliers.
- `oxygen_index`: within-run change, robust outliers, and changed cross-sensor structure.
- `flow_index`: replicate divergence, robust outliers, and changed cross-sensor structure.

The report receipt is:

`88233f2735ea76f7e90f68c05b0ee65ead47c97a221c268af02e8222ef06bb32`

That receipt verifies the complete canonical report, which includes SHA-256 hashes of the exact baseline and candidate inputs.

## Technical novelty

ChipTrace's novelty is not a single exotic detector. It is the **evidence contract around multimodal experiment intelligence**:

1. separate quality evidence from biological interpretation;
2. fuse multiple interpretable drift modes instead of one opaque anomaly score;
3. fail closed when evidence is sparse;
4. protect the public pipeline from accidental identity/clinical-field ingestion;
5. make each result byte-replayable and tamper-evident.

This makes the system useful both as a standalone lab QC prototype and as a reliable upstream gate for more complex OoC AI.

## Trust, ethics, and limitations

ChipTrace is research QC only. It does not diagnose disease, recommend treatment, establish safety or efficacy, or make patient-specific decisions. The checked-in demo is synthetic and contains no sensitive data. Unknown input columns are rejected by design. Fixed thresholds are prototype policy that a real lab should calibrate against its assay and validated QC process.

## Reproduce

```bash
python competitions/pazhou_ai4s_chiptrace_2026/chiptrace.py demo --directory /tmp/chiptrace-demo
python competitions/pazhou_ai4s_chiptrace_2026/chiptrace.py verify /tmp/chiptrace-demo/report.json
```

## Public artifacts to link in the final Writeup

- Public source repository: this Commons path after merge.
- Technical report: `docs/technical_report.md`.
- Demo video: record from `docs/demo_script.md`.
- Static judge report: `demo/report.html`.

## Competition-action note

This file is a submission-ready draft, not a claim that a Kaggle Writeup has already been submitted. Registration, terms acceptance, final video hosting, and actual competition submission remain separate organizer-account actions.
