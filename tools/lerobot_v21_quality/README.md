# LeRobot v2.1 multimodal data-quality inspector

A read-only, deterministic baseline for auditing LeRobot v2.1 robot-trajectory datasets. It maps the Wuhu embodied-intelligence challenge's required fault classes into explicit diagnostics, per-episode metrics, and transparent 0–100 quality/training-value scores.

This directory is a **build artifact, not a competition-registration or submission receipt**. It does not download organizer data, modify datasets, contact a provider, or claim prize eligibility.

## What it checks

The scanner reports the episode, frame, modality, reason, severity, observed value, and threshold for each finding.

| Requirement | Implemented checks |
|---|---|
| LeRobot v2.1 structure | `meta/info.json`, `meta/episodes.jsonl`, declared totals, contiguous/unique episode indices, path templates, expected Parquet/video inventory, non-empty files, v2.1 version fence |
| Challenge schema | exactly three camera features; 20-dimensional `observation.state`; 20-dimensional `action`; positive finite FPS |
| Temporal integrity | missing/duplicate/backward frame indices, non-increasing timestamps, frame-rate jitter, metadata/observed length mismatch |
| Multimodal synchronization | coverage, median offset, p95 absolute offset, drift, late start/early stop for state, action, and every camera |
| State/action content | missing/malformed vectors, dimension mismatch, NaN/Infinity, configurable physical range bounds |
| Visual content | missing/corrupt decoded frames, black-frame mean luminance, low-texture proxy, saturation/occlusion proxy |
| Training value | per-episode quality/value, usable-frame ratio, signal richness, coverage, task distribution/entropy, low/high-value episode ratios, p10/median/p90 |
| Reporting | deterministic JSON, Markdown, and dependency-free HTML; semantic exit codes; content/inventory fingerprint |

The organizer description calls for automated analysis of about 100 dual-arm trajectories, three image streams, 20-dimensional state/actions, timing and synchronization faults, content/structure faults, and a 0–100 training-value score. The implementation keeps every threshold and weight visible instead of hiding decisions in a learned black box.

## Input modes

### 1. Native LeRobot v2.1 scan

Native mode reads the conventional v2.1 layout:

```text
dataset/
├── meta/
│   ├── info.json
│   └── episodes.jsonl
├── data/chunk-000/episode_000000.parquet
└── videos/chunk-000/<video-key>/episode_000000.mp4
```

Install the optional decoders:

```bash
python -m pip install -r requirements-optional.txt
```

Run a full scan. Put reports **outside** the raw dataset root:

```bash
python lerobot_quality.py /data/wuhu-v21 \
  --output /reports/wuhu-v21 \
  --format json --format markdown --format html
```

Native Parquet decoding requires `pyarrow`. Native MP4 decoding and image statistics require `opencv-python-headless`. Missing dependencies produce an explicit incomplete-scan diagnostic and exit code `2`; they never silently produce a passing report.

### 2. Canonical observation manifest

A trusted decoder may emit one JSON object per observed frame. This seam is also used by the synthetic fault-injection suite. The scanner still validates the dataset's declared Parquet/video inventory, but it obtains decoded state/action/camera observations from the manifest instead of importing native decoders.

```bash
python lerobot_quality.py /data/wuhu-v21 \
  --manifest /work/decoded-observations.jsonl \
  --output /reports/wuhu-v21
```

Each line has this shape:

```json
{
  "episode_index": 0,
  "frame_index": 12,
  "timestamp": 0.4,
  "task_index": 0,
  "state_timestamp": 0.4,
  "action_timestamp": 0.4,
  "observation.state": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9],
  "action": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9],
  "cameras": {
    "observation.images.image": {
      "timestamp": 0.4,
      "present": true,
      "decode_ok": true,
      "mean_luma": 108.2,
      "luma_stddev": 22.7,
      "occlusion_ratio": 0.03
    },
    "observation.images.left_wrist_image": {
      "timestamp": 0.401,
      "present": true,
      "decode_ok": true,
      "mean_luma": 104.8,
      "luma_stddev": 19.6,
      "occlusion_ratio": 0.04
    },
    "observation.images.right_wrist_image": {
      "timestamp": 0.399,
      "present": true,
      "decode_ok": true,
      "mean_luma": 111.0,
      "luma_stddev": 25.1,
      "occlusion_ratio": 0.02
    }
  }
}
```

Indices reject booleans and non-integral numbers. Numeric vector/timestamp fields reject booleans; non-finite vector values become located diagnostics. Camera entries may be `null` to represent an absent frame.

## Read-only contract

The scanner only opens dataset and manifest files for reading. It refuses to place reports at the dataset root or any descendant, including a symlink-resolved descendant. Reports are written to temporary sibling files and atomically replaced in the requested external output directory.

The input fingerprint is deterministic and bounded: it hashes each relevant path, size, first 64 KiB, and last 64 KiB. It avoids rereading entire large MP4 files while still changing for ordinary content/inventory changes. Wall-clock timestamps are deliberately absent from reports, so an unchanged scan replays byte-for-byte.

## Thresholds

Defaults are conservative corruption fences, not claims about the robot's true physical limits. Replace state/action bounds with organizer- or robot-authoritative limits before final scoring.

```text
state/action dimensions       20 / 20
state/action absolute maximum 1,000,000
FPS interval jitter           20%
median sync offset            25 ms
clock drift                   50 ms
minimum modality coverage     98%
black-frame mean luma         <= 8
low-texture luma stddev       <= 4
occlusion/saturation proxy    >= 0.85
```

Every threshold has a CLI flag:

```bash
python lerobot_quality.py DATASET \
  --state-abs-max 3.2 \
  --action-abs-max 1.0 \
  --fps-jitter-fraction 0.10 \
  --sync-offset-ms 15 \
  --sync-drift-ms 30 \
  --minimum-modality-coverage 0.995 \
  --black-luma-max 6 \
  --low-texture-stddev-max 3 \
  --occlusion-ratio-min 0.90
```

## Scoring

All component scores are clamped to `[0, 100]`.

### Quality score

```text
20% structure
25% temporal integrity
25% multimodal synchronization
30% content validity
```

- **Structure** starts at 100 and loses bounded penalties for metadata length disagreement, frame gaps/duplicates, row episode mismatch, and invalid timestamps.
- **Temporal** is `40% frame continuity + 30% timestamp monotonicity + 30% FPS stability`.
- **Synchronization** averages modality scores built from `50% coverage + 30% median offset + 20% drift`.
- **Content** combines vector validity/range, camera decode success, non-black ratio, non-occluded ratio, and texture coverage. Unmeasured image content is not assumed healthy.

### Training-value score

```text
65% quality
15% multimodal coverage
10% visual signal richness
 5% task-index presence
 5% usable-frame ratio
```

Dataset summaries add task counts, Shannon entropy, normalized balance, and episode value distributions. These are explainable baselines, not assertions that a simple luminance or task-index statistic fully captures semantic demonstration value.

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | complete scan and no error-severity findings |
| `1` | complete scan, but data-quality errors were found |
| `2` | scan incomplete (missing files/decoder/dependency/invalid manifest) |
| `3` | runtime/configuration/output error |

`argparse` syntax errors retain the conventional exit code `2`.

## Tests

```bash
python -B -m unittest -v
python -B -m compileall -q .
```

The suite injects and asserts every required anomaly family:

- frame gaps, FPS jitter, timestamp reversal, and frame-order reversal;
- modality offset, drift, and incomplete coverage;
- corrupt, black, low-texture, and occluded camera samples;
- malformed dimensions, NaN/Infinity, and configured range violations;
- version/schema/camera-count/episode-index/inventory defects;
- deterministic JSON/Markdown/HTML replay;
- raw-input immutability and refusal to write reports beneath the dataset root;
- semantic CLI exit codes.

## Limits and next evidence

- The visual occlusion metric is a transparent saturation/low-texture proxy, not a learned semantic occlusion model. A competition submission should benchmark and, if useful, augment it with a task-specific detector.
- Native camera timestamps are currently inferred as `frame_index / fps`. If organizer data exposes independent device-clock timestamps, export them through the canonical manifest for true clock-offset/drift analysis.
- Default state/action bounds catch corruption, not physically invalid poses. Replace them with authoritative joint/end-effector limits.
- No organizer dataset was downloaded or executed in this build. The next evidence gate is a read-only run against the provided reference dataset, followed by threshold calibration on reference-only data and a blind replay on the anomaly set.
- Registration, team eligibility, submission packaging, and prize/payment remain separate owner-controlled actions.

## Sources

- Challenge/task description and stated v2.1 modalities/fault classes/schedule: <https://zhuanlan.zhihu.com/p/2077791364478194086>
- Competition landing page cited by the build order: <https://cvmart.net/cv_landing/list/wuhu2026>
- LeRobot dataset API and metadata model: <https://huggingface.co/docs/lerobot/main/api/datasets>
- LeRobot repository: <https://github.com/huggingface/lerobot>
