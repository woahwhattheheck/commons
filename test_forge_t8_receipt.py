#!/usr/bin/env python3
"""Battery pin: FORGE T8 TitanMCP execute TABLE receipt stays on main."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p" / "forge-titanmcp-execute-20260904-01.md"

REQUIRED = (
    "forge-titanmcp-execute-20260904-01",
    "claim_assignment",
    "report_assignment_result",
    "execute_piece",
    "piece_text",
    "peer_worker.py",
    "47ec5255dee632bea90fb4fa48d18ec450b9adcb",
    "1.4.4",
    "webmcp-pad.vercel.app",
)


class ForgeT8ReceiptBatteryPin(unittest.TestCase):
    def test_t8_execute_receipt_is_present_with_mechanism_strings(self):
        self.assertTrue(RECEIPT.is_file(), f"missing {RECEIPT.relative_to(ROOT)}")
        text = RECEIPT.read_text(encoding="utf-8")
        for needle in REQUIRED:
            self.assertIn(needle, text, f"receipt missing {needle!r}")
        self.assertIn("Commons `/mcp` KEEP", text)
        self.assertIn("No contest/Devpost restore.", text)


if __name__ == "__main__":
    unittest.main()
