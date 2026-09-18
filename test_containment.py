#!/usr/bin/env python3
"""Containment leftover classifies GAUGE artifacts; it does not clear them."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from containment import (
    ALLOWED_STATUS,
    CALIBRATION,
    REQUIRED_IDS,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    SOURCE_ID,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
)


def _complete_facts(**overrides):
    facts = {
        "card_present": True,
        "catalog_present": True,
        "found_phrases": list(REQUIRED_PHRASES),
        "claude_output": "INFORMATIONAL",
        "artifacts": [
            {
                "id": "gauge-secret-rescan-20260825-04",
                "status": "UNSCANNED",
                "remeasurement_owner": "any non-Claude seat",
            },
            {
                "id": "claudelocal-titan-move-go-20260825-01",
                "status": "QUARANTINED",
                "remeasurement_owner": "DIO",
            },
            {
                "id": "gauge-xyz-zero-audit-results-20260825-03",
                "status": "INFORMATIONAL",
                "remeasurement_owner": "DIO",
            },
            {
                "id": "owner-action-done-receipts-20260825",
                "status": "WORK_RECORD",
                "remeasurement_owner": "any non-Claude seat",
            },
        ],
        "branches": [
            {"name": "sd-wx", "status": "UNSCANNED"},
            {"name": "player1-publish", "status": "UNSCANNED"},
            {"name": "vent-final", "status": "UNSCANNED"},
            {"name": "vent-fix", "status": "UNSCANNED"},
        ],
        "packet_present": True,
        "remeasurement_owner": "Codex / Grok Build",
        "allowed_remeasurers": [
            "deterministic local checks",
            "GitHub Actions",
            "Codex",
            "Codex / Grok Build",
        ],
        "xyz_required": True,
        "calibration_ok": True,
        "calibration_hits": list(CALIBRATION),
        "source_post_present": False,
    }
    facts.update(overrides)
    return facts


class TestContainment(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])
        self.assertEqual(row["z"], "FINDER-UNVERIFIED")

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
        self.assertIn("Never 0", verdict["note"])
        self.assertEqual(verdict["z"], "FINDER-UNVERIFIED")

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "misses": ["ground/CONTAINMENT.md"],
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-UNVERIFIED")

    def test_clean_status_is_forbidden(self):
        facts = _complete_facts()
        facts["artifacts"][0]["status"] = "CLEAN"
        verdict = classify(measure_from_rows(facts))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-UNVERIFIED")
        self.assertIn("CLEAN/0", verdict["note"])

    def test_zero_status_is_forbidden(self):
        facts = _complete_facts()
        facts["artifacts"][0]["status"] = "0"
        verdict = classify(measure_from_rows(facts))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-UNVERIFIED")

    def test_missing_packet_is_finder_unverified(self):
        verdict = classify(measure_from_rows(_complete_facts(packet_present=False)))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-UNVERIFIED")
        self.assertIn("packet path", verdict["note"])

    def test_complete_leftover_is_integrated(self):
        verdict = classify(measure_from_rows(_complete_facts()))
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_live_tree_matches_the_report(self):
        catalog_path = os.path.join(ROOT, "ground", "CONTAINMENT.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["source_id"], SOURCE_ID)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertEqual(catalog["claude_output"], "INFORMATIONAL")
        self.assertTrue(catalog["xyz_required"])
        self.assertEqual(catalog["remeasurement_owner"], "Codex / Grok Build")
        self.assertGreaterEqual(len(catalog["allowed_remeasurers"]), 4)
        self.assertEqual(
            [item["id"] for item in catalog["artifacts"]], list(REQUIRED_IDS)
        )
        self.assertTrue(
            all(item["status"] in ALLOWED_STATUS for item in catalog["artifacts"])
        )
        self.assertTrue(
            all(item["status"] == "UNSCANNED" for item in catalog["branches"])
        )
        self.assertEqual(len(catalog["branches"]), 4)
        row = measure_root(ROOT)
        self.assertTrue(
            row["calibration_ok"],
            "known-present calibration must hit HEAD + EXECUTE + Action Pad",
        )
        self.assertEqual(sorted(row["calibration_hits"]), sorted(CALIBRATION))
        self.assertEqual(row["search_space"], list(SEARCH_SPACE))
        self.assertTrue(row["packet_present"])
        self.assertTrue(row["quarantined_post_present"])
        self.assertTrue(row["source_post_present"])
        self.assertEqual(row["source_post_state"], "DURABLE_ON_MAIN")
        self.assertTrue(row["source_provenance_ok"])
        self.assertEqual(row["source_provenance_mismatches"], [])
        hostile = dict(row, source_post_state="UNVERIFIED_PRESENT", source_provenance_ok=False)
        self.assertEqual(classify(hostile)["state"], "NOT_LANDED")
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertIn("containment_compliance", row["found_phrases"])
        self.assertIn("unscanned", row["found_phrases"])


if __name__ == "__main__":
    unittest.main()
