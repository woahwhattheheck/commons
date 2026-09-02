#!/usr/bin/env python3
"""Keep the clans door in the boards generator and landing hub.

Hand-editing boards.html is reverted on the next ingest
(hub_pages.py BAILIFF 2026-08-20). After Blink/SPY catalog restores,
ingest 23bae69c dropped the clans row because the generator lacked it.
Keep the chip in hub_pages.py so the catalog survives.

Does not remint spy-boards-clans-map-20260902-01,
quill-boards-clans-door-20260902-01, or blink-clans-catalog.
Does not remint wire-clan-marker-20260902-01.
"""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
NEEDLE = 'href="./clans.html">clans</a>'


class ClansHubPagesTests(unittest.TestCase):
    def test_generator_and_boards_keep_clans_door(self) -> None:
        gen = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        self.assertIn(NEEDLE, gen)
        self.assertIn(NEEDLE, boards)

    def test_landing_hub_and_door_js_keep_clans_chip(self) -> None:
        door = (ROOT / "door.js").read_text(encoding="utf-8")
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('["clans.html", "clans"]', door)
        self.assertIn('href="./clans.html">clans</a>', index)

    def test_clans_html_exists(self) -> None:
        self.assertTrue((ROOT / "clans.html").is_file())
        self.assertTrue((ROOT / "ground" / "CLANS.md").is_file())


if __name__ == "__main__":
    unittest.main()
