from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import lerobot_quality as quality

CAMERAS = [
    "observation.images.image",
    "observation.images.left_wrist_image",
    "observation.images.right_wrist_image",
]


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _info(total_episodes: int, total_frames: int, *, version: str = "v2.1", cameras: list[str] | None = None) -> dict:
    cameras = CAMERAS if cameras is None else cameras
    features = {
        "observation.state": {"dtype": "float32", "shape": [20]},
        "action": {"dtype": "float32", "shape": [20]},
        "timestamp": {"dtype": "float32", "shape": [1]},
        "frame_index": {"dtype": "int64", "shape": [1]},
        "episode_index": {"dtype": "int64", "shape": [1]},
        "task_index": {"dtype": "int64", "shape": [1]},
    }
    for camera in cameras:
        features[camera] = {"dtype": "video", "shape": [480, 640, 3]}
    return {
        "codebase_version": version,
        "robot_type": "dual_arm_fixture",
        "total_episodes": total_episodes,
        "total_frames": total_frames,
        "total_tasks": 1,
        "total_videos": total_episodes * len(cameras),
        "total_chunks": 1,
        "chunks_size": 1000,
        "fps": 10,
        "splits": {"train": f"0:{total_episodes}"},
        "data_path": "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet",
        "video_path": "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4",
        "features": features,
    }


def _good_row(episode: int, frame: int, *, timestamp: float | None = None) -> dict:
    timestamp = frame / 10 if timestamp is None else timestamp
    return {
        "episode_index": episode,
        "frame_index": frame,
        "timestamp": timestamp,
        "task_index": 0,
        "state_timestamp": timestamp,
        "action_timestamp": timestamp,
        "observation.state": [float(frame + offset / 100) for offset in range(20)],
        "action": [float(frame - offset / 100) for offset in range(20)],
        "cameras": {
            camera: {
                "timestamp": timestamp,
                "decode_ok": True,
                "mean_luma": 110 + frame,
                "luma_stddev": 24 + frame,
                "occlusion_ratio": 0.02,
            }
            for camera in CAMERAS
        },
    }


class DatasetFixture:
    def __init__(
        self,
        root: Path,
        rows: list[dict],
        *,
        info: dict | None = None,
        episodes: list[dict] | None = None,
        create_inventory: bool = True,
    ):
        self.root = root
        (root / "meta").mkdir(parents=True)
        info = info or _info(1, len(rows))
        episodes = episodes or [{"episode_index": 0, "length": len(rows), "tasks": ["fixture"]}]
        (root / "meta" / "info.json").write_text(json.dumps(info, sort_keys=True), encoding="utf-8")
        (root / "meta" / "episodes.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in episodes), encoding="utf-8"
        )
        self.manifest = root / "observations.jsonl"
        self.manifest.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
        if create_inventory:
            camera_keys = sorted(
                key for key in info.get("features", {}) if str(key).startswith("observation.images.")
            )
            chunks_size = int(info.get("chunks_size", 1000))
            episode_indices = sorted(
                {int(row["episode_index"]) for row in rows if "episode_index" in row}
                | {int(row["episode_index"]) for row in episodes if "episode_index" in row}
            )
            for episode_index in episode_indices:
                values = {
                    "episode_index": episode_index,
                    "episode_chunk": episode_index // max(1, chunks_size),
                    "chunk_index": episode_index // max(1, chunks_size),
                }
                data_path = root / info["data_path"].format(**values)
                data_path.parent.mkdir(parents=True, exist_ok=True)
                data_path.write_bytes(b"PAR1 synthetic fixture bytes")
                for camera in camera_keys:
                    video_path = root / info["video_path"].format(video_key=camera, **values)
                    video_path.parent.mkdir(parents=True, exist_ok=True)
                    video_path.write_bytes(b"synthetic mp4 fixture bytes")


class LeRobotQualityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "dataset"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _fixture(self, rows: list[dict], **kwargs) -> DatasetFixture:
        return DatasetFixture(self.root, rows, **kwargs)

    def test_clean_manifest_scores_high_and_is_diagnostic_free(self) -> None:
        fixture = self._fixture([_good_row(0, frame) for frame in range(8)])
        report = quality.inspect_dataset(fixture.root, manifest=fixture.manifest)
        self.assertTrue(report.complete)
        self.assertEqual(report.summary["diagnostic_counts"]["error"], 0)
        self.assertEqual(report.summary["diagnostic_counts"]["warning"], 0)
        self.assertEqual(report.summary["frame_count"], 8)
        self.assertGreaterEqual(report.summary["quality_score"], 99.0)
        self.assertGreaterEqual(report.summary["value_score"], 90.0)
        self.assertEqual(report.episodes[0].metrics["frame_continuity_ratio"], 1.0)
        self.assertEqual(report.episodes[0].metrics["camera_decode_ratio"], 1.0)

    def test_temporal_fault_injection_covers_gap_order_reversal_timestamp_and_jitter(self) -> None:
        rows = [_good_row(0, 0, timestamp=0.0), _good_row(0, 2, timestamp=0.35), _good_row(0, 1, timestamp=0.20)]
        fixture = self._fixture(rows)
        report = quality.inspect_dataset(fixture.root, manifest=fixture.manifest)
        codes = {item.code for item in report.episodes[0].diagnostics}
        self.assertTrue({"frame_gap", "frame_order_reversal", "timestamp_reversal", "fps_jitter"}.issubset(codes))
        self.assertLess(report.episodes[0].subscores["temporal"], 50.0)

    def test_sync_fault_injection_covers_offset_drift_and_coverage(self) -> None:
        rows = [_good_row(0, frame) for frame in range(6)]
        for frame, row in enumerate(rows):
            row["action_timestamp"] = row["timestamp"] + 0.060 + frame * 0.020
        rows[0]["cameras"][CAMERAS[0]] = None
        rows[1]["cameras"][CAMERAS[0]] = None
        fixture = self._fixture(rows)
        report = quality.inspect_dataset(fixture.root, manifest=fixture.manifest)
        codes = {item.code for item in report.episodes[0].diagnostics}
        self.assertIn("sync_offset", codes)
        self.assertIn("sync_drift", codes)
        self.assertIn("modality_coverage", codes)
        action_metrics = report.episodes[0].metrics["synchronization"]["action"]
        self.assertGreater(action_metrics["median_offset_ms"], 25.0)
        self.assertLess(report.episodes[0].subscores["synchronization"], 90.0)

    def test_content_fault_injection_covers_corrupt_black_occluded_and_low_texture(self) -> None:
        rows = [_good_row(0, frame) for frame in range(4)]
        rows[0]["cameras"][CAMERAS[0]]["decode_ok"] = False
        rows[1]["cameras"][CAMERAS[1]]["mean_luma"] = 1.0
        rows[2]["cameras"][CAMERAS[2]]["luma_stddev"] = 0.5
        rows[3]["cameras"][CAMERAS[2]]["occlusion_ratio"] = 0.99
        fixture = self._fixture(rows)
        report = quality.inspect_dataset(fixture.root, manifest=fixture.manifest)
        codes = {item.code for item in report.episodes[0].diagnostics}
        self.assertTrue({"corrupt_camera_frame", "black_frame", "low_texture_frame", "occluded_frame"}.issubset(codes))
        self.assertLess(report.episodes[0].subscores["content"], 100.0)

    def test_vector_fault_injection_covers_dimension_nonfinite_and_range(self) -> None:
        rows = [_good_row(0, frame) for frame in range(4)]
        rows[0]["observation.state"] = [0.0] * 19
        rows[1]["action"][3] = float("nan")
        rows[2]["observation.state"][4] = float("inf")
        rows[3]["action"][5] = 123.0
        fixture = self._fixture(rows)
        thresholds = quality.Thresholds(state_abs_max=10.0, action_abs_max=10.0)
        report = quality.inspect_dataset(fixture.root, manifest=fixture.manifest, thresholds=thresholds)
        codes = {item.code for item in report.episodes[0].diagnostics}
        self.assertIn("vector_dimension", codes)
        self.assertIn("nonfinite_value", codes)
        self.assertIn("out_of_range_value", codes)
        # Serialization must remain valid JSON even when the source included NaN/Infinity.
        parsed = json.loads(report.json_text())
        self.assertEqual(parsed["summary"]["diagnostic_counts"]["error"], report.summary["diagnostic_counts"]["error"])

    def test_layout_faults_cover_version_schema_camera_and_episode_indices(self) -> None:
        rows = [_good_row(0, 0)]
        bad_info = _info(2, 1, version="v2.0", cameras=CAMERAS[:2])
        bad_info["features"]["observation.state"]["shape"] = [19]
        bad_info["features"]["action"]["shape"] = [21]
        fixture = self._fixture(
            rows,
            info=bad_info,
            episodes=[{"episode_index": 0, "length": 1}, {"episode_index": 0, "length": 1}],
        )
        report = quality.inspect_dataset(fixture.root, manifest=fixture.manifest)
        codes = {item.code for item in report.diagnostics}
        self.assertTrue(
            {
                "version_mismatch",
                "state_schema_dimension",
                "action_schema_dimension",
                "camera_schema_count",
                "duplicate_episode_index",
                "missing_episode_index",
            }.issubset(codes)
        )

    def test_replay_stability_and_raw_input_immutability(self) -> None:
        fixture = self._fixture([_good_row(0, frame) for frame in range(5)])
        before = _tree_digest(fixture.root)
        first = quality.inspect_dataset(fixture.root, manifest=fixture.manifest)
        second = quality.inspect_dataset(fixture.root, manifest=fixture.manifest)
        self.assertEqual(first.json_text(), second.json_text())
        self.assertEqual(first.markdown_text(), second.markdown_text())
        self.assertEqual(first.html_text(), second.html_text())
        output = Path(self.temp.name) / "reports"
        paths = quality.write_reports(first, output, ["json", "markdown", "html"])
        self.assertEqual(set(paths), {"json", "markdown", "html"})
        self.assertEqual(before, _tree_digest(fixture.root))
        self.assertEqual(paths["json"].read_text(encoding="utf-8"), first.json_text())

    def test_fingerprint_changes_when_manifest_changes(self) -> None:
        fixture = self._fixture([_good_row(0, frame) for frame in range(2)])
        first = quality.inspect_dataset(fixture.root, manifest=fixture.manifest)
        rows = [_good_row(0, frame) for frame in range(2)]
        rows[1]["action"][0] = 9.5
        fixture.manifest.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
        second = quality.inspect_dataset(fixture.root, manifest=fixture.manifest)
        self.assertNotEqual(first.input_fingerprint, second.input_fingerprint)

    def test_cli_writes_all_formats_and_uses_semantic_exit_codes(self) -> None:
        fixture = self._fixture([_good_row(0, frame) for frame in range(3)])
        output = Path(self.temp.name) / "cli-report"
        completed = subprocess.run(
            [sys.executable, str(Path(quality.__file__)), str(fixture.root), "--manifest", str(fixture.manifest), "--output", str(output)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue((output / "report.json").is_file())
        self.assertTrue((output / "report.md").is_file())
        self.assertTrue((output / "report.html").is_file())
        receipt = json.loads(completed.stdout)
        self.assertTrue(receipt["complete"])

        rows = [_good_row(0, frame) for frame in range(3)]
        rows[1]["frame_index"] = 4
        fixture.manifest.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
        failed = subprocess.run(
            [sys.executable, str(Path(quality.__file__)), str(fixture.root), "--manifest", str(fixture.manifest), "--output", str(output)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(failed.returncode, 1, failed.stderr)

    def test_native_mode_reports_missing_files_without_mutating_dataset(self) -> None:
        fixture = self._fixture([_good_row(0, 0)], create_inventory=False)
        before = _tree_digest(fixture.root)
        report = quality.inspect_dataset(fixture.root)
        self.assertFalse(report.complete)
        self.assertIn("missing_data_file", {item.code for item in report.diagnostics})
        self.assertEqual(before, _tree_digest(fixture.root))

    def test_manifest_validation_fails_closed(self) -> None:
        fixture = self._fixture([_good_row(0, 0)])
        fixture.manifest.write_text('{"episode_index": 0}\n', encoding="utf-8")
        report = quality.inspect_dataset(fixture.root, manifest=fixture.manifest)
        self.assertFalse(report.complete)
        self.assertIn("invalid_manifest", {item.code for item in report.diagnostics})

    def test_manifest_mode_validates_inventory_and_empty_files(self) -> None:
        fixture = self._fixture([_good_row(0, 0)])
        video = next((fixture.root / "videos").rglob("*.mp4"))
        video.write_bytes(b"")
        report = quality.inspect_dataset(fixture.root, manifest=fixture.manifest)
        self.assertFalse(report.complete)
        self.assertIn("empty_video_file", {item.code for item in report.diagnostics})

    def test_report_writer_refuses_dataset_root_descendants(self) -> None:
        fixture = self._fixture([_good_row(0, 0)])
        report = quality.inspect_dataset(fixture.root, manifest=fixture.manifest)
        with self.assertRaisesRegex(ValueError, "outside the read-only dataset root"):
            quality.write_reports(report, fixture.root / "reports", ["json"])

    def test_threshold_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, "sync_offset_ms must be positive"):
            quality.Thresholds(sync_offset_ms=0)
        with self.assertRaisesRegex(ValueError, "minimum_modality_coverage must be in"):
            quality.Thresholds(minimum_modality_coverage=1.1)


if __name__ == "__main__":
    unittest.main()
