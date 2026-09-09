#!/usr/bin/env python3
"""Landing hub must surface the AutoGTM door.

PR 8287 / SHA 9674f4e3 cataloged autogtm.html on boards.html without
adding it to door.js / the no-JS index hub. tests.yml run
33673616505 then failed test_door_hub.js:
"hub surfaces every HTML door cataloged by boards.html: autogtm.html".
Keep the Use-tab chip next to reply ledger, and keep the boards
catalog row in hub_pages.py so ingest cannot erase the door.
Do not remint AutoGTM SHIP, Harborline /qualify, or LEAD Sheshiyer.
"""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
NEEDLE_JS = '["autogtm.html", "AutoGTM"]'
NEEDLE_HUB = 'href="./autogtm.html">AutoGTM</a>'
NEEDLE_BOARDS = 'href="./autogtm.html">AutoGTM</a>'


class AutogtmDoorHubTests(unittest.TestCase):
    def test_door_js_and_index_surface_autogtm(self) -> None:
        door = (ROOT / "door.js").read_text(encoding="utf-8")
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        hub = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        self.assertIn(NEEDLE_JS, door)
        self.assertIn(NEEDLE_HUB, index)
        self.assertIn(NEEDLE_BOARDS, boards)
        self.assertIn(NEEDLE_BOARDS, hub)
        self.assertTrue((ROOT / "autogtm.html").is_file())
        reply_at = door.index('["reply-to-revenue.html", "reply ledger"]')
        autogtm_at = door.index(NEEDLE_JS)
        rails_at = door.index('["payment-capability.html", "payment rails"]')
        self.assertLess(reply_at, autogtm_at)
        self.assertLess(autogtm_at, rails_at)

    def test_autogtm_door_returns_home_without_login(self) -> None:
        page = (ROOT / "autogtm.html").read_text(encoding="utf-8")
        self.assertIn('href="./index.html"', page)
        self.assertNotIn('type="password"', page)
        self.assertIn("No login", page)


if __name__ == "__main__":
    unittest.main()
