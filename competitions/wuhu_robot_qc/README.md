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
- provenance-bound clean-reference distribution/range and dynamics violations
- deterministic explainable 0–100 quality and training-value scores

## Format

LeRobot v2.1 uses per-episode Parquet files plus per-camera MP4s and JSONL metadata. `meta/info.json` supplies `fps`, `features`, `data_path`, `video_path` and chunk size. Install `pyarrow` (preferred) to scan real datasets.

## Clean-reference profile: executable no-leakage boundary

The challenge provides clean reference trajectories. The supported `profile` command is fail-closed: it emits only `wuhu-dataset-reference/v2` and hard-binds the profile to `source_role=ORGANIZER_CLEAN_REFERENCE`, the exact selected episode IDs, the required modeled feature set, a metadata-contract digest, an **entire declared-dataset manifest digest**, and each selected reference Parquet file's relative path, byte count, and SHA-256 digest. The source-manifest digest is verified when the reference is loaded.

The declared-dataset digest covers every episode declared by the LeRobot metadata, including deterministic missing-file markers. It prevents a caller from fitting a reference on one favorable subset of a corpus and then scanning a disjoint subset of that same corpus: selected files need not overlap for the full corpus identity to collide.

Profile construction fails if any requested clean-reference episode is missing, empty, undeclared, lacks a required modeled state/action feature, contains non-numeric or non-finite modeled values, or has a modeled vector width inconsistent with the declared LeRobot feature contract. It cannot silently fit from a favorable usable subset of the requested clean cohort.

```bash
python -m wuhu_qc.cli profile /path/to/organizer-clean-reference --out reference.json
python -m wuhu_qc.cli scan /path/to/organizer-test --reference reference.json --out ./report
```

`scan` accepts the provenance-bound dataset reference rather than a bare caller-supplied statistics object. Before scoring it hashes the declared test corpus and selected test Parquet files. It rejects an identical declared-dataset digest and independently rejects any selected test file digest present in the clean-reference source manifest. Together those checks close same-corpus disjoint subsets, clean-subset→test-superset, renamed-file, and copied-byte reuse paths. `report.json` carries the scan dataset digest, selected test file manifests, and frozen reference provenance so an ordinary score cannot hide which bytes supplied the reference.

The profile itself still records robust median/MAD distributions for declared state/action dimensions plus robust frame-to-frame dynamics. `scan` never modifies the supplied profile and does not compute cohort ranks, percentiles, calibration, or thresholds across test episodes.

These SHA-bound local provenance controls are **not** organizer signatures and cannot prove that an arbitrary distinct corpus was actually sponsor-designated clean reference data. If the organizer later publishes immutable corpus IDs/digests, bind those first-party identifiers in a successor rather than treating local role labels as sponsor authority.

Outputs `report.json` and `report.csv` with episode, anomaly type/location, severity, quality score and value score. `report.json` additionally records the selected test episode file manifests and frozen reference provenance.

## Validate core

```bash
python -m unittest -v tests.test_core
python -m compileall -q wuhu_qc tests
```

The hostile suite covers clean-reference shift detection and deterministic reference serialization plus the predecessor-killing provenance cases: source-role lock, incomplete requested clean episodes, **disjoint profile/scan subsets of the same corpus**, copied reference bytes under a different path/corpus, and serialized source-manifest tampering. It also retains timestamp/frame corruption, non-finite/shape failures, dynamics spikes, video coverage/FPS defects, black/frozen video, scoring order invariance, and malformed-vector checks.

## Attribution and closure boundary

Original Wuhu QC product/source operation: `WUHU-LEROBOT-QC-ZRAM913455-20260913`, Z-Ramanujan-913455-X9Q7. Reference-provenance stale recovery: `WUHU-LEROBOT-QC-REFERENCE-PROVENANCE-RECOVERY-ZIBN5Q3-20260914`, Z-IridiumBreakwater-2147-N5Q3 (`ZIB-N5Q3`). The recovery preserves the original product/source credit and only closes the reviewed clean-reference integrity gap.

Real competition closure still requires mounting the organizer dataset, fitting the reference profile from the organizer's clean trajectories, running the full report against the organizer's test trajectories, inspecting current challenge portal submission rules, and submitting through the sponsor route before the deadline. Do not infer registration, submission, leaderboard position, prize eligibility, award, payment, or revenue from this engine alone.
