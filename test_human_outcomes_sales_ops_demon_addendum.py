import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
OPS = ROOT / "revenue" / "human_outcomes" / "sales_ops"

class DemonSalesOpsAddendumTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.peer_targets = json.loads((OPS / "targets.json").read_text(encoding="utf-8"))
        cls.peer_activation = json.loads((OPS / "owner_activation.json").read_text(encoding="utf-8"))
        cls.demand = json.loads((OPS / "demand_r6.json").read_text(encoding="utf-8"))
        cls.rails = json.loads((OPS / "rails_r7.json").read_text(encoding="utf-8"))
        cls.addendum = (OPS / "DEMON_ADDENDUM.md").read_text(encoding="utf-8")

    def test_peer_layer_is_preserved_as_venues(self):
        self.assertTrue((OPS / "sow_template.md").is_file())
        self.assertTrue((OPS / "invoice_template.md").is_file())
        self.assertTrue((OPS / "outreach.json").is_file())
        self.assertTrue(all(row["buyer_named"] is False for row in self.peer_targets["current_public_targets"]))
        self.assertEqual(self.peer_activation["collected_cash_usd"], 0)
        self.assertFalse(self.peer_activation["contact_sent"])

    def test_demand_is_buyer_side_but_not_fiction(self):
        truth = self.demand["truth"]
        self.assertEqual(truth["collected_cash_usd"], 0)
        self.assertFalse(truth["banking_only_blocker"])
        self.assertEqual(truth["buyer_authorizations_observed"], 0)
        self.assertEqual(truth["targets_supporting_current_catalog_price"], 0)
        self.assertEqual(truth["send_ready_without_founder_qualification"], 0)
        self.assertEqual(len(self.demand["targets"]), 8)
        for row in self.demand["targets"]:
            self.assertFalse(row["send_ready"])
            self.assertTrue(row["public_url"].startswith("https://"))
            self.assertTrue(row["disqualifier"])
            self.assertTrue(row["founder_action"])

    def test_rail_sequence_is_precise(self):
        self.assertEqual(self.rails["recommended_primary"]["provider"], "Stripe")
        self.assertEqual(self.rails["fallback"]["provider"], "Square")
        self.assertEqual(
            self.rails["recommended_primary"]["bank_destination_needed_before_buyer_can_pay"],
            "NO_REPORTED_BY_OFFICIAL_SOURCE_RESEARCH",
        )
        threshold = self.rails["bank_details_only_threshold"]
        self.assertFalse(threshold["reached"])
        self.assertIn("real buyer accepted the SOW/invoice", threshold["preconditions"])
        self.assertIn("no buyer authorization", threshold["why_not_reached"])

    def test_no_secret_or_contact_claim(self):
        raw = json.dumps(self.demand) + json.dumps(self.rails)
        self.assertNotRegex(raw, r"\b\d{9}\b")
        self.assertNotIn("sk_live_", raw)
        self.assertNotIn("acct_", raw)
        self.assertIn("$0 / NOT_LANDED", self.addendum)
        self.assertIn("Contact sent remains false", self.addendum)

if __name__ == "__main__":
    unittest.main()
