"""The public Sidewalk Signal offer door: buyer-clean, slot-reading, nothing invented.

packs/sidewalk-signal-web-desk-20260902-01/offer.html is the page an ad can point at. It reads the
instance's existing owner-paste slot (manifest.json -> checkout.url) for the Buy button and the
existing pixel slot (ground/BUSINESS_PACK_THANKS.json); it never carries a Stripe URL or a pixel ID
itself. These checks pin that shape.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "packs" / "sidewalk-signal-web-desk-20260902-01"
DOOR = PACK / "offer.html"
FACTORY_WORDS = re.compile(
    r"OWNER_UNSET|NOT_MINTED|HOLD_COUNSEL|OWNER_PASTE|owner pastes|Owner pastes|337 NO|CLONE_STAMP|"
    r"FINDER-FAILED|Do not remint|do not remint|commons\.mno|\bCommons\b|\bBryce\b|\bSCOUT\b|\bTALLY\b"
)


class OfferDoor(unittest.TestCase):
    def setUp(self) -> None:
        self.page = DOOR.read_text(encoding="utf-8")

    def test_buyer_clean_copy_and_price(self) -> None:
        hits = sorted({m.group(0) for m in FACTORY_WORDS.finditer(self.page)})
        self.assertEqual(hits, [], hits)
        self.assertIn("$250", self.page)
        self.assertNotIn("$200", self.page)
        self.assertIn("Sidewalk Signal", self.page)
        self.assertIn("sold once", self.page)
        self.assertIn('<meta name="robots" content="index, follow"/>', self.page)

    def test_nothing_invented_and_slots_read_not_written(self) -> None:
        self.assertNotIn("https://buy.stripe.com/", self.page)
        self.assertNotIn("https://checkout.stripe.com/", self.page)
        self.assertNotIn("static.ads-twitter.com", self.page)  # the pixel script src comes from the slot JSON only
        self.assertIn('fetch("./manifest.json")', self.page)
        self.assertIn('fetch("../../ground/BUSINESS_PACK_THANKS.json")', self.page)
        self.assertIn("client_reference_id", self.page)
        self.assertIn('"ViewContent"', self.page)
        self.assertEqual(self.page.count("<script"), 1)
        self.assertNotIn("<form", self.page)
        self.assertNotIn("<input", self.page)
        self.assertIn("../waitlist.html", self.page)
        self.assertIn("mailto:tokenjunkielabs@gmail.com", self.page)

    def test_slots_exist_and_are_owner_paste(self) -> None:
        manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
        checkout = manifest.get("checkout", {})
        self.assertIn("url", checkout)
        url = str(checkout.get("url") or "")
        self.assertTrue(
            url == "" or url.startswith("https://buy.stripe.com/") or url.startswith("https://checkout.stripe.com/"),
            url,
        )
        self.assertEqual(
            manifest.get("copy_verdicts", {}).get("offer.html"),
            "COPY_OK",
            "offer.html is a pack text file; TENON 9ae6e4885 added it without refreshing copy_verdicts",
        )
        law = json.loads((ROOT / "ground" / "BUSINESS_PACK_THANKS.json").read_text(encoding="utf-8"))
        self.assertIn("pixel_id", law)
        self.assertEqual(law.get("pixel_slot"), "owner_paste")
        self.assertTrue(law.get("empty_loads_zero_third_party_scripts"))

    def test_shared_doors_it_points_at_exist(self) -> None:
        self.assertTrue((ROOT / "packs" / "waitlist.html").exists())
        self.assertTrue((ROOT / "packs" / "thanks.html").exists())


if __name__ == "__main__":
    unittest.main()
