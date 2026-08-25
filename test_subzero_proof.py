#!/usr/bin/env python3
"""Subzero Explorer v2 leftover classifies proofs and refuses promotions."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from subzero_proof import (
    ALREADY_LANDED,
    CALIBRATION,
    EXPECTED_EXCERPTS,
    HEAVY_STATE,
    JOB,
    ORDER,
    REQUIRED_BINDINGS,
    REQUIRED_PHRASES,
    RUNNER,
    SEARCH_SPACE,
    SLACK_TS,
    STEP,
    V1_PIN,
    classify,
    classify_claim,
    count_or_unresolved,
    load_catalog,
    measure_from_rows,
    measure_root,
    self_test,
    strict_bool,
)


def _bound(**extra):
    row = {
        "job": JOB,
        "step": STEP,
        "order": ORDER,
        "sha": V1_PIN,
        "runner": RUNNER,
        "receipt": "pending-this-leftover",
    }
    row.update(extra)
    return row


def _complete(**extra):
    row = {
        "card_present": True,
        "catalog_present": True,
        "door_present": True,
        "v1_present": True,
        "landed_present": list(ALREADY_LANDED),
        "landed_missing": [],
        "found_phrases": list(REQUIRED_PHRASES),
        "excerpt_count": EXPECTED_EXCERPTS,
        "structural_count": EXPECTED_EXCERPTS,
        "unresolved_claims": [],
        "promoted": False,
        "bools_ok": True,
        "bindings_ok": True,
        "heavy_audits": HEAVY_STATE,
        "titan_in_verdict": False,
        "posting_open": True,
        "no_auth": True,
        "no_gate": True,
        "calibration_ok": True,
        "titan": "NOT_WRITTEN",
    }
    row.update(extra)
    return measure_from_rows(row)


class TestSubzeroProof(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])
        self.assertEqual(row["z"], "FINDER-FAILED")

    def test_failed_calibration_is_instrument_failure(self):
        verdict = classify(
            {
                "measured": True,
                "calibration_ok": False,
                "calibration_hits": [],
                "card_present": True,
                "catalog_present": True,
                "door_present": True,
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
                "door_present": False,
                "misses": ["ground/SUBZERO_PROOF.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_missing_binding_is_unresolved_never_zero(self):
        verdict = classify_claim({"class": "STRUCTURAL_ONLY", "hash_match": True})
        self.assertEqual(verdict["state"], "UNRESOLVED")
        self.assertEqual(set(verdict["missing_bindings"]), set(REQUIRED_BINDINGS))
        self.assertIn("never 0", verdict["note"].lower())
        self.assertEqual(count_or_unresolved([], False), "UNRESOLVED")
        self.assertEqual(count_or_unresolved([], True), "UNRESOLVED")

    def test_promotion_to_runtime_is_not_landed(self):
        sold = classify_claim(
            _bound(
                **{
                    "class": "RUNTIME_MEASURED",
                    "measured_class": "STRUCTURAL_ONLY",
                    "hash_match": True,
                }
            )
        )
        self.assertEqual(sold["state"], "NOT_LANDED")
        self.assertIn("refused promotion", sold["note"])

    def test_promotion_to_customer_ready_is_not_landed(self):
        sold = classify_claim(
            _bound(
                **{
                    "class": "CUSTOMER_READY",
                    "measured_class": "STRUCTURAL_ONLY",
                    "hash_match": True,
                }
            )
        )
        self.assertEqual(sold["state"], "NOT_LANDED")
        self.assertIn("CUSTOMER_READY", sold["note"])

    def test_string_boolean_is_not_landed(self):
        catalog = load_catalog('{"no_auth": "true", "no_gate": true, "posting_open": true, "runtime_measured": false, "copy_private_lda": false, "titan_in_verdict": false}')
        self.assertEqual(strict_bool({"no_auth": "true"}, "no_auth"), "NOT_BOOL")
        self.assertEqual(strict_bool({}, "no_auth"), "UNRESOLVED")
        self.assertEqual(catalog["no_auth"], "NOT_BOOL")
        self.assertIs(catalog["no_gate"], True)

    def test_titan_status_does_not_decide(self):
        measured = _complete(titan="WRITTEN")
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("Titan status does not decide", verdict["note"])
        blocked = classify(_complete(titan_in_verdict=True, titan="WRITTEN"))
        self.assertEqual(blocked["state"], "NOT_LANDED")
        self.assertIn("titan status must not decide", blocked["note"])

    def test_heavy_synthesis_is_not_landed(self):
        verdict = classify(_complete(heavy_audits="SYNTHESIZED"))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("does not synthesize", verdict["note"])

    def test_complete_leftover_is_integrated(self):
        verdict = classify(_complete())
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_self_test_ok(self):
        self.assertEqual(self_test(), "ok")

    def test_live_tree_has_the_leftover(self):
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(row["landed_missing"], [])
        self.assertEqual(row["excerpt_count"], EXPECTED_EXCERPTS)
        self.assertEqual(row["structural_count"], EXPECTED_EXCERPTS)
        self.assertEqual(row["unresolved_claims"], [])
        self.assertFalse(row["promoted"])
        self.assertTrue(row["bools_ok"])
        self.assertTrue(row["bindings_ok"])
        self.assertEqual(row["heavy_audits"], HEAVY_STATE)
        self.assertIs(row["titan_in_verdict"], False)
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(SLACK_TS, "1787648254.904309")
        self.assertEqual(len(CALIBRATION), 3)
        self.assertGreaterEqual(len(SEARCH_SPACE), 8)
        with open(os.path.join(ROOT, "ground", "SUBZERO_PROOF.json"), encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["label"], "STRUCTURAL_ONLY")
        self.assertEqual(catalog["sha"], V1_PIN)
        self.assertEqual(catalog["job"], JOB)
        self.assertEqual(catalog["heavy_audits"], HEAVY_STATE)
        self.assertIs(catalog["no_auth"], True)
        self.assertIs(catalog["titan_in_verdict"], False)
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        bound = classify_claim(
            _bound(**{"class": "STRUCTURAL_ONLY", "hash_match": True})
        )
        self.assertEqual(bound["state"], "STRUCTURAL_ONLY")


if __name__ == "__main__":
    unittest.main()
