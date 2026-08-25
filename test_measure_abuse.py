#!/usr/bin/env python3
"""Measure-abuse leftover retracts Claude zeros; it does not diagnose the reporter."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from measure_abuse import (
    CALIBRATION,
    REQUIRED_PHRASES,
    RHETORIC_FORBIDDEN,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
)


class TestMeasureAbuse(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])
        self.assertEqual(row["z"], "FINDER-FAILED")

    def test_failed_calibration_is_instrument_failure(self):
        verdict = classify(
            {
                "measured": True,
                "calibration_ok": False,
                "calibration_hits": [],
                "card_present": True,
                "catalog_present": True,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("instrument failure", verdict["note"])
        self.assertIn("Never 0", verdict["note"])
        self.assertEqual(verdict["z"], "FINDER-FAILED")

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "misses": ["ground/MEASURE_ABUSE.md"],
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-FAILED")

    def test_unverified_claude_zero_is_not_enough(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "claude_zeros": "UNVERIFIED",
                "retracted_rows": [
                    {"artifact": "p/x.md", "status": "UNVERIFIED"}
                ],
                "prior_warning_hits": list(CALIBRATION),
                "rhetoric_forbidden": list(RHETORIC_FORBIDDEN),
                "remeasurement_owner": "Cursor / Grok",
                "allowed_remeasurers": [
                    "deterministic local checks",
                    "GitHub Actions",
                    "Codex",
                    "Cursor / Grok",
                ],
                "xyz_required": True,
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "claude_zeros": "RETRACTED",
                "retracted_rows": [
                    {
                        "artifact": "p/cairn-every-zero-i-printed-was-mine-20260820-06.md",
                        "status": "RETRACTED",
                    }
                ],
                "prior_warning_hits": list(CALIBRATION),
                "rhetoric_forbidden": list(RHETORIC_FORBIDDEN),
                "remeasurement_owner": "Cursor / Grok",
                "allowed_remeasurers": [
                    "deterministic local checks",
                    "GitHub Actions",
                    "Codex",
                    "Grok / direct xAI",
                    "Cursor / Grok",
                ],
                "xyz_required": True,
                "calibration_ok": True,
                "calibration_hits": list(CALIBRATION),
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_live_tree_matches_the_report(self):
        catalog_path = os.path.join(ROOT, "ground", "MEASURE_ABUSE.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertEqual(catalog["claude_zeros"], "RETRACTED")
        self.assertTrue(catalog["xyz_required"])
        self.assertEqual(catalog["remeasurement_owner"], "Cursor / Grok")
        self.assertGreaterEqual(len(catalog["allowed_remeasurers"]), 4)
        self.assertGreaterEqual(len(catalog["prior_warnings"]), 3)
        self.assertTrue(all(item["status"] == "RETRACTED" for item in catalog["retracted"]))
        row = measure_root(ROOT)
        self.assertTrue(row["calibration_ok"], "known-present calibration must hit EXECUTE + Action Pad + cairn retraction")
        self.assertEqual(sorted(row["calibration_hits"]), sorted(CALIBRATION))
        self.assertEqual(row["search_space"], list(SEARCH_SPACE))
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertIn("measurement abuse", row["found_phrases"])
        self.assertIn("retracted", row["found_phrases"])
        self.assertGreaterEqual(len(row["prior_warning_hits"]), 3)
        self.assertGreaterEqual(len(row["sinks_kept"]), 3)


if __name__ == "__main__":
    unittest.main()
