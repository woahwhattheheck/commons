#!/usr/bin/env python3
"""Regression guards for source-observation clocks used by build_sync."""

import datetime as dt
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "reconcile"))

import build_sync  # noqa: E402


class TestObservationClockGuard(unittest.TestCase):
    def test_far_future_observation_is_unmeasured(self):
        now = dt.datetime(2026, 9, 11, 5, 0, tzinfo=dt.timezone.utc)
        posts = [{
            "observed_event": "slack:C0BRGMDQB6G:1789080000.000100:1",
        }]
        observation = {
            "sink": "slack:C0BRGMDQB6G",
            "latest_source_ts": "1789080600.000100",
            "observed_at": "2099-01-01T00:00:00Z",
            "observer": "TEST",
        }
        row = build_sync.slack_row(posts, None, observation, now)
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("future", row["detail"])

    def test_small_future_skew_is_tolerated(self):
        now = dt.datetime(2026, 9, 11, 5, 0, tzinfo=dt.timezone.utc)
        posts = [{
            "observed_event": "slack:C0BRGMDQB6G:1789080000.000100:1",
        }]
        observation = {
            "sink": "slack:C0BRGMDQB6G",
            "latest_source_ts": "1789080600.000100",
            "observed_at": "2026-09-11T05:04:00Z",
            "observer": "TEST",
        }
        row = build_sync.slack_row(posts, None, observation, now)
        self.assertIn(row["state"], {"SYNCED", "STALE"})
        self.assertNotEqual(row["state"], "UNMEASURED")

    def test_nonfinite_numeric_timestamps_degrade_to_unknown(self):
        for text in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(text=text):
                self.assertIsNone(build_sync._parse_ts(text))

    def test_out_of_range_numeric_timestamp_degrades_to_unknown(self):
        self.assertIsNone(build_sync._parse_ts("1e309"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
