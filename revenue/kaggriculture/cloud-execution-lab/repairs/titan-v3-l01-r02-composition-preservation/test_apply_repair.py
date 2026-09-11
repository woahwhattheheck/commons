#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ast
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
import tempfile
import unittest
from unittest import mock

import apply_repair as repair


class CompositionCarrierTests(unittest.TestCase):
    def fixture(self) -> str:
        return "prefix\n" + repair.INIT_OLD + "\n" + repair.R02_METHOD_OLD + "suffix\n"

    def generated_probe(self):
        tree = ast.parse("VALUE = (\n" + repair.R02_METHOD_NEW + ")\n")
        methods = ast.literal_eval(tree.body[0].value)
        namespace = {}
        exec("class Probe:\n" + methods, namespace)
        return namespace["Probe"]

    @staticmethod
    def features(**overrides):
        values = dict(
            r02_route_bank=True,
            l01_land=True,
            l01_sheep=False,
            l01_day0buy=False,
            l01_leanplant=False,
        )
        values.update(overrides)
        return SimpleNamespace(**values)

    @staticmethod
    def r02_module(*, mutate_to="R02"):
        module = ModuleType("r02_route_bank")
        module.ROUTE_STEP = 144
        module.FINAL_PLAN_STEP = 648
        module.plan_for = lambda obs: 3

        def step(agent, obs, enabled):
            state = agent._v3_r02
            route = agent.controller.R["MAIN"]
            route[:] = [{"marker": mutate_to}]
            agent.controller._fs_for = None
            state["plan"] = 3
            state["replaced"] = 15
            state["reasons"].append("R02_plan:3")
            return state

        module.step = step
        return module

    def step_probe(self):
        Probe = self.generated_probe()
        agent = Probe()
        route = [{"marker": "L01_PREVIOUS"}]
        routes = {"MAIN": route}
        controller = SimpleNamespace(R=routes, cur="MAIN", _fs_for={"cached": 1})
        state = {
            "plan": 0,
            "endgame": False,
            "reasons": ["old"],
            "replaced": 10,
            "tapes": [[{"marker": "TAPE"}]],
        }
        agent.controller = controller
        agent._v3_r02 = state
        agent.features = self.features()
        agent.diagnostics = {}
        return agent, routes, route, state

    def test_transform_changes_only_the_two_owned_anchors(self):
        source = self.fixture()
        repaired = repair.transform(source)
        self.assertEqual(repaired.count(repair.INIT_NEW), 1)
        self.assertEqual(repaired.count(repair.R02_METHOD_NEW), 1)
        self.assertNotIn(repair.INIT_OLD, repaired)
        self.assertNotIn(repair.R02_METHOD_OLD, repaired)
        self.assertTrue(repaired.startswith("prefix\n"))
        self.assertTrue(repaired.endswith("suffix\n"))

    def test_repaired_generated_runtime_is_valid_python(self):
        tree = ast.parse("VALUE = (\n" + repair.R02_METHOD_NEW + ")\n")
        methods = ast.literal_eval(tree.body[0].value)
        self.assertIn("def _v3_l01_r02_snapshot", methods)
        self.assertIn("def _v3_r02_l01_install", methods)
        self.assertIn("rolled_back", methods)
        self.assertIn("V3_L01_ERROR_", methods)
        ast.parse("class Probe:\n" + methods)

    def test_second_application_fails_closed(self):
        repaired = repair.transform(self.fixture())
        with self.assertRaisesRegex(ValueError, "initialize order"):
            repair.transform(repaired)

    def test_duplicate_anchor_fails_closed(self):
        source = self.fixture() + repair.INIT_OLD
        with self.assertRaisesRegex(ValueError, "initialize order"):
            repair.transform(source)

    def test_apply_file_rejects_unbound_preimage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "apply_v3.py"
            path.write_text(self.fixture(), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "preimage drift"):
                repair.apply_file(path)

    def test_step_rolls_back_raw_r02_tail_when_l01_swallow_reports_error(self):
        agent, routes, route, state = self.step_probe()
        original_route = [dict(row) for row in route]
        original_state = {
            "plan": 0,
            "endgame": False,
            "reasons": ["old"],
            "replaced": 10,
            "tapes": [[{"marker": "TAPE"}]],
        }

        def swallowed_l01_failure():
            agent.controller.R["MAIN"][:] = [{"marker": "BROKEN_L01"}]
            agent._v3_r02["tapes"][0][0]["marker"] = "BROKEN_TAPE"
            agent.diagnostics["v3_l01"] = {
                "activations": {},
                "reasons": ["V3_L01_ERROR_RuntimeError"],
            }

        agent._v3_l01_install = swallowed_l01_failure
        with mock.patch.dict(sys.modules, {"r02_route_bank": self.r02_module()}):
            agent._v3_r02_step({"step": 144})

        self.assertIs(agent.controller.R, routes)
        self.assertIs(agent.controller.R["MAIN"], route)
        self.assertEqual(route, original_route)
        self.assertIs(agent._v3_r02, state)
        self.assertEqual(state, original_state)
        self.assertEqual(agent.controller._fs_for, {"cached": 1})
        self.assertEqual(
            agent.diagnostics["v3_l01"]["reasons"],
            ["V3_L01_ERROR_RuntimeError"],
        )
        self.assertEqual(
            agent.diagnostics["v3_r02_step"],
            {
                "plan": 0,
                "endgame": False,
                "replaced": 10,
                "l01_reapplied": False,
                "rolled_back": True,
                "error": "V3_L01_ERROR_RuntimeError",
            },
        )

    def test_step_commits_r02_then_l01_on_success(self):
        agent, routes, route, state = self.step_probe()

        def successful_l01():
            agent.controller.R["MAIN"].append({"marker": "L01"})
            agent.diagnostics["v3_l01"] = {
                "activations": {"LAND": 1},
                "reasons": [],
            }

        agent._v3_l01_install = successful_l01
        with mock.patch.dict(sys.modules, {"r02_route_bank": self.r02_module()}):
            agent._v3_r02_step({"step": 144})

        self.assertIs(agent.controller.R, routes)
        self.assertIs(agent.controller.R["MAIN"], route)
        self.assertEqual(route, [{"marker": "R02"}, {"marker": "L01"}])
        self.assertEqual(state["plan"], 3)
        self.assertEqual(state["replaced"], 15)
        self.assertIsNone(agent.controller._fs_for)
        self.assertEqual(agent.diagnostics["v3_r02_step"]["l01_reapplied"], True)
        self.assertEqual(agent.diagnostics["v3_r02_step"]["rolled_back"], False)

    def test_step_without_tape_l01_commits_without_snapshot_reapply(self):
        agent, _, route, state = self.step_probe()
        agent.features = self.features(
            l01_land=False,
            l01_sheep=False,
            l01_day0buy=False,
            l01_leanplant=False,
        )
        called = []
        agent._v3_l01_install = lambda: called.append(True)
        with mock.patch.dict(sys.modules, {"r02_route_bank": self.r02_module()}):
            agent._v3_r02_step({"step": 144})
        self.assertEqual(route, [{"marker": "R02"}])
        self.assertEqual(state["replaced"], 15)
        self.assertEqual(called, [])
        self.assertEqual(agent.diagnostics["v3_r02_step"]["l01_reapplied"], False)
        self.assertEqual(agent.diagnostics["v3_r02_step"]["rolled_back"], False)

    def test_startup_rolls_back_r02_and_l01_when_l01_swallow_reports_error(self):
        Probe = self.generated_probe()
        agent = Probe()
        route = [{"marker": "CANONICAL"}]
        routes = {"MAIN": route}
        controller = SimpleNamespace(R=routes, cur="MAIN", _fs_for={"cached": 7})
        agent.controller = controller
        agent.features = self.features()
        agent.diagnostics = {}

        def r02_install():
            route[:] = [{"marker": "R02_PLAN0"}]
            controller._fs_for = None
            agent._v3_r02 = {
                "plan": 0,
                "replaced": 719,
                "reasons": ["R02_seated:plan0"],
                "tapes": [[{"marker": "TAPE"}]],
            }
            agent.diagnostics["v3_r02"] = {
                "plan": 0,
                "replaced": 719,
                "reasons": ["R02_seated:plan0"],
            }

        def swallowed_l01_failure():
            route[:] = [{"marker": "BROKEN_L01"}]
            agent.diagnostics["v3_l01"] = {
                "activations": {},
                "reasons": ["V3_L01_ERROR_ValueError"],
            }

        agent._v3_r02_install = r02_install
        agent._v3_l01_install = swallowed_l01_failure
        agent._v3_r02_l01_install()

        self.assertIs(agent.controller.R, routes)
        self.assertIs(agent.controller.R["MAIN"], route)
        self.assertEqual(route, [{"marker": "CANONICAL"}])
        self.assertFalse(hasattr(agent, "_v3_r02"))
        self.assertEqual(controller._fs_for, {"cached": 7})
        self.assertEqual(
            agent.diagnostics["v3_l01_r02_init"],
            {"rolled_back": True, "error": "V3_L01_ERROR_ValueError"},
        )

    def test_startup_commits_r02_then_l01_on_success(self):
        Probe = self.generated_probe()
        agent = Probe()
        route = [{"marker": "CANONICAL"}]
        agent.controller = SimpleNamespace(R={"MAIN": route}, cur="MAIN", _fs_for={"cached": 7})
        agent.features = self.features()
        agent.diagnostics = {}

        def r02_install():
            route[:] = [{"marker": "R02_PLAN0"}]
            agent.controller._fs_for = None
            agent._v3_r02 = {
                "plan": 0,
                "replaced": 719,
                "reasons": ["R02_seated:plan0"],
                "tapes": [[{"marker": "TAPE"}]],
            }
            agent.diagnostics["v3_r02"] = {
                "plan": 0,
                "replaced": 719,
                "reasons": ["R02_seated:plan0"],
            }

        def successful_l01():
            route.append({"marker": "L01"})
            agent.diagnostics["v3_l01"] = {
                "activations": {"LAND": 1},
                "reasons": [],
            }

        agent._v3_r02_install = r02_install
        agent._v3_l01_install = successful_l01
        agent._v3_r02_l01_install()
        self.assertEqual(route, [{"marker": "R02_PLAN0"}, {"marker": "L01"}])
        self.assertEqual(
            agent.diagnostics["v3_l01_r02_init"],
            {"rolled_back": False, "l01_applied": True},
        )


if __name__ == "__main__":
    unittest.main()
