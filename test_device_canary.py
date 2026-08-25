#!/usr/bin/env python3
"""Device-canary leftover measures a landed ACTION without a result."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from device_canary import (
    ACTION_PATH,
    CALIBRATION,
    CANARY_ID,
    PEER_ID,
    REQUIRED_PHRASES,
    RESULT_PATH,
    SEARCH_SPACE,
    SLACK_TS,
    action_is_device,
    classify,
    load_catalog,
    load_result,
    measure_from_rows,
    measure_root,
)


class TestDeviceCanary(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

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
        self.assertIn("never 0", verdict["note"].lower())

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "misses": ["ground/DEVICE_CANARY.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_missing_action_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "action_present": False,
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("jojo-device-path-canary-20260825-01", verdict["note"])

    def test_leftover_is_integrated_while_result_missing(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "action_present": True,
                "action_is_device": True,
                "result_present": False,
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("NOT_LANDED", verdict["note"])
        self.assertIn("still not the file", verdict["note"])

    def test_scope_device_result_is_named(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "action_present": True,
                "action_is_device": True,
                "result_present": True,
                "result_scope": "device",
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("scope=device result", verdict["note"])

    def test_live_tree_measures_integrated_without_result(self):
        row = measure_root(ROOT)
        verdict = classify(row)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertTrue(row["action_present"])
        self.assertTrue(row["action_is_device"])
        self.assertFalse(row["result_present"])
        self.assertEqual(row["canary_result_state"], "NOT_LANDED")
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertFalse(row["self_hosted_dispatch"])
        self.assertEqual(row.get("slack_ts") or SLACK_TS, SLACK_TS)
        self.assertEqual(row.get("canary_id") or CANARY_ID, CANARY_ID)
        self.assertEqual(row.get("peer_id") or PEER_ID, PEER_ID)

    def test_catalog_and_result_parsers(self):
        catalog_path = os.path.join(ROOT, "ground", "DEVICE_CANARY.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["canary_id"], CANARY_ID)
        self.assertEqual(catalog["peer_id"], PEER_ID)
        self.assertEqual(catalog["posting"], "OPEN")
        self.assertTrue(catalog["no_auth"])
        self.assertTrue(catalog["no_gate"])
        self.assertFalse(catalog["self_hosted_dispatch"])
        empty = load_result("")
        self.assertFalse(empty["present"])
        scoped = load_result('{"scope":"device","ok":true}')
        self.assertTrue(scoped["present"])
        self.assertEqual(scoped["scope"], "device")

    def test_action_headers_and_search_space(self):
        action = os.path.join(ROOT, ACTION_PATH)
        with open(action, encoding="utf-8") as handle:
            self.assertTrue(action_is_device(handle.read()))
        self.assertIn("ground/DEVICE_CANARY.md", SEARCH_SPACE)
        self.assertIn(ACTION_PATH, SEARCH_SPACE)
        self.assertIn("ground/EXECUTE.md", CALIBRATION)
        self.assertEqual(RESULT_PATH, "actions/results/jojo-device-path-canary-20260825-01.json")


if __name__ == "__main__":
    unittest.main()
