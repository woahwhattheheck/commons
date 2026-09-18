#!/usr/bin/env python3
"""Heavy lanes leftover consumes H-001/H-002 and refuses a Slack live line."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from heavy_lanes import (
    ALREADY_LANDED,
    CALIBRATION,
    LIVE_IDS,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
    output_states,
    packet_errors,
    sprint_packet_ids,
)


class TestHeavyLanes(unittest.TestCase):
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
                "misses": ["ground/HEAVY_LANES.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_missing_live_ids_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "packet_errors": ["missing live packet H-001-ARCHITECT"],
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "consumer_gap": {"id": "G-001", "unresolved": "gap"},
                "cursor_grok_is_not_heavy_substitute": True,
                "do_not_duplicate": True,
                "sprint_has_live": False,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("Do not remint SUPERGROK_HEAVY", verdict["note"])

    def test_sprint_remint_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "packet_errors": [],
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "consumer_gap": {"id": "G-001", "unresolved": "gap"},
                "cursor_grok_is_not_heavy_substitute": True,
                "do_not_duplicate": True,
                "sprint_has_live": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("remint", verdict["note"].lower())

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "packet_errors": [],
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "consumer_gap": {"id": "G-001", "unresolved": "gap"},
                "cursor_grok_is_not_heavy_substitute": True,
                "do_not_duplicate": True,
                "sprint_has_live": False,
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
        self.assertFalse(row["sprint_has_live"])
        self.assertEqual(row.get("slack_ts") or SLACK_TS, SLACK_TS)
        self.assertEqual(row["consumer_gap"].get("id"), "G-001")
        outputs = {item["id"]: item["state"] for item in row["packet_outputs"]}
        self.assertEqual(outputs.get("H-001-ARCHITECT"), "CANDIDATE")
        self.assertEqual(outputs.get("H-002-CONTAMINATION"), "CANDIDATE")

    def test_catalog_names_live_packets_and_gap(self):
        catalog_path = os.path.join(ROOT, "ground", "HEAVY_LANES.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertTrue(catalog["cursor_grok_is_not_heavy_substitute"])
        self.assertTrue(catalog["do_not_duplicate"])
        self.assertEqual(catalog["posting"], "OPEN")
        self.assertTrue(catalog["no_auth"])
        self.assertTrue(catalog["no_gate"])
        ids = [item.get("id") for item in catalog["packets"]]
        self.assertEqual(list(LIVE_IDS), ids)
        self.assertEqual(catalog["consumer_gap"].get("id"), "G-001")
        self.assertIn("ground/SUPERGROK_HEAVY.md", catalog["already_landed"])

    def test_sprint_catalog_does_not_name_live_ids(self):
        ids = sprint_packet_ids(ROOT)
        self.assertIn("heavy-dir9-read-mesh", ids)
        self.assertIn("heavy-dir19-agent-swarm", ids)
        for live_id in LIVE_IDS:
            self.assertNotIn(live_id, ids)

    def test_missing_output_is_candidate_never_zero(self):
        rows = output_states(
            ROOT,
            [
                {
                    "id": "H-001-ARCHITECT",
                    "output_path": "ground/H001_ARCHITECT.json",
                }
            ],
        )
        self.assertEqual(rows[0]["state"], "CANDIDATE")
        self.assertNotEqual(rows[0]["state"], "0")

    def test_packet_errors_catch_bare_zero(self):
        errors = packet_errors(
            ROOT,
            [
                {
                    "id": "H-001-ARCHITECT",
                    "lane": "heavy",
                    "state": "CANDIDATE",
                    "output_path": "ground/H001_ARCHITECT.json",
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
        self.assertIn("missing live packet H-002-CONTAMINATION", joined)

    def test_search_space_and_calibration_named(self):
        self.assertIn("ground/HEAVY_LANES.md", SEARCH_SPACE)
        self.assertIn("ground/SUPERGROK_HEAVY.md", SEARCH_SPACE)
        self.assertIn("ground/SUPERGROK_HEAVY.md", CALIBRATION)
        self.assertIn("ground/EXECUTE.md", CALIBRATION)
        self.assertIn("ground/SUPERGROK_HEAVY.md", ALREADY_LANDED)
        self.assertIn("ground/MUHL_RECEIPT_LANE.md", ALREADY_LANDED)


if __name__ == "__main__":
    unittest.main()
