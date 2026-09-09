import json
import pathlib
import unittest

# Hermetic pins for right-now Autopsy rank-1 + Linux LF control hashes.

ROOT = pathlib.Path(__file__).resolve().parent
CATALOG_PATH = ROOT / "revenue" / "right_now" / "catalog.json"
PAGE_PATH = ROOT / "right-now.html"


class RightNowRevenueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        cls.page = PAGE_PATH.read_text(encoding="utf-8")
        cls.human = json.loads(
            (ROOT / "revenue" / "human_outcomes" / "offers.json").read_text(
                encoding="utf-8"
            )
        )
        cls.survival = json.loads(
            (ROOT / "revenue" / "production_survival" / "offer.json").read_text(
                encoding="utf-8"
            )
        )
        cls.diagnostic = json.loads(
            (ROOT / "revenue" / "right_now" / "diagnostic_offer.json").read_text(
                encoding="utf-8"
            )
        )
        cls.autopsy = json.loads(
            (ROOT / "revenue" / "right_now" / "autopsy_offer.json").read_text(
                encoding="utf-8"
            )
        )

    def test_catalog_keeps_cash_and_checkout_truth_separate(self):
        truth = self.catalog["truth"]
        self.assertEqual(truth["collected_cash_usd"], 0)
        self.assertEqual(truth["verified_positive_replies"], 0)
        self.assertEqual(truth["accepted_scopes"], 0)
        self.assertIs(truth["active_chargeable_checkout"], True)
        self.assertNotIn("buy.stripe.com", self.page)
        self.assertNotIn("donate.stripe.com", self.page)
        self.assertIn("agent-failure-autopsy-29", self.page)
        self.assertIn("agent-rescue.html", self.page)

    def test_rank_is_unique_contiguous_and_bottlenecks_are_explicit(self):
        offers = self.catalog["offers"]
        self.assertEqual([row["rank"] for row in offers], list(range(1, len(offers) + 1)))
        self.assertEqual(len({row["id"] for row in offers}), len(offers))
        allowed = {
            "BUYER_SPECIFIC_HANDOFF_REQUIRED",
            "LIVE_PUBLIC_CHECKOUT_PAGE",
        }
        for row in offers:
            self.assertTrue(row["next_external_event"])
            self.assertTrue(row["founder_bottleneck"])
            self.assertTrue(row["commons_bottleneck"])
            self.assertIn(row["payment_state"], allowed)
        autopsy = next(r for r in offers if r["id"] == "agent-failure-autopsy-29")
        self.assertEqual(autopsy["rank"], 1)
        self.assertEqual(autopsy["payment_state"], "LIVE_PUBLIC_CHECKOUT_PAGE")
        self.assertEqual(autopsy["start_route"], "agent-rescue.html")
        survival = next(r for r in offers if r["id"] == "same-day-agent-survival-proof")
        self.assertNotEqual(survival["start_route"], "agent-rescue.html")

    def test_prices_and_routes_are_copied_from_canonical_sources(self):
        canonical = {
            row["id"]: row for row in self.human["offers"]
        }
        entry = self.survival["entry_offer"]
        canonical[entry["id"]] = entry
        canonical[self.diagnostic["id"]] = self.diagnostic
        canonical[self.autopsy["id"]] = self.autopsy
        for row in self.catalog["offers"]:
            self.assertIn(row["id"], canonical)
            self.assertEqual(row["price_usd"], canonical[row["id"]]["fixed_amount"])
            self.assertIn(row["start_route"].split("#", 1)[0], self.page)
            self.assertIn(row["id"], self.page)

    def test_survival_start_route_is_not_autopsy_html(self):
        survival = next(
            row
            for row in self.catalog["offers"]
            if row["id"] == "same-day-agent-survival-proof"
        )
        self.assertEqual(
            survival["start_route"], "revenue/production_survival/README.md"
        )
        self.assertNotEqual(survival["start_route"], "agent-rescue.html")
        start = self.page.index('id="same-day-agent-survival-proof"')
        end = self.page.index("</article>", start)
        card = self.page[start:end]
        self.assertIn("revenue/production_survival/README.md", card)
        self.assertNotIn('href="./agent-rescue.html"', card)
        self.assertNotIn(">agent survival</a>", self.page)

    def test_diagnostic_has_a_bounded_scope_first_contract(self):
        self.assertEqual(self.diagnostic["fixed_amount"], 199)
        self.assertEqual(self.diagnostic["payment_collection"], "BUYER_SPECIFIC_HANDOFF_REQUIRED")
        self.assertEqual(len(self.diagnostic["acceptance"]), 5)
        self.assertIn("agent-triage.html", self.diagnostic["source_paths"])

    def test_autopsy_is_the_live_chargeable_right_now_offer(self):
        self.assertEqual(self.autopsy["fixed_amount"], 29)
        self.assertEqual(self.autopsy["payment_collection"], "LIVE_PUBLIC_CHECKOUT_PAGE")
        self.assertEqual(self.autopsy["public_checkout_page"], "agent-rescue.html")
        self.assertIn("agent-rescue.html", self.autopsy["source_paths"])
        self.assertIn("Open the $29 Autopsy page", self.page)
        self.assertIn("Send the one sentence", self.page)
        self.assertIn("revenue/production_survival/README.md", self.page)

    def test_long_horizon_catalog_is_preserved(self):
        self.assertEqual(set(self.catalog["portfolio"]), {"NOW", "SOON", "LATER"})
        self.assertIn("commerce.html", self.catalog["preserved_long_horizon_routes"])
        self.assertIn("full commerce catalog", self.page)


if __name__ == "__main__":
    unittest.main()
