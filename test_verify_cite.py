#!/usr/bin/env python3
"""Verify-cite leftover is a measurement, not a seat."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from verify_cite import (
    CALIBRATION_PATH,
    FINDER_UNVERIFIED,
    classify,
    listing_from_root,
    load_catalog,
    measure_from_parts,
    measure_paths,
    probe_git_sha,
)


class TestVerifyCite(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not measured", row["note"])

    def test_empty_catalog_is_not_landed(self):
        measured = measure_from_parts('{"cited_paths": []}', [])
        self.assertEqual(measured["cited_paths"], [])
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_unknown_commons_sha_is_not_landed(self):
        catalog = json.dumps(
            {
                "slack_ts": "1787634746.313679",
                "cited_sha": "cd7d4f864f0c04143a573173e0b42f61f3c65533",
                "cited_paths": [
                    "host/muhl_revenue.py",
                    "host/test_muhl_revenue.py",
                ],
            }
        )
        measured = measure_from_parts(catalog, [], sha_known=False)
        self.assertEqual(measured["present_count"], 0)
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("not a Commons object", verdict["note"])

    def test_missing_paths_are_not_landed(self):
        catalog = json.dumps(
            {
                "cited_paths": [
                    "host/muhl_revenue.py",
                    "host/test_muhl_revenue.py",
                ]
            }
        )
        measured = measure_from_parts(catalog, ["unrelated.py"])
        self.assertEqual(measured["present_count"], 0)
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("0/2", verdict["note"])

    def test_partial_cite_is_candidate(self):
        catalog = json.dumps(
            {
                "cited_paths": [
                    "host/muhl_revenue.py",
                    "host/test_muhl_revenue.py",
                ]
            }
        )
        measured = measure_from_parts(
            catalog, ["host/muhl_revenue.py"], sha_known=True
        )
        self.assertEqual(measured["present"], ["host/muhl_revenue.py"])
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "CANDIDATE")
        self.assertIn("host/test_muhl_revenue.py", verdict["note"])

    def test_all_present_is_integrated(self):
        catalog = json.dumps(
            {
                "cited_paths": [
                    "host/muhl_revenue.py",
                    "host/test_muhl_revenue.py",
                ]
            }
        )
        measured = measure_from_parts(
            catalog,
            ["host/muhl_revenue.py", "host/test_muhl_revenue.py"],
            sha_known=True,
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")

    def test_catalog_dedupes_and_skips_blank(self):
        catalog = load_catalog(
            json.dumps(
                {
                    "cited_sha": "abc",
                    "cited_paths": ["a.py", "", "a.py", "b.py"],
                    "hands_off": ["LDA titan --check"],
                }
            )
        )
        self.assertEqual(catalog["cited_paths"], ["a.py", "b.py"])
        self.assertEqual(catalog["cited_sha"], "abc")
        self.assertEqual(catalog["hands_off"], ["LDA titan --check"])

    def test_listing_from_root_sees_public_files_only(self):
        found = listing_from_root(
            ROOT, ["host/verify_cite.py", "host/muhl_revenue.py"]
        )
        self.assertEqual(found, ["host/verify_cite.py"])

    def test_missing_tree_root_is_finder_unverified(self):
        catalog = os.path.join(ROOT, "ground", "VERIFY_CITE.json")
        missing_root = os.path.join(ROOT, "definitely-missing-verify-cite-root")
        row = measure_paths(catalog, missing_root)
        self.assertFalse(row["measured"])
        self.assertEqual(row["finder_state"], FINDER_UNVERIFIED)
        self.assertFalse(row["calibrated"])
        self.assertIsNone(row["observed"])
        verdict = classify(row)
        self.assertEqual(verdict["state"], FINDER_UNVERIFIED)
        self.assertNotIn("0/", verdict["note"])
        self.assertEqual(row["search_space"]["path"], os.path.abspath(missing_root))

    def test_known_present_calibration_miss_voids_tree_zero(self):
        catalog = os.path.join(ROOT, "ground", "VERIFY_CITE.json")
        with tempfile.TemporaryDirectory(prefix="verify-cite-root-") as temp_root:
            os.makedirs(os.path.join(temp_root, "host"))
            row = measure_paths(catalog, temp_root)
        self.assertFalse(row["measured"])
        self.assertEqual(row["finder_state"], FINDER_UNVERIFIED)
        self.assertFalse(row["calibrated"])
        self.assertEqual(row["calibration_id"], CALIBRATION_PATH)
        self.assertIn(CALIBRATION_PATH, row["calibration_missed"])
        self.assertNotIn("0/", classify(row)["note"])

    def test_calibrated_path_miss_has_named_space_not_bare_zero(self):
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".json", delete=False
        ) as handle:
            json.dump({"cited_paths": ["host/definitely-missing-cite.py"]}, handle)
            catalog = handle.name
        self.addCleanup(lambda: os.path.exists(catalog) and os.unlink(catalog))
        row = measure_paths(catalog, ROOT)
        self.assertTrue(row["measured"], row.get("finder_note"))
        self.assertTrue(row["calibrated"])
        self.assertEqual(row["finder_state"], "CALIBRATED")
        self.assertEqual(row["find_state"], FINDER_UNVERIFIED)
        self.assertIsNone(row["find_count"])
        self.assertEqual(row["miss_behavior"], "CALIBRATED_ABSENCE")
        self.assertEqual(row["observed"]["calibration_hits"], [CALIBRATION_PATH])
        verdict = classify(row)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn(FINDER_UNVERIFIED, verdict["note"])
        self.assertNotIn("0/", verdict["note"])
        self.assertTrue(row["search_space"]["complete"])

    def test_live_catalog_names_the_taking_cite(self):
        path = os.path.join(ROOT, "ground", "VERIFY_CITE.json")
        row = measure_paths(path, ROOT)
        self.assertTrue(row["measured"], row.get("error"))
        self.assertTrue(row["calibrated"])
        self.assertEqual(row["finder_state"], "CALIBRATED")
        self.assertEqual(row["calibration_id"], CALIBRATION_PATH)
        self.assertEqual(row["observed"]["calibration_hits"], [CALIBRATION_PATH])
        self.assertEqual(
            row["cited_sha"],
            "cd7d4f864f0c04143a573173e0b42f61f3c65533",
        )
        self.assertIn("host/muhl_revenue.py", row["cited_paths"])
        self.assertIn("host/test_muhl_revenue.py", row["cited_paths"])
        self.assertEqual(row["present_count"], 0)
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(row["sha_known"], False)
        self.assertEqual(probe_git_sha(row["cited_sha"], cwd=ROOT), False)
        verdict = classify(row)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("not a Commons object", verdict["note"])


if __name__ == "__main__":
    unittest.main()
