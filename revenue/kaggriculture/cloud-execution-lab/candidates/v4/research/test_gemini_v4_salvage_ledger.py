#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "GEMINI-V4-SALVAGE.json"

EXPECTED_IDS = {
    *(f"AG{i:02d}" for i in range(1, 16)),
    "APEX-DUMP",
    "FLASH-MKT",
    "G01-E11",
    "G01-E20",
    "G01-O01",
    "G01-SHOP",
    "IDLE-SVC",
    "META01",
    "META02",
    "META03",
    "META04",
    "PRO-CAP",
    "S33",
}

ALLOWED_STATUS = {
    "CANONICAL",
    "CORRECTED_DESCENDANT",
    "FIELD_BLOCKED",
    "FALSIFIED",
    "OPPONENT_SPECIFIC",
    "SPLIT",
}


class GeminiSalvageLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_is_research_only(self):
        self.assertEqual(self.raw["schema"], "titan.v4.gemini-salvage.v1")
        self.assertIs(self.raw["policy_authority"], False)

    def test_required_ids_are_complete_and_exact(self):
        required = self.raw["required_ids"]
        self.assertEqual(len(required), len(set(required)))
        self.assertEqual(set(required), EXPECTED_IDS)

    def test_entries_cover_required_ids_exactly_once(self):
        entries = self.raw["entries"]
        ids = [entry["id"] for entry in entries]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), EXPECTED_IDS)
        self.assertEqual(set(ids), set(self.raw["required_ids"]))

    def test_every_entry_has_bounded_disposition(self):
        for entry in self.raw["entries"]:
            with self.subTest(entry=entry.get("id")):
                self.assertEqual(
                    set(entry),
                    {"id", "origin", "status", "authority", "next_gate"},
                )
                self.assertIn(entry["status"], ALLOWED_STATUS)
                for key in ("origin", "authority", "next_gate"):
                    self.assertIs(type(entry[key]), str)
                    self.assertTrue(entry[key].strip())

    def test_falsified_entries_keep_explicit_do_not_revive_gate(self):
        by_id = {entry["id"]: entry for entry in self.raw["entries"]}
        self.assertEqual(by_id["AG05"]["status"], "FALSIFIED")
        self.assertIn("no blanket", by_id["AG05"]["next_gate"].lower())
        self.assertEqual(by_id["META01"]["status"], "FALSIFIED")
        self.assertIn("do not revive", by_id["META01"]["next_gate"].lower())

    def test_split_claims_name_the_salvage_authority(self):
        by_id = {entry["id"]: entry for entry in self.raw["entries"]}
        for claim_id in ("AG01", "AG09", "APEX-DUMP", "META02", "META03"):
            with self.subTest(claim_id=claim_id):
                self.assertEqual(by_id[claim_id]["status"], "SPLIT")
                self.assertTrue(by_id[claim_id]["authority"].strip())


if __name__ == "__main__":
    unittest.main()
