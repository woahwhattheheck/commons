#!/usr/bin/env python3
"""Branch-review leftover keeps RETRACTED families and coordinates public branches."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from branch_review import (
    ALLOWED_FAMILY_STATUS,
    CALIBRATION,
    REQUIRED_BRANCHES,
    REQUIRED_FAMILIES,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    SOURCE_ID,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
)


def _families():
    return [
        {
            "id": family_id,
            "status": "RETRACTED",
            "x": "named search space",
            "y": "bytes-derived retraction",
            "z": "FINDER-UNVERIFIED",
        }
        for family_id in REQUIRED_FAMILIES
    ]


def _branches():
    rows = []
    for name in REQUIRED_BRANCHES:
        row = {
            "name": name,
            "status": "UNSCANNED",
            "delete_rewrite": "OWNER_HOLD",
            "origin_head": "PRESENT" if name == "sd-wx" else "ABSENT",
        }
        if name == "sd-wx":
            row["tree_files"] = 3241
            row["claimed_258"] = "NOT_CURRENT_TREE"
        rows.append(row)
    return rows


def _complete_facts(**overrides):
    facts = {
        "card_present": True,
        "catalog_present": True,
        "found_phrases": list(REQUIRED_PHRASES),
        "families": _families(),
        "branches": _branches(),
        "packet_present": True,
        "pfc_census_present": True,
        "clearance_retracted": True,
        "retracted_stays_retracted": True,
        "soften_retracted_to_unverified": False,
        "secret_dump": False,
        "delete_rewrite": "OWNER_HOLD",
        "remeasurement_owner": "Cursor / Grok",
        "allowed_remeasurers": [
            "deterministic local checks",
            "GitHub Actions",
            "Codex",
            "Cursor / Grok",
        ],
        "xyz_required": True,
        "calibration_ok": True,
        "calibration_hits": list(CALIBRATION),
    }
    facts.update(overrides)
    return facts


class TestBranchReview(unittest.TestCase):
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
                "misses": ["ground/BRANCH_REVIEW.md"],
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-UNVERIFIED")

    def test_softened_retracted_is_not_landed(self):
        facts = _complete_facts()
        facts["families"][0]["status"] = "UNVERIFIED"
        verdict = classify(measure_from_rows(facts))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-UNVERIFIED")
        self.assertIn("RETRACTED", verdict["note"])

    def test_soften_flag_is_not_landed(self):
        verdict = classify(
            measure_from_rows(_complete_facts(soften_retracted_to_unverified=True))
        )
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("UNVERIFIED", verdict["note"])

    def test_clean_branch_is_forbidden(self):
        facts = _complete_facts()
        facts["branches"][0]["status"] = "CLEAN"
        verdict = classify(measure_from_rows(facts))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("CLEAN/0", verdict["note"])

    def test_zero_family_status_is_forbidden(self):
        facts = _complete_facts()
        facts["families"][0]["status"] = "0"
        verdict = classify(measure_from_rows(facts))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-UNVERIFIED")

    def test_258_as_current_tree_is_not_landed(self):
        facts = _complete_facts()
        facts["branches"][0]["claimed_258"] = "CURRENT_TREE"
        verdict = classify(measure_from_rows(facts))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("258", verdict["note"])

    def test_complete_leftover_is_integrated(self):
        verdict = classify(measure_from_rows(_complete_facts()))
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_live_tree_matches_the_report(self):
        catalog_path = os.path.join(ROOT, "ground", "BRANCH_REVIEW.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["source_id"], SOURCE_ID)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertTrue(catalog["retracted_stays_retracted"])
        self.assertFalse(catalog["soften_retracted_to_unverified"])
        self.assertEqual(catalog["delete_rewrite"], "OWNER_HOLD")
        self.assertFalse(catalog["secret_dump"])
        self.assertEqual(catalog["remeasurement_owner"], "Cursor / Grok")
        self.assertGreaterEqual(len(catalog["allowed_remeasurers"]), 4)
        self.assertEqual(
            [item["id"] for item in catalog["families"]], list(REQUIRED_FAMILIES)
        )
        self.assertTrue(
            all(item["status"] in ALLOWED_FAMILY_STATUS for item in catalog["families"])
        )
        self.assertEqual(len(catalog["families"]), 10)
        self.assertEqual(
            [item["name"] for item in catalog["branches"]], list(REQUIRED_BRANCHES)
        )
        self.assertTrue(
            all(item["status"] == "UNSCANNED" for item in catalog["branches"])
        )
        sd_wx = catalog["branches"][0]
        self.assertEqual(sd_wx["origin_head"], "PRESENT")
        self.assertEqual(sd_wx["tree_files"], 3241)
        self.assertEqual(sd_wx["claimed_258"], "NOT_CURRENT_TREE")
        self.assertEqual(catalog["pfc_census"]["clearance_sentence"], "RETRACTED")
        row = measure_root(ROOT)
        self.assertTrue(
            row["calibration_ok"],
            "known-present calibration must hit HEAD + EXECUTE",
        )
        self.assertEqual(sorted(row["calibration_hits"]), sorted(CALIBRATION))
        self.assertEqual(row["search_space"], list(SEARCH_SPACE))
        self.assertTrue(row["packet_present"])
        self.assertTrue(row["pfc_census_present"])
        self.assertTrue(row["clearance_retracted"])
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertIn("branch_review", row["found_phrases"])
        self.assertIn("do not soften retracted", row["found_phrases"])


if __name__ == "__main__":
    unittest.main()
