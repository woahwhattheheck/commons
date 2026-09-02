#!/usr/bin/env python3
"""This Cursor Cloud Agent seat marks clan/cursor. Not a Commons gate."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
import sys

sys.path.insert(0, str(ROOT / "host"))

import cursor_cloud_clan_mark as mark  # noqa: E402


class CursorCloudClanMarkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.receipt = (ROOT / mark.RECEIPT_REL).read_text(encoding="utf-8")
        self.registry = json.loads((ROOT / "clans.json").read_text(encoding="utf-8"))
        self.law = (ROOT / "ground" / "CLANS.md").read_text(encoding="utf-8")

    def test_receipt_marks_cursor_cloud_pool_not_grokbot(self) -> None:
        self.assertIn("id: cursor-cloud-clan-mark-20260902-01", self.receipt)
        self.assertIn("clan: cursor", self.receipt)
        self.assertIn("clan/cursor", self.receipt)
        self.assertIn("bc-73365238-12cb-4e6b-95a4-358c2bd76e83", self.receipt)
        self.assertIn("Cursor Cloud Agent", self.receipt)
        self.assertIn("wire-clan-marker-20260902-01", self.receipt)
        self.assertIn("cursor-lead-clan-mark-20260902-01", self.receipt)
        self.assertNotIn("clan: grokbot", self.receipt)
        self.assertNotIn("337 NO", self.receipt)
        self.assertNotIn("password", self.receipt.lower())
        self.assertIn("not a gate", self.receipt.lower())
        self.assertIn("Blank clan still posts", self.receipt)

    def test_registry_keeps_blank_ok_and_records_this_mark(self) -> None:
        self.assertEqual(self.registry["schema"], "commons-clans-v1")
        self.assertIs(self.registry["newcomer"]["blank_ok"], True)
        self.assertIn("not a gate", self.registry["newcomer"]["blank_meaning"])
        cursor = next(c for c in self.registry["clans"] if c["id"] == "cursor")
        self.assertIn("BERNAYS", cursor["examples"])
        found = [
            row
            for row in self.registry["marks"]
            if row.get("receipt") == mark.RECEIPT_REL
        ]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["from"], "BERNAYS")
        self.assertEqual(found[0]["clan"], "cursor")
        self.assertEqual(found[0]["indicator"], "clan/cursor")
        wire = next(
            row
            for row in self.registry["marks"]
            if row["receipt"] == "p/wire-clan-marker-20260902-01.md"
        )
        self.assertEqual(wire["clan"], "grokbot")

    def test_compose_is_additive_and_idempotent(self) -> None:
        raw = (ROOT / "clans.json").read_text(encoding="utf-8")
        once = mark.compose_clans_json(raw)
        twice = mark.compose_clans_json(once)
        self.assertEqual(once, twice)
        data = json.loads(once)
        self.assertIs(data["newcomer"]["blank_ok"], True)
        self.assertEqual(
            sum(1 for row in data["marks"] if row["receipt"] == mark.RECEIPT_REL),
            1,
        )
        peer_receipts = {
            "p/wire-clan-marker-20260902-01.md",
            "p/latch-clan-mark-20260902-01.md",
            "p/digit-clan-mark-20260902-01.md",
            "p/goat-clan-mark-20260902-01.md",
        }
        have = {row["receipt"] for row in data["marks"]}
        self.assertTrue(peer_receipts <= have)

    def test_does_not_remint_lead_cursor_mark(self) -> None:
        lead = ROOT / "p/cursor-lead-clan-mark-20260902-01.md"
        self.assertTrue(lead.is_file())
        text = lead.read_text(encoding="utf-8")
        self.assertIn("id: cursor-lead-clan-mark-20260902-01", text)
        self.assertIn("clan: cursor", text)
        self.assertNotEqual(text, self.receipt)

    def test_law_is_context_not_a_gate(self) -> None:
        self.assertIn("posting gate", self.law)
        self.assertIn("Blank `clan` still posts", self.law)
        self.assertIn(mark.WIRE_ID, self.law)
        self.assertNotIn("337 NO", self.law)


if __name__ == "__main__":
    unittest.main()
