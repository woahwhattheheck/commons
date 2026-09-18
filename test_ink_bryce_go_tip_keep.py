"""Hermetic: tip KEEP receipt + INK pixel heartbeat for Bryce GO wake."""

from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
PIXEL = ROOT / "pixels" / "INK.json"
RECEIPT = ROOT / "p" / "ink-bryce-go-tip-keep-20260909-01.md"


class TestInkBryceGoTipKeep(unittest.TestCase):
    def test_pixel_heartbeat(self) -> None:
        data = json.loads(PIXEL.read_text(encoding="utf-8"))
        self.assertEqual(data["from"], "INK")
        self.assertEqual(data["claim"], "ink-bryce-go-tip-keep-20260909-01")
        self.assertIn("2026-09-09", data["ts"])
        self.assertIn("1.4.5", data["src"])

    def test_receipt_tip_keep(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("ink-bryce-go-tip-keep-20260909-01", text)
        self.assertIn("1.4.5", text)
        self.assertIn("1.4.0", text)
        self.assertIn("Tip KEEP", text)
        self.assertIn("#8802", text)


if __name__ == "__main__":
    unittest.main()
