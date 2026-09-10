# SPDX-License-Identifier: Apache-2.0
"""Post-merge custody contracts for the executable SELL candidate."""
from __future__ import annotations

import ast
from collections.abc import Mapping
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
PATCH = HERE / "executable_sell_custody.py"
CANDIDATE = HERE / "candidate.py"


def load_patch():
    spec = importlib.util.spec_from_file_location("_sell_custody_pin_under_test", PATCH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {PATCH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P = load_patch()


class MappingController:
    ROUTE_ID = "7015cc00acfa4922"

    def __init__(self, route):
        self.R = {self.ROUTE_ID: route}
        self.cur = self.ROUTE_ID
        self.tag = "preserved"


class RecordingFrozen:
    def __init__(self, route):
        self.controller = MappingController(route)
        self.pending = {}
        self.planned = {}
        self.diagnostics = {}
        self.seen = None

    def cash_reserve(self, *_args, **_kwargs):
        return 0

    def transform(self, obs, config, selected):
        route = self.controller.R[self.controller.cur]
        self.seen = {
            "config": copy.deepcopy(dict(config)),
            "selected_market": copy.deepcopy(selected["market"]),
            "route_markets": [copy.deepcopy(action["market"]) for action in route],
        }
        return copy.deepcopy(selected)


def installed_agent(route):
    module = SimpleNamespace(FrozenSelected=RecordingFrozen, __file__=__file__)
    source_blob = P.git_blob_sha1(__file__)
    P.install(
        module,
        expected_frozen_blob=source_blob,
        expected_scheduler_blob=source_blob,
    )
    return module.FrozenSelected(route)


class OneShotMapping(Mapping):
    """Mapping whose second materialization raises after controller replacement."""

    def __init__(self, data):
        self._data = dict(data)
        self._iterations = 0

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        self._iterations += 1
        if self._iterations > 1:
            raise RuntimeError("second config copy")
        return iter(self._data)

    def __len__(self):
        return len(self._data)


def assigned_string(path: Path, name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == name:
            value = ast.literal_eval(node.value)
            if isinstance(value, str):
                values.append(value)
    if len(values) != 1:
        raise AssertionError(f"expected one string assignment for {name}, got {len(values)}")
    return values[0]


class SellCustodyPinTests(unittest.TestCase):
    def test_candidate_pin_matches_executable_patch_bytes(self):
        expected = assigned_string(CANDIDATE, "EXPECTED_PATCH_GIT_BLOB")
        self.assertEqual(expected, P.git_blob_sha1(PATCH))

    def test_zero_and_negative_limits_reach_delegate_as_official_one(self):
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [[], ["SELL", "CARROT", 3]],
        }
        for configured in (0, -7):
            with self.subTest(configured=configured):
                route = [copy.deepcopy(action), copy.deepcopy(action)]
                agent = installed_agent(route)
                controller = agent.controller
                config = {
                    "maxMarketOrdersPerTurn": configured,
                    "sentinel": "preserved",
                }
                original_config = copy.deepcopy(config)
                original_action = copy.deepcopy(action)
                original_route = copy.deepcopy(route)

                out = agent.transform({}, config, action)

                self.assertEqual(agent.seen["config"]["maxMarketOrdersPerTurn"], 1)
                self.assertEqual(agent.seen["config"]["sentinel"], "preserved")
                self.assertEqual(agent.seen["selected_market"], [[]])
                self.assertEqual(agent.seen["route_markets"], [[[]], [[]]])
                self.assertEqual(config, original_config)
                self.assertEqual(action, original_action)
                self.assertEqual(agent.controller.R[MappingController.ROUTE_ID], original_route)
                self.assertIs(agent.controller, controller)
                self.assertEqual(out, original_action)

    def test_controller_restores_when_second_config_copy_raises(self):
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [[], ["SELL", "CARROT", 3]],
        }
        agent = installed_agent([copy.deepcopy(action)])
        controller = agent.controller
        config = OneShotMapping(
            {
                "maxMarketOrdersPerTurn": 1,
                "sentinel": "preserved",
            }
        )

        with self.assertRaisesRegex(RuntimeError, "second config copy"):
            agent.transform({}, config, action)

        self.assertIs(agent.controller, controller)


if __name__ == "__main__":
    unittest.main()
