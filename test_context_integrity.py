#!/usr/bin/env python3
"""Context-integrity leftover never prints a silent 0."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from context_integrity import (
    CALIBRATION_PATH,
    FINDER_FAILED,
    REQUIRED_ROWS,
    SLACK_TS,
    SOURCE_ID,
    calibrate,
    classify,
    classify_text,
    load_catalog,
    measure_from_rows,
    measure_tree,
    predicted_defect_state,
    probe,
    report_find,
    retract_characterization,
    row_complete,
    search_space,
    uncertainty_labels,
)


class TestContextIntegrity(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_search_space_must_be_named(self):
        incomplete = search_space(query="")
        self.assertFalse(incomplete["complete"])
        self.assertIn("query", incomplete["missing"])
        complete = search_space(
            query="CONTEXT INTEGRITY",
            path="host/context_integrity.py",
            ref=SLACK_TS,
        )
        self.assertTrue(complete["complete"])

    def test_missed_known_present_voids_zeros(self):
        missed = calibrate([], ["ground/HEAD.md"])
        self.assertFalse(missed["calibrated"])
        self.assertEqual(missed["state"], FINDER_FAILED)
        ok = calibrate(["ground/HEAD.md"], ["ground/HEAD.md"])
        self.assertTrue(ok["calibrated"])

    def test_miss_branch_never_prints_zero(self):
        space = search_space(
            query="CONTEXT INTEGRITY",
            path="host/context_integrity.py",
            ref=SLACK_TS,
        )
        silent = report_find([], space, True)
        self.assertEqual(silent["state"], FINDER_FAILED)
        self.assertIsNone(silent["count"])
        self.assertNotEqual(silent["count"], 0)
        found = report_find(["hit"], space, True)
        self.assertEqual(found["state"], "FOUND")
        self.assertEqual(found["count"], 1)

    def test_characterization_is_not_a_measurement(self):
        row = classify_text(
            "those false zeros are unflattering truths about the owner's intellect"
        )
        self.assertEqual(row["state"], "OWNER_CHARACTERIZATION")
        technical = classify_text(
            "finder missed Z. FINDER-FAILED search space host/finder_zero.py calibration labeled"
        )
        self.assertEqual(technical["state"], "TECHNICAL_DISAGREEMENT")

    def test_uncertainty_must_name_five_labels(self):
        unlabeled = uncertainty_labels({"instrument": "host/context_integrity.py"})
        self.assertEqual(unlabeled["state"], "UNLABELED_DOUBT")
        labeled = uncertainty_labels(
            {
                "instrument": "host/context_integrity.py",
                "path": "host/context_integrity.py",
                "query": "CONTEXT INTEGRITY",
                "ref": SLACK_TS,
                "calibration": CALIBRATION_PATH,
            }
        )
        self.assertEqual(labeled["state"], "LABELED")

    def test_predicted_defect_is_investigated_first(self):
        honored = predicted_defect_state(True, True)
        self.assertEqual(honored["state"], "HONORED")
        skipped = predicted_defect_state(True, False)
        self.assertEqual(skipped["state"], "OVERRIDE_UNINVESTIGATED")
        none = predicted_defect_state(False, False)
        self.assertEqual(none["state"], "NOT_PREDICTED")

    def test_characterization_needs_a_correction(self):
        open_row = retract_characterization(
            "unflattering truths about the owner's motives",
            "",
        )
        self.assertEqual(open_row["state"], "OPEN_CHARACTERIZATION")
        closed = retract_characterization(
            "unflattering truths about the owner's motives",
            "p/cairn-every-zero-i-printed-was-mine-20260820-06.md",
        )
        self.assertEqual(closed["state"], "RETRACTED")

    def test_row_requires_xyz_and_correction(self):
        incomplete = row_complete({"id": "x"})
        self.assertFalse(incomplete["complete"])
        complete = row_complete(
            {
                "id": "characterization_retract",
                "kind": "characterization_retract",
                "x": "path",
                "y": FINDER_FAILED,
                "z": FINDER_FAILED,
                "correction": "retract",
                "source_id": SOURCE_ID,
            }
        )
        self.assertTrue(complete["complete"])

    def test_probe_never_prints_zero(self):
        missing = probe(ROOT, "this-path-is-not-a-file-on-purpose.md")
        self.assertEqual(missing["state"], FINDER_FAILED)
        self.assertIsNone(missing["count"])
        present = probe(ROOT, CALIBRATION_PATH)
        self.assertEqual(present["state"], "FOUND")
        self.assertGreater(present["bytes"], 0)
        self.assertIsNone(present["count"])

    def test_rule_is_integrated_when_four_rows_carry_xyz(self):
        measured = measure_from_rows(
            {
                "query": "CONTEXT INTEGRITY",
                "path": "host/context_integrity.py",
                "ref": SLACK_TS,
                "finder_hits": [FINDER_FAILED],
                "known_present": [FINDER_FAILED],
                "predicted": True,
                "investigated": True,
                "sample_text": (
                    "false zeros framed as unflattering truths. missing-Z "
                    "instrument search space."
                ),
                "correction": "p/cairn-every-zero-i-printed-was-mine-20260820-06.md",
                "uncertainty": {
                    "instrument": "host/context_integrity.py",
                    "path": "host/context_integrity.py",
                    "query": "CONTEXT INTEGRITY",
                    "ref": SLACK_TS,
                    "calibration": CALIBRATION_PATH,
                },
                "rows": [
                    {
                        "id": name,
                        "kind": name,
                        "source_id": SOURCE_ID,
                        "x": "path",
                        "y": FINDER_FAILED,
                        "z": FINDER_FAILED,
                        "correction": "retract to instrument",
                    }
                    for name in REQUIRED_ROWS
                ],
            }
        )
        self.assertTrue(measured["calibrated"])
        self.assertEqual(measured["complete_rows"], 4)
        self.assertFalse(measured["missing_rows"])
        self.assertTrue(measured["never_print_zero"])
        measured["instrument"] = True
        measured["card"] = True
        measured["catalog_file"] = True
        self.assertEqual(classify(measured)["state"], "INTEGRATED")
        self.assertIn("still not the file", classify(measured)["note"])
        zeroed = dict(measured)
        zeroed["bare_zero"] = True
        self.assertEqual(classify(zeroed)["state"], "NOT_LANDED")

    def test_live_tree_names_four_required_rows(self):
        catalog_path = os.path.join(ROOT, "ground", "CONTEXT_INTEGRITY.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog_text = handle.read()
        catalog = load_catalog(catalog_text)
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["source_id"], SOURCE_ID)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertEqual(len(catalog["rows"]), 4)
        row = measure_tree(ROOT, catalog_text)
        self.assertTrue(row["measured"])
        self.assertTrue(row["instrument"])
        self.assertTrue(row["card"])
        self.assertTrue(row["catalog_file"])
        self.assertEqual(row["complete_rows"], 4)
        self.assertFalse(row["missing_rows"])
        self.assertEqual(row["uncertainty_state"], "LABELED")
        self.assertEqual(row["predicted_state"], "HONORED")
        self.assertIn(row["retract_state"], {"RETRACTED", "NO_CHARACTERIZATION"})
        self.assertTrue(row["never_print_zero"])
        self.assertNotEqual(row.get("find_count"), 0)
        verdict = classify(row)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])
        cairn = probe(ROOT, "p/cairn-every-zero-i-printed-was-mine-20260820-06.md")
        self.assertEqual(cairn["state"], "FOUND")
        tester = probe(ROOT, os.path.join("ground", "CLAUDE_TESTER.md"))
        self.assertEqual(tester["state"], "FOUND")


if __name__ == "__main__":
    unittest.main()
