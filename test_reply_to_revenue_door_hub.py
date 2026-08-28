#!/usr/bin/env python3
"""Landing hub must surface every boards.html HTML door.

PR 4919 cataloged reply-to-revenue.html without adding it to door.js /
the no-JS index hub. test_door_hub.js then fails. Keep the chip in the
Use tab next to commerce/distribution.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NEEDLE_JS = '["reply-to-revenue.html", "reply ledger"]'
NEEDLE_HTML = 'href="./reply-to-revenue.html">reply ledger</a>'


class ReplyToRevenueDoorHubTests(unittest.TestCase):
    def test_door_js_and_index_surface_reply_ledger(self) -> None:
        door = (ROOT / "door.js").read_text(encoding="utf-8")
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        self.assertIn(NEEDLE_JS, door)
        self.assertIn(NEEDLE_HTML, index)
        self.assertIn(NEEDLE_HTML, boards)
        self.assertTrue((ROOT / "reply-to-revenue.html").is_file())


if __name__ == "__main__":
    unittest.main()
