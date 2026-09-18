#!/usr/bin/env python3
"""Landing hub must surface the payment-capability door.

PR 4933 landed the registry without a door.js / index / boards chip.
test_door_hub.js fails once boards.html catalogs the HTML door.
Keep the Use-tab chip next to reply ledger.
"""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
NEEDLE_JS = '["payment-capability.html", "payment rails"]'
NEEDLE_HTML = 'href="./payment-capability.html">payment rails</a>'


class PaymentCapabilityDoorHubTests(unittest.TestCase):
    def test_door_js_and_index_surface_payment_rails(self) -> None:
        door = (ROOT / "door.js").read_text(encoding="utf-8")
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        self.assertIn(NEEDLE_JS, door)
        self.assertIn(NEEDLE_HTML, index)
        self.assertIn(NEEDLE_HTML, boards)
        self.assertTrue((ROOT / "payment-capability.html").is_file())


if __name__ == "__main__":
    unittest.main()
