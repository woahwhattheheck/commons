#!/usr/bin/env python3
"""boards.html is generated from hub_pages.py.

Hand-editing the bake is reverted on the next ingest
(hub_pages.py BAILIFF 2026-08-20). Keep the Telegram peers door in the
generator so the catalog chip survives. Named regression after board
ingest 755e5b80 dropped the #5334 row from boards.html.

Does not remint commons-peers-telegram-20260829-01.
"""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
NEEDLE = 'href="./telegram.html">Telegram</a>'


class TelegramHubPagesTests(unittest.TestCase):
    def test_generator_and_boards_keep_telegram_door(self) -> None:
        gen = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        self.assertIn(NEEDLE, gen)
        self.assertIn(NEEDLE, boards)

    def test_telegram_html_exists(self) -> None:
        self.assertTrue((ROOT / "telegram.html").is_file())


if __name__ == "__main__":
    unittest.main()
