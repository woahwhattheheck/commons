# SPDX-License-Identifier: Apache-2.0
"""Predecessor-discriminating gates for Capillary same-turn priority custody."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
import uuid

import capillary_priority_guard as guard
from capillary_priority_guard import compile_priority_safe_jit_seed_routes
from jit_seed_staging import compile_jit_expensive_seed_routes as predecessor_compile


LAB = Path(__file__).resolve().parent
ENGINE = LAB / "reference" / "engine" / "kaggriculture.py"


def empty_route(length: int = 24):
    return [{"farmer": ["PASS"], "hands": [], "market": []} for _ in range(length)]


def add_plants(route, step: int, crop: str, quantity: int) -> None:
    rows = [["PLANT", crop] for _ in range(quantity)]
    route[step]["farmer"] = rows[0]
    route[step]["hands"] = rows[1:]


def candidate_route(target_market, *, max_orders: int = 3):
    route = empty_route()
    route[2]["market"] = [["BUY_SEED", "MELON", 1]]
    route[4]["market"] = deepcopy(target_market)
    add_plants(route, 5, "MELON", 1)
    return route, max_orders


def _load_official_engine() -> ModuleType:
    """Load the repository engine exactly; stub only its unused package import."""
    package = ModuleType("kaggle_environments")
    package.__path__ = []
    utils = ModuleType("kaggle_environments.utils")
    utils.resolve_episode_seed = lambda _env: 0
    package.utils = utils

    name = f"_capillary_priority_official_engine_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, ENGINE)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load official engine: {ENGINE}")
    module = importlib.util.module_from_spec(spec)
    previous_package = sys.modules.get("kaggle_environments")
    previous_utils = sys.modules.get("kaggle_environments.utils")
    sys.modules["kaggle_environments"] = package
    sys.modules["kaggle_environments.utils"] = utils
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
        if previous_package is None:
            sys.modules.pop("kaggle_environments", None)
        else:
            sys.modules["kaggle_environments"] = previous_package
        if previous_utils is None:
            sys.modules.pop("kaggle_environments.utils", None)
        else:
            sys.modules["kaggle_environments.utils"] = previous_utils
    return module


def _official_market_result(engine: ModuleType, market_rows, *, money: int = 1000):
    market = engine._new_market()
    farms = [engine._new_farm(10, money), engine._new_farm(10, 3000)]
    privates = [engine._new_private(), engine._new_private()]
    shared = {"market": market, "farms": farms, "day": 0, "hour": 0}
    observations = [
        SimpleNamespace(**shared, private=privates[0], player=0),
        SimpleNamespace(**shared, private=privates[1], player=1),
    ]
    state = [
        SimpleNamespace(
            observation=observations[0],
            action={"farmer": ["PASS"], "hands": [], "market": deepcopy(market_rows)},
        ),
        SimpleNamespace(
            observation=observations[1],
            action={"farmer": ["PASS"], "hands": [], "market": [],},
        ),
    ]
    configuration = SimpleNamespace(
        boardSize=10,
        maxMarketOrdersPerTurn=3,
        farmHandCostMult=1,
        shedCapacity=100,
    )
    engine._process_market(state, SimpleNamespace(configuration=configuration))
    return {
        "money": farms[0]["money"],
        "quadrants": list(farms[0]["unlocked_quadrants"]),
        "melon_seeds": privates[0]["seeds"]["MELON"],
    }


class PlacementPrimitiveTests(unittest.TestCase):
    def test_predecessor_uses_interior_hole_but_successor_uses_trailing_slot(self):
        before = {"market": [[], ["BUY_LAND"], []]}
        old = deepcopy(before)
        new = deepcopy(before)
        # Public predecessor behavior is the exact defect: first blank, slot 0.
        import jit_seed_staging
        placed, old_slot = jit_seed_staging._place_seed_order(old, "MELON", 1, 3)
        self.assertTrue(placed)
        self.assertEqual(old_slot, 0)

        placed, new_slot = guard._place_seed_order_after_inherited(new, "MELON", 1, 3)
        self.assertTrue(placed)
        self.assertEqual(new_slot, 2)
        self.assertEqual(new["market"][1], ["BUY_LAND"])

    def test_full_prefix_with_only_interior_hole_rejects_without_mutation(self):
        action = {"market": [["SELL", "WHEAT", 1], [], ["BUY_LAND"]]}
        before = deepcopy(action)
        placed, slot = guard._place_seed_order_after_inherited(action, "MELON", 1, 3)
        self.assertFalse(placed)
        self.assertIsNone(slot)
        self.assertEqual(action, before)

    def test_append_below_cap_is_after_all_inherited_rows(self):
        action = {"market": [["HIRE"], ["BUY_ANIMAL", "COW", 1]]}
        placed, slot = guard._place_seed_order_after_inherited(action, "MELON", 2, 4)
        self.assertTrue(placed)
        self.assertEqual(slot, 2)
        self.assertEqual(action["market"][-1], ["BUY_SEED", "MELON", 2])


class CompilerBoundaryTests(unittest.TestCase):
    def test_safe_trailing_hole_stages_and_binds_priority_receipt(self):
        route, cap = candidate_route([["SELL", "WHEAT", 1], [], []])
        staged, report = compile_priority_safe_jit_seed_routes(
            {"R": route}, max_orders=cap
        )
        self.assertTrue(report["certified"], report)
        self.assertTrue(report["priority_safety"]["safe"], report)
        self.assertEqual(
            staged["R"][4]["market"],
            [["SELL", "WHEAT", 1], ["BUY_SEED", "MELON", 1], []],
        )
        placement = report["priority_safety"]["placements"][0]
        self.assertGreater(placement["slot"], placement["last_inherited_nonblank_slot"])

    def test_interior_only_capacity_is_exact_priority_unsafe_rollback(self):
        route, cap = candidate_route([["SELL", "WHEAT", 1], [], ["BUY_LAND"]])
        predecessor, predecessor_report = predecessor_compile({"R": route}, max_orders=cap)
        self.assertTrue(predecessor_report["certified"])
        self.assertEqual(predecessor["R"][4]["market"][1], ["BUY_SEED", "MELON", 1])

        staged, report = compile_priority_safe_jit_seed_routes(
            {"R": route}, max_orders=cap
        )
        self.assertEqual(staged, {"R": route})
        self.assertFalse(report["certified"])
        self.assertEqual(report["reason"], "priority_unsafe")
        self.assertEqual(
            report["priority_safety"]["violations"][0]["reason"],
            "no_trailing_priority_safe_slot",
        )

    def test_one_unsafe_prediverged_route_rolls_back_all_routes(self):
        safe, cap = candidate_route([["HIRE"], [], []])
        unsafe, _ = candidate_route([["HIRE"], [], ["BUY_LAND"]])
        safe[0]["farmer"] = ["WEST"]
        unsafe[0]["farmer"] = ["EAST"]
        original = {"SAFE": safe, "UNSAFE": unsafe}
        staged, report = compile_priority_safe_jit_seed_routes(
            original, max_orders=cap
        )
        self.assertEqual(staged, original)
        self.assertFalse(report["certified"])
        self.assertEqual(report["reason"], "priority_unsafe")
        self.assertEqual(report["changed_routes"], [])

    def test_malformed_target_quantity_is_runtime_independent_fail_closed(self):
        route, cap = candidate_route([["BUY_SEED", "MELON", "bad"]])
        staged, report = compile_priority_safe_jit_seed_routes(
            {"R": route}, max_orders=cap
        )
        self.assertEqual(staged, {"R": route})
        self.assertFalse(report["certified"])
        self.assertEqual(report["reason"], "compiler_input_invalid")
        self.assertEqual(
            report["priority_safety"]["violations"][0]["error_type"],
            "ValueError",
        )

    def test_private_compiler_load_leaves_no_registry_root(self):
        module, source_sha256 = guard._load_private_staging()
        self.assertNotIn(module.__name__, sys.modules)
        self.assertIs(module._place_seed_order, guard._place_seed_order_after_inherited)
        self.assertEqual(len(source_sha256), 64)
        int(source_sha256, 16)


class OfficialInterpreterWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = _load_official_engine()

    def test_tail_placement_preserves_inherited_land_fill(self):
        control = [[], ["BUY_LAND"], []]
        predecessor = deepcopy(control)
        successor = deepcopy(control)

        import jit_seed_staging
        self.assertEqual(
            jit_seed_staging._place_seed_order(
                {"market": predecessor}, "MELON", 1, 3
            ),
            (True, 0),
        )
        # The helper above mutated a temporary wrapper around the same list.
        self.assertEqual(predecessor[0], ["BUY_SEED", "MELON", 1])

        self.assertEqual(
            guard._place_seed_order_after_inherited(
                {"market": successor}, "MELON", 1, 3
            ),
            (True, 2),
        )
        control_result = _official_market_result(self.engine, control)
        predecessor_result = _official_market_result(self.engine, predecessor)
        successor_result = _official_market_result(self.engine, successor)

        self.assertIn("NE", control_result["quadrants"])
        self.assertNotIn("NE", predecessor_result["quadrants"])
        self.assertIn("NE", successor_result["quadrants"])
        self.assertEqual(predecessor_result["melon_seeds"], 1)
        self.assertEqual(successor_result["melon_seeds"], 0)
        print(
            "CAPILLARY_PRIORITY_OFFICIAL_WITNESS="
            + json.dumps(
                {
                    "control": control_result,
                    "predecessor": predecessor_result,
                    "successor": successor_result,
                },
                sort_keys=True,
            )
        )


class ExactCurrentAdmissionTests(unittest.TestCase):
    def test_real_current_route_bank_remains_changed_and_priority_safe(self):
        import scheduler

        source = scheduler.parent.routes()
        before = deepcopy(source)
        staged, report = compile_priority_safe_jit_seed_routes(
            source,
            max_orders=10,
            turns_per_day=24,
        )
        receipt = {
            "route_count": len(source),
            "source_sha256": hashlib.sha256(
                json.dumps(before, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "staged_sha256": hashlib.sha256(
                json.dumps(staged, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "report": report,
        }
        print("CAPILLARY_PRIORITY_EXACT_CURRENT=" + json.dumps(receipt, sort_keys=True))
        self.assertEqual(source, before, receipt)
        self.assertEqual(len(source), 4, receipt)
        self.assertTrue(report.get("certified"), receipt)
        self.assertTrue(report.get("changed"), receipt)
        self.assertTrue(report.get("priority_safety", {}).get("safe"), receipt)
        self.assertNotEqual(staged, before, receipt)
        for placement in report["priority_safety"]["placements"]:
            self.assertGreater(
                placement["slot"],
                placement["last_inherited_nonblank_slot"],
                receipt,
            )


class EntrypointIsolationTests(unittest.TestCase):
    def _load(self):
        name = f"_capillary_entrypoint_test_{uuid.uuid4().hex}"
        path = LAB / "capillary_main.py"
        spec = importlib.util.spec_from_file_location(name, path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(name, None)
        return module

    def test_each_evaluator_load_owns_private_canonical_instance_state(self):
        left = self._load()
        right = self._load()
        self.assertIsNot(left._canonical_module(), right._canonical_module())
        self.assertIsNone(left._canonical_module()._INSTANCE)
        self.assertIsNone(right._canonical_module()._INSTANCE)
        marker = object()
        left._canonical_module()._INSTANCE = marker
        self.assertIs(left._canonical_module()._INSTANCE, marker)
        self.assertIsNone(right._canonical_module()._INSTANCE)
        self.assertFalse(any(
            value is left._canonical_module() or value is right._canonical_module()
            for value in sys.modules.values()
        ))


if __name__ == "__main__":
    unittest.main(verbosity=2)
