import copy
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from reconcile import reconcile  # noqa: E402
from test_reconcile import H, synthetic_payload  # noqa: E402


class CommittedDisbursementFenceTests(unittest.TestCase):
    def _first_award(self, payload):
        return payload["awards"][0]

    def _result_award(self, result):
        return next(a for a in result["awards"] if a["award_id"] == "SYNTH-AWARD-01")

    def _append_pending(self, award, amount):
        award["disbursements"].append(
            {
                "event_id": "disb-01-pending-extra",
                "amount_cents": amount,
                "status": "pending",
                "evidence_sha256": H,
            }
        )

    def test_fully_paid_award_with_pending_duplicate_holds(self):
        payload = synthetic_payload()
        award = self._first_award(payload)
        self._append_pending(award, 1)

        result = reconcile(payload)
        result_award = self._result_award(result)

        self.assertEqual(result_award["paid_cents"], result_award["award_cents"])
        self.assertEqual(result_award["pending_cents"], 1)
        self.assertIn("COMMITTED_DISBURSEMENT_EXCEEDS_AWARD", result_award["holds"])
        self.assertIn("COMMITTED_DISBURSEMENT_EXCEEDS_AWARD", result["summary"]["holds"])
        self.assertNotIn("AWARD_NOT_FULLY_DISBURSED", result_award["holds"])

    def test_partial_paid_plus_pending_over_award_holds(self):
        payload = synthetic_payload()
        award = self._first_award(payload)
        award["disbursements"][0]["amount_cents"] -= 100
        self._append_pending(award, 101)

        result_award = self._result_award(reconcile(payload))

        self.assertEqual(result_award["paid_cents"] + result_award["pending_cents"], result_award["award_cents"] + 1)
        self.assertIn("COMMITTED_DISBURSEMENT_EXCEEDS_AWARD", result_award["holds"])
        self.assertIn("AWARD_NOT_FULLY_DISBURSED", result_award["holds"])
        self.assertNotIn("DISBURSEMENT_EXCEEDS_AWARD", result_award["holds"])

    def test_exact_committed_boundary_passes_when_full_payment_not_required(self):
        payload = synthetic_payload()
        payload["require_full_disbursement"] = False
        award = self._first_award(payload)
        award["disbursements"][0]["amount_cents"] -= 100
        self._append_pending(award, 100)

        result = reconcile(payload)
        result_award = self._result_award(result)

        self.assertEqual(result_award["paid_cents"] + result_award["pending_cents"], result_award["award_cents"])
        self.assertNotIn("COMMITTED_DISBURSEMENT_EXCEEDS_AWARD", result_award["holds"])
        self.assertEqual(result_award["status"], "PASS")
        self.assertEqual(result["summary"]["status"], "PASS")

    def test_exact_committed_boundary_preserves_full_disbursement_rule(self):
        payload = synthetic_payload()
        award = self._first_award(payload)
        award["disbursements"][0]["amount_cents"] -= 100
        self._append_pending(award, 100)

        result_award = self._result_award(reconcile(payload))

        self.assertNotIn("COMMITTED_DISBURSEMENT_EXCEEDS_AWARD", result_award["holds"])
        self.assertIn("AWARD_NOT_FULLY_DISBURSED", result_award["holds"])

    def test_paid_only_overage_keeps_existing_hold_without_new_pending_hold(self):
        payload = synthetic_payload()
        award = self._first_award(payload)
        award["disbursements"][0]["amount_cents"] += 1

        result_award = self._result_award(reconcile(payload))

        self.assertIn("DISBURSEMENT_EXCEEDS_AWARD", result_award["holds"])
        self.assertNotIn("COMMITTED_DISBURSEMENT_EXCEEDS_AWARD", result_award["holds"])


if __name__ == "__main__":
    unittest.main()
