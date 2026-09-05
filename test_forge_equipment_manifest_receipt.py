#!/usr/bin/env python3
"""Battery pin: FORGE equipment capability-manifest + newcomer-road receipts stay on main."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

CAPABILITY = ROOT / "p" / "forge-equipment-capability-manifest-20260905-01.md"
NEWCOMER = ROOT / "p" / "forge-equipment-newcomer-road-proof-20260905-01.md"

CAPABILITY_REQUIRED = (
    "forge-equipment-capability-manifest-20260905-01",
    "build_capability_manifest",
    "equipment_capability_manifest",
    "integrations.shared_equipment.services manifest",
    "same_operations_for_every_peer",
    "peer_label_does_not_change_inventory",
    "cb1c443",
)

NEWCOMER_REQUIRED = (
    "forge-equipment-newcomer-road-proof-20260905-01",
    "test_shared_equipment_newcomer_road.py",
    "slack_read_channel",
    "github_create_branch",
    "build_capability_manifest",
    "redacted()",
    "6d5e882",
)


class ForgeEquipmentManifestReceiptBatteryPin(unittest.TestCase):
    def test_capability_manifest_receipt_is_present(self):
        self.assertTrue(CAPABILITY.is_file(), f"missing {CAPABILITY.relative_to(ROOT)}")
        text = CAPABILITY.read_text(encoding="utf-8")
        for needle in CAPABILITY_REQUIRED:
            self.assertIn(needle, text, f"capability receipt missing {needle!r}")
        self.assertIn("#8802", text)

    def test_newcomer_road_receipt_is_present(self):
        self.assertTrue(NEWCOMER.is_file(), f"missing {NEWCOMER.relative_to(ROOT)}")
        text = NEWCOMER.read_text(encoding="utf-8")
        for needle in NEWCOMER_REQUIRED:
            self.assertIn(needle, text, f"newcomer receipt missing {needle!r}")
        self.assertIn("#8802", text)


if __name__ == "__main__":
    unittest.main()
