#!/usr/bin/env python3
"""Gems in house leftover. Does not steal LotRibbon, Sidewalk, or clans."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import pack_gems_in_house as gems  # noqa: E402


INSTANCE = {
    "keep_or_sell": "SELL",
    "unique_instance_sell": True,
    "brand": "Harborline Local Sites",
    "checkout": "OWNER_PASTE_REQUIRED",
    "method_not_customers": True,
    "ftc_437_customers_included": False,
}


NOTE = """# Gems vs this SKU

Trivial swarm revenue and the biggest-potential gems stay in house on Commons.
This Harborline folder is a respectable SELL method pack. It is not trash:
no invented Stripe URL, no earnings claim, no fake royalty.
"""


class GemsInHouseTest(unittest.TestCase):
    def test_does_not_claim_peer_paths(self) -> None:
        self.assertIn("packs/lotribbon-greetings-20260902-01", gems.DO_NOT_OVERWRITE)
        self.assertIn("packs/sidewalk-signal-web-desk-20260902-01", gems.DO_NOT_OVERWRITE)
        self.assertIn("packs/desk-website-service-20260902-01/door.html", gems.DO_NOT_OVERWRITE)
        self.assertIn("clans.json", gems.DO_NOT_OVERWRITE)
        self.assertIn("packs/waitlist.html", gems.DO_NOT_OVERWRITE)
        self.assertIn("packs/desk-website-service-20260902-01/keep-vs-sell.md", gems.DO_NOT_OVERWRITE)

    def test_law_card(self) -> None:
        path = ROOT / "ground" / "BUSINESS_PACK_GEMS_IN_HOUSE.json"
        if not path.is_file():
            self.skipTest("law card not in this tree")
        result = gems.classify_law(path)
        self.assertEqual(result["verdict"], "GEMS_LAW_OK")
        self.assertEqual(result["checkout"], "NOT_MINTED")
        self.assertEqual(result["sends"], 0)
        self.assertNotIn("@", json.dumps(result))

    def test_harborline_fixture_is_respectable_sell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "door.html").write_text(
                "<h1>Harborline Local Sites</h1><p>This instance is $200.</p>",
                encoding="utf-8",
            )
            (folder / "instance.json").write_text(json.dumps(INSTANCE), encoding="utf-8")
            (folder / "gems.md").write_text(NOTE, encoding="utf-8")
            result = gems.classify_pack(folder)
        self.assertEqual(result["verdict"], "RESPECTABLE_SELL_OK")
        self.assertEqual(result["keep_or_sell"], "SELL")
        self.assertNotIn("@", json.dumps(result))

    def test_earnings_is_trash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "door.html").write_text("make $500 this weekend", encoding="utf-8")
            (folder / "instance.json").write_text(json.dumps(INSTANCE), encoding="utf-8")
            (folder / "gems.md").write_text(NOTE, encoding="utf-8")
            result = gems.classify_pack(folder)
        self.assertEqual(result["verdict"], "TRASH_DOOR")
        self.assertIn("earnings_claim", result["errors"])

    def test_missing_note_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "door.html").write_text("<p>$200 desk pack</p>", encoding="utf-8")
            (folder / "instance.json").write_text(json.dumps(INSTANCE), encoding="utf-8")
            result = gems.classify_pack(folder)
        self.assertEqual(result["verdict"], "GEMS_NOTE_INCOMPLETE")
        self.assertIn("gems_note_missing", result["errors"])

    def test_live_harborline_if_present(self) -> None:
        door = gems.HARBORLINE / "door.html"
        instance = gems.HARBORLINE / "instance.json"
        note = gems.HARBORLINE / "gems.md"
        if not (door.is_file() and instance.is_file() and note.is_file() and gems.LAW.is_file()):
            self.skipTest("full Harborline tree not in this checkout")
        result = gems.classify()
        self.assertNotIn("@", json.dumps(result))
        self.assertEqual(result["checkout"], "NOT_MINTED")
        self.assertEqual(result["verdict"], "GEMS_OK")
        self.assertEqual(result["pack"]["verdict"], "RESPECTABLE_SELL_OK")


if __name__ == "__main__":
    unittest.main()
