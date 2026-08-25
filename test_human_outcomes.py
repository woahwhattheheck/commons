import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
CATALOG_PATH = ROOT / "revenue" / "human_outcomes" / "offers.json"
HTML_PATH = ROOT / "humans.html"
README_PATH = ROOT / "revenue" / "human_outcomes" / "README.md"
FULFILLMENT_PATH = ROOT / "revenue" / "human_outcomes" / "fulfillment.md"

class HumanOutcomeCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        cls.html = HTML_PATH.read_text(encoding="utf-8")
        cls.readme = README_PATH.read_text(encoding="utf-8")
        cls.fulfillment = FULFILLMENT_PATH.read_text(encoding="utf-8")

    def test_truth_gate_is_honest(self):
        truth = self.catalog["truth"]
        self.assertEqual(truth["collected_cash_usd"], 0)
        self.assertEqual(truth["collected_cash_state"], "NOT_LANDED")
        self.assertFalse(truth["banking_only_blocker"])
        self.assertFalse(truth["public_checkout"])
        self.assertIn("$0 / NOT_LANDED", self.html)
        self.assertIn("Authorization", self.html)

    def test_offer_contracts_are_bounded(self):
        offers = self.catalog["offers"]
        ids = [offer["id"] for offer in offers]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), set(self.catalog["priority_order"]))
        for offer in offers:
            self.assertGreater(offer["price"]["fixed_amount"], 0)
            self.assertGreater(offer["price"]["deposit_amount"], 0)
            self.assertLessEqual(offer["price"]["deposit_amount"], offer["price"]["fixed_amount"])
            self.assertTrue(offer["deliverables"])
            self.assertTrue(offer["acceptance"])
            self.assertTrue(offer["refund_boundary"])
            self.assertIn(offer["id"], self.html)

    def test_public_surface_has_open_contact_but_no_auth_or_secret_intake(self):
        self.assertIn("mailto:brycembusiness2@gmail.com", self.html)
        self.assertNotIn('type="password"', self.html.lower())
        self.assertNotIn("<form", self.html.lower())
        for forbidden in ("routing number", "account number", "cvv", "tax identifier"):
            self.assertNotIn(forbidden, self.html.lower())

    def test_every_prior_lane_is_preserved(self):
        lanes = (
            "high-ticket White Box",
            "failure packets",
            "paid briefings/training",
            "tools/receipts",
            "licensing",
            "retainers",
            "expert networks",
            "grants",
            "sponsorships/partners",
            "later marketplace",
        )
        for lane in lanes:
            self.assertIn(lane, self.readme)

    def test_fulfillment_subordinates_proof_to_acceptance(self):
        self.assertIn("not acceptance", self.fulfillment)
        self.assertIn("never infer a later state", self.fulfillment)
        self.assertIn("AUTHORIZED -> SETTLED -> PAID_OUT -> BANK_AVAILABLE", self.fulfillment)

if __name__ == "__main__":
    unittest.main()
