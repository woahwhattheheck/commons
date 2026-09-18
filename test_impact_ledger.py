#!/usr/bin/env python3
"""Impact-ledger leftover never prints a silent 0."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from impact_ledger import (
    CALIBRATION_PATH,
    FINDER_FAILED,
    REQUIRED_LANES,
    SLACK_TS,
    SOURCE_ID,
    calibrate,
    classify,
    consumer_complete,
    load_catalog,
    measure_from_rows,
    measure_tree,
    probe,
    quarantine_claude_zero,
    report_find,
    search_space,
)


class TestImpactLedger(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_search_space_must_be_named(self):
        incomplete = search_space(query="")
        self.assertFalse(incomplete["complete"])
        self.assertIn("query", incomplete["missing"])
        complete = search_space(
            query="P0 CONTAINMENT",
            path="host/impact_ledger.py",
            ref=SLACK_TS,
        )
        self.assertTrue(complete["complete"])

    def test_missed_known_present_voids_zeros(self):
        missed = calibrate([], ["ground/HEAD.md"])
        self.assertFalse(missed["calibrated"])
        self.assertEqual(missed["state"], FINDER_FAILED)
        ok = calibrate(["ground/HEAD.md"], ["ground/HEAD.md"])
        self.assertTrue(ok["calibrated"])

    def test_miss_branch_never_prints_zero(self):
        space = search_space(
            query="P0 CONTAINMENT",
            path="host/impact_ledger.py",
            ref=SLACK_TS,
        )
        silent = report_find([], space, True)
        self.assertEqual(silent["state"], FINDER_FAILED)
        self.assertIsNone(silent["count"])
        self.assertNotEqual(silent["count"], 0)
        found = report_find(["hit"], space, True)
        self.assertEqual(found["state"], "FOUND")
        self.assertEqual(found["count"], 1)

    def test_claude_zero_is_quarantined(self):
        row = quarantine_claude_zero(0, source="claude")
        self.assertEqual(row["state"], "QUARANTINED")
        self.assertIsNone(row["count"])
        bare = quarantine_claude_zero(0, source="codex")
        self.assertEqual(bare["state"], FINDER_FAILED)
        self.assertIsNone(bare["count"])

    def test_consumer_requires_xyz(self):
        incomplete = consumer_complete({"id": "x"})
        self.assertFalse(incomplete["complete"])
        complete = consumer_complete(
            {
                "id": "collision",
                "x": "path",
                "y": FINDER_FAILED,
                "z": FINDER_FAILED,
                "owner": "JOJO",
                "repair": "retract",
                "source_id": SOURCE_ID,
            }
        )
        self.assertTrue(complete["complete"])

    def test_probe_never_prints_zero(self):
        missing = probe(ROOT, "this-path-is-not-a-file-on-purpose.md")
        self.assertEqual(missing["state"], FINDER_FAILED)
        self.assertIsNone(missing["count"])
        present = probe(ROOT, CALIBRATION_PATH)
        self.assertEqual(present["state"], "FOUND")
        self.assertGreater(present["bytes"], 0)
        self.assertIsNone(present["count"])

    def test_rule_is_integrated_when_seven_consumers_carry_xyz(self):
        measured = measure_from_rows(
            {
                "query": "P0 CONTAINMENT",
                "path": "host/impact_ledger.py",
                "ref": SLACK_TS,
                "finder_hits": [FINDER_FAILED],
                "known_present": [FINDER_FAILED],
                "consumers": [
                    {
                        "id": name,
                        "lane": name,
                        "source_id": SOURCE_ID,
                        "x": "path",
                        "y": FINDER_FAILED,
                        "z": FINDER_FAILED,
                        "owner": "RIVET",
                        "repair": "remeasure",
                        "claude_zero": True,
                    }
                    for name in REQUIRED_LANES
                ],
            }
        )
        self.assertTrue(measured["calibrated"])
        self.assertEqual(measured["complete_consumers"], 7)
        self.assertFalse(measured["missing_lanes"])
        self.assertTrue(measured["never_print_zero"])
        measured["instrument"] = True
        measured["card"] = True
        measured["catalog_file"] = True
        self.assertEqual(classify(measured)["state"], "INTEGRATED")
        self.assertIn("still not the file", classify(measured)["note"])
        zeroed = dict(measured)
        zeroed["bare_zero"] = True
        self.assertEqual(classify(zeroed)["state"], "NOT_LANDED")

    def test_live_tree_names_seven_high_risk_lanes(self):
        catalog_path = os.path.join(ROOT, "ground", "IMPACT_LEDGER.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog_text = handle.read()
        catalog = load_catalog(catalog_text)
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["source_id"], SOURCE_ID)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertEqual(len(catalog["consumers"]), 7)
        row = measure_tree(ROOT, catalog_text)
        self.assertTrue(row["measured"])
        self.assertTrue(row["instrument"])
        self.assertTrue(row["card"])
        self.assertTrue(row["catalog_file"])
        self.assertTrue(row["calibrated"])
        self.assertGreaterEqual(row["complete_consumers"], 7)
        self.assertFalse(row["missing_lanes"])
        self.assertFalse(row["bare_zero"])
        self.assertEqual(row["titan_write"], "NOT_WRITTEN")
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        pr_row = next(
            item for item in row["consumer_rows"] if item["id"] == "pr-branch-absence"
        )
        self.assertEqual(pr_row["probe_state"], "FOUND")
        self.assertIsNone(pr_row.get("count"))
        self.assertIn("FOUND", pr_row["y"])


if __name__ == "__main__":
    unittest.main()
