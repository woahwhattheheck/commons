import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

import build as builder


HERE = Path(__file__).resolve().parent


class BuildTests(unittest.TestCase):
    def test_materializes_exact_parent_and_canonical_helper(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            baseline = root / "baseline"
            out = root / "candidate"
            baseline.mkdir()
            shutil.copyfile(builder.LAB_ROOT / "main.py", baseline / "main.py")
            receipt = builder.build_candidate(baseline, out)
            self.assertEqual(
                builder.git_blob(out / "baseline_main.py"),
                builder.EXPECTED_PARENT_MAIN_BLOB,
            )
            self.assertEqual(
                builder.git_blob(out / "animal_headroom_harvest.py"),
                builder.EXPECTED_HELPER_BLOB,
            )
            self.assertEqual(
                (out / "main.py").read_bytes(), builder.ENTRY_SOURCE.read_bytes()
            )
            self.assertNotEqual(
                receipt["control_package_sha256"],
                receipt["candidate_package_sha256"],
            )

    def test_rejects_parent_main_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            baseline = root / "baseline"
            baseline.mkdir()
            (baseline / "main.py").write_text("def agent(*_): return {}\n")
            with self.assertRaisesRegex(ValueError, "exact current V5 parent"):
                builder.build_candidate(baseline, root / "candidate")


class EntryTests(unittest.TestCase):
    def load_entry(self, baseline, helper):
        spec = importlib.util.spec_from_file_location("animal_yield_cap_entry_test", HERE / "entry.py")
        module = importlib.util.module_from_spec(spec)
        with mock.patch.dict(
            sys.modules,
            {"baseline_main": baseline, "animal_headroom_harvest": helper},
        ):
            spec.loader.exec_module(module)
        return module

    def test_uses_parent_canonical_identity_for_helper(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        changed = {"farmer": ["HARVEST"], "hands": [], "market": []}
        seen = {}
        baseline = types.ModuleType("baseline_main")
        baseline._canonical_entrypoint_observation = lambda obs, cfg: {
            "player": 0,
            "step": 23,
            "farms": obs["farms"],
            "private": obs["private"],
        }
        baseline.agent = lambda obs, cfg: action
        helper = types.ModuleType("animal_headroom_harvest")

        def plan(parent_action, observation, configuration):
            seen["plan_obs"] = observation
            self.assertIs(parent_action, action)
            return {"eligible": True, "reason": "provable_animal_product_clip"}

        def apply(parent_action, observation, configuration, *, enabled=False):
            seen["apply_obs"] = observation
            self.assertTrue(enabled)
            self.assertIs(parent_action, action)
            return changed

        helper.plan_animal_headroom_harvest = plan
        helper.apply_animal_headroom_harvest = apply
        module = self.load_entry(baseline, helper)
        obs = {"farms": [{"tiles": []}], "private": {}}
        self.assertIs(module.agent(obs, {}), changed)
        self.assertEqual(seen["plan_obs"], seen["apply_obs"])
        self.assertEqual(seen["plan_obs"]["step"], 23)
        report = module.last_report()
        report["eligible"] = False
        self.assertTrue(module.last_report()["eligible"])

    def test_ineligible_helper_preserves_parent_action_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        baseline = types.ModuleType("baseline_main")
        baseline._canonical_entrypoint_observation = lambda obs, cfg: obs
        baseline.agent = lambda obs, cfg: action
        helper = types.ModuleType("animal_headroom_harvest")
        helper.plan_animal_headroom_harvest = lambda *args: {
            "eligible": False,
            "reason": "no_provable_clipping_pass",
        }
        helper.apply_animal_headroom_harvest = (
            lambda parent_action, observation, configuration, *, enabled=False: parent_action
        )
        module = self.load_entry(baseline, helper)
        self.assertIs(module.agent({"player": 0, "step": 0}, {}), action)


if __name__ == "__main__":
    unittest.main()
