#!/usr/bin/env python3
"""H-006 training-bridge leftover validates synthetic packets and never remints JOJO."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from muhl_train_bridge import (
    ALREADY_LANDED,
    CALIBRATION,
    EXPECTED_FIXTURES,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    SWARM_PIN,
    TAKING_ID,
    classify,
    load_catalog,
    load_json,
    measure_from_rows,
    measure_root,
    validate_packet,
)


class TestMuhlTrainBridge(unittest.TestCase):
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
                "door_present": True,
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
                "door_present": False,
                "misses": ["ground/MUHL_TRAIN_BRIDGE.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_empty_packet_is_unmeasured(self):
        self.assertEqual(validate_packet({})["state"], "UNMEASURED")
        self.assertEqual(validate_packet(None)["state"], "UNMEASURED")

    def test_talk_kind_is_carrier_only(self):
        verdict = validate_packet({"kind": "TAKING_BACKEND_SWARM"})
        self.assertEqual(verdict["state"], "CARRIER_ONLY")

    def test_host_inference_is_refused(self):
        path = os.path.join(ROOT, "ground", "muhl_train_bridge", "invalid-host-inference.json")
        with open(path, encoding="utf-8") as handle:
            data = load_json(handle.read())
        self.assertEqual(validate_packet(data, root=ROOT)["state"], "NOT_LANDED")

    def test_live_titan_is_refused(self):
        path = os.path.join(ROOT, "ground", "muhl_train_bridge", "invalid-live-titan.json")
        with open(path, encoding="utf-8") as handle:
            data = load_json(handle.read())
        self.assertEqual(validate_packet(data, root=ROOT)["state"], "NOT_LANDED")

    def test_missing_fields_are_refused(self):
        path = os.path.join(ROOT, "ground", "muhl_train_bridge", "invalid-missing-fields.json")
        with open(path, encoding="utf-8") as handle:
            data = load_json(handle.read())
        self.assertEqual(validate_packet(data, root=ROOT)["state"], "NOT_LANDED")

    def test_valid_synthetic_is_ok(self):
        path = os.path.join(ROOT, "ground", "muhl_train_bridge", "valid-synthetic.json")
        with open(path, encoding="utf-8") as handle:
            data = load_json(handle.read())
        verdict = validate_packet(data, root=ROOT)
        self.assertEqual(verdict["state"], "SYNTHETIC_OK")
        self.assertIn("still not the file", verdict["note"])

    def test_claiming_swarm_integrated_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "door_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "cells": [{"id": "SWARM", "state": "INTEGRATED"}],
                "names_h006_leftover": True,
                "names_h005_named": True,
                "names_h007_named": True,
                "claims_swarm_integrated": True,
                "pin_is_ancestor": True,
                "fixture_states": dict(EXPECTED_FIXTURES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "door_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "cells": [
                    {"id": "H-005", "state": "NAMED"},
                    {"id": "H-006", "state": "THIS_LEFTOVER"},
                    {"id": "H-007", "state": "NAMED"},
                ],
                "names_h006_leftover": True,
                "names_h005_named": True,
                "names_h007_named": True,
                "claims_swarm_integrated": False,
                "pin_is_ancestor": True,
                "fixture_states": dict(EXPECTED_FIXTURES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_live_tree_has_the_leftover(self):
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(row["landed_missing"], [])
        self.assertTrue(row["names_h006_leftover"])
        self.assertTrue(row["names_h005_named"])
        self.assertTrue(row["names_h007_named"])
        self.assertFalse(row["claims_swarm_integrated"])
        self.assertTrue(row["pin_is_ancestor"])
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(SLACK_TS, "1787647412.543649")
        self.assertEqual(TAKING_ID, "jojo-clean-grok-modelwork-swarm-20260825-01")
        self.assertEqual(SWARM_PIN, "6a934ed9d07c293296fead0f403fbbcb3afc15a9")
        self.assertEqual(len(CALIBRATION), 3)
        self.assertGreaterEqual(len(SEARCH_SPACE), 8)
        with open(os.path.join(ROOT, "ground", "MUHL_TRAIN_BRIDGE.json"), encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["pin_relation"], "ANCESTOR")
        self.assertEqual(catalog["taking_id"], TAKING_ID)
        self.assertEqual(classify(row)["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
