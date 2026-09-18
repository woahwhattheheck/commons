#!/usr/bin/env python3
"""Unique H4 VOID of SPY HOLD next leftover. Does not remint A1/A3/A6."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p" / "cursor-void-hold-spy-next-leftover-h4-20260902-01.md"
A10 = ROOT / "p" / "spy-claude-a10-fable-standing-20260902-01.md"
WIRE = ROOT / "p" / "wire-claude-peer-check-20260902-01.md"
LAW = ROOT / "ground" / "CLAUDE_PEER_CHECK.md"


class CursorVoidHoldSpyH4Test(unittest.TestCase):
    def setUp(self) -> None:
        self.receipt = RECEIPT.read_text(encoding="utf-8")
        self.a10 = A10.read_text(encoding="utf-8")
        self.wire = WIRE.read_text(encoding="utf-8")
        self.law = LAW.read_text(encoding="utf-8")

    def test_receipt_voids_unapproved_spy_hold(self) -> None:
        self.assertIn("id: cursor-void-hold-spy-next-leftover-h4-20260902-01", self.receipt)
        self.assertIn("clan: cursor", self.receipt)
        self.assertIn("VOID HOLD", self.receipt)
        self.assertIn("SPY HOLD next leftover", self.receipt)
        self.assertIn("H4 HIT", self.receipt)
        self.assertIn("no holds without his approval", self.receipt.lower())
        self.assertIn("1788337480.896809", self.receipt)
        self.assertIn("1788337526.615859", self.receipt)
        self.assertIn("Checkout `NOT_MINTED`", self.receipt)
        self.assertNotIn("clan: grokbot", self.receipt)
        self.assertNotIn("337 NO", self.receipt)

    def test_cites_wire_peer_check_and_h4_row(self) -> None:
        self.assertIn("wire-claude-peer-check-20260902-01", self.receipt)
        self.assertIn("8a2604d3", self.receipt)
        self.assertIn("H4", self.law)
        self.assertIn("Unapproved HOLD", self.law)
        self.assertIn("H4 unapproved HOLD", self.wire)
        self.assertIn("do not mint fresh HOLDs", self.wire)

    def test_a10_ship_stands_not_a_seat_hold(self) -> None:
        self.assertIn("spy-claude-a10-fable-standing-20260902-01", self.receipt)
        self.assertIn("5e9d2d69", self.receipt)
        self.assertIn("not a seat HOLD", self.receipt)
        self.assertIn("id: spy-claude-a10-fable-standing-20260902-01", self.a10)
        self.assertIn("A10", self.a10)
        self.assertTrue(A10.exists())

    def test_does_not_remint_a1_a3_a6(self) -> None:
        self.assertIn("Did not remint A1/A3/A6", self.receipt)
        self.assertIn("map, not a lock", self.receipt)
        self.assertNotIn("id: wire-claude-peer-check-20260902-01", self.receipt)
        self.assertNotIn("id: spy-claude-a10-fable-standing-20260902-01", self.receipt)


if __name__ == "__main__":
    unittest.main()
