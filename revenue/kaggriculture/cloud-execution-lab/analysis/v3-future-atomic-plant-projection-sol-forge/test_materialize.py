#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Predecessor-killing contracts for the future atomic PLANT repair packet."""
from __future__ import annotations

import ast
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("sol_forge_materialize", HERE / "materialize.py")
materialize = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(materialize)


class FakeMechanics:
    """Small deterministic unit-stage model used only to test packet admission."""

    @staticmethod
    def _inventory(private, actor):
        while len(private["inventories"]) <= actor:
            private["inventories"].append({})
        return private["inventories"][actor]

    @classmethod
    def _apply_unit_action(
        cls,
        farm,
        private,
        actor,
        action,
        board_size,
        day,
        turns_per_day,
        shed_capacity,
    ):
        farm.setdefault("calls", []).append(copy.deepcopy(action))
        if not isinstance(action, list) or not action:
            return
        op = action[0]
        if op == "PASS":
            return
        tile = farm["tiles"][actor]
        if op == "PLANT" and len(action) >= 2:
            crop = action[1]
            if tile is not None or private["seeds"].get(crop, 0) <= 0:
                return
            private["seeds"][crop] -= 1
            farm["tiles"][actor] = {"kind": "PLANT", "crop": crop}
            return
        if op == "BUILD_PASTURE":
            if tile is None:
                farm["tiles"][actor] = {"kind": "PASTURE"}
            return
        if op == "PLACE" and len(action) >= 2:
            animal = action[1]
            inv = cls._inventory(private, actor)
            if not (isinstance(tile, dict) and tile.get("kind") == "PASTURE"):
                return
            if inv.get(animal, 0) <= 0:
                return
            inv[animal] -= 1
            if inv[animal] == 0:
                del inv[animal]
            tile["animal"] = animal

    @staticmethod
    def _drop_inventories_to_shed(private, shed_capacity):
        for inv in private["inventories"]:
            for item in list(inv):
                while inv.get(item, 0) > 0 and sum(private["shed"].values()) < shed_capacity:
                    inv[item] -= 1
                    private["shed"][item] = private["shed"].get(item, 0) + 1
                if inv.get(item, 0) == 0:
                    inv.pop(item, None)


def _helper_from(candidate: Path):
    tree = ast.parse(candidate.read_text(encoding="utf-8"), filename=str(candidate))
    node = next(
        n for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name == "_apply_unit_packet"
    )
    module = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"m": FakeMechanics}
    exec(compile(module, str(candidate), "exec"), namespace)
    return namespace["_apply_unit_packet"], tree


def _blank_state(*, wheat_seeds=1, carrot_seeds=0, cow=False, shed=0):
    farm = {"tiles": [None, None], "calls": []}
    private = {
        "seeds": {"WHEAT": wheat_seeds, "CARROT": carrot_seeds},
        "inventories": [{"COW": 1} if cow else {}, {}],
        "shed": {"WHEAT": shed, "COW": 0},
    }
    return farm, private


def _apply_old_sequential(farm, private, action):
    acts = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
    for actor, selected in enumerate(acts):
        FakeMechanics._apply_unit_action(
            farm, private, actor, selected, 2, 0, 24, 10**6
        )


class FutureAtomicProjectionContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.candidate = cls.root / "candidate" / "scheduler.py"
        cls.receipt_path = cls.root / "candidate" / "RECEIPT.json"
        cls.source_before = materialize.DEFAULT_SOURCE.read_bytes()
        cls.receipt = materialize.materialize(
            materialize.DEFAULT_SOURCE,
            materialize.DEFAULT_ENGINE,
            cls.candidate,
            cls.receipt_path,
        )
        helper, cls.tree = _helper_from(cls.candidate)
        cls.helper = staticmethod(helper)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def apply(self, farm, private, action):
        return self.helper(
            farm,
            private,
            action,
            board_size=2,
            day=0,
            turns_per_day=24,
            shed_capacity=10**6,
        )

    def test_exact_source_and_engine_are_bound(self):
        self.assertEqual(
            materialize.git_blob(materialize.DEFAULT_SOURCE.read_bytes()),
            materialize.BASE_SCHEDULER_GIT_BLOB,
        )
        self.assertEqual(
            materialize.git_blob(materialize.DEFAULT_ENGINE.read_bytes()),
            materialize.OFFICIAL_ENGINE_GIT_BLOB,
        )
        self.assertEqual(self.receipt["base_main"], materialize.BASE_MAIN)

    def test_oversubscribed_same_crop_blocks_every_request(self):
        farm, private = _blank_state(wheat_seeds=1)
        action = {
            "farmer": ["PLANT", "WHEAT"],
            "hands": [["PLANT", "WHEAT"]],
            "market": [],
        }
        before = copy.deepcopy(action)
        blocked = self.apply(farm, private, action)
        self.assertEqual(blocked, {"WHEAT"})
        self.assertEqual(private["seeds"]["WHEAT"], 1)
        self.assertEqual(farm["tiles"], [None, None])
        self.assertEqual(farm["calls"], [["PASS"], ["PASS"]])
        self.assertEqual(action, before)

    def test_exact_supply_plants_both_in_actor_order(self):
        farm, private = _blank_state(wheat_seeds=2)
        blocked = self.apply(
            farm,
            private,
            {
                "farmer": ["PLANT", "WHEAT"],
                "hands": [["PLANT", "WHEAT"]],
            },
        )
        self.assertEqual(blocked, set())
        self.assertEqual(private["seeds"]["WHEAT"], 0)
        self.assertEqual([tile["crop"] for tile in farm["tiles"]], ["WHEAT", "WHEAT"])

    def test_mixed_crop_blocks_only_the_oversubscribed_crop(self):
        farm, private = _blank_state(wheat_seeds=0, carrot_seeds=1)
        blocked = self.apply(
            farm,
            private,
            {
                "farmer": ["PLANT", "WHEAT"],
                "hands": [["PLANT", "CARROT"]],
            },
        )
        self.assertEqual(blocked, {"WHEAT"})
        self.assertIsNone(farm["tiles"][0])
        self.assertEqual(farm["tiles"][1]["crop"], "CARROT")
        self.assertEqual(private["seeds"]["CARROT"], 0)

    def test_predecessor_sequential_projection_is_killed(self):
        action = {
            "farmer": ["PLANT", "WHEAT"],
            "hands": [["PLANT", "WHEAT"]],
        }
        old_farm, old_private = _blank_state(wheat_seeds=1)
        new_farm, new_private = copy.deepcopy(old_farm), copy.deepcopy(old_private)
        _apply_old_sequential(old_farm, old_private, action)
        self.apply(new_farm, new_private, action)
        self.assertEqual(old_private["seeds"]["WHEAT"], 0)
        self.assertEqual(sum(tile is not None for tile in old_farm["tiles"]), 1)
        self.assertEqual(new_private["seeds"]["WHEAT"], 1)
        self.assertEqual(new_farm["tiles"], [None, None])

    def test_minimized_shed_capacity_to_sell_feasibility_witness(self):
        """False sequential plant blocks PLACE; carried cow then overfills at EOD."""
        oversubscribed = {
            "farmer": ["PLANT", "WHEAT"],
            "hands": [["PLANT", "WHEAT"]],
        }
        build = {"farmer": ["BUILD_PASTURE"], "hands": [["PASS"]]}
        place = {"farmer": ["PLACE", "COW"], "hands": [["PASS"]]}

        old_farm, old_private = _blank_state(wheat_seeds=1, cow=True, shed=99)
        new_farm, new_private = copy.deepcopy(old_farm), copy.deepcopy(old_private)
        _apply_old_sequential(old_farm, old_private, oversubscribed)
        self.apply(new_farm, new_private, oversubscribed)
        for packet in (build, place):
            _apply_old_sequential(old_farm, old_private, packet)
            self.apply(new_farm, new_private, packet)
        FakeMechanics._drop_inventories_to_shed(old_private, 10**6)
        FakeMechanics._drop_inventories_to_shed(new_private, 10**6)

        old_total = sum(old_private["shed"].values())
        new_total = sum(new_private["shed"].values())
        self.assertEqual((old_total, new_total), (100, 99))
        cap = 100
        old_feasible = not (old_total > cap - 1)
        new_feasible = not (new_total > cap - 1)
        self.assertFalse(old_feasible)
        self.assertTrue(new_feasible)

    def test_only_shared_primitive_directly_calls_unit_mechanics(self):
        direct_call_owners = []
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and func.attr == "_apply_unit_action"
                and isinstance(func.value, ast.Name)
                and func.value.id == "m"
            ):
                continue
            owner = next(
                (
                    candidate.name
                    for candidate in ast.walk(self.tree)
                    if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node in list(ast.walk(candidate))
                ),
                None,
            )
            direct_call_owners.append(owner)
        self.assertEqual(direct_call_owners, ["_apply_unit_packet"])

    def test_both_current_and_future_paths_use_shared_primitive(self):
        post = next(
            node for node in self.tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "post_units"
        )
        scheduler_class = next(
            node for node in self.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "SellScheduler"
        )
        receipt = next(
            node for node in scheduler_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "receipt_profile"
        )

        def calls_named(node, name):
            return [
                call for call in ast.walk(node)
                if isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == name
            ]

        self.assertEqual(len(calls_named(post, "_apply_unit_packet")), 1)
        self.assertEqual(len(calls_named(receipt, "_apply_unit_packet")), 1)

    def test_materialization_is_deterministic_and_nonmutating(self):
        with tempfile.TemporaryDirectory() as other:
            other = Path(other)
            second_output = other / "scheduler.py"
            second_receipt = other / "receipt.json"
            receipt = materialize.materialize(
                materialize.DEFAULT_SOURCE,
                materialize.DEFAULT_ENGINE,
                second_output,
                second_receipt,
            )
            self.assertEqual(second_output.read_bytes(), self.candidate.read_bytes())
            self.assertEqual(receipt["candidate"]["git_blob"], self.receipt["candidate"]["git_blob"])
            self.assertEqual(receipt["candidate"]["sha256"], self.receipt["candidate"]["sha256"])
        self.assertEqual(materialize.DEFAULT_SOURCE.read_bytes(), self.source_before)

    def test_source_drift_fails_before_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            drifted = temporary / "scheduler.py"
            drifted.write_bytes(materialize.DEFAULT_SOURCE.read_bytes() + b"# drift\n")
            output = temporary / "candidate.py"
            with self.assertRaisesRegex(RuntimeError, "scheduler source drift"):
                materialize.materialize(
                    drifted,
                    materialize.DEFAULT_ENGINE,
                    output,
                    temporary / "receipt.json",
                )
            self.assertFalse(output.exists())

    def test_receipt_is_strict_json_and_makes_no_strength_claim(self):
        parsed = json.loads(self.receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(parsed, self.receipt)
        self.assertFalse(parsed["canonical_source_mutated"])
        self.assertFalse(parsed["score_claim"])
        self.assertEqual(parsed["disposition"], "SOURCE_REAL_ACTION_UNMEASURED")
        self.assertEqual(
            parsed["replacements"],
            {
                "future_receipt_profile_callsite": 1,
                "shared_atomic_unit_packet": 1,
            },
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
