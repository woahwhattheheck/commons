#!/usr/bin/env python3
"""Device-path census leftover re-runs JOJO X/Y/Z and inspects one lawful canary."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from device_path_census import (
    CALIBRATION,
    CANARY_ID,
    FinderError,
    JOJO_ID,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    count_prefix,
    count_result_scopes,
    inspect_canary,
    load_catalog,
    ls_tree,
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

    def test_valid_ref_calibrates_tree_reader(self):
        paths = ls_tree(ROOT, "HEAD")
        self.assertIn("ground/HEAD.md", paths)
        self.assertGreater(len(paths), 0)
        self.assertEqual(count_prefix(paths, "actions/device-reservations/"), 0)

    def test_invalid_ref_is_finder_failed_not_integrated(self):
        ref = "refs/heads/does-not-exist-device-zero-regression"
        with self.assertRaises(FinderError):
            ls_tree(ROOT, ref)
        row = measure_root(ROOT, ref=ref)
        self.assertEqual(row["tree_finder_status"], "FINDER-FAILED")
        self.assertIsNone(row["tree_count"])
        self.assertIsNone(row["reservation_count"])
        self.assertIsNone(row["batch_count"])
        self.assertIsNone(row["result_count"])
        self.assertIsNone(row["scope_device"])
        self.assertIsNone(row["parse_failures"])
        self.assertEqual(classify(row)["state"], "UNMEASURED")
        self.assertIn("null, not zero", classify(row)["note"])

    def test_successful_empty_git_tree_remains_measured_empty(self):
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["git", "init", "-q"], cwd=td, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=DEMON test",
                    "-c",
                    "user.email=demon@example.invalid",
                    "commit",
                    "-q",
                    "--allow-empty",
                    "-m",
                    "empty",
                ],
                cwd=td,
                check=True,
            )
            paths = ls_tree(td, "HEAD")
        self.assertEqual(paths, [])
        self.assertEqual(count_prefix(paths, "actions/device-reservations/"), 0)

    def test_broken_result_json_nulls_scopes_not_blob_count(self):
        with tempfile.TemporaryDirectory() as td:
            result_dir = Path(td) / "actions" / "results"
            result_dir.mkdir(parents=True)
            (result_dir / "broken.json").write_text("{", encoding="utf-8")
            got = count_result_scopes(td, ["actions/results/broken.json"])
        self.assertEqual(got["result_count"], 1)
        self.assertEqual(got["parse_failures"], 1)
        self.assertIsNone(got["scope_github"])
        self.assertIsNone(got["scope_device"])

    def test_explicit_none_is_not_rezeroed(self):
        row = measure_from_rows(
            {
                "tree_count": None,
                "reservation_count": None,
                "batch_count": None,
                "tree_finder_status": "FINDER-FAILED",
                "calibration_ok": True,
            }
        )
        self.assertIsNone(row["tree_count"])
        self.assertIsNone(row["reservation_count"])
        self.assertIsNone(row["batch_count"])
        self.assertEqual(classify(row)["state"], "UNMEASURED")

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

    def test_search_space_and_calibration_named(self):
        self.assertIn(os.path.join("ground", "DEVICE_PATH_CENSUS.md"), SEARCH_SPACE)
        self.assertIn(os.path.join("ground", "DEVICE_PATH_CANARY.md"), SEARCH_SPACE)
        self.assertIn("device_action_state.py", CALIBRATION)
        self.assertIn(os.path.join("ground", "DEVICE_CHURN.md"), CALIBRATION)
        self.assertIn(os.path.join("ground", "EXECUTE.md"), CALIBRATION)


if __name__ == "__main__":
    unittest.main()
    FinderError,
    ls_tree,
