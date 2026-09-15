from pathlib import Path
import json
import shutil
import tempfile
import unittest

import cv2
import numpy as np
import pandas as pd

from wuhu_qc.core import analyze_episode, fit_reference, inspect_video, ReferenceProfile, score_findings
from wuhu_qc.lerobot_v21 import DatasetReference, REFERENCE_ROLE, fit_dataset_reference, scan_dataset


def good_df(n=60, fps=30.0, episode_index=0):
    t = np.arange(n) / fps
    state = np.stack([np.sin(t), np.cos(t), t, t * 0 + 1], axis=1)
    action = np.stack([np.sin(t + .02), np.cos(t + .02), t + .01, t * 0 + .5], axis=1)
    return pd.DataFrame({
        "timestamp": t,
        "frame_index": np.arange(n),
        "episode_index": np.full(n, episode_index, dtype=int),
        "task_index": np.zeros(n, dtype=int),
        "observation.state": list(state),
        "action": list(action),
    })


def write_video(path: Path, frames: list[np.ndarray], fps=30.0):
    h, w = frames[0].shape[:2]
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    assert writer.isOpened()
    for frame in frames:
        writer.write(frame)
    writer.release()


def write_dataset(root: Path, *, corrupt_episode: int | None = None, copy_episode_from: Path | None = None):
    (root / "meta").mkdir(parents=True)
    (root / "data" / "chunk-000").mkdir(parents=True)
    info = {
        "codebase_version": "v2.1",
        "fps": 30,
        "chunks_size": 1000,
        "total_episodes": 2,
        "data_path": "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet",
        "features": {
            "observation.state": {"dtype": "float32", "shape": [4]},
            "action": {"dtype": "float32", "shape": [4]},
        },
    }
    (root / "meta" / "info.json").write_text(json.dumps(info, sort_keys=True) + "\n", encoding="utf-8")
    (root / "meta" / "episodes.jsonl").write_text("".join(json.dumps({"episode_index": ep}) + "\n" for ep in range(2)), encoding="utf-8")
    for ep in range(2):
        target = root / "data" / "chunk-000" / f"episode_{ep:06d}.parquet"
        if copy_episode_from is not None and ep == 0:
            shutil.copy2(copy_episode_from, target)
            continue
        df = good_df(40 + ep, episode_index=ep)
        if corrupt_episode == ep:
            df = df.drop(columns=["action"])
        df.to_parquet(target, index=False)


class CoreTests(unittest.TestCase):
    def test_clean_episode_scores_high(self):
        r = analyze_episode(good_df(), 0, 30, expected_shapes={"observation.state": [4], "action": [4]}, numeric_keys=["observation.state", "action"])
        self.assertEqual(r.findings, [])
        self.assertEqual(r.quality_score, 100)
        self.assertEqual(r.value_score, 100)

    def test_frame_gap_and_timestamp_regression(self):
        d = good_df()
        d.loc[20:, "frame_index"] += 2
        d.loc[35, "timestamp"] = d.loc[34, "timestamp"] - .1
        r = analyze_episode(d, 0, 30, numeric_keys=[])
        codes = {f.code for f in r.findings}
        self.assertIn("FRAME_GAP", codes)
        self.assertIn("TIMESTAMP_REGRESSION", codes)
        self.assertLess(r.quality_score, 100)

    def test_nonfinite_state_is_high_severity(self):
        d = good_df()
        x = d.at[10, "observation.state"].copy()
        x[1] = np.nan
        d.at[10, "observation.state"] = x
        r = analyze_episode(d, 0, 30, expected_shapes={"observation.state": [4]}, numeric_keys=["observation.state"])
        hits = [f for f in r.findings if f.code == "NONFINITE_FEATURE"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].severity, "high")

    def test_shape_mismatch_fails_closed(self):
        d = good_df()
        d.at[3, "action"] = np.array([1, 2])
        r = analyze_episode(d, 0, 30, expected_shapes={"action": [4]}, numeric_keys=["action"])
        codes = {f.code for f in r.findings}
        self.assertTrue({"INCONSISTENT_VECTOR_SHAPE", "NON_NUMERIC_FEATURE"} & codes)

    def test_motion_spike_detected(self):
        d = good_df()
        x = d.at[30, "action"].copy()
        x[0] = 1e6
        d.at[30, "action"] = x
        r = analyze_episode(d, 0, 30, numeric_keys=["action"])
        self.assertIn("MOTION_SPIKE", {f.code for f in r.findings})

    def test_video_black_and_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "cam.mp4"
            frames = []
            for i in range(20):
                if i < 12:
                    frames.append(np.zeros((64, 96, 3), dtype=np.uint8))
                else:
                    image = np.zeros((64, 96, 3), dtype=np.uint8)
                    cv2.line(image, (0, i), (95, 63 - i), (255, 255, 255), 2)
                    frames.append(image)
            write_video(path, frames, 30)
            findings = inspect_video(path, 0, 60, 30, sample_limit=20)
            codes = {row.code for row in findings}
            self.assertIn("VIDEO_FRAME_COVERAGE_MISMATCH", codes)
            self.assertIn("BLACK_FRAME_RATE", codes)

    def test_frozen_video_detected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "frozen.mp4"
            image = np.full((64, 96, 3), 120, dtype=np.uint8)
            cv2.circle(image, (40, 30), 15, (255, 255, 255), -1)
            write_video(path, [image.copy() for _ in range(30)], 30)
            codes = {row.code for row in inspect_video(path, 0, 30, 30, sample_limit=30)}
            self.assertIn("FROZEN_VIDEO_RATE", codes)

    def test_scoring_is_order_invariant(self):
        d = good_df()
        d.loc[10:, "frame_index"] += 1
        findings = analyze_episode(d, 0, 30).findings
        self.assertEqual(score_findings(findings), score_findings(list(reversed(findings))))

    def test_clean_reference_flags_distribution_shift(self):
        refs = [good_df(80) for _ in range(3)]
        profile = fit_reference(refs, ["observation.state", "action"])
        shifted = good_df(80)
        shifted["observation.state"] = [np.asarray(value) + np.array([20., 0, 0, 0]) for value in shifted["observation.state"]]
        r = analyze_episode(shifted, 0, 30, numeric_keys=["observation.state", "action"], reference=profile)
        self.assertIn("REFERENCE_RANGE_VIOLATION", {f.code for f in r.findings})

    def test_reference_roundtrip_is_deterministic(self):
        profile = fit_reference([good_df(40), good_df(55)], ["action"])
        again = ReferenceProfile.from_dict(profile.as_dict())
        self.assertEqual(profile, again)


class ProvenanceBoundaryTests(unittest.TestCase):
    def test_profile_is_role_locked_and_roundtrips(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "clean"
            write_dataset(root)
            reference = fit_dataset_reference(root)
            self.assertEqual(reference.source_role, REFERENCE_ROLE)
            self.assertEqual(reference, DatasetReference.from_dict(reference.as_dict()))
            with self.assertRaisesRegex(ValueError, "source_role"):
                fit_dataset_reference(root, source_role="ORGANIZER_TEST")

    def test_profile_rejects_incomplete_requested_clean_episode(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "clean"
            write_dataset(root, corrupt_episode=1)
            with self.assertRaisesRegex(ValueError, "missing required modeled feature action"):
                fit_dataset_reference(root)

    def test_same_dataset_disjoint_subset_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "dataset"
            write_dataset(root)
            reference = fit_dataset_reference(root, episodes=[0])
            with self.assertRaisesRegex(ValueError, "dataset identity overlap"):
                scan_dataset(root, Path(td) / "out", episodes=[1], reference=reference)

    def test_copied_reference_bytes_are_rejected_and_manifest_tamper_fails(self):
        with tempfile.TemporaryDirectory() as td:
            clean = Path(td) / "clean"
            test = Path(td) / "test"
            write_dataset(clean)
            copied = clean / "data" / "chunk-000" / "episode_000000.parquet"
            write_dataset(test, copy_episode_from=copied)
            reference = fit_dataset_reference(clean, episodes=[0])
            with self.assertRaisesRegex(ValueError, "reference/test source overlap"):
                scan_dataset(test, Path(td) / "out", episodes=[0], reference=reference)

            payload = reference.as_dict()
            payload["source_files"][0]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "source manifest digest mismatch"):
                DatasetReference.from_dict(payload)


if __name__ == "__main__":
    unittest.main()
