# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import materialize_stage_knockouts as m

EXACT_CONFIG = b'''{
  "consumer": "frozen",
  "seed": true,
  "funding": true,
  "terminal_route": false,
  "committed": true,
  "budget_seconds": 1.0,
  "reserve_seconds": 0.01,
  "terminal_history": false,
  "redundant_hire": true,
  "fourth_quadrant": false,
  "market_pressure": true,
  "committed_seed_retry": false,
  "operating_stock": true,
  "idle_fertilizer": true,
  "crop_release": true,
  "early_capital": true,
  "town_procurement": true
}
'''


class ProductionV3PostprocessorAttributionTest(unittest.TestCase):
    def baseline(self):
        return {
            "TITAN-CONFIG.json": EXACT_CONFIG,
            "main.py": b"v3 entry placeholder\n",
            "retained.py": b"retained\n",
        }

    def test_exact_production_config_is_bound(self):
        self.assertEqual(m.digest(EXACT_CONFIG), m.BASELINE_CONFIG_SHA256)
        config = m._baseline_config(self.baseline())
        for key, value in m.SCREEN_PREIMAGE.items():
            self.assertEqual(config[key], value)

    def test_three_knockouts_are_disjoint_and_leave_town_frozen(self):
        self.assertEqual(set(m.ARMS), {"seed_hire_off", "inventory_spatial_off", "late_market_off"})
        seen = set()
        for name, changes in m.ARMS.items():
            self.assertTrue(seen.isdisjoint(changes), name)
            seen.update(changes)
        self.assertEqual(
            seen,
            {
                "seed", "funding", "redundant_hire",
                "operating_stock", "idle_fertilizer", "crop_release",
                "market_pressure", "early_capital",
            },
        )
        self.assertNotIn("consumer", seen)
        self.assertNotIn("town_procurement", seen)

    def test_each_arm_changes_only_config_and_preserves_valid_dependencies(self):
        baseline = self.baseline()
        for arm, changes in m.ARMS.items():
            treatment = m.arm_members(baseline, arm)
            self.assertEqual(
                [name for name in baseline if baseline[name] != treatment[name]],
                ["TITAN-CONFIG.json"],
            )
            cfg = json.loads(treatment["TITAN-CONFIG.json"])
            self.assertEqual(cfg["consumer"], "frozen")
            self.assertIs(cfg["town_procurement"], True)
            for key, before in m.SCREEN_PREIMAGE.items():
                expected = changes.get(key, before)
                self.assertEqual(cfg[key], expected, (arm, key))
            self.assertEqual(treatment["main.py"], baseline["main.py"])
            self.assertEqual(treatment["retained.py"], baseline["retained.py"])

    def test_inventory_knockout_disables_coupled_stock_spatial_stage(self):
        cfg = json.loads(m.arm_members(self.baseline(), "inventory_spatial_off")["TITAN-CONFIG.json"])
        self.assertFalse(cfg["operating_stock"])
        self.assertFalse(cfg["idle_fertilizer"])
        self.assertFalse(cfg["crop_release"])
        self.assertTrue(cfg["market_pressure"])
        self.assertTrue(cfg["early_capital"])
        self.assertTrue(cfg["seed"])

    def test_seed_hire_knockout_keeps_frozen_transform_and_later_stages(self):
        cfg = json.loads(m.arm_members(self.baseline(), "seed_hire_off")["TITAN-CONFIG.json"])
        self.assertEqual(cfg["consumer"], "frozen")
        self.assertFalse(cfg["seed"])
        self.assertFalse(cfg["funding"])
        self.assertFalse(cfg["redundant_hire"])
        self.assertTrue(cfg["operating_stock"])
        self.assertTrue(cfg["market_pressure"])
        self.assertTrue(cfg["town_procurement"])

    def test_late_market_knockout_is_only_pressure_plus_capital(self):
        cfg = json.loads(m.arm_members(self.baseline(), "late_market_off")["TITAN-CONFIG.json"])
        self.assertFalse(cfg["market_pressure"])
        self.assertFalse(cfg["early_capital"])
        self.assertTrue(cfg["operating_stock"])
        self.assertTrue(cfg["crop_release"])
        self.assertTrue(cfg["seed"])

    def test_wrong_preimage_rejects_before_treatment(self):
        baseline = self.baseline()
        baseline["TITAN-CONFIG.json"] = EXACT_CONFIG.replace(
            b'"market_pressure": true', b'"market_pressure": false'
        )
        with self.assertRaisesRegex(ValueError, "exact production-v3"):
            m.arm_members(baseline, "late_market_off")

    def test_unknown_arm_rejects(self):
        with self.assertRaisesRegex(ValueError, "unknown attribution arm"):
            m.arm_members(self.baseline(), "not-an-arm")

    def test_bundle_is_deterministic_and_binds_every_arm(self):
        first_bundle, first_receipt = m.build_screen(self.baseline())
        second_bundle, second_receipt = m.build_screen(self.baseline())
        self.assertEqual(first_bundle, second_bundle)
        self.assertEqual(first_receipt, second_receipt)
        self.assertEqual(first_receipt["bundle_sha256"], m.digest(first_bundle))
        self.assertEqual(set(first_receipt["arms"]), set(m.ARMS))
        self.assertEqual(first_receipt["native_economics_status"], "PENDING_MATCHED_NATIVE_9901")
        self.assertTrue(first_receipt["kaggle_submission_hold"])
        for arm, record in first_receipt["arms"].items():
            self.assertEqual(record["changed_members"], ["TITAN-CONFIG.json"])
            self.assertEqual(record["member_count"], len(self.baseline()))
            self.assertEqual(set(record["config_changes"]), set(m.ARMS[arm]))

    def test_bundle_contains_screen_and_three_nested_archives(self):
        bundle, receipt = m.build_screen(self.baseline())
        members = m.support.parse_archive_bytes(bundle, receipt["bundle_sha256"])
        self.assertEqual(
            set(members),
            {
                "SCREEN.json",
                "arms/seed_hire_off.tar.gz",
                "arms/inventory_spatial_off.tar.gz",
                "arms/late_market_off.tar.gz",
            },
        )
        screen = json.loads(members["SCREEN.json"])
        self.assertEqual(screen["schema"], m.SCHEMA)
        self.assertEqual(screen["baseline_archive_sha256"], m.BASELINE_ARCHIVE_SHA256)
        for arm in m.ARMS:
            nested = m.support.parse_archive_bytes(
                members[f"arms/{arm}.tar.gz"], screen["arms"][arm]["archive_sha256"]
            )
            self.assertEqual(set(nested), set(self.baseline()))
            self.assertEqual(nested["main.py"], self.baseline()["main.py"])

    def test_semantic_map_rotates_only_v3_main_identity(self):
        self.assertEqual(
            m.SEMANTIC_MEMBER_SHA256["main.py"],
            "b98aec64f83ea9a216def7ab1fef320a6498ae37816f506af1f891c934027035",
        )
        for name, sha in m.support.SEMANTIC_MEMBER_SHA256.items():
            if name != "main.py":
                self.assertEqual(m.SEMANTIC_MEMBER_SHA256[name], sha)


if __name__ == "__main__":
    unittest.main()
