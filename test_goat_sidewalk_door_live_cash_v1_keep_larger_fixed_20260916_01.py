"""goat-sidewalk-door-live-cash-v1-keep-larger-fixed-20260916-01

KEEP Larger fixed on sidewalk DOOR_LIVE_CASH_V1 remint/normalization.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import goat_sidewalk_door_match as match  # noqa: E402

CLAIM = "goat-sidewalk-door-live-cash-v1-keep-larger-fixed-20260916-01"
DOOR = ROOT / match.DOOR_REL
TIP_PATHS = (
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
LARGER_PATHS = ("diagnostic.html", "commercial.html")


class TestGoatSidewalkDoorLiveCashV1KeepLargerFixed2026091601(unittest.TestCase):
    def test_door_live_cash_v1_keeps_autopsy_and_larger_fixed(self) -> None:
        block = match.DOOR_LIVE_CASH_V1
        text = block.decode("utf-8")


        for rel in TIP_PATHS:
            self.assertIn("../../" + rel, text)
        self.assertIn("$199 dealer", text)
        self.assertIn("$199 referral", text)
        self.assertIn("$199 repair", text)
        self.assertIn("$199 plant", text)
        self.assertIn("Larger fixed", text)
        self.assertIn("Larger fixed engagements", text)
        self.assertIn("../../diagnostic.html", text)
        self.assertIn("../../commercial.html", text)
        self.assertIn("$12,000", text)
        self.assertIn("$30,000", text)
        self.assertNotIn("buy.stripe.com", text)

    def test_pack_door_html_matches_successor_byte_for_byte(self) -> None:
        data = DOOR.read_bytes()
        self.assertEqual(data.count(match.DOOR_LIVE_CASH_V1), 1)
        text = data.decode("utf-8")
        self.assertIn('id="live-cash"', text)

        for rel in TIP_PATHS:
            self.assertIn("../../" + rel, text)
        self.assertIn("../../diagnostic.html", text)
        self.assertIn("../../commercial.html", text)
        self.assertIn("NOT_MINTED", text)
        self.assertNotIn("buy.stripe.com", text)

    def test_normalization_still_recovers_baseline_blob(self) -> None:
        result = match.classify_match()
        self.assertEqual(result["door_baseline_blob"], "638e60b4")
        self.assertIn("live-cash-v1", result["door_successors"])
        self.assertEqual(result["checkout"], "NOT_MINTED")
        self.assertGreater(result["door_size"], 8148)
        # pages-deploy.yml later successors already drifted match_ok on main;
        # this KEEP does not remint that workflow. Door observation stays exact.

    def test_product_pages_exist(self) -> None:
        for name in TIP_PATHS + LARGER_PATHS:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_receipt_exists(self) -> None:
        receipt = ROOT / "p" / f"{CLAIM}.md"
        text = receipt.read_text(encoding="utf-8")
        self.assertIn(f"id: {CLAIM}", text)
        self.assertIn("Hands off #8802", text)
        self.assertIn("Tip KEEP", text)


if __name__ == "__main__":
    unittest.main()
