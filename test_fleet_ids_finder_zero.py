#!/usr/bin/env python3
"""Finder-zero regression coverage for host/fleet_ids.py."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import fleet_ids


class TestFleetIdsFinderZero(unittest.TestCase):
    def _fixture(self, root: Path, ids=("alpha", "beta")) -> tuple[Path, Path]:
        catalog = root / "catalog.json"
        posts = root / "posts"
        posts.mkdir()
        catalog.write_text(
            json.dumps(
                {
                    "source_id": "jojo-revenue-fleet-20260825-01",
                    "slack_ts": "1787633743.561299",
                    "ids": list(ids),
                }
            ),
            encoding="utf-8",
        )
        return catalog, posts

    def _calibrate(self, posts: Path) -> None:
        (posts / (fleet_ids.CALIBRATION_POST_ID + ".md")).write_text(
            "known present\n", encoding="utf-8"
        )

    def test_listing_oserror_is_unverified_not_false_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            catalog, posts = self._fixture(Path(temp))
            self._calibrate(posts)
            with mock.patch.object(
                fleet_ids.os, "listdir", side_effect=OSError("synthetic listing failure")
            ):
                row = fleet_ids.measure_paths(str(catalog), str(posts))
        self.assertFalse(row["measured"])
        self.assertEqual(row["finder_state"], fleet_ids.FINDER_UNVERIFIED)
        self.assertEqual(fleet_ids.classify(row)["state"], fleet_ids.FINDER_UNVERIFIED)
        self.assertNotIn("present_count", row)
        self.assertNotIn("missing_count", row)
        self.assertIn("posts listing failed", row["error"])

    def test_cli_failure_is_exit_two_with_no_numeric_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            catalog, posts = self._fixture(Path(temp))
            self._calibrate(posts)
            output = io.StringIO()
            with mock.patch.object(
                fleet_ids.os, "listdir", side_effect=OSError("synthetic listing failure")
            ), contextlib.redirect_stdout(output):
                exit_code = fleet_ids.main(
                    ["--catalog", str(catalog), "--posts-dir", str(posts)]
                )
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["state"], fleet_ids.FINDER_UNVERIFIED)
        self.assertFalse(payload["measured"])
        self.assertNotIn("present_count", payload)
        self.assertNotIn("missing_count", payload)

    def test_missing_posts_directory_is_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            catalog, posts = self._fixture(Path(temp))
            os.rmdir(posts)
            row = fleet_ids.measure_paths(str(catalog), str(posts))
        self.assertFalse(row["measured"])
        self.assertEqual(fleet_ids.classify(row)["state"], fleet_ids.FINDER_UNVERIFIED)
        self.assertIn("posts directory missing", row["error"])

    def test_success_records_search_space_present_missing_and_calibration(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            catalog, posts = self._fixture(Path(temp))
            self._calibrate(posts)
            (posts / "alpha.md").write_text("present\n", encoding="utf-8")
            row = fleet_ids.measure_paths(str(catalog), str(posts))
        self.assertTrue(row["measured"], row.get("error"))
        self.assertEqual(row["finder_state"], "MEASURED")
        self.assertEqual(row["search_space"]["path"], str(posts.resolve()))
        self.assertEqual(row["search_space"]["pattern"], "{id}.md")
        self.assertEqual(row["observed"]["present"], ["alpha"])
        self.assertEqual(row["observed"]["missing"], ["beta"])
        self.assertEqual(row["calibration"]["state"], "CALIBRATED")
        self.assertEqual(fleet_ids.classify(row)["state"], "CANDIDATE")

    def test_calibrated_zero_remains_a_measured_not_landed_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            catalog, posts = self._fixture(Path(temp), ids=("alpha",))
            self._calibrate(posts)
            row = fleet_ids.measure_paths(str(catalog), str(posts))
        self.assertTrue(row["measured"], row.get("error"))
        self.assertEqual(row["present_count"], 0)
        self.assertEqual(row["missing"], ["alpha"])
        self.assertEqual(row["calibration"]["state"], "CALIBRATED")
        self.assertEqual(fleet_ids.classify(row)["state"], "NOT_LANDED")

    def test_calibration_miss_voids_absence_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            catalog, posts = self._fixture(Path(temp), ids=("alpha",))
            row = fleet_ids.measure_paths(str(catalog), str(posts))
        self.assertFalse(row["measured"])
        self.assertEqual(row["present_count"], 0)
        self.assertEqual(row["finder_state"], fleet_ids.FINDER_UNVERIFIED)
        self.assertFalse(row["calibration"]["known_present"])
        self.assertFalse(row["calibration"]["observed"])
        self.assertEqual(fleet_ids.classify(row)["state"], fleet_ids.FINDER_UNVERIFIED)
        self.assertIn("absence verdict is void", row["error"])

    def test_calibration_miss_does_not_void_complete_positive_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            catalog, posts = self._fixture(Path(temp), ids=("alpha",))
            (posts / "alpha.md").write_text("present\n", encoding="utf-8")
            row = fleet_ids.measure_paths(str(catalog), str(posts))
        self.assertTrue(row["measured"], row.get("error"))
        self.assertEqual(row["present"], ["alpha"])
        self.assertEqual(row["missing"], [])
        self.assertEqual(fleet_ids.classify(row)["state"], "INTEGRATED")

    def test_existing_self_test_stays_green(self) -> None:
        self.assertTrue(fleet_ids._self_test())


if __name__ == "__main__":
    unittest.main()
