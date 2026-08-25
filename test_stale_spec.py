#!/usr/bin/env python3
"""Stale-spec leftover is a measurement, not a remint."""

from __future__ import annotations

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from stale_spec import classify, load_catalog, measure_from_parts, measure_paths


class TestStaleSpec(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not measured", row["note"])

    def test_missing_historical_input_is_not_landed(self):
        catalog = json.dumps(
            {
                "current_authority": [
                    {"slack_ts": "1787628542.573719"},
                    {"slack_ts": "1787628900.201179"},
                    {"slack_ts": "1787629309.162109"},
                ],
                "still_refused": ["smash/wipe of commons.mno"],
            }
        )
        measured = measure_from_parts(
            catalog,
            "",
            "Smash/wipe of `commons.mno` is refused. first-class",
        )
        self.assertFalse(measured["historical_present"])
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_missing_owner_slack_is_not_landed(self):
        catalog = json.dumps(
            {
                "historical_input": {
                    "path": "muhl/lda-docs/SESSION_GROUNDING.md"
                },
                "current_authority": [{"slack_ts": "1787628542.573719"}],
                "still_refused": ["smash/wipe of commons.mno"],
            }
        )
        measured = measure_from_parts(
            catalog,
            "# SESSION GROUNDING\nHost = inject\n",
            "Smash/wipe of `commons.mno` is refused. first-class",
        )
        self.assertFalse(measured["current_slack_complete"])
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")
        self.assertIn("1787629309.162109", classify(measured)["note"])

    def test_missing_smash_refusal_is_not_landed(self):
        catalog = json.dumps(
            {
                "historical_input": {
                    "path": "muhl/lda-docs/SESSION_GROUNDING.md"
                },
                "current_authority": [
                    {"slack_ts": "1787628542.573719"},
                    {"slack_ts": "1787628900.201179"},
                    {"slack_ts": "1787629309.162109"},
                ],
                "still_refused": [],
            }
        )
        measured = measure_from_parts(
            catalog,
            "# SESSION GROUNDING\nHost = inject\n",
            "Smash/wipe of `commons.mno` is refused. first-class",
        )
        self.assertFalse(measured["smash_refused"])
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("destructive mutation", verdict["note"])

    def test_reconciled_catalog_is_integrated(self):
        catalog = json.dumps(
            {
                "historical_input": {
                    "path": "muhl/lda-docs/SESSION_GROUNDING.md",
                    "role": "historical/session-bound specification input",
                    "not": "standing never-touch / blanket non-actuation rule",
                },
                "current_authority": [
                    {"slack_ts": "1787628542.573719"},
                    {"slack_ts": "1787628900.201179"},
                    {"slack_ts": "1787629309.162109"},
                    {"path": "ground/HEAD.md"},
                ],
                "still_refused": ["smash/wipe of commons.mno"],
                "titan": "NOT_WRITTEN",
            }
        )
        measured = measure_from_parts(
            catalog,
            "# SESSION GROUNDING\nHost = inject\n",
            "Smash/wipe of `commons.mno` is refused. Substrate work is first-class.",
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("historical input", verdict["note"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")

    def test_live_catalog_names_the_errata(self):
        path = os.path.join(ROOT, "ground", "STALE_SPEC.json")
        row = measure_paths(
            path,
            os.path.join(ROOT, "muhl", "lda-docs", "SESSION_GROUNDING.md"),
            os.path.join(ROOT, "ground", "HEAD.md"),
        )
        self.assertTrue(row["measured"], row.get("error"))
        self.assertTrue(row["historical_present"])
        self.assertTrue(row["current_slack_complete"])
        self.assertTrue(row["head_current"])
        self.assertTrue(row["smash_refused"])
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        with open(path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], "1787635067.695619")
        self.assertIn("muhl/lda-docs/SESSION_GROUNDING.md", catalog["historical_path"])
        self.assertEqual(classify(row)["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
