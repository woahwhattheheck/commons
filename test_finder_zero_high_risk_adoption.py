#!/usr/bin/env python3
"""BD084: one high-risk finder cannot emit a bare 0.

Wraps host/taking_trace.py (taking_listing_zero) with the existing
host/finder_zero.py instrument. Does not remint the instrument.
Existing test_finder_zero.py stays.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from finder_zero import FINDER_UNVERIFIED
from taking_trace import (
    CALIBRATION_ID,
    classify,
    list_posts_dir,
    measure_from_parts,
    measure_paths,
    taking_search_space,
)


CATALOG = json.dumps(
    {
        "source_id": "demon-rolling-utilization-20260825-01",
        "commons_ids": [
            "grok46-revenue-discovery-20260825-01",
            "grok46-open-revenue-desk-20260825-01",
        ],
    }
)


class TestFinderZeroHighRiskAdoption(unittest.TestCase):
    def test_chosen_finder_is_taking_trace(self):
        source = os.path.join(ROOT, "host", "taking_trace.py")
        with open(source, encoding="utf-8") as handle:
            body = handle.read()
        self.assertIn("from finder_zero import", body)
        self.assertIn("search_space", body)
        self.assertIn("calibrate", body)
        self.assertIn("report_find", body)
        self.assertIn("collision_clearance", body)
        self.assertIn(CALIBRATION_ID, body)
        self.assertIn("def list_posts_dir", body)
        self.assertNotIn("except OSError:\n            listing = []", body)

    def test_prints_exact_search_space(self):
        space = taking_search_space(
            ["grok46-revenue-discovery-20260825-01"],
            posts_dir="p",
        )
        self.assertTrue(space["complete"])
        self.assertIn("taking-trace commons_ids", space["query"])
        self.assertEqual(space["path"], "p")
        self.assertEqual(space["pattern"], "p/{id}.md")
        incomplete = taking_search_space([], posts_dir="")
        # empty catalog still names a query; path defaults to p
        self.assertTrue(incomplete["complete"])
        self.assertIn("(empty catalog)", incomplete["query"])

    def test_same_run_known_present_calibration(self):
        miss = measure_from_parts(CATALOG, ["unrelated.md"])
        self.assertFalse(miss["calibrated"])
        self.assertEqual(miss["calibration_state"], FINDER_UNVERIFIED)
        self.assertEqual(miss["known_present"], CALIBRATION_ID)
        self.assertIsNone(miss["find_count"])
        self.assertEqual(classify(miss)["state"], FINDER_UNVERIFIED)
        self.assertNotIn("0/", classify(miss)["note"])

        ok = measure_from_parts(CATALOG, ["unrelated.md", CALIBRATION_ID + ".md"])
        self.assertTrue(ok["calibrated"])
        self.assertEqual(ok["known_present"], CALIBRATION_ID)
        self.assertEqual(ok["find_state"], FINDER_UNVERIFIED)
        self.assertIsNone(ok["find_count"])

    def test_listing_failure_is_unverified_never_zero(self):
        listed = list_posts_dir(os.path.join(ROOT, "no-such-p-dir-adoption"))
        self.assertFalse(listed["listing_ok"])
        self.assertIsNone(listed["listing"])
        self.assertIn(FINDER_UNVERIFIED, listed["error"])

        with tempfile.NamedTemporaryFile(prefix="taking-not-a-dir-") as handle:
            failed = measure_paths(
                os.path.join(ROOT, "ground", "TAKING_TRACE.json"),
                handle.name,
            )
        self.assertTrue(failed["measured"])
        self.assertFalse(failed["listing_ok"])
        self.assertIsNone(failed["find_count"])
        self.assertFalse(failed["calibrated"])
        verdict = classify(failed)
        self.assertEqual(verdict["state"], FINDER_UNVERIFIED)
        self.assertNotIn("0/", verdict["note"])
        self.assertNotEqual(verdict["note"].strip(), "0")
        self.assertIn(failed["search_space"]["query"], verdict["note"])
        self.assertIn(failed["search_space"]["pattern"], verdict["note"])

    def test_miss_branch_cannot_emit_bare_zero(self):
        row = measure_from_parts(
            CATALOG,
            ["unrelated.md", CALIBRATION_ID + ".md"],
        )
        self.assertIsNone(row["find_count"])
        self.assertNotEqual(row["find_count"], 0)
        verdict = classify(row)
        dumped = json.dumps(row) + verdict["note"]
        self.assertNotRegex(dumped, r"(?m)^0$")
        self.assertNotIn("0/", verdict["note"])
        self.assertIn(FINDER_UNVERIFIED, verdict["note"])
        self.assertIn(row["search_space"]["query"], verdict["note"])

    def test_search_only_zero_is_not_clearance(self):
        unpaired = measure_from_parts(
            CATALOG,
            ["unrelated.md", CALIBRATION_ID + ".md"],
            pair_hits=[],
        )
        self.assertFalse(unpaired["clearance"])
        self.assertEqual(unpaired["collision_state"], FINDER_UNVERIFIED)
        paired = measure_from_parts(
            CATALOG,
            ["unrelated.md", CALIBRATION_ID + ".md"],
            pair_hits=["grok46-revenue-discovery-20260825-01"],
        )
        self.assertFalse(paired["clearance"])
        self.assertEqual(paired["collision_state"], FINDER_UNVERIFIED)
        self.assertIn("Search-only zero is not clearance", paired["collision_note"])

    def test_live_tree_calibrates_known_present(self):
        row = measure_paths(
            os.path.join(ROOT, "ground", "TAKING_TRACE.json"),
            os.path.join(ROOT, "p"),
        )
        self.assertTrue(row["measured"], row.get("error"))
        self.assertTrue(row["listing_ok"])
        self.assertTrue(row["search_space"]["complete"])
        self.assertEqual(row["known_present"], CALIBRATION_ID)
        self.assertTrue(row["calibrated"], row.get("calibration_note"))
        self.assertNotEqual(row["find_count"], 0)
        verdict = classify(row)
        self.assertNotIn("0/", verdict["note"])
        self.assertNotEqual(verdict.get("count"), 0)


if __name__ == "__main__":
    unittest.main()
