#!/usr/bin/env python3
"""Hermetic: job cash doors via job.html pointer + tools-cash.html shelf."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOB = ROOT / "job.html"
CASH = ROOT / "tools-cash.html"

REQUIRED_CASH = [
    'id="cash-doors"',
    "./agent-rescue.html",
    "./dealer-service-lead-rescue.html",
    "./referral-intake-completeness.html",
    "./repair-booking-preflight.html",
    "./plant-downtime-handoff.html",
    "$29 Autopsy checkout",
    "$199 dealer diagnostic",
]


class CoilJobCashDoorsTest(unittest.TestCase):
    def test_job_points_at_cash_shelf(self) -> None:
        self.assertTrue(JOB.is_file(), "job.html missing")
        text = JOB.read_text(encoding="utf-8")
        self.assertIn('id="cash-doors"', text)
        self.assertIn("./tools-cash.html", text)
        self.assertIn("$29 Autopsy", text)

    def test_tools_cash_page_still_present(self) -> None:
        self.assertTrue(CASH.is_file(), "tools-cash.html missing")
        text = CASH.read_text(encoding="utf-8")
        for needle in REQUIRED_CASH:
            self.assertIn(needle, text, f"missing {needle}")
        self.assertNotIn("buy.stripe.com", text)


if __name__ == "__main__":
    unittest.main()
