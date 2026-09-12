# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

import paired


class PairedTest(unittest.TestCase):
    def test_score_triplet_binds_tested_seat(self):
        game = {"status": "complete", "steps": 719, "scores": [100, 75]}
        self.assertEqual(
            paired.score_triplet(game, 0),
            {"own": 100.0, "rival": 75.0, "margin": 25.0},
        )
        self.assertEqual(
            paired.score_triplet(game, 1),
            {"own": 75.0, "rival": 100.0, "margin": -25.0},
        )

    def test_score_triplet_rejects_incomplete_or_bool(self):
        self.assertIsNone(paired.score_triplet(
            {"status": "complete", "steps": 718, "scores": [1, 2]}, 0
        ))
        self.assertIsNone(paired.score_triplet(
            {"status": "complete", "steps": 719, "scores": [True, 2]}, 0
        ))

    def test_summarize_keeps_own_rival_margin_and_interaction(self):
        def cell(opponent, values):
            control = {"own": 100.0, "rival": 90.0, "margin": 10.0}
            metrics = {"control": control, "v31_reference": control, **values}
            return {
                "opponent": opponent,
                "metrics": metrics,
                "deltas_vs_control": {
                    arm: paired._delta(metrics[arm], control)
                    for arm in paired.RUN_ARMS if arm != "control"
                },
            }

        rows = [cell("apex_v7", {
            "min_v31": {"own": 105.0, "rival": 90.0, "margin": 15.0},
            "no_reorder": {"own": 102.0, "rival": 89.0, "margin": 13.0},
            "funding_pair_v31": {"own": 110.0, "rival": 88.0, "margin": 22.0},
        })]
        summary = paired.summarize(rows)
        self.assertEqual(summary["complete_cells"], 1)
        self.assertEqual(
            summary["arms_vs_v4_control"]["min_v31"]["mean_own_delta"], 5.0
        )
        self.assertEqual(summary["interaction"]["mean_margin_delta"], 4.0)

    def test_parse_csv_requires_distinct_values(self):
        self.assertEqual(paired.parse_csv_ints("1,2"), [1, 2])
        with self.assertRaisesRegex(ValueError, "distinct"):
            paired.parse_csv_ints("1,1")

    def test_capture_archive_single_read_and_hash(self):
        payload = b"archive"
        expected = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "archive.tar.gz"
            path.write_bytes(payload)
            captured = paired.capture_archive(path, expected, "fixture")
            path.write_bytes(b"poison")
            self.assertEqual(captured, payload)

    def test_capture_archive_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "archive.tar.gz"
            target.write_bytes(b"x")
            link = root / "link.tar.gz"
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "ordinary file"):
                paired.capture_archive(
                    link, hashlib.sha256(b"x").hexdigest(), "fixture"
                )

    def test_capture_git_blob(self):
        raw = b"print('ok')\n"
        expected = paired.git_blob_bytes(raw)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "helper.py"
            path.write_bytes(raw)
            self.assertEqual(paired.capture_git_blob(path, expected), raw)


if __name__ == "__main__":
    unittest.main()
