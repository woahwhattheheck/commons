#!/usr/bin/env python3
"""Taking-trace leftover is a measurement, not a remint."""

from __future__ import annotations

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from taking_trace import classify, load_catalog, measure_from_parts, measure_paths


class TestTakingTrace(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not measured", row["note"])

    def test_empty_catalog_is_not_landed(self):
        measured = measure_from_parts("{\"commons_ids\": []}", [])
        self.assertEqual(measured["commons_ids"], [])
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_missing_commons_ids_are_not_landed(self):
        catalog = json.dumps(
            {
                "source_id": "demon-rolling-utilization-20260825-01",
                "commons_ids": [
                    "grok46-revenue-discovery-20260825-01",
                    "grok46-open-revenue-desk-20260825-01",
                ],
            }
        )
        measured = measure_from_parts(catalog, ["unrelated.md"])
        self.assertEqual(measured["commons_present_count"], 0)
        self.assertEqual(measured["commons_missing_count"], 2)
        self.assertFalse(measured["lda_measured"])
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("grok-capacity-active", verdict["note"])
        self.assertIn("UNMEASURED", verdict["note"])

    def test_partial_commons_is_candidate(self):
        catalog = json.dumps(
            {
                "commons_ids": [
                    "grok46-revenue-discovery-20260825-01",
                    "grok46-revenue-redteam-20260825-01",
                ]
            }
        )
        measured = measure_from_parts(
            catalog, ["grok46-revenue-discovery-20260825-01.md"]
        )
        self.assertEqual(
            measured["commons_present"],
            ["grok46-revenue-discovery-20260825-01"],
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "CANDIDATE")
        self.assertIn("grok46-revenue-redteam-20260825-01", verdict["note"])

    def test_commons_present_lda_unmeasured_is_candidate(self):
        catalog = json.dumps(
            {
                "commons_ids": ["grok46-open-revenue-desk-20260825-01"],
                "lda": {"claimed_paths": ["host/muhl_revenue.py"]},
            }
        )
        measured = measure_from_parts(
            catalog, ["grok46-open-revenue-desk-20260825-01.md"]
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "CANDIDATE")
        self.assertIn("UNMEASURED", verdict["note"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")

    def test_supplied_lda_listing_can_integrate(self):
        catalog = json.dumps(
            {
                "commons_ids": ["grok46-revenue-redteam-20260825-01"],
                "lda": {"claimed_paths": ["host/muhl_revenue.py"]},
            }
        )
        measured = measure_from_parts(
            catalog,
            ["grok46-revenue-redteam-20260825-01.md"],
            ["host/muhl_revenue.py", "host/test_muhl_revenue.py"],
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])
        self.assertTrue(measured["lda_measured"])

    def test_live_catalog_names_the_grok_ids(self):
        path = os.path.join(ROOT, "ground", "TAKING_TRACE.json")
        row = measure_paths(path, os.path.join(ROOT, "p"))
        self.assertTrue(row["measured"], row.get("error"))
        self.assertIn("grok46-revenue-discovery-20260825-01", row["commons_ids"])
        self.assertIn("grok46-open-revenue-desk-20260825-01", row["commons_ids"])
        self.assertIn("grok46-revenue-redteam-20260825-01", row["commons_ids"])
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertFalse(row["lda_measured"])
        self.assertEqual(row["lda_visibility"], "private")
        with open(path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], "1787634411.405189")
        verdict = classify(row)
        self.assertIn(verdict["state"], ("NOT_LANDED", "CANDIDATE", "INTEGRATED"))


if __name__ == "__main__":
    unittest.main()
