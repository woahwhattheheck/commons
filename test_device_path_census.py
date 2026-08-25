#!/usr/bin/env python3
"""Device-path census leftover re-runs JOJO X/Y/Z and inspects one lawful canary."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from device_path_census import (
    CALIBRATION,
    CANARY_ID,
    JOJO_ID,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    inspect_canary,
    load_catalog,
    measure_from_rows,
    measure_root,
    parse_action,
)


class TestDevicePathCensus(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])
        self.assertIn("never 0", row["note"].lower())

    def test_failed_calibration_is_instrument_failure(self):
        verdict = classify(
            {
                "measured": True,
                "calibration_ok": False,
                "calibration_hits": [],
                "card_present": True,
                "catalog_present": True,
                "canary_present": True,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("instrument failure", verdict["note"])

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "canary_present": False,
                "misses": ["ground/DEVICE_PATH_CENSUS.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_pending_canary_is_not_lawful(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "canary_present": True,
                "canary_lawful": False,
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("Lawful", verdict["note"])

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "canary_present": True,
                "canary_lawful": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "self_hosted_dispatch": False,
                "host_inference": False,
                "parse_failures": 0,
                "calibration_ok": True,
                "reservation_count": 0,
                "batch_count": 0,
                "scope_device": 0,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_canary_fixture_is_open_device_and_not_pending(self):
        path = os.path.join(ROOT, "ground", "DEVICE_PATH_CANARY.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        rec = parse_action(text)
        self.assertEqual(rec["id"], CANARY_ID)
        self.assertEqual(rec["verb"], "OPEN")
        self.assertEqual(rec["target"], "DEVICE")
        self.assertTrue(rec["payload"].strip().startswith("https://"))
        live = os.path.isfile(os.path.join(ROOT, "p", CANARY_ID + ".md"))
        self.assertFalse(live)
        canary = inspect_canary(text, live)
        self.assertTrue(canary["lawful"])
        self.assertFalse(canary["pending"])
        self.assertFalse(canary["host_inference"])
        self.assertFalse(canary["self_hosted_dispatch"])

    def test_live_tree_measures_integrated(self):
        row = measure_root(ROOT)
        verdict = classify(row)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertGreater(row["tree_count"], 0)
        self.assertEqual(row["reservation_count"], 0)
        self.assertEqual(row["batch_count"], 0)
        self.assertGreaterEqual(row["result_count"], 48)
        self.assertEqual(row["scope_device"], 0)
        self.assertEqual(row["parse_failures"], 0)
        self.assertTrue(row["canary_lawful"])
        self.assertFalse(row["self_hosted_dispatch"])
        self.assertFalse(row["host_inference"])
        self.assertEqual(row.get("slack_ts") or SLACK_TS, SLACK_TS)
        self.assertEqual(row.get("jojo_id") or JOJO_ID, JOJO_ID)

    def test_catalog_names_jojo_id_and_hands_off_churn(self):
        catalog_path = os.path.join(ROOT, "ground", "DEVICE_PATH_CENSUS.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["jojo_id"], JOJO_ID)
        self.assertEqual(catalog["canary_id"], CANARY_ID)
        self.assertEqual(catalog["posting"], "OPEN")
        self.assertTrue(catalog["no_auth"])
        self.assertTrue(catalog["no_gate"])
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")

    def test_invalid_ref_is_unmeasured_never_zero(self):
        row = measure_root(ROOT, "this-ref-does-not-exist-zzzz")
        verdict = classify(row)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertFalse(row["tree_ok"])
        self.assertIsNone(row["tree_count"])
        self.assertIsNone(row["reservation_count"])
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("never []", verdict["note"].lower())
        self.assertIn("FINDER-FAILED", verdict["note"])

    def test_search_space_and_calibration_named(self):
        self.assertIn("ground/DEVICE_PATH_CENSUS.md", SEARCH_SPACE)
        self.assertIn("ground/DEVICE_PATH_CANARY.md", SEARCH_SPACE)
        self.assertIn("device_action_state.py", CALIBRATION)
        self.assertIn("ground/DEVICE_CHURN.md", CALIBRATION)
        self.assertIn("ground/EXECUTE.md", CALIBRATION)


if __name__ == "__main__":
    unittest.main()
