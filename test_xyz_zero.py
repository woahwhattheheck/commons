#!/usr/bin/env python3
"""X-Y-Z leftover measures; a bare zero is not a result."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from xyz_zero import (
    AUDIT_SCOPE,
    FINDER_UNVERIFIED,
    PROTECTED_CLAIMS,
    SLACK_TS,
    SOURCE_ID,
    applies_to,
    classify,
    load_catalog,
    measure_from_rows,
    measure_tree,
    run_finder,
    scoped_verdict,
    y_sources_from_bytes,
    z_is_verified,
)


class TestXyzZero(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_x_missing_is_void(self):
        row = run_finder({"id": "no-x"}, "bytes", True)
        self.assertTrue(row["void"])
        self.assertIn("X is not written", row["void_reason"])

    def test_y_must_come_from_found_bytes(self):
        row = run_finder(
            {
                "id": "hit",
                "x_pattern": "A bake is not the board",
                "x_path": "ground/HEAD.md",
                "calibration": True,
            },
            "# A bake is not the board\nBryce",
            True,
        )
        self.assertTrue(row["hit"])
        self.assertTrue(row["y_from_bytes"])
        self.assertIn("A bake is not the board", row["y"])
        self.assertFalse(y_sources_from_bytes("FOUND", "A bake is not the board"))

    def test_miss_prints_finder_unverified_and_search_space(self):
        row = run_finder(
            {
                "id": "miss",
                "x_pattern": "THIS-STRING-IS-NOT-ON-THE-BOARD-XYZ-20260825",
                "x_path": "ground/HEAD.md",
            },
            "# A bake is not the board\n",
            True,
        )
        self.assertFalse(row["hit"])
        self.assertTrue(row["z_verified"])
        self.assertIn(FINDER_UNVERIFIED, row["z"])
        self.assertIn("ground/HEAD.md", row["z"])
        self.assertIn("THIS-STRING-IS-NOT-ON-THE-BOARD-XYZ-20260825", row["z"])
        self.assertFalse(z_is_verified("none found"))
        self.assertFalse(z_is_verified("0"))
        self.assertFalse(z_is_verified(FINDER_UNVERIFIED + " path=ground/HEAD.md"))

    def test_silent_else_is_the_bug_shape(self):
        row = run_finder(
            {
                "id": "silent",
                "x_pattern": "nope",
                "x_path": "ground/HEAD.md",
            },
            "# A bake is not the board\n",
            True,
            silent_miss=True,
        )
        self.assertTrue(row["void"])
        self.assertIn("silent miss", row["void_reason"])
        measured = measure_from_rows([row])
        self.assertTrue(measured["void_run"])
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_calibration_miss_voids_the_run(self):
        miss = run_finder(
            {
                "id": "calib",
                "x_pattern": "not-on-this-page",
                "x_path": "ground/HEAD.md",
                "calibration": True,
            },
            "# A bake is not the board\n",
            True,
        )
        measured = measure_from_rows([miss])
        self.assertTrue(measured["void_run"])
        self.assertIn("known-present", measured["void_reason"])
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_no_calibration_is_no_valid_zero(self):
        miss = run_finder(
            {
                "id": "miss-only",
                "x_pattern": "THIS-STRING-IS-NOT-ON-THE-BOARD-XYZ-20260825",
                "x_path": "ground/HEAD.md",
            },
            "# A bake is not the board\n",
            True,
        )
        measured = measure_from_rows([miss])
        self.assertTrue(measured["void_run"])
        self.assertIn("no known-present finder calibration", measured["void_reason"])

    def test_finder_audit_cannot_override_protected_results(self):
        failed_finder_audit = measure_from_rows([])
        original = {
            "state": "SUCCESS",
            "value": 42,
            "attribution": "PFC_ATTRIBUTED",
        }
        for claim_kind in PROTECTED_CLAIMS:
            self.assertFalse(applies_to(claim_kind), claim_kind)
            guarded = scoped_verdict(claim_kind, original, failed_finder_audit)
            self.assertFalse(guarded["applies"])
            self.assertEqual(guarded["scope"], AUDIT_SCOPE)
            self.assertIs(guarded["result"], original)
            self.assertEqual(guarded["audit_state"], "OUT_OF_SCOPE")
        self.assertTrue(applies_to("absence_search"))
        self.assertTrue(applies_to("negative-finder-claim"))

    def test_live_tree_hits_known_present_and_prints_z_on_miss(self):
        catalog_path = os.path.join(ROOT, "ground", "XYZ_ZERO.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog_text = handle.read()
        catalog = load_catalog(catalog_text)
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["source_id"], SOURCE_ID)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertEqual(len(catalog["finders"]), 3)
        row = measure_tree(ROOT, catalog_text)
        self.assertTrue(row["measured"])
        self.assertFalse(row["void_run"])
        self.assertEqual(row["calibration_count"], 2)
        self.assertEqual(row["calibration_hits"], 2)
        self.assertEqual(row["hit_count"], 2)
        self.assertEqual(row["miss_count"], 1)
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        ids = {item["id"]: item for item in row["finders"]}
        self.assertIn("A bake is not the board", ids["calib-head-md"]["y"])
        self.assertIn(
            "ACTION PAD IS AN UNRESTRICTED OPEN DOOR",
            ids["calib-owner-door"]["y"],
        )
        self.assertIn(FINDER_UNVERIFIED, ids["miss-absent-needle"]["z"])
        self.assertIn("ground/HEAD.md", ids["miss-absent-needle"]["z"])
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertIn("still not the file", classify(row)["note"])


if __name__ == "__main__":
    unittest.main()
    applies_to,
