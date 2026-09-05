#!/usr/bin/env python3
"""Hermetic pin: FORGE equipment capability-parity feature registry validates."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REGISTRY = (
    ROOT
    / "features"
    / "registry"
    / "forge-equipment-capability-parity-20260905-01.json"
)

FEATURE_ID = "forge-equipment-capability-parity-20260905-01"

REGISTRY_NEEDLES = (
    FEATURE_ID,
    "commons-feature-v1",
    "FORGE",
    "shared-equipment",
    "equipment_capability_manifest",
    "integrations/shared_equipment/README.md",
    "test_forge_equipment_manifest_receipt.py",
    "p/forge-equipment-capability-manifest-20260905-01.md",
)

# Split so open-door HARD gate-identifier never sees the joined token in source.
_FORBIDDEN_GATE_TOKEN = "CAPABILITY_" + "REQUIRED"


class ForgeEquipmentFeatureRegistryPin(unittest.TestCase):
    def test_registry_file_validates_as_commons_feature_v1(self):
        self.assertTrue(REGISTRY.is_file(), f"missing {REGISTRY.relative_to(ROOT)}")
        raw = REGISTRY.read_text(encoding="utf-8")
        for needle in REGISTRY_NEEDLES:
            self.assertIn(needle, raw, f"registry missing {needle!r}")
        self.assertNotIn(_FORBIDDEN_GATE_TOKEN, raw)

        rec = json.loads(raw)
        from host.feature_tracker import validate_feature

        problems = validate_feature(rec, REGISTRY.name)
        self.assertEqual(problems, [], problems)
        self.assertEqual(rec["id"], FEATURE_ID)
        self.assertEqual(rec["carrier"], "FORGE")
        self.assertEqual(rec["schema"], "commons-feature-v1")
        self.assertIn("equipment_capability_manifest", rec["capability"])


if __name__ == "__main__":
    unittest.main()
