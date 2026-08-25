#!/usr/bin/env python3
"""Device-queue-cap leftover: a Slack COLLISION_RESOLVED is not a remint."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from device_queue_cap import (
    JOJO_TAKING,
    QUEUE_MAX,
    QUEUE_SINGLE,
    REQUIRED_PHRASES,
    SLACK_TS,
    WORKFLOW,
    classify,
    measure_from_rows,
    measure_root,
    measure_workflow,
)


class TestDeviceQueueCap(unittest.TestCase):
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
                    "misses": ["ground/DEVICE_QUEUE_CAP.md"],
                    "calibration_ok": True,
                    "queue_single": True,
                    "cancel_false": True,
                }
            )
        )
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("FINDER-FAILED", row["note"])
        self.assertRegex(row["note"], r"(?i)never 0")

    def test_queue_max_regression_is_not_landed(self):
        measured = measure_workflow("concurrency:\n      queue: max\n      cancel-in-progress: false\n")
        self.assertTrue(measured["queue_max"])
        self.assertFalse(measured["queue_single"])
        row = classify(
            measure_from_rows(
                {
                    "card_present": True,
                    "catalog_present": True,
                    "queue_max": True,
                    "queue_single": False,
                    "cancel_false": True,
                    "calibration_ok": True,
                }
            )
        )
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("queue: max", row["note"])

    def test_backlog_cleared_claim_is_not_landed(self):
        row = classify(
            measure_from_rows(
                {
                    "card_present": True,
                    "catalog_present": True,
                    "queue_single": True,
                    "cancel_false": True,
                    "historical_backlog_cleared": True,
                    "calibration_ok": True,
                }
            )
        )
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("backlog", row["note"].lower())

    def test_complete_row_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "queue_single": True,
                "cancel_false": True,
                "test_pins_single": True,
                "test_refuses_max": True,
                "jojo_taking_absent": True,
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
        self.assertTrue(row["queue_single"])
        self.assertFalse(row["queue_max"])
        self.assertTrue(row["cancel_false"])
        self.assertTrue(row["test_pins_single"])
        self.assertTrue(row["test_refuses_max"])
        self.assertTrue(row["jojo_taking_absent"])
        self.assertFalse(row["historical_backlog_cleared"])
        self.assertFalse(row["cancel_historical_runs"])
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(SLACK_TS, "1787645425.769089")
        self.assertEqual(WORKFLOW, os.path.join(".github", "workflows", "commons-device-executor.yml"))
        self.assertEqual(JOJO_TAKING, os.path.join("p", "jojo-device-queue-collapse-20260825-01.md"))
        self.assertIn(QUEUE_SINGLE, _workflow())
        self.assertNotIn(QUEUE_MAX, _workflow())
        self.assertEqual(classify(row)["state"], "INTEGRATED")


def _workflow():
    path = os.path.join(ROOT, WORKFLOW)
    with open(path, encoding="utf-8") as handle:
        return handle.read()


if __name__ == "__main__":
    unittest.main()
