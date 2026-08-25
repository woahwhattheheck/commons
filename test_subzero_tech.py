#!/usr/bin/env python3
"""SUBZERO tech leftover measures; it does not evaluate organs."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from subzero_tech import (
    DISPATCH_ID,
    SLACK_TS,
    WHITE_BOX_OFFER,
    classify,
    classify_organ,
    load_catalog,
    measure_from_rows,
    measure_titan_presence,
    measure_tree,
    search_space,
)


class TestSubzeroTech(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])
        self.assertIn("Never 0", row["note"])

    def test_structural_only_is_not_runtime(self):
        self.assertEqual(
            classify_organ(
                {
                    "excerpt": True,
                    "fab": True,
                    "test": True,
                    "header_ok": True,
                    "evaluated": False,
                }
            ),
            "STRUCTURAL_ONLY",
        )
        self.assertEqual(classify_organ({"fab": True}), "UNKNOWN")

    def test_titan_presence_never_escalates(self):
        present = measure_titan_presence(
            ROOT,
            isfile=lambda path: path.endswith("titan.gguf"),
        )
        self.assertEqual(present["state"], "PRESENT")
        self.assertFalse(present["runtime_proof"])
        self.assertGreaterEqual(len(present["present_paths"]), 1)
        self.assertIn(r"C:\llm\models\titan.gguf", present["search_space"])
        self.assertEqual(
            classify_organ(
                {
                    "excerpt": True,
                    "fab": True,
                    "test": True,
                    "header_ok": True,
                    "titan_file_present": True,
                    "titan_remeasured": True,
                    "evaluated": True,
                }
            ),
            "STRUCTURAL_ONLY",
        )
        self.assertEqual(
            classify_organ(
                {
                    "excerpt": True,
                    "header_ok": True,
                    "customer_ready": True,
                }
            ),
            "STRUCTURAL_ONLY",
        )
        self.assertEqual(
            classify_organ(
                {
                    "excerpt": True,
                    "header_ok": True,
                    "evaluated": True,
                    "runtime_receipt": {
                        "kind": "SUBZERO_RUNTIME_RECEIPT",
                        "cross_process": True,
                        "pid": os.getpid() + 9,
                        "host": "other-process",
                    },
                }
            ),
            "CROSS_PROCESS/RUNTIME_MEASURED",
        )
        self.assertEqual(
            classify_organ(
                {
                    "excerpt": True,
                    "header_ok": True,
                    "customer_ready": True,
                    "buyer_receipt": {
                        "kind": "SUBZERO_BUYER_VALIDATION",
                        "status": "PASS",
                        "bound": True,
                        "buyer_id": "P01_catalog_receipt",
                    },
                }
            ),
            "CUSTOMER_READY",
        )

    def test_current_main_facts_are_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "plumb_count": 31,
                "excerpt_count": 31,
                "fab_count": 31,
                "test_count": 31,
                "structural_only": 31,
                "runtime_measured": 0,
                "customer_ready": 0,
                "unknown": 0,
                "titan_local": "FINDER-FAILED",
                "titan_write": "NOT_WRITTEN",
                "white_box_offer": WHITE_BOX_OFFER,
                "refuse_remint_white_box": True,
                "calibration_ok": True,
                "missing_cards": ["ground/SUBZERO_CHPR.md"],
                "organs": [
                    {
                        "name": "muhl_grbn",
                        "excerpt": True,
                        "fab": True,
                        "test": True,
                        "header_ok": True,
                    }
                ],
            }
        )
        self.assertEqual(measured["organ_classes"]["muhl_grbn"], "STRUCTURAL_ONLY")
        self.assertEqual(classify(measured)["state"], "INTEGRATED")
        self.assertIn("still not the file", classify(measured)["note"])

    def test_runtime_overclaim_blocks_land(self):
        measured = measure_from_rows(
            {
                "plumb_count": 31,
                "structural_only": 31,
                "runtime_measured": 1,
                "customer_ready": 0,
                "white_box_offer": WHITE_BOX_OFFER,
                "refuse_remint_white_box": True,
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")
        self.assertIn("overclaim", classify(measured)["note"])

    def test_customer_ready_overclaim_blocks_land(self):
        measured = measure_from_rows(
            {
                "plumb_count": 31,
                "structural_only": 31,
                "runtime_measured": 0,
                "customer_ready": 1,
                "white_box_offer": WHITE_BOX_OFFER,
                "refuse_remint_white_box": True,
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")
        self.assertIn("CUSTOMER_READY", classify(measured)["note"])

    def test_live_tree_matches_the_report(self):
        catalog_path = os.path.join(ROOT, "ground", "SUBZERO_TECH.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog_text = handle.read()
        catalog = load_catalog(catalog_text)
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["source_id"], DISPATCH_ID)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertTrue(catalog["refuse_remint_white_box"])
        self.assertEqual(len(catalog["organs"]), 31)
        row = measure_tree(ROOT, catalog_text)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(row["plumb_count"], 31)
        self.assertEqual(row["excerpt_count"], 31)
        self.assertEqual(row["fab_count"], 31)
        self.assertEqual(row["test_count"], 31)
        self.assertGreaterEqual(row["structural_only"], 29)
        self.assertEqual(row["runtime_measured"], 0)
        self.assertEqual(row["customer_ready"], 0)
        self.assertIn(row["titan_local"], ("FINDER-FAILED", "PRESENT"))
        self.assertFalse(row["titan_presence_is_runtime_proof"])
        if row["titan_local"] == "PRESENT":
            self.assertTrue(row["titan_presence_paths"])
        self.assertEqual(row["titan_write"], "NOT_WRITTEN")
        self.assertEqual(row["white_box_offer"], WHITE_BOX_OFFER)
        self.assertIn("ground/SUBZERO_CHPR.md", row["missing_cards"])
        self.assertIn("ground/SUBZERO_CHLS.md", row["missing_cards"])
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        names = [item["name"] for item in row["organs"]]
        self.assertEqual(names[6], "muhl_grbn")
        grbn = row["organs"][6]
        self.assertEqual(grbn["class"], "STRUCTURAL_ONLY")
        self.assertEqual(grbn["measured_n_gate"], 8704)
        self.assertTrue(grbn["header_ok"])
        self.assertEqual(len(row["live_twelve"]), 12)
        self.assertFalse(row["live_twelve"][0]["excerpt"])
        self.assertIn(os.path.join("excerpts", "20260823"), search_space())


if __name__ == "__main__":
    unittest.main()
