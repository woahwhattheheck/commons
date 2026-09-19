from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXED = (
    ("hotel-room-turn-evidence.html", "$2,500 hotel room-turn pilot"),
    ("late-cancel-noshow-fee-leakage.html", "$3,500 late-cancel / no-show leakage"),
    ("chargeback-evidence-readiness.html", "$4,000 chargeback readiness"),
)


class T(unittest.TestCase):
    def test_health_live_cash_includes_tip_and_fixed_product_pages(self):
        text = (ROOT / "health.html").read_text(encoding="utf-8")
        self.assertIn('id="live-cash"', text)
        for href in (
            "dealer-service-lead-rescue.html",
            "referral-intake-completeness.html",
            "repair-booking-preflight.html",
            "plant-downtime-handoff.html",
        ):
            self.assertIn(href, text)
        for href, label in FIXED:
            self.assertIn(f'href="./{href}"', text)
            self.assertIn(label, text)

    def test_index_live_cash_runtime_uses_existing_door_carrier_not_hot_index_rewrite(self):
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        door = (ROOT / "door.js").read_text(encoding="utf-8")
        self.assertIn('id="live-cash"', index)
        self.assertIn('src="./door.js?', index)
        self.assertIn("FIXED_DISCOVERY", door)
        self.assertIn("augmentIndexLiveCash", door)
        self.assertIn('document.getElementById("live-cash")', door)
        self.assertIn('document.getElementById("door-hub")', door)
        for href, label in FIXED:
            self.assertIn(f'["{href}", "{label}"]', door)
        self.assertNotIn("buy.stripe.com", door)

    def test_fixed_discovery_matches_attested_provider_receipt(self):
        ledger = (ROOT / "land" / "fixed-diagnostic-payment-links-20260914.md").read_text(encoding="utf-8")
        health = (ROOT / "health.html").read_text(encoding="utf-8")
        door = (ROOT / "door.js").read_text(encoding="utf-8")
        self.assertIn("charges_enabled=true", ledger)
        self.assertIn("payouts_enabled=true", ledger)
        self.assertIn("requirements.currently_due=[]", ledger)
        for href, _label in FIXED:
            self.assertIn(f"public door: `../{href}`", ledger)
            self.assertIn(href, health)
            self.assertIn(href, door)


if __name__ == "__main__":
    unittest.main()
