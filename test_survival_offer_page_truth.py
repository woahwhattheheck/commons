#!/usr/bin/env python3
"""Hermetic: Survival Proof offer package must not claim agent-rescue.html."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AREA = ROOT / "revenue" / "production_survival"
OFFER = AREA / "offer.json"
README = AREA / "README.md"


class SurvivalOfferPageTruthTests(unittest.TestCase):
    def test_offer_canonical_page_is_not_agent_rescue(self) -> None:
        offer = json.loads(OFFER.read_text(encoding="utf-8"))
        self.assertEqual(offer["kind"], "PRODUCTION_SURVIVAL_OFFER")
        self.assertEqual(offer["entry_offer"]["fixed_amount"], 2500)
        page = offer.get("canonical_page")
        self.assertNotEqual(page, "agent-rescue.html")
        self.assertTrue(
            page in ("", None)
            or str(page).upper().startswith("NONE")
            or offer.get("canonical_page_state") == "NO_DEDICATED_PUBLIC_HTML",
            msg="canonical_page must not sell Survival on Autopsy HTML",
        )
        self.assertEqual(
            offer.get("canonical_page_state"), "NO_DEDICATED_PUBLIC_HTML"
        )
        routes = offer.get("public_entry_routes") or []
        self.assertTrue(any("tokenjunkielabs@gmail.com" in r for r in routes))
        self.assertTrue(any("marketplaces.md" in r for r in routes))
        note = offer.get("canonical_page_note") or ""
        self.assertIn("Autopsy", note)
        self.assertNotIn(
            '"canonical_page": "agent-rescue.html"',
            OFFER.read_text(encoding="utf-8"),
        )

    def test_readme_does_not_name_agent_rescue_as_buyer_page(self) -> None:
        text = README.read_text(encoding="utf-8")
        self.assertIn("no dedicated Commons HTML sell page", text.lower())
        banned = [
            "The public buyer page is [`agent-rescue.html`]",
            "The public buyer page is agent-rescue.html",
        ]
        for phrase in banned:
            self.assertNotIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
