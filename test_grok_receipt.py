#!/usr/bin/env python3
"""Exact-one-fence leftover. Last-fence is collision."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from grok_receipt import (
    ALREADY_LANDED,
    CALIBRATION,
    CANDIDATE_RECEIPTS,
    H009_PATCHED,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
    normalize_envelope,
    raw_sha,
)


class TestGrokReceipt(unittest.TestCase):
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
                "h009_present": True,
                "raw_sha": "0" * 40,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("instrument failure", verdict["note"])
        self.assertIn("never 0", verdict["note"].lower())

    def test_null_sha_is_unmeasured(self):
        verdict = classify(
            measure_from_rows(
                {
                    "card_present": True,
                    "catalog_present": True,
                    "h009_present": True,
                    "calibration_ok": True,
                    "raw_sha": None,
                }
            )
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("raw SHA is null", verdict["note"])

    def test_two_fences_are_finder_failed(self):
        envelope = (
            "scratch thought {\"rank\": 1}\n"
            "```json\n{\"scratch\": true}\n```\n"
            "more thought\n"
            "```json\n{\"ok\": true, \"delta\": [\"rivet\"]}\n```\n"
        )
        got = normalize_envelope(envelope)
        self.assertEqual(got["status"], "CANDIDATE")
        self.assertIsNone(got["authoritative"])
        self.assertEqual(got["fence_count"], 2)
        self.assertIn("FINDER-FAILED", got["error"])
        self.assertIn("collision", got["error"].lower())

    def test_exact_one_fence_is_authoritative(self):
        got = normalize_envelope("```json\n{\"ok\": true, \"delta\": [\"rivet\"]}\n```\n")
        self.assertEqual(got["status"], "CANDIDATE")
        self.assertEqual(got["authoritative"], {"ok": True, "delta": ["rivet"]})
        self.assertEqual(got["fence_count"], 1)
        self.assertIn("scratch/thought", got["excluded"])

    def test_missing_fence_is_finder_failed(self):
        got = normalize_envelope("thought only")
        self.assertEqual(got["status"], "CANDIDATE")
        self.assertIsNone(got["authoritative"])
        self.assertIn("FINDER-FAILED", got["error"])

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "h009_present": False,
                "misses": ["ground/GROK_RECEIPT.md"],
                "calibration_ok": True,
                "raw_sha": "0" * 40,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_live_tree_is_exact_one_fence(self):
        catalog_path = os.path.join(ROOT, "ground", "GROK_RECEIPT.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertEqual(catalog["titan_helper"], "BOUNDARY_ONLY")
        self.assertEqual(catalog["architect_rank_1"], "REFUSED")
        self.assertEqual(catalog["posting"], "OPEN")
        ids = [item["id"] for item in catalog["receipts"]]
        for name in CANDIDATE_RECEIPTS:
            self.assertTrue(any(name.lower() in item.lower() for item in ids), name)
        self.assertTrue(all(item["status"] == "CANDIDATE" for item in catalog["receipts"]))
        sha = raw_sha(ROOT)
        self.assertIsNotNone(sha)
        self.assertEqual(len(sha), 40)
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(len(row["calibration_hits"]), len(CALIBRATION))
        self.assertEqual(row["raw_sha"], sha)
        self.assertTrue(row["exact_one_fence"])
        self.assertTrue(row["last_fence_absent"])
        self.assertTrue(row["rivet_heartbeat_row"])
        self.assertTrue(row["gemma_path_current"])
        self.assertTrue(row["dump_impl_present"])
        self.assertTrue(row["census_invalid_ref_null"])
        self.assertTrue(row["churn_missing_dir_null"])
        self.assertTrue(row["titan_helper_boundary"])
        self.assertEqual(len(row["h009_patched"]), len(H009_PATCHED))
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertIn("still not the file", classify(row)["note"])
        self.assertGreaterEqual(len(SEARCH_SPACE), 8)
        self.assertEqual(len(row["landed_missing"]), 0)
        self.assertEqual(len(row["landed_present"]), len(ALREADY_LANDED))


if __name__ == "__main__":
    unittest.main()
