#!/usr/bin/env python3
"""SuperGrok Heavy leftover names unfinished builds and refuses a Slack map."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from supergrok_heavy import (
    ALREADY_LANDED,
    CALIBRATION,
    MIN_HEAVY_PACKETS,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    classify_sha,
    load_catalog,
    measure_from_rows,
    measure_root,
    packet_errors,
)


class TestSuperGrokHeavy(unittest.TestCase):
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
                "misses": ["ground/SUPERGROK_HEAVY.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_foreign_measured_head_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "sha_relation": "FOREIGN",
                "measured_head": "deadbeefdeadbeef",
                "official_head": "cafebabecafebabe",
                "packet_errors": [],
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "pool": "shared_weekly",
                "cursor_grok_is_not_heavy_substitute": True,
                "revenue_ideation": "refused",
                "receipt_ok": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("not an ancestor", verdict["note"])

    def test_incomplete_packets_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "sha_relation": "ANCESTOR",
                "packet_errors": ["heavy packets 0 < 2"],
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "pool": "shared_weekly",
                "cursor_grok_is_not_heavy_substitute": True,
                "revenue_ideation": "refused",
                "receipt_ok": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("generic idea list", verdict["note"])

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "sha_relation": "ANCESTOR",
                "packet_errors": [],
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "pool": "shared_weekly",
                "cursor_grok_is_not_heavy_substitute": True,
                "revenue_ideation": "refused",
                "receipt_ok": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_live_tree_measures_integrated(self):
        row = measure_root(ROOT)
        verdict = classify(row)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertFalse(row["landed_missing"])
        self.assertFalse(row["packet_errors"])
        self.assertGreaterEqual(row["heavy_count"], MIN_HEAVY_PACKETS)
        self.assertEqual(row.get("slack_ts") or SLACK_TS, SLACK_TS)
        self.assertIn(row["sha_relation"], ("HEAD", "ANCESTOR"))

    def test_catalog_parses_pool_and_packets(self):
        catalog_path = os.path.join(ROOT, "ground", "SUPERGROK_HEAVY.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["pool"], "shared_weekly")
        self.assertFalse(catalog["grok_build_separate_bucket"])
        self.assertTrue(catalog["cursor_grok_is_not_heavy_substitute"])
        self.assertEqual(catalog["revenue_ideation"], "refused")
        self.assertEqual(catalog["posting"], "OPEN")
        self.assertTrue(catalog["no_auth"])
        self.assertTrue(catalog["no_gate"])
        self.assertGreaterEqual(len(catalog["packets"]), MIN_HEAVY_PACKETS)
        self.assertIn("ground/GROK_HYGIENE.md", catalog["already_landed"])

    def test_packet_errors_catch_bare_zero_and_missing_verifier(self):
        errors = packet_errors(
            ROOT,
            [
                {
                    "id": "bad",
                    "lane": "heavy",
                    "source_paths": ["DIRECTIVES.md"],
                    "source_sha": "94d52927b",
                    "unresolved": "0",
                    "deliverable": "ideas",
                    "verifier": "ask Grok",
                    "do_not_remint": ["x"],
                }
            ],
        )
        joined = " ".join(errors)
        self.assertIn("bare unresolved zero", joined)
        self.assertIn("missing non-Grok verifier", joined)
        self.assertIn("heavy packets 1 < 2", joined)

    def test_classify_sha_names_ancestor(self):
        self.assertEqual(classify_sha("abc1234", "abc1234def", False), "HEAD")
        self.assertEqual(classify_sha("abc1234", "deadbeef", True), "ANCESTOR")
        self.assertEqual(classify_sha("abc1234", "deadbeef", False), "FOREIGN")
        self.assertEqual(classify_sha("", "deadbeef", False), "UNMEASURED")

    def test_search_space_and_calibration_named(self):
        self.assertIn("ground/SUPERGROK_HEAVY.md", SEARCH_SPACE)
        self.assertIn("ground/GROK_HYGIENE.md", SEARCH_SPACE)
        self.assertIn("ground/GROK_HYGIENE.md", CALIBRATION)
        self.assertIn("ground/EXECUTE.md", CALIBRATION)
        self.assertIn("ground/CASH_NOW.md", ALREADY_LANDED)
        self.assertIn("ground/SPECTER_FINAL.md", ALREADY_LANDED)
        self.assertIn("ground/SITTING_PR.md", ALREADY_LANDED)
        self.assertIn("ground/DEVICE_QUEUE_CAP.md", ALREADY_LANDED)


if __name__ == "__main__":
    unittest.main()
