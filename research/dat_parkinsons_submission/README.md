# DaT Parkinson's Challenge — data-free submission carrier

This tree is public competition engineering only. **It contains no challenge scans, labels, smoke-test data, or trained weights.** The DaT Parkinson's Challenge rules prohibit uploading competition data to services such as retained AI assistants; keep all competition bytes on the registered participant's local machine.

## Contract

Observed public organizer contract on 2026-09-14:

- challenge: DrivenData DaT Parkinson's Challenge, competition 311
- deadline: 2026-09-16 23:59 UTC
- runtime source: `drivendataorg/competition-sfmn-parkinsons-runtime@976fdcea1e6e586ca8af13bdab703de4a6c260a4` (latest commit returned by the public GitHub commits endpoint on 2026-09-14; re-pin immediately before final submission)
- Python 3.12; offline inference; one NVIDIA A100 80 GiB; 24 vCPU; 220 GB RAM; <=3 hours
- input: `/code_execution/data/niftis/<uid>.nii.gz` + `/code_execution/data/submission_format.csv`
- output: `/code_execution/submission.csv`, exactly `uid,is_pathologic`, calibrated probability in `[0,1]`
- inference must process test cases independently; no test-time fitting, pseudo-labeling, or cross-case features

The organizer runtime already includes PyTorch, MONAI, TorchIO, nibabel, ANTs, scipy, scikit-image, scikit-learn, LightGBM and XGBoost. No inference-time network dependency is required by this carrier.

## Design

This is a deliberately compact 3-D baseline that can be trained *locally by the entrant* after they obtain challenge data under the organizer's terms:

1. canonical NIfTI load with finite-value validation;
2. foreground crop derived from that one scan only;
3. robust positive-intensity clipping and scale normalization;
4. fixed `(64, 96, 96)` tensor resampling;
5. a residual 3-D CNN with global pooling;
6. patient/center/group-aware cross-validation when an admitted local metadata group column is supplied; otherwise deterministic stratified folds are explicitly labeled as a weaker fallback;
7. fold ensemble + scalar temperature calibration fit from out-of-fold predictions only;
8. deterministic model bundle and manifest;
9. inference that reads each test scan independently and preserves the organizer's submission row order exactly.

The point is to remove packaging/runtime/leakage failure modes before scarce final-day local GPU runs. It is not a medical-device claim and no score is asserted without an actual participant-local validation run.

## Entrant-local usage

Expected local training labels are a CSV containing at least `uid,is_pathologic`. If the downloaded competition metadata exposes a hospital/patient/group authority, pass its exact column name with `--group-column`; do not invent groups from filenames.

```bash
python train.py \
  --labels /PRIVATE/dat/train_labels.csv \
  --nifti-dir /PRIVATE/dat/niftis \
  --out bundle \
  --group-column center

python scripts/build_submission.py --bundle bundle --out submission_src/model_bundle
python scripts/verify_public_tree.py .
```

Copy `submission_src/` into the official runtime repository's `submission_src/`, then use the organizer's `just pack-submission`, `just check-submission`, and local Docker test. Only the human participant should perform account enrollment, smoke tests, or full submissions.

## Evidence discipline

- Do not commit competition data, smoke-test data, local labels, derived per-case features, predictions, or challenge-trained weights to this public tree.
- `model_bundle/` is intentionally gitignored here; a final `submission.zip` is a participant-local artifact.
- Public source may be MIT licensed, but external model/data licenses still need explicit entrant-side verification before use.
- A leaderboard score is not a validation result; retain fold assignments, OOF probabilities, calibration parameters, source hashes, and local runtime receipts.
