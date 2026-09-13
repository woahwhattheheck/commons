# Source map

Source review date: 2026-09-13.

## Competition brief

**Zhihu / CVMart organization account**  
“机器人轨迹数据集开放！具身多模态数据质量检测算法等你来测”  
https://zhuanlan.zhihu.com/p/2077791364478194086

Mapped requirements:

- roughly 100 dual-arm humanoid multimodal trajectories;
- temporal checks: frame loss, unstable FPS, timestamp reversal, ordering, jitter;
- multimodal checks: timestamp offset, drift, late start/early stop, incomplete coverage;
- content/structure checks: black/corrupt/occluded imagery, illegal/out-of-range state, missing fields, corrupt files;
- 0–100 data-value assessment and a full automated report;
- LeRobot v2.1;
- three visual streams (`image`, `left_wrist_image`, `right_wrist_image`);
- 20D state and 20D actions plus timestamp/frame/episode/task indices;
- advertised preliminary registration window through September 14, 2026.

The competition website remains authoritative for rules and submission state. This package does not automate registration or submission.

## Upstream LeRobot format evidence

**Hugging Face LeRobot migration implementation**  
`src/lerobot/scripts/convert_dataset_v21_to_v30.py`  
https://github.com/huggingface/lerobot/blob/b6ec0060779550c0a157ae34feb89e0cf86012a8/src/lerobot/scripts/convert_dataset_v21_to_v30.py

Mapped v2.1 assumptions:

- `data/chunk-000/episode_000000.parquet` (one data file per episode);
- `videos/chunk-000/CAMERA/episode_000000.mp4` (one video per camera and episode);
- `meta/episodes.jsonl` rows with `episode_index`, `tasks`, and `length`;
- `meta/tasks.jsonl` rows with `task_index` and `task`;
- `meta/episodes_stats.jsonl` rows with `episode_index` and `stats`;
- camera keys are discovered from `info.json` features whose dtype is video;
- local v2.1 roots contain `meta/`, `data/`, and `videos/`.

## Public v2.1 structural reference

**AgiBotWorld2026 dataset card**  
https://huggingface.co/datasets/Alleneworld/AgiBotWorld2026

Mapped assumptions:

- schema is primarily declared by `meta/info.json`;
- data and video paths are generated from `data_path` and `video_path` templates;
- required frame features include state, action, episode index, frame index, global index, task index, and timestamp;
- one complete episode is stored in each Parquet file;
- one camera stream for one episode is stored in each video file;
- camera metadata includes video rate/shape information.

## Deliberate implementation boundaries

The scoring formula, severity penalties, motion signal, black/white thresholds, and low-texture heuristic are baseline design choices in this repository. They are exposed in the report configuration and README rather than attributed to an organizer rule. They should be calibrated against organizer reference data before submission.
