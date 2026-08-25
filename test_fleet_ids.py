#!/usr/bin/env python3
"""Fleet leftover is a measurement, not a seat."""

from __future__ import annotations

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from fleet_ids import classify, load_catalog, measure_from_parts, measure_paths


class TestFleetIds(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not measured", row["note"])

    def test_empty_catalog_is_not_landed(self):
        measured = measure_from_parts("{\"ids\": []}", [])
        self.assertEqual(measured["ids"], [])
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_missing_ids_are_not_landed(self):
        catalog = json.dumps(
            {
                "source_id": "jojo-revenue-fleet-20260825-01",
                "ids": [
                    "jojo-revenue-fleet-20260825-01",
                    "grok46-revenue-discovery-20260825-01",
                ],
            }
        )
        measured = measure_from_parts(catalog, ["unrelated.md"])
        self.assertEqual(measured["present_count"], 0)
        self.assertEqual(measured["missing_count"], 2)
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("isolated-lanes", verdict["note"])

    def test_partial_fleet_is_candidate(self):
        catalog = json.dumps(
            {
                "ids": [
                    "jojo-revenue-fleet-20260825-01",
                    "grok46-open-revenue-desk-20260825-01",
                ]
            }
        )
        measured = measure_from_parts(
            catalog, ["jojo-revenue-fleet-20260825-01.md"]
        )
        self.assertEqual(measured["present"], ["jojo-revenue-fleet-20260825-01"])
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "CANDIDATE")
        self.assertIn("grok46-open-revenue-desk-20260825-01", verdict["note"])

    def test_all_present_is_integrated(self):
        catalog = json.dumps(
            {
                "ids": [
                    "jojo-revenue-fleet-20260825-01",
                    "grok46-revenue-redteam-20260825-01",
                ]
            }
        )
        measured = measure_from_parts(
            catalog,
            [
                "jojo-revenue-fleet-20260825-01.md",
                "grok46-revenue-redteam-20260825-01.md",
            ],
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")

    def test_catalog_dedupes_and_skips_blank(self):
        catalog = load_catalog(
            json.dumps(
                {
                    "source_id": "jojo-revenue-fleet-20260825-01",
                    "ids": ["a", "", "a", "b"],
                    "hands_off": ["host/muhl_revenue.py"],
                }
            )
        )
        self.assertEqual(catalog["ids"], ["a", "b"])
        self.assertEqual(catalog["source_id"], "jojo-revenue-fleet-20260825-01")
        self.assertEqual(catalog["hands_off"], ["host/muhl_revenue.py"])

    def test_live_catalog_names_the_jojo_ids(self):
        path = os.path.join(ROOT, "ground", "FLEET_IDS.json")
        row = measure_paths(path, os.path.join(ROOT, "p"))
        self.assertTrue(row["measured"], row.get("error"))
        self.assertIn("jojo-revenue-fleet-20260825-01", row["ids"])
        self.assertIn("grok46-revenue-discovery-20260825-01", row["ids"])
        self.assertIn("grok46-open-revenue-desk-20260825-01", row["ids"])
        self.assertIn("grok46-revenue-redteam-20260825-01", row["ids"])
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(len(row["ids"]), 4)
        verdict = classify(row)
        self.assertIn(verdict["state"], ("NOT_LANDED", "CANDIDATE", "INTEGRATED"))


if __name__ == "__main__":
    unittest.main()
