#!/usr/bin/env python3
"""Hermetic pin: Autopsy post-pay seat board is standby until real payment."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AREA = ROOT / "revenue" / "agent_failure_autopsy"
SEATS = AREA / "seats.json"
SEATS_MD = AREA / "SEATS.md"
OFFER = AREA / "offer.json"


class TestForgeAutopsyPostpaySeatBoard(unittest.TestCase):
    def test_seat_board_standby_until_paid(self) -> None:
        board = json.loads(SEATS.read_text(encoding="utf-8"))
        self.assertEqual(board.get("kind"), "AUTOPSY_POST_PAY_SEAT_BOARD")
        self.assertEqual(board.get("offer_id"), "agent-failure-autopsy-29")
        self.assertEqual(board.get("payment_gate"), "REAL_STRIPE_PAYMENT_OBSERVED")
        state = board.get("live_payment_state") or {}
        self.assertEqual(state.get("board_mode"), "STANDBY_UNTIL_PAID")
        self.assertEqual(state.get("paid_cases_observed"), 0)
        self.assertGreaterEqual(state.get("open_unpaid_sessions"), 1)
        seats = board.get("seats") or []
        ids = {s.get("seat_id") for s in seats}
        self.assertIn("autopsy-coordinator-primary", ids)
        self.assertIn("autopsy-coordinator-backup", ids)
        self.assertIn("autopsy-independent-reviewer", ids)
        for seat in seats:
            self.assertEqual(seat.get("state"), "VACANT_STANDBY")
        self.assertEqual(board.get("case_rows"), [])
        checkout = board.get("checkout_truth") or {}
        self.assertTrue(checkout.get("do_not_remint"))
        self.assertTrue(checkout.get("do_not_edit_agent_rescue_html"))

    def test_does_not_remint_offer_or_invent_plink(self) -> None:
        board_text = SEATS.read_text(encoding="utf-8")
        offer = json.loads(OFFER.read_text(encoding="utf-8"))
        # Seat board must not paste a new buy.stripe.com URL; checkout stays in offer.json.
        self.assertNotIn("buy.stripe.com", board_text)
        self.assertEqual(
            offer.get("price", {}).get("payment_url_state"), "LIVE_VERIFIED"
        )
        md = SEATS_MD.read_text(encoding="utf-8")
        self.assertIn("STANDBY_UNTIL_PAID", md)
        self.assertIn("do not remint", md.lower())


if __name__ == "__main__":
    unittest.main()
