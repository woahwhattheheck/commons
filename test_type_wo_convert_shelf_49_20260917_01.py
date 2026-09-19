#!/usr/bin/env python3
"""type-wo-convert-shelf-49-20260917-01 — WO-CONVERT-SHELF-49 pack land."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "packs" / "convert-shelf-49-20260917-01"
RECEIPT = ROOT / "p" / "type-wo-convert-shelf-49-20260917-01.md"
TIPS = ROOT / "tips.html"
CITE = "type-wo-convert-shelf-49-20260917-01"
REQUIRED = (
    "README.md",
    "offer.md",
    "checkout.md",
    "instructions.md",
    "sell-blurb.md",
    "sample-shelf.html",
    "door.html",
)
INVENTED_FORBIDDEN = re.compile(
    r"https://buy\.stripe\.com/(?!8x27sK2Kp3UZ9uF2SC43S07)[A-Za-z0-9_-]+"
)
AUTOPSY = "4gM9AS3Ot8bfeOZ78S43S0g"


class TestTypeWoConvertShelf49(unittest.TestCase):
    def test_pack_files_and_receipt(self) -> None:
        for name in REQUIRED:
            self.assertTrue((PACK / name).is_file(), name)
        self.assertTrue(RECEIPT.is_file())
        self.assertIn(CITE, RECEIPT.read_text(encoding="utf-8"))

    def test_checkout_not_minted(self) -> None:
        text = (PACK / "checkout.md").read_text(encoding="utf-8")
        self.assertIn("NOT_MINTED", text)
        self.assertNotIn(AUTOPSY, text)

    def test_sample_uses_owner_paste_not_invented(self) -> None:
        sample = (PACK / "sample-shelf.html").read_text(encoding="utf-8")
        self.assertIn("OWNER_PASTE_PAYMENT_LINK", sample)
        self.assertNotIn("buy.stripe.com", sample)
        self.assertNotIn(AUTOPSY, sample)

    def test_door_and_tips_funnel(self) -> None:
        door = (PACK / "door.html").read_text(encoding="utf-8")
        self.assertIn("NOT_MINTED", door)
        self.assertIn(CITE, door)
        tips = TIPS.read_text(encoding="utf-8")
        self.assertIn("convert-shelf-49-20260917-01", tips)
        self.assertIn("sku-convert-shelf-pack-49", tips)
        # tips may mention White Box EXISTING PL elsewhere; pack card must not invent a $49 PL
        card = tips.split('id="sku-convert-shelf-pack-49"', 1)[1].split("</article>", 1)[0]
        self.assertNotIn("buy.stripe.com/", card)


if __name__ == "__main__":
    unittest.main()
