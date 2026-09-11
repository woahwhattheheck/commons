#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ast
from collections import Counter
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import apply_repair as repair


def _decode(fragment: str) -> str:
    tree = ast.parse("VALUE = (\n" + fragment + ")\n")
    return ast.literal_eval(tree.body[0].value)


def _probe_class():
    namespace = {}
    exec("class Probe:\n" + _decode(repair.ROUTE_INSTALL_METHOD), namespace)
    return namespace["Probe"]


class _Features:
    r02_route_bank = True
    l01_land = True
    l01_sheep = False
    l01_day0buy = False
    l01_leanplant = False


class _Controller:
    def __init__(self):
        self.R = {"MAIN": [{"tag": "canonical"}]}
        self._fs_for = "cache"


def _fake_modules(*, fail_patch=False, fail_l01=False, fail_r02=False, calls=None):
    calls = calls if calls is not None else []

    l01 = types.ModuleType("l01_mechanics")
    l01.flags_from_features = lambda f: {
        "LAND": f.l01_land,
        "SHEEP": f.l01_sheep,
        "DAY0BUY": f.l01_day0buy,
        "LEANPLANT": f.l01_leanplant,
        "TRANCHE": False,
    }

    def patch_routes(routes, flags, activations, reasons):
        calls.append("patch_tapes")
        if fail_patch:
            raise RuntimeError("patch")
        for route in routes.values():
            route[0]["l01"] = True
            activations["LAND"] += 1

    l01.patch_routes = patch_routes

    def install_l01(agent, flags):
        calls.append("install_l01")
        agent.controller.R["MAIN"][0]["live_l01"] = True
        if fail_l01:
            raise RuntimeError("l01")
        return {"activations": Counter({"LAND": 1}), "reasons": []}

    l01.install = install_l01

    tapes = types.ModuleType("r01_tapes")
    tapes.load_tapes = lambda: [
        [{"tag": "plan0"}],
        [{"tag": "plan1"}],
    ]

    r02 = types.ModuleType("r02_route_bank")

    def install_r02(agent, enabled, tapes=None):
        calls.append("install_r02")
        agent.controller.R["MAIN"][:] = deepcopy(tapes[0])
        agent.controller._fs_for = None
        agent._v3_r02 = {
            "plan": 0,
            "replaced": 1,
            "reasons": ["seated"],
            "tapes": tapes,
        }
        if fail_r02:
            raise RuntimeError("r02")
        return agent._v3_r02

    r02.install = install_r02
    return {
        "l01_mechanics": l01,
        "r01_tapes": tapes,
        "r02_route_bank": r02,
    }, calls


def _agent():
    probe = _probe_class()
    agent = probe()
    agent.features = _Features()
    agent.controller = _Controller()
    agent.diagnostics = {}
    agent._v3_r02 = None
    agent.fallback_calls = 0

    def fallback_l01():
        agent.fallback_calls += 1
        agent.controller.R["MAIN"][0]["fallback_l01"] = True

    def fallback_r02():
        raise AssertionError("composed path must not call fallback R02 installer")

    agent._v3_l01_install = fallback_l01
    agent._v3_r02_install = fallback_r02
    return agent


class CarrierTransformTests(unittest.TestCase):
    def fixture(self) -> str:
        return (
            "prefix\n"
            + repair.INIT_OLD
            + "\n"
            + repair.R02_BOUNDARY_OLD
            + "suffix\n"
        )

    def test_transform_changes_only_the_two_owned_anchors(self):
        source = self.fixture()
        repaired = repair.transform(source)
        self.assertEqual(repaired.count(repair.INIT_NEW), 1)
        self.assertEqual(repaired.count(repair.ROUTE_INSTALL_METHOD), 1)
        self.assertNotIn(repair.INIT_OLD, repaired)
        self.assertNotIn(repair.R02_BOUNDARY_OLD, repaired)
        self.assertTrue(repaired.startswith("prefix\n"))
        self.assertTrue(repaired.endswith("suffix\n"))

    def test_generated_route_install_method_is_valid_python(self):
        method = _decode(repair.ROUTE_INSTALL_METHOD)
        self.assertIn("patch_routes", method)
        self.assertIn("install_r02(self, True, tapes=tapes)", method)
        self.assertIn("'r02_installed': False", method)
        ast.parse("class Probe:\n" + method)

    def test_second_application_fails_closed(self):
        repaired = repair.transform(self.fixture())
        with self.assertRaisesRegex(ValueError, "initialize composition seam"):
            repair.transform(repaired)

    def test_duplicate_anchor_fails_closed(self):
        source = self.fixture() + repair.INIT_OLD
        with self.assertRaisesRegex(ValueError, "initialize composition seam"):
            repair.transform(source)

    def test_apply_file_rejects_unbound_preimage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "apply_v3.py"
            path.write_text(self.fixture(), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "preimage drift"):
                repair.apply_file(path)


class ExecutableCompositionTests(unittest.TestCase):
    def test_success_pretransforms_every_r02_tape_before_seating(self):
        agent = _agent()
        modules, calls = _fake_modules()
        with patch.dict(sys.modules, modules):
            agent._v3_route_install()
        self.assertEqual(calls, ["patch_tapes", "install_l01", "install_r02"])
        self.assertTrue(agent.controller.R["MAIN"][0]["l01"])
        self.assertTrue(all(tape[0]["l01"] for tape in agent._v3_r02["tapes"]))
        self.assertTrue(agent.diagnostics["v3_l01_r02"]["composed"])
        self.assertFalse(agent.diagnostics["v3_l01_r02"]["rolled_back"])
        self.assertEqual(agent.fallback_calls, 0)

    def test_future_switch_source_is_already_l01_transformed(self):
        agent = _agent()
        modules, _ = _fake_modules()
        with patch.dict(sys.modules, modules):
            agent._v3_route_install()
        future_tape = deepcopy(agent._v3_r02["tapes"][1])
        agent.controller.R["MAIN"][:] = future_tape
        self.assertTrue(agent.controller.R["MAIN"][0]["l01"])
        self.assertEqual(agent.controller.R["MAIN"][0]["tag"], "plan1")

    def test_l01_failure_never_installs_r02_and_rolls_back_then_falls_back(self):
        agent = _agent()
        modules, calls = _fake_modules(fail_l01=True)
        with patch.dict(sys.modules, modules):
            agent._v3_route_install()
        self.assertEqual(calls, ["patch_tapes", "install_l01"])
        self.assertNotIn("live_l01", agent.controller.R["MAIN"][0])
        self.assertTrue(agent.controller.R["MAIN"][0]["fallback_l01"])
        self.assertIsNone(agent._v3_r02)
        report = agent.diagnostics["v3_l01_r02"]
        self.assertFalse(report["composed"])
        self.assertTrue(report["rolled_back"])
        self.assertFalse(report["r02_installed"])
        self.assertEqual(report["error"], "RuntimeError")

    def test_partial_r02_failure_rolls_back_route_cache_and_state(self):
        agent = _agent()
        modules, calls = _fake_modules(fail_r02=True)
        with patch.dict(sys.modules, modules):
            agent._v3_route_install()
        self.assertEqual(calls, ["patch_tapes", "install_l01", "install_r02"])
        self.assertEqual(agent.controller.R["MAIN"][0]["tag"], "canonical")
        self.assertTrue(agent.controller.R["MAIN"][0]["fallback_l01"])
        self.assertEqual(agent.controller._fs_for, "cache")
        self.assertIsNone(agent._v3_r02)
        report = agent.diagnostics["v3_l01_r02"]
        self.assertFalse(report["composed"])
        self.assertTrue(report["rolled_back"])
        self.assertFalse(report["r02_installed"])

    def test_tape_patch_failure_never_touches_live_r02(self):
        agent = _agent()
        modules, calls = _fake_modules(fail_patch=True)
        with patch.dict(sys.modules, modules):
            agent._v3_route_install()
        self.assertEqual(calls, ["patch_tapes"])
        self.assertEqual(agent.controller.R["MAIN"][0]["tag"], "canonical")
        self.assertTrue(agent.controller.R["MAIN"][0]["fallback_l01"])
        self.assertIsNone(agent._v3_r02)

    def test_noncomposed_path_uses_existing_helpers_in_l01_then_r02_order(self):
        probe = _probe_class()
        agent = probe()
        features = _Features()
        features.r02_route_bank = False
        agent.features = features
        agent.controller = _Controller()
        agent.diagnostics = {}
        calls = []
        agent._v3_l01_install = lambda: calls.append("l01")
        agent._v3_r02_install = lambda: calls.append("r02")
        agent._v3_route_install()
        self.assertEqual(calls, ["l01", "r02"])


if __name__ == "__main__":
    unittest.main()
