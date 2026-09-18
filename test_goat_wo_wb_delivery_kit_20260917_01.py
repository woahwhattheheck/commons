#!/usr/bin/env python3
"""goat-wo-wb-delivery-kit-20260917-01 — White Box delivery kit hermetic."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "packs" / "wb-delivery-kit-20260917-01"
RECEIPT = ROOT / "p" / "goat-wo-wb-delivery-kit-20260917-01.md"
WB_PL = "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07"
REQUIRED = (
    "README.md",
    "checkout.md",
    "door.html",
    "instructions.md",
    "offer.md",
    "receipt-template.md",
    "scope-checklist.md",
    "sell-blurb.md",
)


class GoatWbDeliveryKit(unittest.TestCase):
    def test_pack_files_exist(self):
        for name in REQUIRED:
            self.assertTrue((PACK / name).is_file(), name)

    def test_existing_pl_keep_no_invent(self):
        checkout = (PACK / "checkout.md").read_text(encoding="utf-8")
        self.assertIn("EXISTING_PL_KEEP", checkout)
        self.assertIn(WB_PL, checkout)
        door = (PACK / "door.html").read_text(encoding="utf-8")
        self.assertIn(WB_PL, door)
        self.assertNotIn("buy.stripe.com/test", door.lower())

    def test_autopsy_scrapped_never_bryce_buyer(self):
        blob = "\n".join(
            (PACK / n).read_text(encoding="utf-8") for n in REQUIRED
        )
        self.assertIn("SCRAPPED", blob.upper())
        self.assertTrue(
            "never Bryce-as-buyer" in blob or "Never Bryce-as-buyer" in blob
        )
        self.assertNotRegex(blob, r"(?i)sell autopsy")

    def test_receipt_and_checklist(self):
        scope = (PACK / "scope-checklist.md").read_text(encoding="utf-8")
        self.assertIn("Pre-call", scope)
        self.assertIn("land/session-YYYYMMDD.md", scope)
        tmpl = (PACK / "receipt-template.md").read_text(encoding="utf-8")
        self.assertIn("sku-whitebox-hour-20260826", tmpl)
        self.assertIn(WB_PL, tmpl)

    def test_receipt_file(self):
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("WO-WB-DELIVERY-KIT", text)
        self.assertIn(WB_PL, text)
        self.assertIn("goat-wo-wb-delivery-kit-20260917-01", text)


if __name__ == "__main__":
    unittest.main()
