# Wuhu 2026 LeRobot v2.1 trajectory QC engine

Competition asset for the 2026 Yangtze River Delta (Wuhu) multimodal embodied-data quality challenge. The organizer's published task is to analyze roughly 100 dual-arm robot trajectories, locate temporal, multimodal-sync, content/structure defects, and output a 0–100 data-value score. The published dataset uses LeRobot v2.1 and includes three camera streams, state/actions and frame/timestamp/episode/task indices.

This package is deliberately useful **before** organizer data are available to the runtime: the detection core is validated on synthetic hostile trajectories and videos, while the dataset adapter targets the documented LeRobot v2.1 episode layout. It makes no leaderboard, registration, eligibility, submission, or prize claim.

## Checks

- frame-index gaps, repeats, reversals
- timestamp reversals, declared-FPS mismatch, jitter
- required schema/episode identity and feature-vector width
- NaN/Inf and inconsistent numeric feature shape
- robust frame-to-frame state/action spikes and long near-static runs
- per-camera file/decode/frame-count/FPS coverage
- sampled black, low-detail/blur and frozen-video rates
- clean-reference distribution/range and dynamics violations
- deterministic explainable 0–100 quality and training-value scores

## Format

LeRobot v2.1 uses per-episode Parquet files plus per-camera MP4s and JSONL metadata. `meta/info.json` supplies `fps`, `features`, `data_path`, `video_path` and chunk size. Install `pyarrow` (preferred) to scan real datasets.

## Clean-reference profile

The challenge provides clean reference trajectories. Fit their state/action statistics once, save the profile, and then score test trajectories independently against that frozen reference. **Do not fit or recalibrate this profile on the test cohort.**

```bash
python -m wuhu_qc.cli profile /path/to/clean-reference --out reference.json
python -m wuhu_qc.cli scan /path/to/test-dataset --reference reference.json --out ./report
```

`profile` records robust median/MAD distributions for declared state/action dimensions plus robust frame-to-frame dynamics. `scan` never modifies the supplied profile and does not compute cohort ranks, percentiles, or thresholds across test episodes.

Outputs `report.json` and `report.csv` with episode, anomaly type/location, severity, quality score and value score.

## Validate core

```bash
python -m unittest -v tests.test_core
python -m compileall -q wuhu_qc tests
```

The hostile suite covers clean-reference shift detection and deterministic reference serialization in addition to timestamp/frame corruption, non-finite/shape failures, dynamics spikes, video coverage/FPS defects, black/frozen video, scoring order invariance, and fail-closed malformed vectors.

## Closure boundary

Real competition closure still requires mounting the organizer dataset, fitting the reference profile from the organizer's clean trajectories, running the full report against the organizer's test trajectories, inspecting current challenge portal submission rules, and submitting through the sponsor route before the deadline. Do not infer registration, submission, leaderboard position, prize eligibility, or prize payment from this engine alone.
