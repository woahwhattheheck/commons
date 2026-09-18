from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLAIM = "grok-newbot05-json-larger-fixed-20260916-01"
DOORS = [
    "commands",
    "compress",
    "delta",
    "embassy",
    "feature-tracker",
    "mirrors",
    "observatory",
    "reach",
    "ringdelta",
]
PRODUCT_PATHS = [
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
]


class T(unittest.TestCase):
    def test_newbot05_json_larger_fixed(self):
        for stem in DOORS:
            with self.subTest(stem=stem):
                data = json.loads((ROOT / f"{stem}.json").read_text(encoding="utf-8"))
                cash = data["live_cash"]
                products = cash["products"]
                self.assertEqual([p["path"] for p in products], PRODUCT_PATHS)
                self.assertEqual([p["price_usd"] for p in products], [199, 199, 199, 199])
                larger = cash["larger_fixed"]
                self.assertEqual([x["path"] for x in larger], ["diagnostic.html", "commercial.html"])
                self.assertEqual(larger[0]["price_usd"], 12000)
                self.assertEqual(larger[1]["price_usd"], 30000)
                blob = json.dumps(data)
                self.assertNotIn("buy.stripe.com", blob)
                self.assertIn(CLAIM, cash["cite"])
                html = (ROOT / f"{stem}.html").read_text(encoding="utf-8")
                self.assertIn("Larger fixed engagements", html)
                self.assertIn("diagnostic.html", html)
                self.assertIn("commercial.html", html)


if __name__ == "__main__":
    unittest.main()
