# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "overlay"))
import land_overlay as land


class DummyController:
    def __init__(self, routes):
        self.R = routes

    def act(self, obs):
        return deepcopy(self.R["MAIN"][int(obs["step"])])


class DummyAgent:
    def __init__(self, routes):
        self.controller = DummyController(routes)
        self.diagnostics = {}
        self.calls = 0

    def _initialize(self):
        self.calls += 1


class SpatialRebuilder:
    """Minimal predecessor matching SpatialTempo.install/_begin route behavior."""

    def __init__(self):
        self.calls = 0
        self._crop_routes = None

    def install(self, controller):
        pristine = controller.R
        self._crop_routes = pristine
        original = controller.act

        def act(obs):
            self.calls += 1
            controller.R = {key: list(rows) for key, rows in pristine.items()}
            return original(obs)

        controller.act = act


class SpatialAgent:
    def __init__(self, routes):
        self.source_routes = routes
        self.controller = None
        self.spatial = SpatialRebuilder()
        self.diagnostics = {}
        self.calls = 0

    def _initialize(self):
        self.calls += 1
        self.controller = DummyController(self.source_routes)
        self.spatial.install(self.controller)


class LandOverlayContracts(unittest.TestCase):
    @staticmethod
    def route(length=300):
        return [
            {"farmer": ["PASS"], "hands": [], "market": []}
            for _ in range(length)
        ]

    def test_exact_two_insertions_and_fallbacks_preserved(self):
        route = self.route()
        route[150]["market"] = [["BUY_LAND"]]
        route[265]["market"] = [["BUY_LAND"], ["BUY_SEED", "WHEAT", 2]]
        before = deepcopy(route)
        patched, report = land.patch_routes({"MAIN": route})
        self.assertEqual(report.insertions, 2)
        self.assertEqual(report.inserted_by_step, {"74": 1, "98": 1})
        self.assertEqual(patched["MAIN"][74]["market"], [["BUY_LAND"]])
        self.assertEqual(patched["MAIN"][98]["market"], [["BUY_LAND"]])
        self.assertEqual(patched["MAIN"][150], before[150])
        self.assertEqual(patched["MAIN"][265], before[265])
        self.assertEqual(route, before, "source route mutated")

    def test_copy_on_write_and_alias_preservation(self):
        shared = self.route()
        routes = {"a": shared, "b": shared}
        patched, report = land.patch_routes(routes)
        self.assertIs(routes["a"], shared)
        self.assertIs(patched["a"], patched["b"])
        self.assertIsNot(patched["a"], shared)
        self.assertIs(patched["a"][73], shared[73])
        self.assertIsNot(patched["a"][74], shared[74])
        self.assertIs(patched["a"][75], shared[75])
        self.assertEqual(shared[74]["market"], [])
        self.assertEqual(report.distinct_routes, 1)
        self.assertEqual(report.changed_routes, 1)
        self.assertEqual(report.insertions, 2)

    def test_duplicate_full_and_short_routes_fail_closed(self):
        duplicate = self.route()
        duplicate[74]["market"] = [["BUY_LAND"]]
        full = self.route()
        full[74]["market"] = [["PASS"]] * 10
        short = self.route(80)
        patched, report = land.patch_routes({"dup": duplicate, "full": full, "short": short})
        self.assertEqual(report.skipped_duplicate, 1)
        self.assertEqual(report.skipped_full, 1)
        self.assertEqual(report.skipped_short_route, 1)
        self.assertEqual(patched["dup"][74]["market"], [["BUY_LAND"]])
        self.assertEqual(patched["full"][74]["market"], [["PASS"]] * 10)
        self.assertEqual(len(patched["short"]), 80)

    def test_wrap_installs_before_first_production_and_only_once_per_controller(self):
        route = self.route()
        agent = DummyAgent({"MAIN": route})
        wrapped = land.wrap(agent)
        self.assertIs(wrapped, agent)
        agent._initialize()
        first = agent.controller.R
        agent._initialize()
        self.assertIs(agent.controller.R, first)
        self.assertEqual(agent.calls, 2)
        self.assertEqual(agent._land_7498_report.insertions, 2)
        self.assertFalse(agent._land_7498_spatial_rebound)

    def test_wrap_reinstalls_after_controller_replacement(self):
        agent = DummyAgent({"MAIN": self.route()})
        land.wrap(agent)
        agent._initialize()
        first_controller = agent.controller
        self.assertEqual(first_controller.R["MAIN"][74]["market"], [["BUY_LAND"]])

        replacement_source = self.route()
        agent.controller = DummyController({"MAIN": replacement_source})
        agent._initialize()

        self.assertIsNot(agent.controller, first_controller)
        self.assertEqual(agent.controller.R["MAIN"][74]["market"], [["BUY_LAND"]])
        self.assertEqual(agent.controller.R["MAIN"][98]["market"], [["BUY_LAND"]])
        self.assertEqual(replacement_source[74]["market"], [])
        self.assertIs(agent._land_7498_controller, agent.controller)

    def test_spatial_predecessor_keeps_candidate_rows_live_and_control_isolated(self):
        source = {"MAIN": self.route()}
        before = deepcopy(source)
        agent = SpatialAgent(source)
        land.wrap(agent)
        agent._initialize()

        installed = agent.controller.R
        self.assertIsNot(installed, source)
        self.assertIs(agent.spatial._crop_routes, installed)
        self.assertTrue(agent._land_7498_spatial_rebound)
        self.assertTrue(agent.diagnostics["land_74_98"]["spatial_pristine_rebound"])

        # SpatialTempo-style _begin rebuilds controller.R from its captured
        # pristine mapping before the producer reads the current step.
        first = agent.controller.act({"step": 74})
        second = agent.controller.act({"step": 98})
        self.assertIn(["BUY_LAND"], first["market"])
        self.assertIn(["BUY_LAND"], second["market"])

        # The shared source remains byte/value clean for a same-process control.
        self.assertEqual(source, before)
        control = DummyController(source)
        self.assertNotIn(["BUY_LAND"], control.act({"step": 74})["market"])
        self.assertNotIn(["BUY_LAND"], control.act({"step": 98})["market"])

        # Reconstructing the controller creates a fresh captured mapping; the
        # wrapper must bind that predecessor again rather than trust agent state.
        first_controller = agent.controller
        agent._initialize()
        self.assertIsNot(agent.controller, first_controller)
        self.assertTrue(agent._land_7498_spatial_rebound)
        self.assertIn(["BUY_LAND"], agent.controller.act({"step": 74})["market"])
        self.assertIn(["BUY_LAND"], agent.controller.act({"step": 98})["market"])
        self.assertEqual(source, before)

    def test_unrecognized_spatial_wrapper_fails_before_route_publication(self):
        source = {"MAIN": self.route()}
        agent = DummyAgent(source)
        agent.spatial = object()
        original = agent.controller.R
        with self.assertRaisesRegex(RuntimeError, "SpatialTempo producer wrapper"):
            land.install(agent)
        self.assertIs(agent.controller.R, original)
        self.assertEqual(source["MAIN"][74]["market"], [])

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(TypeError):
            land.patch_routes([])
        with self.assertRaises(ValueError):
            land.patch_routes({}, max_orders=0)
        with self.assertRaises(ValueError):
            land.patch_routes({}, land_steps=(74, 74))

    def test_official_extracted_buy_land_cost_and_order(self):
        mechanics_path = next(
            (ancestor / "mechanics.py" for ancestor in (ROOT, *ROOT.parents)
             if (ancestor / "mechanics.py").is_file()),
            None,
        )
        if mechanics_path is None:
            self.skipTest("official extracted mechanics.py is unavailable in this staging tree")
        spec = importlib.util.spec_from_file_location("land_test_mechanics", mechanics_path)
        mechanics = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mechanics)
        board = 10
        tiles = []
        for y in range(board):
            row = []
            for x in range(board):
                quadrant = ("N" if y < 5 else "S") + ("W" if x < 5 else "E")
                row.append(None if quadrant == "NW" else "LOCKED")
            tiles.append(row)
        farm = {
            "money": 4000,
            "unlocked_quadrants": ["NW"],
            "tiles": tiles,
            "farmer": [4, 4],
            "hands": [],
            "hires_today": 0,
        }
        mechanics._do_buy_land(farm, board)
        self.assertEqual(farm["unlocked_quadrants"], ["NW", "NE"])
        self.assertEqual(farm["money"], 3000)
        mechanics._do_buy_land(farm, board)
        self.assertEqual(farm["unlocked_quadrants"], ["NW", "NE", "SW"])
        self.assertEqual(farm["money"], 1000)
        self.assertIsNone(farm["tiles"][1][7])
        self.assertIsNone(farm["tiles"][7][1])


if __name__ == "__main__":
    unittest.main()
