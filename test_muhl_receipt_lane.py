#!/usr/bin/env python3
"""Receipt-lane leftover validates request->receiver->result and refuses a silent 0."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from muhl_receipt_lane import (
    CALIBRATION,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
    request_hash,
    synthetic_receiver,
    synthetic_request,
    synthetic_result,
    tree_state,
    validate_chain,
    validate_receiver,
    validate_request,
    validate_result,
)


class TestMuhlReceiptLane(unittest.TestCase):
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
                "misses": ["ground/MUHL_RECEIPT_LANE.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_synthetic_chain_validates(self):
        request = synthetic_request()
        receiver = synthetic_receiver(request)
        result = synthetic_result(request)
        chain = validate_chain(request, receiver, result)
        self.assertTrue(chain["ok"], chain.get("blocked_reasons"))
        self.assertTrue(validate_request(request)["ok"])
        self.assertTrue(validate_receiver(receiver, request)["ok"])
        self.assertTrue(validate_result(result, request)["ok"])
        self.assertEqual(request["request_sha256"], request_hash(request))

    def test_unpublished_receiver_is_blocked(self):
        request = synthetic_request()
        row = validate_receiver(None, request)
        self.assertFalse(row["ok"])
        self.assertEqual(row["z"], "FINDER-FAILED")
        self.assertIn("receiver receipt unpublished", row["blocked_reasons"])

    def test_hash_mismatch_is_blocked(self):
        request = synthetic_request()
        receiver = synthetic_receiver(request)
        receiver["request_sha256"] = "0" * 64
        row = validate_receiver(receiver, request)
        self.assertFalse(row["ok"])
        self.assertIn("receiver request_sha256 mismatch", row["blocked_reasons"])

    def test_overlap_is_blocked(self):
        request = synthetic_request()
        request["result"] = {"name": "answer", "offset": 200, "len": 8}
        request.pop("request_sha256", None)
        request["request_sha256"] = request_hash(request)
        row = validate_request(request)
        self.assertFalse(row["ok"])
        self.assertTrue(
            any("overlap" in item for item in row["blocked_reasons"]),
            row["blocked_reasons"],
        )

    def test_auth_gate_is_blocked(self):
        request = synthetic_request()
        request["allowlist"] = ["nobody"]
        request.pop("request_sha256", None)
        request["request_sha256"] = request_hash(request)
        row = validate_request(request)
        self.assertFalse(row["ok"])
        self.assertIn("gate:allowlist", row["blocked_reasons"])

    def test_claimed_175_with_zero_published_is_finder_failed(self):
        row = tree_state(175, 0)
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertEqual(row["z"], "FINDER-FAILED")
        self.assertIn("never 0", row["note"].lower())
        self.assertEqual(row["published_count"], 0)
        self.assertEqual(row["claimed_count"], 175)

    def test_claimed_175_with_three_published_is_unverified_not_truncated(self):
        row = tree_state(175, 3)
        self.assertEqual(row["state"], "FINDER-UNVERIFIED")
        self.assertFalse(row["truncated"])
        self.assertEqual(row["published_count"], 3)
        self.assertEqual(row["claimed_count"], 175)

    def test_truncated_tree_is_not_landed(self):
        row = tree_state(175, 3, truncated=True)
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertTrue(row["truncated"])

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "chain_ok": True,
                "claimed_tree": 175,
                "published_tree": 3,
                "truncated": False,
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "leave_unmerged": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertEqual(verdict["taking_state"], "CLAIMED")
        self.assertIn("still not the file", verdict["note"])

    def test_copied_source_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "chain_ok": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "leave_unmerged": True,
                "copied_source": True,
                "calibration_ok": True,
                "claimed_tree": 175,
                "published_tree": 3,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_catalog_and_live_tree(self):
        parsed = load_catalog("{")
        self.assertEqual(parsed["error"], "catalog is not JSON")
        live = load_catalog(
            '{"slack_ts":"%s","claimed_tree":175,"published_tree":3,"leave_unmerged":true,"posting":"OPEN","no_auth":true,"no_gate":true}'
            % SLACK_TS
        )
        self.assertEqual(live["slack_ts"], SLACK_TS)
        self.assertEqual(live["claimed_tree"], 175)
        self.assertTrue(live["leave_unmerged"])
        row = measure_root(ROOT)
        verdict = classify(row)
        self.assertTrue(row["calibration_ok"], row.get("calibration_hits"))
        self.assertEqual(set(row["calibration_hits"]), set(CALIBRATION))
        self.assertEqual(row["slack_ts"], SLACK_TS)
        self.assertTrue(row["chain_ok"])
        self.assertEqual(row["claimed_tree"], 175)
        self.assertEqual(row["published_tree"], 3)
        self.assertFalse(row["truncated"])
        self.assertEqual(row["tree_state"], "FINDER-UNVERIFIED")
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertEqual(verdict["taking_state"], "CLAIMED")
        for rel in SEARCH_SPACE[:3]:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)


if __name__ == "__main__":
    unittest.main()
