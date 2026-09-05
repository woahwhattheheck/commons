#!/usr/bin/env python3
"""Hermetic pin: Survival Proof canonical_page is not agent-rescue.html."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OFFER = ROOT / "revenue" / "production_survival" / "offer.json"
README = ROOT / "revenue" / "production_survival" / "README.md"


class TestForgeSurvivalCanonicalPageRemint(unittest.TestCase):
    def test_canonical_page_off_agent_rescue(self) -> None:
        offer = json.loads(OFFER.read_text(encoding="utf-8"))
        self.assertEqual(offer.get("kind"), "PRODUCTION_SURVIVAL_OFFER")
        self.assertEqual(
            offer.get("entry_offer", {}).get("fixed_amount"), 2500
        )
        page = offer.get("canonical_page")
        self.assertNotEqual(page, "agent-rescue.html")
        self.assertEqual(page, "revenue/production_survival/INTAKE.md")
        # Stripe/plink truth not invented in this remint.
        blob = json.dumps(offer)
        for forbidden in ("buy.stripe.com", "plink_", "price_", "prod_"):
            self.assertNotIn(forbidden, blob)

    def test_readme_does_not_sell_survival_on_agent_rescue(self) -> None:
        text = README.read_text(encoding="utf-8")
        self.assertIn("Agent Failure Autopsy", text)
        self.assertIn("INTAKE.md", text)
        self.assertNotIn(
            "The public buyer page is [`agent-rescue.html`]", text
        )


if __name__ == "__main__":
    unittest.main()
