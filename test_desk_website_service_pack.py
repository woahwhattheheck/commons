#!/usr/bin/env python3
"""$200 Harborline desk pack: method not customers, unique instance."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import desk_website_service_pack as pack  # noqa: E402


PACK_DIR = ROOT / "packs" / "desk-website-service-20260902-01"
LAW_ID = "cursor-desk-website-service-pack-20260902-01"
DEMAND = "scout-demand-desk-website-service-pack-20260902-01"


class DeskWebsiteServicePackTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = pack.load_law()
        self.instance = pack.load_instance()
        self.result = pack.classify()

    def test_law_and_instance_match_demand(self) -> None:
        self.assertEqual(self.law["id"], LAW_ID)
        self.assertEqual(self.law["scout_demand_id"], DEMAND)
        self.assertEqual(self.law["tier_usd"], 200)
        self.assertIs(self.law["method_not_customers"], True)
        self.assertIs(self.law["ftc_437_customers_included"], False)
        self.assertIs(self.law["tally_showcase_copied"], False)
        self.assertEqual(self.instance["brand"], "Harborline Local Sites")
        self.assertEqual(self.instance["checkout"], "OWNER_PASTE_REQUIRED")
        self.assertIs(self.instance["ftc_437_customers_included"], False)
        self.assertEqual(
            self.instance["tally_showcase"]["repo"],
            "woahwhattheheck/smb-showcase-inventory",
        )
        self.assertIs(self.instance["tally_showcase"]["copied_into_this_pack"], False)
        self.assertNotIn("337 NO", json.dumps(self.law))

    def test_pack_ok_unique_sell_copy_and_ten_gaps(self) -> None:
        self.assertEqual(self.result["verdict"], "PACK_OK")
        self.assertEqual(self.result["sell_instance"]["verdict"], "UNIQUE_INSTANCE_SELL_OK")
        self.assertEqual(self.result["copy"]["verdict"], "COPY_OK")
        self.assertFalse(self.result["copy"]["earnings_claim"])
        self.assertFalse(self.result["copy"]["customers_promised"])
        self.assertFalse(self.result["copy"]["franchise_vocab"])
        self.assertEqual(self.result["copy"]["invented_stripe_urls"], [])
        self.assertGreaterEqual(self.result["gap_recipe_count"], 10)
        self.assertEqual(
            self.result["gap_ids"],
            ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"],
        )
        self.assertTrue(self.result["stranger_can_find_ten_gaps"])
        self.assertTrue(self.result["tally_showcase_pointer_only"])
        self.assertFalse(self.result["clone_stamp"])
        self.assertTrue(self.result["marketing_uniqueness_ok"])
        self.assertTrue(self.result["sell_instance"]["owner_paste_required"])
        self.assertGreaterEqual(self.result["sell_checklist_checked"], 6)
        self.assertEqual(self.result["missing_files"], [])
        self.assertTrue(self.result["operator_day_file"])
        self.assertTrue(self.result["paid_tjlabs_support_file"])
        self.assertTrue((PACK_DIR / "paperwork.md").is_file())
        self.assertIn("OWNER_UNSET", (PACK_DIR / "running-cost.md").read_text(encoding="utf-8"))

    def test_clone_stamp_when_second_sale_reuses_fingerprint(self) -> None:
        clone = pack.classify(other_sales=[self.instance])
        self.assertTrue(clone["clone_stamp"])
        self.assertFalse(clone["marketing_uniqueness_ok"])
        self.assertEqual(clone["verdict"], "PACK_INCOMPLETE")

    def test_door_and_checkout_have_no_payment_link(self) -> None:
        door = (PACK_DIR / "door.html").read_text(encoding="utf-8")
        checkout = (PACK_DIR / "checkout.md").read_text(encoding="utf-8")
        self.assertIn("Harborline Local Sites", door)
        self.assertIn("index, follow", door)
        self.assertIn("OWNER_PASTE_REQUIRED", door)
        self.assertIn("does not ship customers", door.lower())
        self.assertIn("packs/waitlist.html", door)
        self.assertIn("../waitlist.html", door)
        self.assertNotIn("https://buy.stripe.com/", door)
        self.assertNotIn("https://donate.stripe.com/", checkout)
        self.assertNotIn("https://buy.stripe.com/", checkout)
        self.assertIn("NOT_MINTED", checkout)
        self.assertIn("packs/thanks.html", checkout)
        self.assertNotIn("<form", door.lower())
        self.assertNotIn('type="password"', door.lower())

    def test_terms_do_not_invent_tjlabs_share(self) -> None:
        terms = (PACK_DIR / "terms.md").read_text(encoding="utf-8")
        self.assertIn("OWNER_UNSET", terms)
        self.assertNotRegex(terms, r"tjlabs_profit_share_percent:\s*[0-9]")

    def test_cli(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "desk_website_service_pack.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "PACK_OK")
        self.assertEqual(payload["law_id"], LAW_ID)
        self.assertEqual(payload["instance_brand"], "Harborline Local Sites")


if __name__ == "__main__":
    unittest.main()
