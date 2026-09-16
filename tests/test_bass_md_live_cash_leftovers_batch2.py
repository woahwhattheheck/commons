from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLAIM = "bass-md-live-cash-20260916-02"
FILES = [
    "commercial/cpca-hccn-connect/revenue_model.md",
    "commercial/cpca-hccn-connect/teaming_outreach_packets.md",
    "commercial/cpca-hccn-connect/teaming_shortlist.md",
    "commercial/edss_migration_acceptance/README.md",
    "commercial/edss_migration_acceptance/SOUTH_DAKOTA_TEAMING.md",
    "commercial/edss_migration_acceptance/fixtures/synthetic_ready_receipt.md",
    "commercial/twelve-ejet-provenance/ACCEPTANCE.md",
    "commercial/twelve-ejet-provenance/README.md",
]


class T(unittest.TestCase):
    def test_exact_live_cash_batch(self):
        self.assertEqual(len(FILES), 8)
        for rel in FILES:
            with self.subTest(rel=rel):
                data = (ROOT / rel).read_bytes()
                text = data.decode("utf-8")
                prefix = "../" * rel.count("/")
                self.assertEqual(text.count("## Live cash"), 1)
                self.assertIn("Verified product pages only — no invented Stripe links.", text)
                for page in (
                    "agent-rescue.html",
                    "dealer-service-lead-rescue.html",
                    "referral-intake-completeness.html",
                    "repair-booking-preflight.html",
                    "plant-downtime-handoff.html",
                ):
                    self.assertIn(f"{prefix}{page}", text)
                self.assertNotIn("buy.stripe.com", text)
                self.assertNotIn("\x00", text)
        self.assertTrue(CLAIM)


if __name__ == "__main__":
    unittest.main()
