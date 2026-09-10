# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

LANE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "dominance_audit", LANE / "audit_disabled_feature_dominance.py")
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class DominanceHarness(unittest.TestCase):
    def classify(self, source: str, *, target: str = "self._continue_weed",
                 off_world: dict[str, object] | None = None) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "sample.py"
            path.write_text(source, encoding="utf-8")
            rule = {
                "id": "TEST",
                "file": "sample.py",
                "class": "SpatialTempo",
                "function": "transform",
                "target": target,
                "off_world": off_world or {
                    "self.pathing": False,
                    "self.tempo": False,
                    "self.weed_continuation": False,
                },
            }
            return module.audit(root, [rule])["rules"][0]

    def test_pinned_predecessor_is_rejected(self) -> None:
        source = (LANE / "fixtures" / "predecessor_hidden_weed.py").read_text()
        result = self.classify(source)
        self.assertEqual("reject", result["status"])
        self.assertEqual("OFF_PATH_REACHABLE", result["code"])
        self.assertEqual([3], result["reachable_off_lines"])

    def test_short_circuit_successor_is_accepted(self) -> None:
        source = (LANE / "fixtures" / "successor_flag_guarded.py").read_text()
        result = self.classify(source)
        self.assertEqual("accept", result["status"])
        self.assertEqual([], result["reachable_off_lines"])

    def test_pre_return_guard_is_accepted(self) -> None:
        source = """
class SpatialTempo:
    def transform(self, obs, selected, controller):
        if not (self.pathing or self.tempo):
            return selected
        return self._continue_weed(obs, selected, controller, 24)
"""
        self.assertEqual("accept", self.classify(source)["status"])

    def test_explicit_weed_flag_is_accepted(self) -> None:
        source = """
class SpatialTempo:
    def transform(self, obs, selected, controller):
        if self.weed_continuation:
            return self._continue_weed(obs, selected, controller, 24)
        return selected
"""
        self.assertEqual("accept", self.classify(source)["status"])

    def test_guard_after_call_does_not_dominate(self) -> None:
        source = """
class SpatialTempo:
    def transform(self, obs, selected, controller):
        changed = self._continue_weed(obs, selected, controller, 24)
        if not self.pathing and not self.tempo:
            return selected
        return changed
"""
        self.assertEqual("reject", self.classify(source)["status"])

    def test_unknown_early_return_cannot_manufacture_a_pass(self) -> None:
        source = """
class SpatialTempo:
    def transform(self, obs, selected, controller):
        if obs.get('skip'):
            return selected
        return self._continue_weed(obs, selected, controller, 24)
"""
        self.assertEqual("reject", self.classify(source)["status"])

    def test_or_short_circuit_with_false_flag_still_reaches_target(self) -> None:
        source = """
class SpatialTempo:
    def transform(self, obs, selected, controller):
        if self.pathing or self._continue_weed(obs, selected, controller, 24):
            return selected
        return selected
"""
        self.assertEqual("reject", self.classify(source)["status"])

    def test_target_in_dead_and_operand_is_not_reached(self) -> None:
        source = """
class SpatialTempo:
    def transform(self, obs, selected, controller):
        if self.pathing and self._continue_weed(obs, selected, controller, 24):
            return selected
        return selected
"""
        self.assertEqual("accept", self.classify(source)["status"])

    def test_target_rename_fails_closed(self) -> None:
        source = """
class SpatialTempo:
    def transform(self, obs, selected, controller):
        return selected
"""
        result = self.classify(source)
        self.assertEqual("reject", result["status"])
        self.assertEqual("TARGET_NOT_FOUND", result["code"])

    def test_comparison_guard_is_understood(self) -> None:
        source = """
class SpatialTempo:
    def transform(self, obs, selected, controller):
        if self.weed_continuation is False:
            return selected
        return self._continue_weed(obs, selected, controller, 24)
"""
        self.assertEqual("accept", self.classify(source)["status"])

    def test_rules_file_and_report_are_deterministic(self) -> None:
        rules = module.load_rules(LANE / "rules.json")
        self.assertGreaterEqual(len(rules), 18)
        # Determinism is engine-level; use a tiny one-rule temporary source.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sample.py").write_text(
                (LANE / "fixtures" / "successor_flag_guarded.py").read_text(),
                encoding="utf-8")
            rule = dict(rules[0], file="sample.py")
            first = module.audit(root, [rule])
            second = module.audit(root, [rule])
            self.assertEqual(first, second)
            self.assertEqual(json.dumps(first, sort_keys=True),
                             json.dumps(second, sort_keys=True))


class RepositoryContract(unittest.TestCase):
    PINNED_SPATIAL_BLOB = "edbc423023479dbe2e78131495334384a87b607f"
    PINNED_RUNTIME_BLOB = "b952c9c228ecbde592bf3d2df01638677abb0d24"

    @staticmethod
    def repository_root() -> Path:
        for candidate in (LANE, *LANE.parents):
            if (candidate / "revenue/kaggriculture/cloud-execution-lab").is_dir():
                return candidate
        return Path("/__titan_repository_not_present__")

    def test_exact_repository_head_is_classified(self) -> None:
        root = self.repository_root()
        spatial = root / "revenue/kaggriculture/cloud-execution-lab/spatial_tempo.py"
        runtime = root / "revenue/kaggriculture/cloud-execution-lab/titan_runtime.py"
        if not spatial.is_file() or not runtime.is_file():
            self.skipTest("repository source tree is not present")
        rules = module.load_rules(LANE / "rules.json")
        report = module.audit(root, rules)
        self.assertEqual(len(rules), report["summary"]["rules"])
        self.assertFalse(any(item["code"] in {
            "SOURCE_NOT_FOUND", "SOURCE_PARSE_FAILED", "FUNCTION_NOT_FOUND", "TARGET_NOT_FOUND"
        } for item in report["rules"]))

        spatial_blob = module.git_blob_sha1(spatial.read_bytes())
        runtime_blob = module.git_blob_sha1(runtime.read_bytes())
        if spatial_blob == self.PINNED_SPATIAL_BLOB and runtime_blob == self.PINNED_RUNTIME_BLOB:
            by_id = {item["id"]: item for item in report["rules"]}
            predecessor = by_id["SPATIAL-WEED-OFF-001"]
            self.assertEqual("reject", report["status"])
            self.assertEqual([861], predecessor["reachable_off_lines"])
            self.assertIn("SPATIAL-WEED-OFF-001", report["error_rule_ids"])
            self.assertIn("RUNTIME-SPATIAL-INSTALL-OFF-W01", report["warning_rule_ids"])


if __name__ == "__main__":
    unittest.main()
