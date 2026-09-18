#!/usr/bin/env python3
"""Hermetic: catalog/commons-slack/keyb/titanmcp/telegram Live cash doors."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ["catalog.html","commons-slack.html","keyb.html","titanmcp.html","telegram.html"]
class T(unittest.TestCase):
    def test_all(self) -> None:
        for name in FILES:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn('id="live-cash"', text, name)


            self.assertIn("dealer-service-lead-rescue.html", text, name)
            self.assertIn("referral-intake-completeness.html", text, name)
            self.assertIn("repair-booking-preflight.html", text, name)
            self.assertIn("plant-downtime-handoff.html", text, name)
            self.assertIn("$199", text, name)
            if name == "catalog.html":
                # Convert shelf reuses existing live buys; exact allowlist is
                # test_type_resources_catalog_convert_shelf_20260917_01.py.
                continue
            if name == "keyb.html":
                # Convert shelf reuses existing live buys; Live cash product-page
                # doors stay relative (latch-head-keyb-convert-shelf-20260917-01).
                live_cash = text.split('id="live-cash"', 1)[1].split("</section>", 1)[0]
                self.assertNotIn("buy.stripe.com", live_cash, name)
                continue
            self.assertNotIn("buy.stripe.com", text, name)
if __name__ == "__main__":
    unittest.main()
