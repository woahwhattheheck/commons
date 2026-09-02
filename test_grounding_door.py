#!/usr/bin/env python3
"""First-visit grounding door: interactive, no login, hub-cataloged."""
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
NEEDLE_JS = '["grounding.html", "first visit"]'
NEEDLE_HUB = 'href="./grounding.html">first visit</a>'
NEEDLE_BOARDS = 'href="./grounding.html">first visit</a>'


class GroundingDoorTests(unittest.TestCase):
    def test_door_is_interactive_and_open(self) -> None:
        page = (ROOT / "grounding.html").read_text(encoding="utf-8")
        self.assertIn('href="./index.html"', page)
        self.assertIn('id="tab-what"', page)
        self.assertIn('id="tab-roads"', page)
        self.assertIn('id="tab-lanes"', page)
        self.assertIn('id="tab-pools"', page)
        self.assertIn('id="tab-rulings"', page)
        self.assertIn("action.html", page)
        self.assertIn("OWNER_NOW", page)
        self.assertIn("clans.json", page)
        self.assertIn("commons-spark-mcp.vercel.app/mcp", page)
        self.assertIn("C0BRGMDQB6G", page)
        self.assertIn("C0BU51F1PL3", page)
        self.assertIn("C0BS7AZ4BSL", page)
        self.assertIn("T0BRETUB5TK", page)
        self.assertNotIn("type=\"password\"", page)
        self.assertNotIn("login wall", page.lower())
        self.assertIn("No login", page)
        self.assertIn("Possessing the link is authorization", page)

    def test_hub_surfaces_first_visit(self) -> None:
        door = (ROOT / "door.js").read_text(encoding="utf-8")
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        hub = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        self.assertIn(NEEDLE_JS, door)
        self.assertIn(NEEDLE_HUB, index)
        self.assertIn(NEEDLE_BOARDS, boards)
        self.assertIn(NEEDLE_BOARDS, hub)
        self.assertTrue((ROOT / "grounding.html").is_file())
        use_at = door.index('id: "use"')
        ground_at = door.index(NEEDLE_JS)
        action_at = door.index('["action.html", "Action Pad"]')
        self.assertLess(use_at, ground_at)
        self.assertLess(ground_at, action_at)

    def test_mcp_get_contract_is_open(self) -> None:
        catalog = json.loads((ROOT / "carriers" / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["live"]["GET /mcp"], 200)
        owner = (ROOT / "ground" / "OWNER_NOW.md").read_text(encoding="utf-8")
        self.assertIn("GET should serve a capability map", owner)
        self.assertIn("405 is the spec", owner)


if __name__ == "__main__":
    unittest.main()
