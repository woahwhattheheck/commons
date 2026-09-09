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
CATALOG = ROOT / "revenue" / "right_now" / "catalog.json"
CONTROL = ROOT / "revenue" / "right_now" / "control.json"
PAGE = ROOT / "right-now.html"
SURVIVAL_ID = "same-day-agent-survival-proof"
START_ROUTE = "revenue/production_survival/README.md"


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
        self.assertIn("no dedicated commons html sell page", text.lower())
        banned = [
            "The public buyer page is [`agent-rescue.html`]",
            "The public buyer page is agent-rescue.html",
        ]
        for phrase in banned:
            self.assertNotIn(phrase, text)

    def test_right_now_catalog_and_control_leave_agent_rescue(self) -> None:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        control = json.loads(CONTROL.read_text(encoding="utf-8"))
        offer = next(row for row in catalog["offers"] if row["id"] == SURVIVAL_ID)
        snap = next(row for row in control["offers"] if row["id"] == SURVIVAL_ID)
        self.assertEqual(offer["start_route"], START_ROUTE)
        self.assertEqual(snap["start_route"], offer["start_route"])
        self.assertNotEqual(offer["start_route"], "agent-rescue.html")
        self.assertNotEqual(snap["start_route"], "agent-rescue.html")

    def test_right_now_page_survival_card_does_not_start_at_autopsy(self) -> None:
        page = PAGE.read_text(encoding="utf-8")
        card = page.split(f'id="{SURVIVAL_ID}"', 1)[1].split("</article>", 1)[0]
        self.assertNotIn('href="./agent-rescue.html"', card)
        self.assertIn(START_ROUTE, card)


if __name__ == "__main__":
    unittest.main()
