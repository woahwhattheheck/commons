#!/usr/bin/env python3
"""Claude-intermediate leftover amends the charter; it does not lock the door."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from claude_intermediate import (
    ADJUDICATOR,
    CALIBRATION,
    OPERATING_LABEL,
    REQUIRED_CLAUSES,
    REQUIRED_GATES,
    REQUIRED_PHRASES,
    REQUIRED_STATUS,
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
        "clauses": [
            {"id": clause_id, "status": REQUIRED_STATUS[clause_id]}
            for clause_id in REQUIRED_CLAUSES
        ],
        "rehab_gates": [
            {"id": gate_id, "need": gate_id, "state": "OPEN"}
            for gate_id in REQUIRED_GATES
        ],
        "operating_label": OPERATING_LABEL,
        "adjudicator": ADJUDICATOR,
        "claude_output": "INFORMATIONAL",
        "preserve_claude_artifacts": True,
        "preserve_peer_charter": True,
        "peer_charter_present": True,
        "no_gate": True,
        "posting_open": True,
        "xyz_required": True,
        "source_post_present": False,
        "source_durable": "CARRIER_ONLY",
        "calibration_ok": True,
        "calibration_hits": list(CALIBRATION),
    }
    facts.update(overrides)
    return facts


class TestClaudeIntermediate(unittest.TestCase):
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
                "misses": ["ground/CLAUDE_INTERMEDIATE.md"],
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-UNVERIFIED")

    def test_clean_status_is_forbidden(self):
        facts = _complete_facts()
        facts["clauses"][0]["status"] = "CLEAN"
        verdict = classify(measure_from_rows(facts))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("CLEAN/0", verdict["note"])

    def test_missing_peer_charter_is_not_landed(self):
        verdict = classify(measure_from_rows(_complete_facts(peer_charter_present=False)))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("peer charter must stay", verdict["note"])

    def test_locked_rehab_gate_is_not_landed(self):
        facts = _complete_facts()
        facts["rehab_gates"][0]["state"] = "LOCKED"
        verdict = classify(measure_from_rows(facts))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("lock", verdict["note"])

    def test_gate_flag_keeps_the_door_open(self):
        verdict = classify(measure_from_rows(_complete_facts(no_gate=False)))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("door must stay open", verdict["note"])

    def test_complete_leftover_is_integrated(self):
        verdict = classify(measure_from_rows(_complete_facts()))
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_live_tree_matches_the_report(self):
        catalog_path = os.path.join(ROOT, "ground", "CLAUDE_INTERMEDIATE.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["source_id"], SOURCE_ID)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertEqual(catalog["claude_output"], "INFORMATIONAL")
        self.assertEqual(catalog["operating_label"], OPERATING_LABEL)
        self.assertEqual(catalog["adjudicator"], ADJUDICATOR)
        self.assertTrue(catalog["no_gate"])
        self.assertTrue(catalog["posting_open"])
        self.assertTrue(catalog["preserve_peer_charter"])
        self.assertEqual(catalog["source_durable"], "CARRIER_ONLY")
        self.assertEqual([item["id"] for item in catalog["clauses"]], list(REQUIRED_CLAUSES))
        self.assertEqual(
            {item["id"]: item["status"] for item in catalog["clauses"]},
            REQUIRED_STATUS,
        )
        row = measure_root(ROOT)
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(sorted(row["calibration_hits"]), sorted(CALIBRATION))
        self.assertEqual(row["search_space"], list(SEARCH_SPACE))
        self.assertTrue(row["source_post_present"])
        self.assertEqual(row["source_durable"], "DURABLE_ON_MAIN")
        self.assertTrue(row["source_provenance_ok"])
        self.assertEqual(row["source_provenance_mismatches"], [])
        hostile = dict(row, source_durable="UNVERIFIED_PRESENT", source_provenance_ok=False)
        self.assertEqual(classify(hostile)["state"], "NOT_LANDED")
        self.assertTrue(row["peer_charter_present"])
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertIn("quarantined intermediate worker", row["found_phrases"])
        self.assertIn("rejected for now", row["found_phrases"])
        self.assertIn("p6 amended", row["found_phrases"])


if __name__ == "__main__":
    unittest.main()
