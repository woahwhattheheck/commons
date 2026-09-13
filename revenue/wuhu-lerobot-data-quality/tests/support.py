from __future__ import annotations

import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import wuhu_quality as wq  # noqa: E402

CAMERAS = (
    "observation.images.image",
    "observation.images.left_wrist_image",
    "observation.images.right_wrist_image",
)


def write_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def dataset_snapshot(root: pathlib.Path) -> dict[str, tuple[bytes, int]]:
    snapshot: dict[str, tuple[bytes, int]] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        snapshot[path.relative_to(root).as_posix()] = (path.read_bytes(), path.stat().st_mode)
    return snapshot


class Fixture:
    def __init__(self, base: pathlib.Path, episodes: int = 2, length: int = 8, fps: int = 10) -> None:
        self.root = base / "dataset"
        self.episodes = episodes
        self.length = length
        self.fps = fps
        self.root.mkdir(parents=True)
        self.info = {
            "codebase_version": "v2.1",
            "robot_type": "dual_arm_humanoid",
            "total_episodes": episodes,
            "total_frames": episodes * length,
            "total_tasks": 1,
            "total_videos": episodes * len(CAMERAS),
            "total_chunks": 1,
            "chunks_size": 1000,
            "fps": fps,
            "splits": {"train": f"0:{episodes}"},
            "data_path": "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet",
            "video_path": "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4",
            "features": {
                "observation.state": {"dtype": "float32", "shape": [20]},
                "action": {"dtype": "float32", "shape": [20]},
                "timestamp": {"dtype": "float32", "shape": [1]},
                "frame_index": {"dtype": "int64", "shape": [1]},
                "episode_index": {"dtype": "int64", "shape": [1]},
                "task_index": {"dtype": "int64", "shape": [1]},
                "index": {"dtype": "int64", "shape": [1]},
                **{
                    camera: {
                        "dtype": "video",
                        "shape": [480, 640, 3],
                        "video_info": {"video.fps": fps, "video.codec": "h264"},
                    }
                    for camera in CAMERAS
                },
            },
        }
        write_json(self.root / "meta/info.json", self.info)
        write_jsonl(
            self.root / "meta/episodes.jsonl",
            [
                {"episode_index": episode, "tasks": ["pick and place"], "length": length}
                for episode in range(episodes)
            ],
        )
        write_jsonl(self.root / "meta/tasks.jsonl", [{"task_index": 0, "task": "pick and place"}])
        write_jsonl(
            self.root / "meta/episodes_stats.jsonl",
            [{"episode_index": episode, "stats": {"observation.state": {"count": [length]}}} for episode in range(episodes)],
        )
        for episode in range(episodes):
            data = self.root / f"data/chunk-000/episode_{episode:06d}.parquet"
            data.parent.mkdir(parents=True, exist_ok=True)
            data.write_bytes(f"PARQUET-PLACEHOLDER-{episode}".encode())
            for camera in CAMERAS:
                video = self.root / f"videos/chunk-000/{camera}/episode_{episode:06d}.mp4"
                video.parent.mkdir(parents=True, exist_ok=True)
                video.write_bytes(f"MP4-PLACEHOLDER-{episode}-{camera}".encode())

    def fingerprint(self) -> str:
        sink = wq.IssueSink()
        context = wq.load_context(self.root, wq.Config(), sink)
        return context.fingerprint

    def clean_rows(self) -> list[dict]:
        rows: list[dict] = [
            {
                "kind": "manifest",
                "schema_version": wq.PROBE_SCHEMA,
                "dataset_fingerprint": self.fingerprint(),
                "capabilities": {
                    "parquet": "complete",
                    "video_container": "complete",
                    "visual_content": "complete",
                },
                "producer": "test-fixture",
            }
        ]
        global_index = 0
        for episode in range(self.episodes):
            for frame in range(self.length):
                # Every dimension changes smoothly so clean training-value signal
                # is high and jitter detection sees a constant step.
                state = [episode + frame * 0.01 + index * 0.001 for index in range(20)]
                action = [episode + frame * 0.02 + index * 0.002 for index in range(20)]
                rows.append(
                    {
                        "kind": "frame",
                        "episode_index": episode,
                        "frame_index": frame,
                        "index": global_index,
                        "task_index": 0,
                        "timestamp": frame / self.fps,
                        "observation.state": state,
                        "action": action,
                    }
                )
                global_index += 1
            end = (self.length - 1) / self.fps
            for camera in CAMERAS:
                rows.append(
                    {
                        "kind": "video",
                        "episode_index": episode,
                        "camera": camera,
                        "path": f"videos/chunk-000/{camera}/episode_{episode:06d}.mp4",
                        "frame_count": self.length,
                        "fps": self.fps,
                        "start_timestamp": 0.0,
                        "end_timestamp": end,
                        "duration": end,
                        "width": 640,
                        "height": 480,
                        "decode_ok": True,
                        "sample_count": 8,
                        "black_ratio": 0.0,
                        "flat_ratio": 0.0,
                        "mean_luma": 100.0,
                        "mean_luma_std": 30.0,
                    }
                )
        return rows

    def write_probe(self, path: pathlib.Path, rows: list[dict] | None = None) -> pathlib.Path:
        write_jsonl(path, rows if rows is not None else self.clean_rows())
        return path


class WuhuQualityCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.temp.name)
        self.fixture = Fixture(self.base)
        self.probe = self.fixture.write_probe(self.base / "probe.jsonl")

    def tearDown(self) -> None:
        self.temp.cleanup()

