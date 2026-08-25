#!/usr/bin/env python3
"""Claude-park leftover parks named lanes; it is never 0."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from claude_park import (
    BAKE_SCAN,
    CALIBRATION,
    DOORBELL,
    REQUIRED_LANE_IDS,
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
        "lanes": [
            {"id": "pfc-bake-scan", "status": "PARKED", "owner": "Cursor / Grok"},
            {"id": "tester-verifier", "status": "PARKED", "owner": "Codex"},
            {"id": "new-claude-assignment", "status": "PARKED", "owner": "Cursor / Grok"},
            {"id": "claude-self-certify", "status": "REFUSED", "owner": "Cursor / Grok"},
            {"id": "colony-role-proposal", "status": "PARKED", "owner": "Cursor / Grok"},
        ],
        "census_owner": "Cursor / Grok",
        "reinstatement": "BRYCE_ONLY",
        "claude_certify": "REFUSED",
        "xyz_required": True,
        "preserve_evidence": True,
        "posting_gate": False,
        "label": "CLAUDE-FAMILY-PARK-REROUTE",
        "doorbell_present": True,
        "bake_scan_present": False,
        "calibration_ok": True,
        "calibration_hits": list(CALIBRATION),
    }
    facts.update(overrides)
    return measure_from_rows(facts)


class TestClaudePark(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])
        self.assertEqual(row["z"], "FINDER-FAILED")
        self.assertIn("Never 0", row["note"])

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
        self.assertEqual(verdict["z"], "FINDER-FAILED")

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "misses": ["ground/CLAUDE_PARK.md"],
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-FAILED")
        self.assertIn("Never 0", verdict["note"])

    def test_claude_owner_is_not_landed(self):
        measured = _complete_facts(
            lanes=[
                {"id": "pfc-bake-scan", "status": "PARKED", "owner": "CLAUDE"},
                {"id": "tester-verifier", "status": "PARKED", "owner": "Codex"},
                {"id": "new-claude-assignment", "status": "PARKED", "owner": "Cursor / Grok"},
                {"id": "claude-self-certify", "status": "REFUSED", "owner": "Cursor / Grok"},
                {"id": "colony-role-proposal", "status": "PARKED", "owner": "Cursor / Grok"},
            ]
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("pfc-bake-scan", verdict["note"])
        self.assertEqual(verdict["z"], "FINDER-FAILED")

    def test_vote_reinstatement_is_not_landed(self):
        measured = _complete_facts(reinstatement="COLONY_VOTE")
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("BRYCE_ONLY", verdict["note"])

    def test_complete_leftover_is_integrated(self):
        measured = _complete_facts()
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_live_tree_matches_the_report(self):
        catalog_path = os.path.join(ROOT, "ground", "CLAUDE_PARK.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["source_id"], SOURCE_ID)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertEqual(catalog["label"], "CLAUDE-FAMILY-PARK-REROUTE")
        self.assertTrue(catalog["xyz_required"])
        self.assertEqual(catalog["census_owner"], "Cursor / Grok")
        self.assertEqual(catalog["reinstatement"], "BRYCE_ONLY")
        self.assertEqual(catalog["claude_certify"], "REFUSED")
        self.assertTrue(catalog["preserve_evidence"])
        self.assertFalse(catalog["posting_gate"])
        self.assertGreaterEqual(len(catalog["allowed_owners"]), 4)
        self.assertEqual(
            [item["id"] for item in catalog["lanes"]],
            list(REQUIRED_LANE_IDS),
        )
        row = measure_root(ROOT)
        self.assertTrue(row["calibration_ok"], "known-present calibration must hit HEAD + EXECUTE + Action Pad")
        self.assertEqual(sorted(row["calibration_hits"]), sorted(CALIBRATION))
        self.assertEqual(row["search_space"], list(SEARCH_SPACE))
        self.assertTrue(row["doorbell_present"], "ping/claude.md must stay as evidence")
        self.assertFalse(row["bake_scan_present"], "pfc_bake_scan.py stays off current main and PARKED")
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertIn("full claude-family suspension", row["found_phrases"])
        self.assertIn("bryce_only", row["found_phrases"])
        self.assertFalse(os.path.isfile(os.path.join(ROOT, BAKE_SCAN)))
        self.assertTrue(os.path.isfile(os.path.join(ROOT, DOORBELL)))
        self.assertNotEqual(classify(row)["note"], "0")


if __name__ == "__main__":
    unittest.main()
