#!/usr/bin/env python3
"""README audit leftover measures live README and does not edit it."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from readme_audit import (
    CALIBRATION,
    README_PATH,
    REQUIRED_PATCH_IDS,
    SEARCH_SPACE,
    STALE_ROSTER,
    classify,
    load_audit,
    measure_from_rows,
    measure_root,
)


class TestReadmeAudit(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])
        self.assertEqual(row["z"], "FINDER-FAILED")

    def test_stale_roster_is_not_landed(self):
        measured = measure_from_rows(
            {
                "calibration_ok": True,
                "readme_present": True,
                "audit_present": True,
                "stale_roster_restored": True,
                "finding": "STALE_ROSTER_ALREADY_REPLACED",
                "xyz_required": True,
                "remeasurement_owner": "Codex / Grok Build",
                "titan": "NOT_WRITTEN",
                "do_not_edit": ["README.md"],
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_apply_now_is_not_landed(self):
        measured = measure_from_rows(
            {
                "calibration_ok": True,
                "readme_present": True,
                "audit_present": True,
                "stale_roster_restored": False,
                "phrase_miss": [],
                "patch_miss": [],
                "readme_edit_in_this_leftover": True,
                "finding": "STALE_ROSTER_ALREADY_REPLACED",
                "xyz_required": True,
                "remeasurement_owner": "Codex / Grok Build",
                "titan": "NOT_WRITTEN",
                "do_not_edit": ["README.md"],
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_live_tree_matches_the_report(self):
        readme = os.path.join(ROOT, README_PATH)
        with open(readme, encoding="utf-8") as handle:
            body = handle.read()
        self.assertNotIn(STALE_ROSTER, body)
        self.assertIn("Open door", body)
        self.assertIn("names.html", body)
        self.assertIn("action.html", body)
        self.assertIn("HTTP is not the computer", body)
        self.assertIn("proves PC execution", body)
        audit_path = os.path.join(ROOT, "audit", "readme-20260825", "audit.json")
        with open(audit_path, encoding="utf-8") as handle:
            audit = load_audit(handle.read())
        self.assertEqual(audit["finding"], "STALE_ROSTER_ALREADY_REPLACED")
        self.assertFalse(audit["readme_edit_in_this_leftover"])
        self.assertEqual([item["id"] for item in audit["patches"]], list(REQUIRED_PATCH_IDS))
        self.assertTrue(all(item.get("apply_now") is False for item in audit["patches"]))
        self.assertIn("README.md", audit["do_not_edit"])
        row = measure_root(ROOT)
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(sorted(row["calibration_hits"]), sorted(CALIBRATION))
        self.assertEqual(row["search_space"], list(SEARCH_SPACE))
        self.assertFalse(row["stale_roster_restored"])
        self.assertEqual(row["phrase_miss"], [])
        self.assertEqual(row["patch_miss"], [])
        self.assertEqual(classify(row)["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
