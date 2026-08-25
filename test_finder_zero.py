#!/usr/bin/env python3
"""Finder-zero leftover never prints a silent 0."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from finder_zero import (
    FINDER_UNVERIFIED,
    SLACK_TS,
    SOURCE_ID,
    calibrate,
    classify,
    collision_clearance,
    load_catalog,
    measure_from_rows,
    measure_tree,
    report_find,
    scan_bare_find,
    search_space,
    slack_query_defects,
)


class TestFinderZero(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_search_space_must_be_named(self):
        incomplete = search_space(query="")
        self.assertFalse(incomplete["complete"])
        self.assertIn("query", incomplete["missing"])
        complete = search_space(
            query="Alt-Text",
            channel="#commons",
            pattern="Alt-Text",
        )
        self.assertTrue(complete["complete"])

    def test_slack_or_and_after_are_named_defects(self):
        defects = slack_query_defects(
            "in:#commons after:1787630000 visual CI OR render_check extra"
        )
        ids = [item["id"] for item in defects]
        self.assertIn("or_literal", ids)
        self.assertIn("multi_term_and", ids)
        self.assertIn("after_filter", ids)

    def test_missed_known_present_voids_zeros(self):
        missed = calibrate([], ["known-present"])
        self.assertFalse(missed["calibrated"])
        self.assertEqual(missed["state"], FINDER_UNVERIFIED)
        ok = calibrate(["known-present"], ["known-present"])
        self.assertTrue(ok["calibrated"])

    def test_miss_branch_never_prints_zero(self):
        space = search_space(
            query="Alt-Text",
            channel="#commons",
            pattern="Alt-Text",
        )
        silent = report_find([], space, True)
        self.assertEqual(silent["state"], FINDER_UNVERIFIED)
        self.assertIsNone(silent["count"])
        self.assertNotEqual(silent["count"], 0)
        found = report_find(["hit"], space, True)
        self.assertEqual(found["state"], "FOUND")
        self.assertEqual(found["count"], 1)

    def test_search_only_is_not_clearance(self):
        process = collision_clearance(
            [],
            process_hits=["jojo-visual-ci-20260825-01"],
        )
        self.assertEqual(process["state"], FINDER_UNVERIFIED)
        self.assertFalse(process["clearance"])
        unpaired = collision_clearance([])
        self.assertEqual(unpaired["state"], FINDER_UNVERIFIED)
        self.assertFalse(unpaired["clearance"])

    def test_bare_find_without_miss_branch(self):
        bare = scan_bare_find("if find(x): print(y)")
        self.assertEqual(bare["bare_find"], 1)
        self.assertFalse(bare["has_miss_branch"])
        guarded = scan_bare_find(
            "hits = find(x)\n"
            "if hits:\n"
            "    print(y)\n"
            "else:\n"
            "    print('FINDER UNVERIFIED')\n"
        )
        self.assertTrue(guarded["has_miss_branch"])

    def test_rule_is_integrated_when_zeros_stay_unnamed(self):
        measured = measure_from_rows(
            {
                "query": "Alt-Text",
                "channel": "#commons",
                "pattern": FINDER_UNVERIFIED,
                "finder_hits": [FINDER_UNVERIFIED],
                "known_present": [FINDER_UNVERIFIED],
                "search_hits": [],
                "pair_hits": [SOURCE_ID],
                "source": "print('FINDER UNVERIFIED')",
                "catalog_defects": [{}, {}, {}, {}],
            }
        )
        self.assertTrue(measured["calibrated"])
        self.assertEqual(measured["find_count"], 1)
        self.assertFalse(measured["clearance"])
        self.assertEqual(classify(measured)["state"], "INTEGRATED")
        self.assertIn("still not the file", classify(measured)["note"])
        zeroed = dict(measured)
        zeroed["find_count"] = 0
        self.assertEqual(classify(zeroed)["state"], "NOT_LANDED")

    def test_live_tree_names_four_defects(self):
        catalog_path = os.path.join(ROOT, "ground", "FINDER_ZERO.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog_text = handle.read()
        catalog = load_catalog(catalog_text)
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["source_id"], SOURCE_ID)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertEqual(len(catalog["defects"]), 4)
        row = measure_tree(ROOT, catalog_text)
        self.assertTrue(row["measured"])
        self.assertTrue(row["instrument"])
        self.assertTrue(row["card"])
        self.assertTrue(row["catalog_file"])
        self.assertFalse(row["gauge_post"])
        self.assertTrue(row["calibrated"])
        self.assertEqual(row["find_state"], "FOUND")
        self.assertEqual(row["collision_state"], FINDER_UNVERIFIED)
        self.assertFalse(row["clearance"])
        self.assertGreaterEqual(row["catalog_defects"], 4)
        self.assertEqual(row["titan_write"], "NOT_WRITTEN")
        self.assertEqual(classify(row)["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
