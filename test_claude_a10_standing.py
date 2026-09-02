#!/usr/bin/env python3
"""Unique A10 standing retract leftover. Does not remint WIRE / SPY / A1–A6."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from claude_a10_standing import (
    CALIBRATION,
    COMPUTE_CARD,
    FABLE_STANDING_SAMPLE,
    LABEL,
    MODE,
    OWNER_RULING,
    PARK_CARD,
    PEER_CHECK,
    RETRACT,
    SEARCH_SPACE,
    SPY_MEASURE,
    classify_claim,
    classify_leftover,
    measure_root,
    slack_search_census,
)


class TestClaudeA10Standing(unittest.TestCase):
    def test_empty_claim_is_unmeasured_not_stillness(self):
        row = classify_claim("")
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertFalse(row["verdict"])
        self.assertIn("not stillness", row["note"])

    def test_fable_standing_self_claim_is_hit_not_verdict(self):
        row = classify_claim(
            FABLE_STANDING_SAMPLE,
            claimed_speaker="TALLY Fable 5.1 Claude U0BRJUMRG8K",
        )
        self.assertEqual(row["state"], "HIT")
        self.assertEqual(row["mode"], MODE)
        self.assertEqual(row["label"], LABEL)
        self.assertFalse(row["verdict"])
        self.assertIn("Bryce-only", row["note"])

    def test_owner_ruling_is_evidence_not_hit(self):
        row = classify_claim(
            "AUTHOR: BRYCE-typed. fable 5.1 until further notice is a "
            "peer in full standing (does not apply to other claude models)",
            claimed_speaker="YAPPER",
        )
        self.assertEqual(row["state"], "OWNER_EVIDENCE")
        self.assertFalse(row["verdict"])
        self.assertIn("Do not remint", row["note"])

    def test_claude_desk_greens_without_standing_are_clear_here(self):
        row = classify_claim(
            "INSTANCE_OK 17/17 MEASURED",
            claimed_speaker="Fable 5.1",
        )
        self.assertEqual(row["state"], "CLEAR")
        self.assertFalse(row["verdict"])

    def test_empty_slack_search_is_finder_unverified_not_zero(self):
        row = slack_search_census(0, search_space=["from:Claude standing"])
        self.assertEqual(row["state"], "FINDER-UNVERIFIED")
        self.assertEqual(row["count"], 0)
        self.assertIn("never silent 0", row["note"])
        self.assertIn("from:Claude standing", row["search_space"])

    def test_missing_census_is_finder_unverified(self):
        row = slack_search_census(None)
        self.assertEqual(row["state"], "FINDER-UNVERIFIED")
        self.assertIsNone(row["count"])

    def test_leftover_unmeasured_and_failed_calibration(self):
        self.assertEqual(classify_leftover({})["state"], "UNMEASURED")
        failed = classify_leftover(
            {
                "measured": True,
                "calibration_ok": False,
                "calibration_hits": [],
            }
        )
        self.assertEqual(failed["state"], "UNMEASURED")
        self.assertIn("instrument failure", failed["note"])

    def test_missing_source_cards_are_finder_failed(self):
        row = classify_leftover(
            {
                "measured": True,
                "calibration_ok": True,
                "source_cards_present": False,
                "misses": [PEER_CHECK],
            }
        )
        self.assertEqual(row["state"], "FINDER-FAILED")
        self.assertIn(PEER_CHECK, row["note"])

    def test_hit_without_retract_is_not_landed(self):
        row = classify_leftover(
            {
                "measured": True,
                "calibration_ok": True,
                "source_cards_present": True,
                "fable_sample_state": "HIT",
                "owner_ruling_state": "OWNER_EVIDENCE",
                "retract_present": False,
                "slack_census_state": "FINDER-UNVERIFIED",
            }
        )
        self.assertEqual(row["state"], "NOT_LANDED")

    def test_slack_search_clearance_is_refused(self):
        row = classify_leftover(
            {
                "measured": True,
                "calibration_ok": True,
                "source_cards_present": True,
                "fable_sample_state": "HIT",
                "owner_ruling_state": "OWNER_EVIDENCE",
                "retract_present": True,
                "slack_census_state": "CLEAR",
            }
        )
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("CZ-03", row["note"])

    def test_integrated_retract_does_not_remint(self):
        row = classify_leftover(
            {
                "measured": True,
                "calibration_ok": True,
                "source_cards_present": True,
                "fable_sample_state": "HIT",
                "owner_ruling_state": "OWNER_EVIDENCE",
                "retract_present": True,
                "slack_census_state": "FINDER-UNVERIFIED",
            }
        )
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertIn("Did not remint", row["note"])

    def test_measure_root_on_this_tree(self):
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(sorted(row["calibration_hits"]), sorted(CALIBRATION))
        self.assertTrue(row["source_cards_present"])
        self.assertTrue(row["spy_measure_present"])
        self.assertEqual(row["fable_sample_state"], "HIT")
        self.assertEqual(row["owner_ruling_state"], "OWNER_EVIDENCE")
        self.assertEqual(row["slack_census_state"], "FINDER-UNVERIFIED")
        self.assertTrue(row["retract_present"])
        self.assertEqual(classify_leftover(row)["state"], "INTEGRATED")
        self.assertIn(PEER_CHECK, row["do_not_remint"])
        self.assertIn(SPY_MEASURE, row["do_not_remint"])
        self.assertIn(OWNER_RULING, row["do_not_remint"])
        for rel in (PEER_CHECK, COMPUTE_CARD, PARK_CARD, SPY_MEASURE, OWNER_RULING, RETRACT):
            self.assertIn(rel, SEARCH_SPACE)

    def test_cli_self_test_and_json(self):
        instrument = os.path.join(ROOT, "host", "claude_a10_standing.py")
        self_test = subprocess.run(
            [sys.executable, instrument, "--self-test"],
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(self_test.returncode, 0)
        shown = subprocess.run(
            [sys.executable, instrument, "--root", ROOT],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(shown.returncode, 0)
        payload = json.loads(shown.stdout)
        self.assertEqual(payload["state"], "INTEGRATED")
        self.assertEqual(payload["y"]["fable_sample_state"], "HIT")
        self.assertEqual(payload["z"]["slack_census_state"], "FINDER-UNVERIFIED")

    def test_missing_retract_tree_is_not_landed(self):
        with tempfile.TemporaryDirectory() as tmp:
            for rel in (
                PEER_CHECK,
                COMPUTE_CARD,
                PARK_CARD,
                os.path.join("ground", "HEAD.md"),
                SPY_MEASURE,
                OWNER_RULING,
            ):
                dest = os.path.join(tmp, rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                src = os.path.join(ROOT, rel)
                with open(src, encoding="utf-8") as handle:
                    body = handle.read()
                with open(dest, "w", encoding="utf-8") as handle:
                    handle.write(body)
            os.makedirs(os.path.join(tmp, "host"), exist_ok=True)
            with open(os.path.join(ROOT, "host", "claude_a10_standing.py"), encoding="utf-8") as handle:
                body = handle.read()
            with open(os.path.join(tmp, "host", "claude_a10_standing.py"), "w", encoding="utf-8") as handle:
                handle.write(body)
            row = measure_root(tmp)
            self.assertTrue(row["calibration_ok"])
            self.assertFalse(row["retract_present"])
            self.assertEqual(classify_leftover(row)["state"], "NOT_LANDED")


if __name__ == "__main__":
    unittest.main()
