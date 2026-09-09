#!/usr/bin/env python3
"""A11 leftover: named laptop companion walk. Never silent 0."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from claude_laptop_finder import (
    CALIBRATION,
    CORNER_NAME,
    DO_NOT_REMINT,
    DO_NOT_REWRITE,
    DO_NOT_WRITE,
    LAPTOP_RELATIVES,
    LAPTOP_ROOTS,
    PEER_CHECK,
    SEARCH_SPACE,
    classify,
    companion_row,
    measure_from_rows,
    measure_root,
    root_row,
    self_test,
)


def _complete(**overrides):
    facts = {
        "calibration_ok": True,
        "calibration_hits": list(CALIBRATION),
        "no_auth": True,
        "no_gate": True,
        "posting": "OPEN",
        "roots": [{"path": path, "state": "FINDER-FAILED"} for path in LAPTOP_ROOTS],
        "companions": [
            {"path": os.path.join(path, relative), "state": "FINDER-FAILED"}
            for path in LAPTOP_ROOTS
            for relative in LAPTOP_RELATIVES
        ],
        "wrote_corner": False,
        "treated_miss_as_clear": False,
    }
    facts.update(overrides)
    return measure_from_rows(facts)


class TestClaudeLaptopFinder(unittest.TestCase):
    def test_self_test_ok(self):
        self.assertEqual(self_test(), "ok")

    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertEqual(row["z"], "FINDER-FAILED")
        self.assertIn("Never 0", row["note"])
        self.assertNotEqual(row.get("count"), 0)

    def test_failed_calibration_is_instrument_failure(self):
        row = classify(_complete(calibration_ok=False, calibration_hits=[]))
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertEqual(row["z"], "FINDER-FAILED")
        self.assertIn("instrument failure", row["note"])

    def test_closed_door_is_discarded(self):
        row = classify(_complete(no_auth=False))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("closed the door", row["note"])

    def test_writing_corner_is_the_failure_mode(self):
        row = classify(_complete(wrote_corner=True))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertEqual(row["z"], "HIT")
        self.assertIn("failure", row["note"].lower())

    def test_cloud_miss_treated_as_clear_is_refused(self):
        row = classify(_complete(treated_miss_as_clear=True))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("CLEAR", row["note"])

    def test_companion_absent_is_finder_failed(self):
        row = companion_row("/definitely-not-lucys", CORNER_NAME)
        self.assertEqual(row["state"], "FINDER-FAILED")
        self.assertIsNone(row["count"])
        self.assertFalse(row["present"])
        self.assertFalse(row["permission"])
        self.assertIn("Never 0", row["note"])

    def test_companion_corner_present_is_hit_not_graduation(self):
        with tempfile.TemporaryDirectory(prefix="laptop-hit-") as tmp:
            with open(os.path.join(tmp, CORNER_NAME), "w", encoding="utf-8") as handle:
                handle.write("architect close-the-case\n")
            row = companion_row(tmp, CORNER_NAME)
        self.assertEqual(row["state"], "HIT")
        self.assertEqual(row["count"], 1)
        self.assertTrue(row["present"])
        self.assertFalse(row["permission"])

    def test_non_corner_found_is_not_permission(self):
        with tempfile.TemporaryDirectory(prefix="laptop-found-") as tmp:
            dest = os.path.join(tmp, "Desktop", "MUHL_GO")
            os.makedirs(dest)
            with open(
                os.path.join(dest, "LIVE_INSTRUMENTS.md"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write("instruments\n")
            row = companion_row(tmp, os.path.join("Desktop", "MUHL_GO", "LIVE_INSTRUMENTS.md"))
        self.assertEqual(row["state"], "FOUND")
        self.assertFalse(row["permission"])
        self.assertIn("not --go", row["note"])

    def test_fixture_absent_is_integrated(self):
        with tempfile.TemporaryDirectory(prefix="laptop-live-") as tmp:
            os.makedirs(os.path.join(tmp, "ground"))
            os.makedirs(os.path.join(tmp, "host"))
            laptop = os.path.join(tmp, "not-lucys")
            os.makedirs(laptop)
            with open(os.path.join(tmp, "ground", "HEAD.md"), "w", encoding="utf-8") as handle:
                handle.write("HEAD truth\n")
            with open(
                os.path.join(tmp, "ground", "CLAUDE_PEER_CHECK.md"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write("A11 HIT-SR01 laptop C:\\Users\\lucys FINDER-FAILED\n")
            with open(
                os.path.join(tmp, "host", "claude_laptop_finder.py"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write("# leftover\n")
            row = measure_root(tmp, laptop_roots=[laptop])
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertTrue(row["calibration_ok"])
        self.assertIs(row["permission"], False)
        self.assertEqual(row["posting"], "OPEN")
        self.assertEqual(row["roots"][0]["state"], "FOUND")
        self.assertEqual(
            [item["state"] for item in row["companions"]],
            ["FINDER-FAILED"] * len(LAPTOP_RELATIVES),
        )
        self.assertIn(CORNER_NAME, DO_NOT_WRITE)

    def test_fixture_corner_is_hit(self):
        with tempfile.TemporaryDirectory(prefix="laptop-corner-") as tmp:
            os.makedirs(os.path.join(tmp, "ground"))
            laptop = os.path.join(tmp, "lucys")
            os.makedirs(laptop)
            with open(os.path.join(tmp, "ground", "HEAD.md"), "w", encoding="utf-8") as handle:
                handle.write("HEAD truth\n")
            with open(
                os.path.join(tmp, "ground", "CLAUDE_PEER_CHECK.md"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write("A11 HIT-SR01\n")
            with open(os.path.join(laptop, CORNER_NAME), "w", encoding="utf-8") as handle:
                handle.write("do not graduate\n")
            row = measure_root(tmp, laptop_roots=[laptop])
        self.assertEqual(row["state"], "HIT")
        self.assertEqual(row["z"]["corner"], "HIT")
        self.assertFalse(row["permission"])

    def test_live_tree_measures_finder_failed_without_writing(self):
        row = measure_root(ROOT)
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertEqual(row["posting"], "OPEN")
        self.assertTrue(row["no_auth"])
        self.assertTrue(row["no_gate"])
        self.assertIs(row["permission"], False)
        self.assertEqual(len(LAPTOP_ROOTS), 3)
        self.assertEqual(len(LAPTOP_RELATIVES), 8)
        self.assertEqual(
            [item["state"] for item in row["roots"]],
            ["FINDER-FAILED"] * 3,
        )
        self.assertEqual(
            [item["state"] for item in row["companions"]],
            ["FINDER-FAILED"] * (3 * 8),
        )
        self.assertTrue(all(item["count"] is None for item in row["companions"]))
        self.assertFalse(os.path.isfile(os.path.join(ROOT, CORNER_NAME)))
        self.assertIn("cursor-claude-peer-check-seated-builder-slack-20260902-01", DO_NOT_REMINT)
        self.assertIn(
            "cursor-claude-peer-check-seated-builder-slack-readback-20260902-01",
            DO_NOT_REMINT,
        )
        self.assertEqual(len(DO_NOT_REWRITE), 6)
        self.assertEqual(DO_NOT_WRITE, (CORNER_NAME,))
        self.assertIn(PEER_CHECK, SEARCH_SPACE)
        live_root = root_row(r"C:\Users\lucys")
        self.assertEqual(live_root["state"], "FINDER-FAILED")
        self.assertIsNone(live_root["count"])


if __name__ == "__main__":
    unittest.main()
