#!/usr/bin/env python3
"""Paperwork factory is a shared slot, not a pack instance."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_paperwork_slot as slot  # noqa: E402


class BusinessPackPaperworkSlotTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = slot.load_law()
        self.card = (ROOT / "ground" / "BUSINESS_PACK_PAPERWORK_SLOT.md").read_text(
            encoding="utf-8"
        )
        self.receipt = (
            ROOT / "p" / "cursor-business-pack-paperwork-slot-20260902-01.md"
        ).read_text(encoding="utf-8")

    def test_law_clears_plant_and_is_not_a_gate(self) -> None:
        self.assertEqual(
            self.law["id"], "cursor-business-pack-paperwork-slot-20260902-01"
        )
        self.assertEqual(self.law["kind"], "BUSINESS_PACK_PAPERWORK_SLOT")
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.law["commons_admission"], False)
        self.assertEqual(
            self.law["clear_claim"], "cursor-plant-yard-greeting-pack-20260902-01"
        )
        self.assertEqual(self.law["lead_owner"], "bc-23891c63")
        self.assertEqual(self.law["home"], "factory_shared_slot")
        self.assertIs(self.law["not_instance"], True)
        self.assertIs(self.law["not_legal_advice"], True)
        self.assertEqual(self.law["slots"], "OWNER_UNSET")
        self.assertEqual(self.law["checkout"], "NOT_MINTED")
        self.assertIn("packs/lotribbon-greetings-20260902-01/**", self.law["lead_keeps"])
        self.assertIn("ground/BUSINESS_PACK_PLANT.json", self.law["will_not_write"])
        self.assertIn("ground/BUSINESS_PACK_PAPERWORK.json", self.law["will_not_write"])
        dumped = json.dumps(self.law)
        self.assertNotIn("337 NO", dumped)
        self.assertNotIn("337 NO", self.card)
        self.assertNotIn("buy.stripe.com", self.card.lower())
        self.assertIn("shared slot", self.card.lower())
        self.assertIn("CLEAR", self.receipt)

    def test_factory_home_is_shared_slot_ok(self) -> None:
        result = slot.classify_slot({"paperwork_home": "factory"})
        self.assertEqual(result["verdict"], "SHARED_SLOT_OK")
        self.assertTrue(result["shared_slot"])
        self.assertTrue(result["not_instance"])
        self.assertIs(result["gate"], False)
        self.assertIs(result["commons_admission"], False)
        self.assertEqual(result["cleared_claim"], "cursor-plant-yard-greeting-pack-20260902-01")

    def test_instance_owned_paperwork_is_flagged(self) -> None:
        result = slot.classify_slot(
            {"paperwork_home": "instance", "owns_factory": True}
        )
        self.assertEqual(result["verdict"], "INSTANCE_OWNED")
        self.assertFalse(result["shared_slot"])

    def test_plant_paths_are_excluded(self) -> None:
        self.assertTrue(slot.reserved_plant_path("packs/lotribbon-greetings-20260902-01/offer.md"))
        self.assertTrue(slot.reserved_plant_path("ground/BUSINESS_PACK_PLANT.json"))
        self.assertFalse(slot.reserved_plant_path("packs/_template/paperwork.md"))
        result = slot.classify_slot(
            {
                "paperwork_home": "factory",
                "writes": ["packs/lotribbon-greetings-20260902-01/offer.md"],
            }
        )
        self.assertEqual(result["verdict"], "PLANT_INSTANCE_EXCLUDED")
        self.assertTrue(result["plant_write"])

    def test_peer_factory_rewrite_is_stolen(self) -> None:
        self.assertTrue(slot.peer_factory_path("host/business_pack_paperwork.py"))
        result = slot.classify_slot(
            {
                "paperwork_home": "factory",
                "writes": ["ground/BUSINESS_PACK_PAPERWORK.json"],
            }
        )
        self.assertEqual(result["verdict"], "FACTORY_PATH_STOLEN")

    def test_legal_advice_and_franchise_and_earnings(self) -> None:
        self.assertEqual(
            slot.classify_slot({"paperwork_home": "factory", "legal_advice": True})[
                "verdict"
            ],
            "LEGAL_ADVICE_CLAIM",
        )
        self.assertEqual(
            slot.classify_slot({"paperwork_home": "factory", "copy": "buy a franchise"})[
                "verdict"
            ],
            "FRANCHISE_VOCAB",
        )
        self.assertEqual(
            slot.classify_slot({"paperwork_home": "factory", "copy": "Make $200 this weekend"})[
                "verdict"
            ],
            "EARNINGS_COPY",
        )

    def test_missing_home_is_not_a_gate(self) -> None:
        result = slot.classify_slot({})
        self.assertEqual(result["verdict"], "MISSING_HOME")
        self.assertIs(result["gate"], False)

    def test_instance_may_fill_factory_slot(self) -> None:
        result = slot.classify_slot(
            {
                "paperwork_home": "template",
                "instance_id": "harborline-local-sites-20260902-01",
                "fills_slot": True,
            }
        )
        self.assertEqual(result["verdict"], "SHARED_SLOT_OK")

    def test_cli(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "business_pack_paperwork_slot.py"),
                "--pack-json",
                json.dumps({"paperwork_home": "shared"}),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "SHARED_SLOT_OK")
        self.assertEqual(
            payload["law_id"], "cursor-business-pack-paperwork-slot-20260902-01"
        )


if __name__ == "__main__":
    unittest.main()
