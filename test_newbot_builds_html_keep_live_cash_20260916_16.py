"""newbot-builds-html-keep-live-cash-20260916-16 — KEEP live-cash on builds.html remint."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "newbot-builds-html-keep-live-cash-20260916-16"
PRODUCTS = [
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
]
LARGER = ("diagnostic.html", "commercial.html")


def _live_cash(cite=CLAIM):
    return {
        "cite": [cite],
        "note": "fixture keep",
        "products": [
            {"name": "Dealer Service Lead Rescue", "price_usd": 199, "path": "dealer-service-lead-rescue.html"},
            {"name": "Referral Intake Completeness", "price_usd": 199, "path": "referral-intake-completeness.html"},
            {"name": "Repair Booking Preflight", "price_usd": 199, "path": "repair-booking-preflight.html"},
            {"name": "Plant Downtime Handoff", "price_usd": 199, "path": "plant-downtime-handoff.html"},
        ],
        "larger_fixed": [
            {"name": "GGUF diagnostic", "price_usd": 12000, "days": 10, "path": "diagnostic.html"},
            {"name": "White Box pilot", "price_usd": 30000, "days": 30, "path": "commercial.html"},
        ],
    }


class TestNewbotBuildsHtmlKeepLiveCash2026091616(unittest.TestCase):
    def test_tip_builds_json_still_has_live_cash(self):
        path = ROOT / "builds.json"
        self.assertTrue(path.is_file())
        doc = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("live_cash", doc)
        paths = [p.get("path") for p in (doc["live_cash"].get("products") or [])]
        for prod in PRODUCTS:
            self.assertIn(prod, paths, prod)
        self.assertNotIn("buy.stripe.com", json.dumps(doc))

    def test_tip_builds_html_has_autopsy_and_larger(self):
        html = (ROOT / "builds.html").read_text(encoding="utf-8")
        self.assertIn('id="live-cash"', html)
        self.assertIn("agent-rescue.html", html)

        self.assertIn("Larger fixed engagements", html)
        for path in LARGER:
            self.assertIn(path, html)
        self.assertNotIn("buy.stripe.com", html.split('id="live-cash"', 1)[1].split('</section>', 1)[0])

    def test_product_pages_exist(self):
        for name in PRODUCTS + list(LARGER):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_builds_ledger_remint_keeps_live_cash_html_and_json(self):
        sys.path.insert(0, str(ROOT))
        import builds_ledger

        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "builds" / "records").mkdir(parents=True)
        live = _live_cash()
        (root / "builds.json").write_text(
            json.dumps({"note": "prev", "live_cash": live}, indent=2) + "\n",
            encoding="utf-8",
        )
        written = {}

        def write(path, text):
            written[os.path.basename(path)] = text
            Path(path).write_text(text, encoding="utf-8")

        projection = builds_ledger.project(str(root), write, open_prs=[], main_sha="")
        self.assertIn("live_cash", projection)
        paths = [p.get("path") for p in (projection["live_cash"].get("products") or [])]
        for prod in PRODUCTS:
            self.assertIn(prod, paths, prod)
        html = written.get("builds.html") or (root / "builds.html").read_text(encoding="utf-8")
        self.assertIn('id="live-cash"', html)
        self.assertIn("agent-rescue.html", html)
        self.assertIn("Larger fixed engagements", html)
        self.assertIn("diagnostic.html", html)
        self.assertIn("commercial.html", html)
        self.assertNotIn("buy.stripe.com", html.split('id="live-cash"', 1)[1].split('</section>', 1)[0])


if __name__ == "__main__":
    unittest.main()
