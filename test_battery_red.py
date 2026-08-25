#!/usr/bin/env python3
"""Battery-red leftover: a Slack no-global-green claim is not a land."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from battery_red import (
    REQUIRED_PHRASES,
    RUN_ID,
    SLACK_TS,
    TITANX_LEVELS,
    classify,
    measure_from_rows,
    measure_root,
)


class TestBatteryRed(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_miss_is_finder_failed_never_zero(self):
        row = classify(
            measure_from_rows(
                {
                    "card_present": False,
                    "catalog_present": False,
                    "misses": ["ground/BATTERY_RED.md"],
                    "calibration_ok": True,
                }
            )
        )
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("FINDER-FAILED", row["note"])
        self.assertRegex(row["note"], r"(?i)never 0")

    def test_padding_titanx_is_not_landed(self):
        row = classify(
            measure_from_rows(
                {
                    "card_present": True,
                    "catalog_present": True,
                    "pads_titanx": True,
                    "calibration_ok": True,
                }
            )
        )
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("pad", row["note"].lower())

    def test_complete_row_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "titanx_kind": True,
                "forge_levels": TITANX_LEVELS["muhl_titanx_forge.mno"],
                "mirror_levels": TITANX_LEVELS["muhl_titanx_mirror.mno"],
                "commons_levels": TITANX_LEVELS["muhl_titanx_commons.mno"],
                "todo_headings": 36,
                "todo_fallback_exact": True,
                "stranded_found": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "INTEGRATED")

    def test_live_tree_has_the_leftover(self):
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["titanx_kind"])
        self.assertEqual(row["forge_levels"], 182)
        self.assertEqual(row["mirror_levels"], 240)
        self.assertTrue(row["todo_fallback_exact"])
        self.assertGreaterEqual(row["todo_headings"], 22)
        self.assertTrue(row["stranded_found"])
        self.assertFalse(row["global_green_claim"])
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(SLACK_TS, "1787643497.122079")
        self.assertEqual(RUN_ID, "32822236088")
        self.assertEqual(classify(row)["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
