from __future__ import annotations

import copy
import unittest

from revenue.commercial_lifecycle_ledger.lifecycle import LedgerError, compile_ledger
from revenue.commercial_lifecycle_ledger.test_lifecycle import full_payload


class LateDuplicateIdempotencyTests(unittest.TestCase):
    ASOF = "2026-09-13T11:00:00Z"

    def test_delayed_retry_of_first_event_is_collapsed(self) -> None:
        baseline_payload = full_payload()
        baseline = compile_ledger(baseline_payload, trusted_as_of=self.ASOF)

        retried = full_payload()
        retried["events"].append(copy.deepcopy(retried["events"][0]))
        receipt = compile_ledger(retried, trusted_as_of=self.ASOF)

        self.assertEqual(receipt["state"], baseline["state"])
        self.assertEqual(receipt["unique_event_count"], baseline["unique_event_count"])
        self.assertEqual(receipt["input_event_count"], baseline["input_event_count"] + 1)
        self.assertEqual(receipt["normalized_input_sha256"], baseline["normalized_input_sha256"])
        self.assertEqual(receipt["event_chain_head_sha256"], baseline["event_chain_head_sha256"])
        self.assertEqual(receipt["net_cash_evidenced_minor"], baseline["net_cash_evidenced_minor"])
        self.assertEqual(
            receipt["net_recognized_evidenced_minor"],
            baseline["net_recognized_evidenced_minor"],
        )

    def test_delayed_retry_of_payment_after_recognition_is_collapsed(self) -> None:
        baseline_payload = full_payload()
        baseline = compile_ledger(baseline_payload, trusted_as_of=self.ASOF)

        retried = full_payload()
        # e08 PAYMENT_SETTLED occurs at 10:07; the retry arrives after the 10:08
        # REVENUE_RECOGNIZED event. Input arrival order must not invalidate an
        # exact idempotent retry of already accepted evidence.
        retried["events"].append(copy.deepcopy(retried["events"][7]))
        receipt = compile_ledger(retried, trusted_as_of=self.ASOF)

        self.assertEqual(receipt["settled_amount_minor"], 250000)
        self.assertEqual(receipt["reported_recognized_amount_minor"], 250000)
        self.assertEqual(receipt["unique_event_count"], 9)
        self.assertEqual(receipt["input_event_count"], 10)
        self.assertEqual(receipt["normalized_input_sha256"], baseline["normalized_input_sha256"])
        self.assertEqual(receipt["event_chain_head_sha256"], baseline["event_chain_head_sha256"])

    def test_conflicting_late_reuse_still_fails_closed(self) -> None:
        payload = full_payload()
        conflicting = copy.deepcopy(payload["events"][0])
        conflicting["evidence_sha256"] = "f" * 64
        payload["events"].append(conflicting)

        with self.assertRaisesRegex(LedgerError, "conflicting duplicate event_id: e01"):
            compile_ledger(payload, trusted_as_of=self.ASOF)

    def test_first_seen_unique_event_must_still_be_chronological(self) -> None:
        payload = full_payload()
        late_unique = copy.deepcopy(payload["events"][0])
        late_unique["event_id"] = "e10"
        late_unique["evidence_sha256"] = "a" * 64
        payload["events"].append(late_unique)

        with self.assertRaisesRegex(LedgerError, "events must be nondecreasing by occurred_at"):
            compile_ledger(payload, trusted_as_of=self.ASOF)


if __name__ == "__main__":
    unittest.main()
