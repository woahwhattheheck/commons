#!/usr/bin/env python3
"""Hermetic: START.md + start.html surface Autopsy $29 / agent-rescue; not Survival $2500."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
START_MD = ROOT / "START.md"
START_HTML = ROOT / "start.html"

PRODUCT_MARKERS = (
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)


class HuskStartLiveCashTest(unittest.TestCase):
    def test_start_md_live_cash(self) -> None:
        text = START_MD.read_text(encoding="utf-8")
        self.assertIn("## Live cash", text)
        self.assertIn("Autopsy", text)
        self.assertIn("$29", text)
        self.assertIn("agent-rescue.html", text)
        for marker in PRODUCT_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
        # Survival Proof buyers must not be sent to agent-rescue as $2500
        self.assertNotIn("$2500", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("donate.stripe.com", text)

    def test_start_html_live_cash(self) -> None:
        text = START_HTML.read_text(encoding="utf-8")
        self.assertIn("Live cash", text)
        self.assertIn("Autopsy", text)
        self.assertIn("$29", text)
        self.assertIn("agent-rescue.html", text)
        for marker in PRODUCT_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
        # Survival Proof buyers must not be sent to agent-rescue as $2500
        self.assertNotIn("$2500", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("donate.stripe.com", text)


if __name__ == "__main__":
    unittest.main()
