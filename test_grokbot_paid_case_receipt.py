#!/usr/bin/env python3
"""Hermetic pin: opaque Autopsy seats receipt row binds G2 case without PII."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from integrations.grokbot_control.paid_case import (
    case_from_autopsy_offer,
    receipt_row_from_case,
)

ROOT = Path(__file__).resolve().parent
SEATS = ROOT / "revenue" / "agent_failure_autopsy" / "seats.json"

REQUIRED_SHAPE = ("offer_id", "case_ref", "sku", "state")
OPTIONAL_SHAPE = (
    "client_reference_id",
    "g2_run_id",
    "g2_session_id",
    "payment_observed_at",
)


class TestPaidCaseReceiptSurface(unittest.TestCase):
    def test_seats_documents_case_row_shape_and_stays_empty(self):
        seats = json.loads(SEATS.read_text(encoding="utf-8"))
        self.assertEqual(seats["case_rows"], [])
        self.assertEqual(seats["live_payment_state"]["board_mode"], "STANDBY_UNTIL_PAID")
        shape = seats["case_row_shape"]
        self.assertEqual(tuple(shape["required_keys"]), REQUIRED_SHAPE)
        self.assertEqual(tuple(shape["optional_keys"]), OPTIONAL_SHAPE)
        self.assertIn("receipt_row_from_case", shape["builder"])
        self.assertTrue(shape["do_not_commit_buyer_artifacts"])

    def test_receipt_row_from_case_round_trip(self):
        case = case_from_autopsy_offer(
            case_ref="opaque-case-7",
            client_reference_id="afa29_x_a_v1",
        )
        row = receipt_row_from_case(
            case,
            g2_run_id="run_abc",
            g2_session_id="sess_xyz",
            payment_observed_at="2026-09-05T22:00:00Z",
        )
        self.assertEqual(row["offer_id"], "agent-failure-autopsy-29")
        self.assertEqual(row["case_ref"], "opaque-case-7")
        self.assertEqual(row["sku"], "agent-failure-autopsy-29")
        self.assertEqual(row["client_reference_id"], "afa29_x_a_v1")
        self.assertEqual(row["g2_run_id"], "run_abc")
        self.assertEqual(row["g2_session_id"], "sess_xyz")
        self.assertEqual(row["payment_observed_at"], "2026-09-05T22:00:00Z")
        self.assertEqual(row["state"], "PAYMENT_OBSERVED_STANDBY_INTAKE")
        for forbidden in ("email", "buyer_email", "artifact", "name", "phone"):
            self.assertNotIn(forbidden, row)

    def test_receipt_rejects_pii_keys_and_empty_state(self):
        case = case_from_autopsy_offer(case_ref="opaque-case-8")
        with self.assertRaises(ValueError):
            receipt_row_from_case({**case, "email": "buyer@example.com"})
        with self.assertRaises(ValueError):
            receipt_row_from_case(case, state="")
        with self.assertRaises(ValueError):
            receipt_row_from_case(case, g2_run_id="")


if __name__ == "__main__":
    unittest.main()
