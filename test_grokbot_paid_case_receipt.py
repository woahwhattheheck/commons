#!/usr/bin/env python3
"""Hermetic pin: opaque case receipt rows preserve opaque G2 case identifiers."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from integrations.grokbot_control.paid_case import (
    receipt_from_g2_submit,
    receipt_row_from_case,
)

ROOT = Path(__file__).resolve().parent
OFFER_ID = "dealer-service-lead-rescue"


def _case(case_ref: str, client_reference_id: str | None = None) -> dict:
    case = {"offer_id": OFFER_ID, "case_ref": case_ref, "sku": OFFER_ID}
    if client_reference_id is not None:
        case["client_reference_id"] = client_reference_id
    return case


class TestPaidCaseReceiptSurface(unittest.TestCase):
    def test_receipt_row_from_case_round_trip(self):
        case = _case("opaque-case-7", client_reference_id="afa29_x_a_v1")
        row = receipt_row_from_case(
            case,
            g2_run_id="run_abc",
            g2_session_id="sess_xyz",
            payment_observed_at="2026-09-05T22:00:00Z",
            state="PAYMENT_OBSERVED_STANDBY_INTAKE",
        )
        self.assertEqual(row["offer_id"], OFFER_ID)
        self.assertEqual(row["case_ref"], "opaque-case-7")
        self.assertEqual(row["sku"], OFFER_ID)
        self.assertEqual(row["client_reference_id"], "afa29_x_a_v1")
        self.assertEqual(row["g2_run_id"], "run_abc")
        self.assertEqual(row["g2_session_id"], "sess_xyz")
        self.assertEqual(row["payment_observed_at"], "2026-09-05T22:00:00Z")
        self.assertEqual(row["state"], "PAYMENT_OBSERVED_STANDBY_INTAKE")
        for forbidden in ("email", "buyer_email", "artifact", "name", "phone"):
            self.assertNotIn(forbidden, row)

    def test_receipt_does_not_invent_payment_evidence(self):
        case = _case("opaque-unverified")
        row = receipt_row_from_case(case, g2_run_id="run_unverified")
        self.assertEqual(row["state"], "UNVERIFIED")
        self.assertNotIn("payment_observed_at", row)
        self.assertNotIn("g2_run_id", case)

    def test_receipt_preserves_full_identifiers_or_rejects_overlength(self):
        case = _case("opaque-length")
        for key in ("g2_run_id", "g2_session_id", "payment_observed_at", "state"):
            with self.subTest(key=key):
                exact = "x" * 200
                self.assertEqual(receipt_row_from_case(case, **{key: exact})[key], exact)
                with self.assertRaisesRegex(ValueError, "200 characters"):
                    receipt_row_from_case(case, **{key: exact + "y"})

    def test_receipt_rejects_pii_keys_and_empty_state(self):
        case = _case("opaque-case-8")
        with self.assertRaises(ValueError):
            receipt_row_from_case({**case, "email": "buyer@example.com"})
        with self.assertRaises(ValueError):
            receipt_row_from_case(case, state="")
        with self.assertRaises(ValueError):
            receipt_row_from_case(case, g2_run_id="")

    def test_receipt_from_g2_submit(self):
        case = _case("opaque-from-submit", client_reference_id="afa29_x_a_v1")
        row = receipt_from_g2_submit(
            case,
            {"run_id": "run_from_submit", "session_id": "sess_from_submit"},
        )
        self.assertEqual(row["g2_run_id"], "run_from_submit")
        self.assertEqual(row["g2_session_id"], "sess_from_submit")
        self.assertEqual(row["case_ref"], "opaque-from-submit")
        self.assertEqual(row["state"], "UNVERIFIED")
        with self.assertRaisesRegex(ValueError, "run_id"):
            receipt_from_g2_submit(case, {"run_id": "", "session_id": "sess"})
        with self.assertRaisesRegex(ValueError, "run_id"):
            receipt_from_g2_submit(case, {"session_id": "sess_only"})


if __name__ == "__main__":
    unittest.main()
