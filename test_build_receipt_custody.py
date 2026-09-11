#!/usr/bin/env python3
"""Cross-field custody regressions for commons-build-receipt/v1 hosted runs."""
from __future__ import annotations

import copy
import unittest

from host.build_receipt import ReceiptError, normalize_receipt

BASE = "a" * 40
HEAD = "b" * 40
MERGE = "c" * 40
OTHER = "d" * 40


def payload():
    return {
        "marker": "CUSTODY-TEST-20260910-01",
        "base": BASE,
        "head": HEAD,
        "paths": ["host/build_receipt.py"],
        "tests": [],
        "hosted": {
            "state": "SUCCESS",
            "runs": [
                {
                    "run_id": 101,
                    "event": "pull_request",
                    "run_head_sha": HEAD,
                    "executed_checkout_sha": MERGE,
                    "checkout_mode": "PR_MERGE_REF",
                }
            ],
        },
        "provider_nonclaims": [],
        "release_state": "HOLD",
    }


class BuildReceiptCustodyTests(unittest.TestCase):
    def test_pr_merge_ref_preserves_distinct_executed_checkout(self):
        got = normalize_receipt(payload())["hosted"]["runs"][0]
        self.assertEqual(got["run_head_sha"], HEAD)
        self.assertEqual(got["executed_checkout_sha"], MERGE)
        self.assertEqual(got["checkout_mode"], "PR_MERGE_REF")

    def test_foreign_run_head_cannot_certify_receipt_head(self):
        data = payload()
        data["hosted"]["runs"][0]["run_head_sha"] = OTHER
        with self.assertRaisesRegex(ReceiptError, "does not match receipt head"):
            normalize_receipt(data)

    def test_checkout_mode_must_match_event_class(self):
        cases = [
            ("push", "PR_MERGE_REF"),
            ("workflow_dispatch", "PR_HEAD_EXPLICIT"),
            ("pull_request", "PUSH_DISPATCH_SHA"),
            ("pull_request_target", "PR_MERGE_REF"),
        ]
        for event, mode in cases:
            with self.subTest(event=event, mode=mode):
                data = payload()
                row = data["hosted"]["runs"][0]
                row["event"] = event
                row["checkout_mode"] = mode
                row["executed_checkout_sha"] = None
                with self.assertRaises(ReceiptError):
                    normalize_receipt(data)

    def test_direct_sha_modes_reject_different_executed_checkout(self):
        cases = [
            ("pull_request", "PR_HEAD_EXPLICIT"),
            ("push", "PUSH_DISPATCH_SHA"),
        ]
        for event, mode in cases:
            with self.subTest(event=event, mode=mode):
                data = payload()
                row = data["hosted"]["runs"][0]
                row["event"] = event
                row["checkout_mode"] = mode
                row["executed_checkout_sha"] = OTHER
                with self.assertRaisesRegex(ReceiptError, "direct-SHA checkout"):
                    normalize_receipt(data)

    def test_queued_direct_head_can_keep_checkout_unknown(self):
        data = payload()
        data["hosted"]["state"] = "QUEUED"
        row = data["hosted"]["runs"][0]
        row["checkout_mode"] = "PR_HEAD_EXPLICIT"
        row["executed_checkout_sha"] = None
        got = normalize_receipt(copy.deepcopy(data))["hosted"]["runs"][0]
        self.assertEqual(got["run_head_sha"], HEAD)
        self.assertIsNone(got["executed_checkout_sha"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
