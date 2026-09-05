#!/usr/bin/env python3
"""Hermetic: tools cash doors via tools.html pointer + tools-cash.html shelf."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.html"
CASH = ROOT / "tools-cash.html"

REQUIRED_CASH = [
    'id="cash-doors"',
    "./agent-rescue.html",
    "./dealer-service-lead-rescue.html",
    "./referral-intake-completeness.html",
    "./repair-booking-preflight.html",
    "./plant-downtime-handoff.html",
    "$29 Autopsy checkout",
    "$199 dealer diagnostic",
]


class CoilToolsCashDoorsTest(unittest.TestCase):
    def test_tools_points_at_cash_shelf(self) -> None:
        self.assertTrue(TOOLS.is_file(), "tools.html missing")
        text = TOOLS.read_text(encoding="utf-8")
        self.assertIn('id="cash-doors"', text)
        self.assertIn("./tools-cash.html", text)
        self.assertIn("$29 Autopsy", text)

    def test_tools_cash_page(self) -> None:
        self.assertTrue(CASH.is_file(), "tools-cash.html missing")
        text = CASH.read_text(encoding="utf-8")
        for needle in REQUIRED_CASH:
            self.assertIn(needle, text, f"missing {needle}")
        self.assertNotIn("buy.stripe.com", text)

    def test_ingest_splices_cash_doors_after_hub_rebuild(self) -> None:
        ingest = (ROOT / "board_ingest.py").read_text(encoding="utf-8")
        self.assertIn("def splice_tools_cash_doors", ingest)
        self.assertIn("splice_tools_cash_doors()", ingest)
        self.assertIn('id="cash-doors"', ingest)
        self.assertIn("./tools-cash.html", ingest)
        self.assertIn("$29 Autopsy", ingest)
        hub = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        self.assertNotIn('id="cash-doors"', hub)

    def test_splice_restores_missing_pointer(self) -> None:
        import tempfile
        import shutil
        import board_ingest
        with tempfile.TemporaryDirectory() as td:
            src = TOOLS.read_text(encoding="utf-8")
            stripped = src.replace(board_ingest.CASH_DOORS_POINTER, "")
            if 'id="cash-doors"' in stripped:
                stripped = stripped.replace(
                    '<p class="note cash-doors-link" id="cash-doors"><a href="./tools-cash.html"><strong>Live cash</strong></a> — $29 Autopsy + four $199 tip-shelf diagnostics (product pages only).</p>\n',
                    "",
                )
            dest = Path(td) / "tools.html"
            dest.write_text(stripped, encoding="utf-8")
            self.assertNotIn('id="cash-doors"', dest.read_text(encoding="utf-8"))
            wrote = board_ingest.splice_tools_cash_doors(root=td)
            self.assertTrue(wrote)
            restored = dest.read_text(encoding="utf-8")
            self.assertIn('id="cash-doors"', restored)
            self.assertIn("./tools-cash.html", restored)
            self.assertIn("$29 Autopsy", restored)
            self.assertFalse(board_ingest.splice_tools_cash_doors(root=td))


if __name__ == "__main__":
    unittest.main()
