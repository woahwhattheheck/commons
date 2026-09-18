"""Hermetic: cloud-current.html must not ritualize 337 NO."""
from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
PAGE = ROOT / "cloud-current.html"
RECEIPT = ROOT / "p" / "newbot-cloud-current-drop-337-no-20260909-01.md"


class CloudCurrentDrop337NoTests(unittest.TestCase):
    def test_no_337_no_ritual(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertNotIn("337 NO", text)
        self.assertIn("HTTP is not the computer", text)
        self.assertIn("UNSEATED", text)

    def test_receipt(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("newbot-cloud-current-drop-337-no-20260909-01", text)
        self.assertIn("cloud-current.html", text)


if __name__ == "__main__":
    unittest.main()
