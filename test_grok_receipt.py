#!/usr/bin/env python3
"""Grok receipt leftover normalizes envelopes and reconciles catalog deltas."""

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
    H009_BUGS,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
    normalize_envelope,
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
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("instrument failure", verdict["note"])
        self.assertIn("never 0", verdict["note"].lower())

    def test_last_fenced_json_is_authoritative(self):
        envelope = (
            "scratch thought {\"rank\": 1}\n"
            "```json\n{\"scratch\": true}\n```\n"
            "more thought\n"
            "```json\n{\"ok\": true, \"delta\": [\"rivet\"]}\n```\n"
        )
        got = normalize_envelope(envelope)
        self.assertEqual(got["status"], "CANDIDATE")
        self.assertEqual(got["authoritative"], {"ok": True, "delta": ["rivet"]})
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
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_architect_rank_1_swarm_consumer_is_refused(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "h009_present": True,
                "pixel_js_consumes": True,
                "swarm_js_consumes": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
                "h009_bugs": [bug["id"] for bug in H009_BUGS],
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("ARCHITECT rank 1", verdict["note"])

    def test_live_tree_reconciles_skeptic_deltas(self):
        catalog_path = os.path.join(ROOT, "ground", "GROK_RECEIPT.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertEqual(catalog["architect_rank_1"], "REFUSED")
        self.assertEqual(catalog["posting"], "OPEN")
        ids = [item["id"] for item in catalog["receipts"]]
        for name in CANDIDATE_RECEIPTS:
            self.assertTrue(any(name.lower() in item.lower() for item in ids), name)
            self.assertTrue(
                all(item["status"] == "CANDIDATE" for item in catalog["receipts"])
            )
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(len(row["calibration_hits"]), len(CALIBRATION))
        self.assertTrue(row["pixel_js_consumes"])
        self.assertFalse(row["swarm_js_consumes"])
        self.assertTrue(row["rivet_listed"])
        self.assertTrue(row["rivet_file"])
        self.assertTrue(row["emitter_landed_named"])
        self.assertTrue(row["stranded_names_lda_android"])
        self.assertTrue(row["stranded_names_inventory"])
        self.assertTrue(row["gemma_path_current"])
        self.assertTrue(row["keyb_stale_field"])
        self.assertTrue(row["assemble_hides_fail"])
        self.assertTrue(row["dump_impl_present"])
        self.assertTrue(row["dump_stale_absent"])
        self.assertEqual(len(row["h009_bugs"]), len(H009_BUGS))
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertIn("still not the file", classify(row)["note"])
        self.assertGreaterEqual(len(SEARCH_SPACE), 8)


if __name__ == "__main__":
    unittest.main()
