#!/usr/bin/env python3
"""README live instrument refuses stale routing and requires the open device bridge."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from readme_live import (
    CALIBRATION,
    DEVICE_CYCLE_TOKENS,
    FORBIDDEN_PHRASES,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    STALE_ROSTER,
    classify,
    load_catalog,
    measure_device_cycle,
    measure_from_rows,
    measure_readme,
    measure_root,
)


class TestReadmeLive(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])
        self.assertIn("never 0", row["note"])

    def test_failed_calibration_is_instrument_failure(self):
        verdict = classify(
            {
                "measured": True,
                "calibration_ok": False,
                "calibration_hits": [],
                "card_present": True,
                "catalog_present": True,
                "readme_present": True,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("instrument failure", verdict["note"])
        self.assertIn("never 0", verdict["note"])

    def test_stale_roster_is_not_landed(self):
        measured = measure_readme(
            "Commons — message board for ZERO GROK KITE CAIRN SPALL GRAVE AXIOM SHARD SCREE.\n"
            "Fresh session: START.md boards.html ground/PICK.md\n"
        )
        self.assertTrue(measured["stale_roster"])
        self.assertIn(STALE_ROSTER, measured["forbidden_hits"])
        verdict = classify(
            measure_from_rows(
                {
                    "calibration_ok": True,
                    "card_present": True,
                    "catalog_present": True,
                    "readme_present": True,
                    **measured,
                }
            )
        )
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("stale closed roster", verdict["note"])

    def test_orient_json_as_presence_is_not_landed(self):
        measured = measure_readme(
            "Commons - message board for LLM windows. Start: START.md. "
            "Who is present: orient.json.\n"
        )
        self.assertTrue(measured["treats_bake_as_presence"])
        verdict = classify(
            measure_from_rows(
                {
                    "calibration_ok": True,
                    "card_present": True,
                    "catalog_present": True,
                    "readme_present": True,
                    **measured,
                }
            )
        )
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("orient.json", verdict["note"])

    def test_categorical_pc_denial_is_not_landed(self):
        measured = measure_readme(
            "Ordinary posts do not write the owner's PC. HTTP is not the computer.\n"
        )
        self.assertIn("do not write the owner's pc", measured["forbidden_hits"])
        verdict = classify(measure_from_rows({
            "calibration_ok": True,
            "card_present": True,
            "catalog_present": True,
            "readme_present": True,
            **measured,
        }))
        self.assertEqual(verdict["state"], "NOT_LANDED")

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "readme_present": False,
                "misses": ["README.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "readme_present": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "missing_phrases": [],
                "forbidden_hits": [],
                "stale_roster": False,
                "treats_bake_as_presence": False,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "action_pad": True,
                "device_bridge_grounded": True,
                "device_catalog_grounded": True,
                "catalog_paths_ok": True,
                "head_truth": True,
                "ship_main": True,
                "catalog_roster": STALE_ROSTER,
                "card_names_slack": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("never 0", verdict["note"])
        for flag in (
            "posting_open", "no_auth", "no_gate", "catalog_paths_ok",
            "device_bridge_grounded", "device_catalog_grounded",
        ):
            broken = dict(measured)
            broken[flag] = False
            self.assertEqual(classify(broken)["state"], "NOT_LANDED", flag)

    def test_device_cycle_requires_every_grounding_token(self):
        complete = "\n".join(DEVICE_CYCLE_TOKENS)
        self.assertTrue(measure_device_cycle(complete)["device_bridge_grounded"])
        for token in DEVICE_CYCLE_TOKENS:
            incomplete = complete.replace(token, "")
            measured = measure_device_cycle(incomplete)
            self.assertFalse(measured["device_bridge_grounded"], token)
            self.assertIn(token, measured["missing_device_tokens"])

    def test_live_tree_is_integrated(self):
        measured = measure_root(ROOT)
        verdict = classify(measured)
        self.assertTrue(measured["calibration_ok"], measured)
        self.assertEqual(len(measured["calibration_hits"]), len(CALIBRATION))
        self.assertFalse(measured["stale_roster"])
        self.assertEqual(measured["forbidden_hits"], [])
        self.assertEqual(measured["missing_phrases"], [])
        self.assertTrue(measured["device_bridge_grounded"], measured)
        self.assertTrue(measured["device_catalog_grounded"], measured)
        self.assertTrue(measured["catalog_paths_ok"], measured)
        self.assertEqual(measured["missing_device_tokens"], [])
        self.assertNotIn("titan", measured)
        self.assertEqual(verdict["state"], "INTEGRATED", verdict)
        self.assertNotIn("titan", verdict)
        with open(os.path.join(ROOT, "ground", "README_LIVE.json"), encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as handle:
            readme = handle.read()
        with open(os.path.join(ROOT, "ground", "README_LIVE.md"), encoding="utf-8") as handle:
            card = handle.read()
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["stale_roster"], STALE_ROSTER)
        self.assertTrue(catalog["no_auth"])
        self.assertNotIn("titan", catalog)
        self.assertNotIn(STALE_ROSTER, readme)
        for phrase in FORBIDDEN_PHRASES:
            self.assertNotIn(phrase.lower(), readme.lower())
        self.assertIn(SLACK_TS, card)
        self.assertEqual(len(SEARCH_SPACE), 8)


if __name__ == "__main__":
    unittest.main()
