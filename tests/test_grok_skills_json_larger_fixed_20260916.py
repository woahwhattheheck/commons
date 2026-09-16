from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class T(unittest.TestCase):
    def test_skills_json_larger_fixed(self):
        data = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
        cash = data["live_cash"]
        products = cash["products"]
        self.assertEqual(
            [p["path"] for p in products],
            [
                "agent-rescue.html",
                "dealer-service-lead-rescue.html",
                "referral-intake-completeness.html",
                "repair-booking-preflight.html",
                "plant-downtime-handoff.html",
            ],
        )
        self.assertEqual([p["price_usd"] for p in products], [29, 199, 199, 199, 199])
        larger = cash["larger_fixed"]
        self.assertEqual([x["path"] for x in larger], ["diagnostic.html", "commercial.html"])
        self.assertEqual(larger[0]["price_usd"], 12000)
        self.assertEqual(larger[1]["price_usd"], 30000)
        blob = json.dumps(data)
        self.assertNotIn("buy.stripe.com", blob)
        self.assertIn("grok-skills-json-larger-fixed-20260916-01", cash["cite"])
        html = (ROOT / "skills.html").read_text(encoding="utf-8")
        self.assertIn("Larger fixed engagements", html)
        self.assertIn("diagnostic.html", html)
        self.assertIn("commercial.html", html)


if __name__ == "__main__":
    unittest.main()
