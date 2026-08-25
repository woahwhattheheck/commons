#!/usr/bin/env python3
"""Host-zero leftover is a measurement, not a remint."""

from __future__ import annotations

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from host_zero import classify, load_catalog, measure_from_rows, measure_paths


class TestHostZero(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not measured", row["note"])

    def test_leftover_aspiration_is_not_landed(self):
        measured = measure_from_rows(
            [
                {
                    "path": "resources.html",
                    "present": True,
                    "text": (
                        "it is what finally makes achievable the host does "
                        "zero instead of just in principle"
                    ),
                }
            ]
        )
        self.assertEqual(measured["leftover_paths"], ["resources.html"])
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("aspirational", verdict["note"])

    def test_laptop_do_zero_is_leftover(self):
        measured = measure_from_rows(
            [
                {
                    "path": "resources.html",
                    "present": True,
                    "text": "these pipes make the 8 GB laptop do zero",
                }
            ]
        )
        self.assertEqual(measured["leftover_paths"], ["resources.html"])
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_missing_door_is_not_landed(self):
        measured = measure_from_rows(
            [{"path": "resources.html", "present": False, "text": ""}]
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")
        self.assertIn("missing", classify(measured)["note"])

    def test_partial_achieved_is_candidate(self):
        measured = measure_from_rows(
            [
                {
                    "path": "resources.html",
                    "present": True,
                    "text": "measured host-zero operation was already achieved",
                },
                {
                    "path": "ntfy_relays.py",
                    "present": True,
                    "text": "offloads a peer reconciliation chore only",
                },
            ]
        )
        self.assertEqual(measured["achieved_count"], 1)
        self.assertEqual(classify(measured)["state"], "CANDIDATE")

    def test_all_achieved_no_leftover_is_integrated(self):
        measured = measure_from_rows(
            [
                {
                    "path": "resources.html",
                    "present": True,
                    "text": "measured host-zero operation was already achieved",
                },
                {
                    "path": "ground/BRYCE_EXECUTION_PROFILE.md",
                    "present": True,
                    "text": "Host-zero/decoupling is already achieved and measured",
                },
            ]
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")

    def test_chores_away_from_laptop_is_not_leftover(self):
        measured = measure_from_rows(
            [
                {
                    "path": "resources.html",
                    "present": True,
                    "text": (
                        "measured host-zero operation was already achieved. "
                        "These pipes carry chores away from the 8 GB laptop."
                    ),
                }
            ]
        )
        self.assertEqual(measured["leftover_paths"], [])
        self.assertEqual(classify(measured)["state"], "INTEGRATED")

    def test_live_catalog_names_the_opus_intro(self):
        catalog_path = os.path.join(ROOT, "ground", "HOST_ZERO.json")
        row = measure_paths(ROOT, catalog_path)
        self.assertTrue(row["measured"], row.get("error"))
        self.assertGreaterEqual(row["door_count"], 4)
        self.assertEqual(row["missing"], [])
        self.assertEqual(row["leftover_paths"], [])
        self.assertEqual(row["achieved_count"], row["door_count"])
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(row["slack_ts"], "1787636497.135519")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], "1787636497.135519")
        self.assertEqual(catalog["plumb_ts"], "1787473167.355659")
        self.assertIn("resources.html", catalog["doors"])
        self.assertEqual(classify(row)["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
