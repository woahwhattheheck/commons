#!/usr/bin/env python3
"""LDA receipt leftover validates protocol receipts and never remints JOJO."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from lda_receipt import (
    CALIBRATION,
    EXPECTED_FIXTURES,
    JOJO_PROTOCOL_ID,
    PROTOCOL_MAIN,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    TAKING_ID,
    classify,
    load_json,
    measure_from_rows,
    measure_root,
    validate_receipt,
)


class TestLdaReceipt(unittest.TestCase):
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
                "misses": ["ground/LDA_RECEIPT.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_empty_receipt_is_unmeasured(self):
        self.assertEqual(validate_receipt({})["state"], "UNMEASURED")
        self.assertEqual(validate_receipt(None)["state"], "UNMEASURED")

    def test_talk_kind_is_not_landed(self):
        verdict = validate_receipt({"kind": "PROFITABILITY_HANDOFF"})
        self.assertEqual(verdict["state"], "NOT_LANDED")

    def test_host_inference_is_refused(self):
        path = os.path.join(ROOT, "ground", "lda_receipt", "invalid-host-inference.json")
        with open(path, encoding="utf-8") as handle:
            data = load_json(handle.read())
        self.assertEqual(validate_receipt(data, root=ROOT)["state"], "NOT_LANDED")

    def test_wrong_sha_is_refused(self):
        path = os.path.join(ROOT, "ground", "lda_receipt", "invalid-wrong-sha.json")
        with open(path, encoding="utf-8") as handle:
            data = load_json(handle.read())
        self.assertEqual(validate_receipt(data, root=ROOT)["state"], "NOT_LANDED")

    def test_missing_fields_are_refused(self):
        path = os.path.join(ROOT, "ground", "lda_receipt", "invalid-missing-fields.json")
        with open(path, encoding="utf-8") as handle:
            data = load_json(handle.read())
        self.assertEqual(validate_receipt(data, root=ROOT)["state"], "NOT_LANDED")

    def test_jojo_taking_stays_carrier_only(self):
        path = os.path.join(ROOT, "ground", "lda_receipt", "jojo-taking.json")
        with open(path, encoding="utf-8") as handle:
            data = load_json(handle.read())
        verdict = validate_receipt(data, root=ROOT)
        self.assertEqual(verdict["state"], "CARRIER_ONLY")
        self.assertIn(JOJO_PROTOCOL_ID, verdict["note"])

    def test_schema_valid_fixture_cites_known_present_post(self):
        path = os.path.join(ROOT, "ground", "lda_receipt", "valid-complete.json")
        with open(path, encoding="utf-8") as handle:
            data = load_json(handle.read())
        verdict = validate_receipt(data, root=ROOT)
        self.assertEqual(verdict["state"], "VALID_RECEIPT")
        self.assertEqual(data["protocol_main"], PROTOCOL_MAIN)

    def test_durable_claim_without_file_is_not_landed(self):
        verdict = validate_receipt(
            {
                "kind": "LDA_REQUEST_RECEIPT",
                "protocol_main": PROTOCOL_MAIN,
                "request_id": "missing-post-fixture-20260825-01",
                "receiver": "must refuse a missing Commons file",
                "result_state": "RESULT_ABSENT",
                "foreign_state": "FINDER-UNVERIFIED",
                "commons_state": "DURABLE_ON_MAIN",
                "commons_post_id": "this-id-is-not-a-file-20260825-01",
                "host_inference": False,
                "copied_source": False,
                "titan": "NOT_WRITTEN",
                "no_auth": True,
                "no_gate": True,
            },
            root=ROOT,
        )
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("missing", verdict["note"])

    def test_blob_mismatch_is_not_landed(self):
        verdict = validate_receipt(
            {
                "kind": "LDA_REQUEST_RECEIPT",
                "protocol_main": PROTOCOL_MAIN,
                "request_id": "blob-mismatch-fixture-20260825-01",
                "receiver": "must refuse a mismatched blob",
                "result_state": "RESULT_ABSENT",
                "foreign_state": "FOREIGN_INTEGRATED",
                "commons_state": "CARRIER_ONLY",
                "host_inference": False,
                "copied_source": False,
                "titan": "NOT_WRITTEN",
                "no_auth": True,
                "no_gate": True,
                "blobs": [
                    {
                        "path": "host/muhl_subagent_protocol.py",
                        "claimed": "f4a58a0e5241eff482a58cfadc112914237944f4",
                        "measured": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    }
                ],
            }
        )
        self.assertEqual(verdict["state"], "NOT_LANDED")

    def test_live_tree_is_integrated(self):
        row = measure_root(ROOT)
        verdict = classify(row)
        self.assertEqual(verdict["state"], "INTEGRATED", verdict)
        self.assertEqual(row["slack_ts"], SLACK_TS)
        self.assertEqual(TAKING_ID, "jojo-model-work-profitability-bridge-20260825-02")
        self.assertFalse(row["jojo_protocol_reminted"])
        self.assertTrue(row["foreign_present"])
        self.assertEqual(len(row["fixture_hits"]), len(EXPECTED_FIXTURES))
        self.assertEqual(row["fixture_misses"], [])
        for phrase in REQUIRED_PHRASES:
            self.assertIn(phrase, row["found_phrases"])
        for rel in CALIBRATION:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)
        for rel in SEARCH_SPACE:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)
        self.assertFalse(
            os.path.isfile(os.path.join(ROOT, "p", JOJO_PROTOCOL_ID + ".md"))
        )


if __name__ == "__main__":
    unittest.main()
