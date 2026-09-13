# Wuhu LeRobot v2.1 Data Quality Inspector

A read-only, source-bound Python CLI for the **2026 Yangtze River Delta (Wuhu) Computing Power and Algorithm Innovation Application Competition — embodied-intelligence multimodal data-quality task**.

The competition brief describes roughly 100 dual-arm humanoid trajectories in LeRobot v2.1, with three camera streams, 20-dimensional state and action vectors, timestamp/index metadata, and four required result families: temporal faults, multimodal synchronization faults, content/structure faults, and a 0–100 training-value assessment. This package implements the automated inspection and reporting core without claiming registration, organizer submission, ranking, award, or payment.

## What ships

- Strict LeRobot v2.1 metadata validation for `info.json`, `episodes.jsonl`, `tasks.jsonl`, and `episodes_stats.jsonl`.
- Safe rendering of `data_path` and `video_path`; absolute paths, `..`, unsupported placeholders, and symlink traversal fail closed.
- One-episode-per-Parquet and one-camera-per-MP4 inventory checks, matched against episode metadata.
- Frame-order, frame-loss, FPS, timestamp reversal/duplicate, interval jitter, global-index, episode-index, task-index, and robust vector-jump analysis.
- Exact 20D state/action validation, including malformed, non-finite, wrong-dimension, and configurable out-of-range values.
- Per-camera frame count/FPS/start/end/duration checks plus cross-camera start/end spread, modality coverage, offset, and drift checks.
- Read-only FFmpeg sampling for corrupt video, black/white frames, and low-texture/flat-frame heuristics associated with occlusion or frozen imagery.
- Deterministic per-episode quality and training-value scores, with a transparent severity ledger and no hosted model dependency.
- Stable JSON, JSONL, Markdown, and dependency-free HTML reports.
- Fingerprint-bound probe capture/replay for reproducibility and offline review.
- Synthetic fault injection for every required anomaly family, replay-stability tests, immutable-input snapshots, and path/output safety tests.

## Runtime

Python 3.10+ is required. The CLI itself uses the standard library. Full automatic modality coverage additionally uses:

- `pyarrow` to decode episode Parquet rows;
- `ffprobe` to inspect MP4 stream metadata;
- `ffmpeg` to decode deterministic 64×64 grayscale samples.

Install the Python decoder in the environment that will read the organizer data:

```bash
python3 -m pip install pyarrow
```

Install FFmpeg using the operating system package manager. The tool never silently treats a missing decoder as clean: it emits a critical capability finding, marks coverage incomplete, and can return exit code 3 with `--strict-capabilities`.

## Acceptance test

```bash
cd revenue/wuhu-lerobot-data-quality
python3 -B -m unittest discover -s tests -v
```

Expected result: 15 tests pass. The suite builds isolated LeRobot v2.1-shaped fixtures in temporary directories; no repository fixture is relabeled as organizer data.

## Full inspection

Keep the report directory outside the raw dataset root:

```bash
python3 -B wuhu_quality.py inspect /data/wuhu/trajectory-set \
  --out-dir /data/reports/wuhu-run-001 \
  --strict-capabilities \
  --fail-on critical
```

Outputs:

- `report.json` — canonical machine-readable result and report digest;
- `report.md` — human scorecard and located anomaly list;
- `report.html` — self-contained, escaped browser view;
- `issues.jsonl` — one normalized anomaly span per line.

The output command prints a compact receipt containing the report digest, coverage state, scores, and output paths.

## Capture once, replay exactly

A full probe can be frozen outside the dataset root and reused by reviewers or scoring experiments:

```bash
python3 -B wuhu_quality.py capture /data/wuhu/trajectory-set \
  --out /data/reports/wuhu-run-001/probe.jsonl \
  --require-complete

python3 -B wuhu_quality.py inspect /data/wuhu/trajectory-set \
  --probe-jsonl /data/reports/wuhu-run-001/probe.jsonl \
  --out-dir /data/reports/wuhu-run-001/replay \
  --strict-capabilities
```

The first probe row binds the evidence to a sampled SHA-256 dataset fingerprint. A changed metadata/data/video identity causes replay to fail rather than silently score stale evidence. A probe that claims complete coverage but omits frame, video, or visual records is downgraded and reported.

## Detection contract

### 1. Temporal quality

- non-contiguous or out-of-order `frame_index`;
- global-index discontinuity;
- Parquet row count versus episode length;
- timestamp reversal or duplicate;
- gaps consistent with frame loss;
- declared versus observed FPS;
- interval jitter;
- robust state/action delta spikes.

### 2. Multimodal synchronization

- camera frame count versus episode length;
- camera FPS versus `info.fps`;
- camera start/end versus state/action coverage;
- duration drift;
- cross-camera start/end spread;
- missing camera records and incomplete modality coverage.

### 3. Content and structure

- missing, duplicate, malformed, or inconsistent metadata;
- missing/corrupt Parquet and video files;
- absent required columns/features;
- malformed, non-finite, wrong-dimension, or out-of-range vectors;
- video decode failure;
- black/white sampled frames;
- excessive low-texture sampled frames.

The visual checks are deterministic heuristics, not semantic scene understanding. `flat_ratio` is evidence consistent with occlusion, frozen imagery, or a low-texture view; it is not a claim about the physical cause.

### 4. Training value

Each episode receives four quality dimensions:

- `structure`
- `temporal`
- `synchronization`
- `content`

Each dimension starts at 100 and subtracts capped penalties by independent issue code. The episode quality score is their mean. The episode training-value score is:

```text
0.65 × quality + 0.20 × motion signal + 0.15 × camera coverage
```

The dataset score is:

```text
0.70 × episode-weighted value + 0.15 × task diversity + 0.15 × clean-episode ratio
```

This is an auditable integrity/value baseline. It does **not** claim task success, policy performance, semantic novelty, or downstream model accuracy.

## Read-only and deterministic guarantees

- Dataset files are opened only for reading.
- Report/probe destinations below the dataset root are rejected.
- Dataset and output path components may not traverse symlinks.
- Metadata JSON rejects duplicate keys and non-finite literals.
- Probe JSONL is fingerprint-bound and rejects duplicate frame/video identities.
- Issue ordering, float rounding, report JSON, and report digest are deterministic.
- Repeated frame anomalies are compressed into exact contiguous spans.
- Output files are written atomically in the destination directory.

The fingerprint hashes metadata fully. For potentially large data/video files it binds file size and either the full bytes or deterministic head/tail samples; the report labels this algorithm explicitly. Use external full-file hashes as an additional archival receipt when required by the organizer.

## Exit codes

| Code | Meaning |
|---:|---|
| 0 | command completed and requested gates passed |
| 2 | invalid input, unsafe path, malformed evidence, or I/O failure |
| 3 | `--strict-capabilities` / `--require-complete` requested, but at least one modality probe was incomplete |
| 4 | `--fail-on` threshold was met by a located finding |

Reports are still written before exit 3 or 4 so the failure is inspectable.

## Probe schema

The first JSONL row is a manifest:

```json
{"kind":"manifest","schema_version":"wuhu.lerobot-probe/v1","dataset_fingerprint":"…","capabilities":{"parquet":"complete","video_container":"complete","visual_content":"complete"}}
```

Frame rows contain the normalized required columns and the two vectors. Video rows contain the episode/camera identity, source-relative path, frame count, FPS, timing coverage, decode state, dimensions, sample count, and aggregate luma/texture ratios. `capture` writes this contract; `inspect --probe-jsonl` validates it before scoring.

## Submission boundary

This milestone is source, tests, and a report pipeline. It is not evidence that Bryce or TokenJunkieLabs registered, accepted organizer terms, downloaded the private competition archive, submitted a result, reached a leaderboard position, won an award, or received funds. Those external actions require separate receipts. See `SUBMISSION.md`.

## Source model

- Organizer task summary: Zhihu, “机器人轨迹数据集开放！具身多模态数据质量检测算法等你来测,” published August 31, 2026.
- LeRobot upstream migration implementation: `huggingface/lerobot`, `convert_dataset_v21_to_v30.py`, which documents v2.1’s per-episode Parquet, per-camera episode MP4, and legacy JSONL metadata layout.
- Public v2.1 structural reference: the AgiBotWorld2026 dataset card, including required metadata, path templates, episode rows, camera features, and state/action schema.

Exact source URLs and the mapped assumptions are recorded in `SOURCES.md`.
