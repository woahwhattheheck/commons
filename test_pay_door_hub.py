#!/usr/bin/env python3
"""Landing hub must keep the pay door in door.js.

DIGIT added pay.html next to commerce on the no-JS index hub
(digit-index-pay-door-20260902-01) without the matching door.js chip.
tests.yml run 33610039106 (SHA 408e4587, battery) then failed
test_door_hub.js: static hub vs door.js hrefs/labels/order.
Keep the Use-tab chip next to commerce. Do not remint the index
receipt or live SKU URLs. Hands off boards/Pages.
"""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
NEEDLE_JS = '["pay.html", "pay"]'
NEEDLE_HUB = 'href="./pay.html">pay</a>'


class PayDoorHubTests(unittest.TestCase):
    def test_door_js_and_index_surface_pay(self) -> None:
        door = (ROOT / "door.js").read_text(encoding="utf-8")
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn(NEEDLE_JS, door)
        self.assertIn(NEEDLE_HUB, index)
        self.assertTrue((ROOT / "pay.html").is_file())
        commerce_at = door.index('["commerce.html", "commerce"]')
        pay_at = door.index(NEEDLE_JS)
        license_at = door.index('["data-license.html", "data licensing"]')
        self.assertLess(commerce_at, pay_at)
        self.assertLess(pay_at, license_at)


if __name__ == "__main__":
    unittest.main()
