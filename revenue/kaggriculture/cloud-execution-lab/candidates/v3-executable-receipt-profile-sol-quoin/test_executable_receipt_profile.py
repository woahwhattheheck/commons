# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest import mock

from executable_receipt_profile import (
    executable_market_prefix,
    git_blob_sha1,
    install,
)

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]


class _Base:
    def receipt_profile(self, obs, selected, farm, private, end, item, config):
        route = self.controller.R[self.controller.cur]
        return [selected.get("market", [])] + [
            route[t].get("market", []) for t in range(int(obs["step"]), end + 1)
        ]


def _fake_module(path: Path):
    return SimpleNamespace(__file__=str(path), FrozenSelected=_Base)


class PrefixViewUnitTests(unittest.TestCase):
    def test_action_view_slices_without_mutating_input(self):
        action = {"farmer": ["PASS"], "market": [[], ["HIRE"], ["BUY_LAND"]]}
        before = copy.deepcopy(action)
        viewed = executable_market_prefix(action, 2)
        self.assertEqual(viewed["market"], [[], ["HIRE"]])
        self.assertEqual(action, before)
        self.assertIsNot(viewed, action)

    def test_non_dict_and_non_list_payloads_preserve_predecessor_shape(self):
        self.assertEqual(executable_market_prefix(["PASS"], 1), ["PASS"])
        action = {"market": "malformed"}
        self.assertEqual(executable_market_prefix(action, 1), action)

    def test_installed_wrapper_slices_current_and_future_queues(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "frozen_selected.py"
            source.write_text("# fake frozen selected\n", encoding="utf-8")
            module = _fake_module(source)
            frozen_blob = git_blob_sha1(source)
            scheduler_blob = git_blob_sha1(Path(__file__))
            receipt = install(
                module,
                expected_frozen_blob=frozen_blob,
                expected_scheduler_blob=scheduler_blob,
            )
            obj = object.__new__(module.FrozenSelected)
            original_route = [
                {"market": [["HIRE"], ["BUY_LAND"]]},
                {"market": [[], ["BUY_ANIMAL", "GOOSE", 2]]},
            ]
            obj.controller = SimpleNamespace(cur=0, R=[original_route])
            selected = {"market": [[], ["SELL", "CARROT", 3]]}
            before_selected = copy.deepcopy(selected)
            before_route = copy.deepcopy(original_route)
            seen = obj.receipt_profile(
                {"step": 0}, selected, {}, {}, 1, "CARROT",
                {"maxMarketOrdersPerTurn": 1},
            )
            self.assertTrue(receipt["installed"])
            self.assertEqual(seen, [[[]], [["HIRE"]], [[]]])
            self.assertEqual(selected, before_selected)
            self.assertEqual(original_route, before_route)

    def test_zero_config_uses_official_minimum_one_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "frozen_selected.py"
            source.write_text("# fake frozen selected zero\n", encoding="utf-8")
            module = _fake_module(source)
            install(
                module,
                expected_frozen_blob=git_blob_sha1(source),
                expected_scheduler_blob=git_blob_sha1(Path(__file__)),
            )
            obj = object.__new__(module.FrozenSelected)
            obj.controller = SimpleNamespace(
                cur=0, R=[[{"market": [["HIRE"], ["BUY_LAND"]]}]]
            )
            seen = obj.receipt_profile(
                {"step": 0}, {"market": [["HIRE"], ["BUY_LAND"]]},
                {}, {}, 0, "CARROT", {"maxMarketOrdersPerTurn": 0},
            )
            self.assertEqual(seen, [[["HIRE"]], [["HIRE"]]])

    def test_install_is_idempotent_and_rejects_conflicting_source_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "frozen_selected.py"
            source.write_text("# fake frozen selected idempotent\n", encoding="utf-8")
            module = _fake_module(source)
            frozen_blob = git_blob_sha1(source)
            scheduler_blob = git_blob_sha1(Path(__file__))
            first = install(
                module,
                expected_frozen_blob=frozen_blob,
                expected_scheduler_blob=scheduler_blob,
            )
            second = install(
                module,
                expected_frozen_blob=frozen_blob,
                expected_scheduler_blob=scheduler_blob,
            )
            self.assertTrue(first["installed"])
            self.assertTrue(second["idempotent"])
            with self.assertRaisesRegex(RuntimeError, "different source bytes"):
                install(
                    module,
                    expected_frozen_blob="0" * 40,
                    expected_scheduler_blob=scheduler_blob,
                )

    def test_source_drift_fails_before_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "frozen_selected.py"
            source.write_text("# unexpected bytes\n", encoding="utf-8")
            module = _fake_module(source)
            with self.assertRaisesRegex(RuntimeError, "source drift"):
                install(
                    module,
                    expected_frozen_blob="f" * 40,
                    expected_scheduler_blob=git_blob_sha1(Path(__file__)),
                )
            self.assertIs(module.FrozenSelected, _Base)


@unittest.skipUnless((LAB / "frozen_selected.py").is_file(), "repository source unavailable")
class ExactRepositoryWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if str(LAB) not in sys.path:
            sys.path.insert(0, str(LAB))
        import frozen_selected

        cls.fs = frozen_selected
        cls.predecessor = frozen_selected.FrozenSelected

    @staticmethod
    def _physical_state():
        farm = {
            "money": 0,
            "hires_today": 0,
            "unlocked_quadrants": ["NW"],
            "hands": [],
            "tiles": [[None for _ in range(10)] for _ in range(10)],
        }
        shed = {name: 0 for name in [
            "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "EGG", "MILK", "WOOL", "FERTILIZER", "GOOSE", "COW", "SHEEP",
        ]}
        shed["CARROT"] = 3
        private = {"shed": shed, "seeds": {}, "inventories": [{}]}
        return farm, private

    def _profile(self, cls, route):
        fs = self.fs
        obj = object.__new__(cls)
        obj.controller = SimpleNamespace(cur=0, R=[route])
        farm, private = self._physical_state()

        def projected(*_args, **_kwargs):
            return copy.deepcopy(farm), copy.deepcopy(private)

        with mock.patch.object(fs, "post_units", side_effect=projected), \
             mock.patch.object(fs.m, "_apply_unit_action", return_value=None):
            return obj.receipt_profile(
                {"step": 0},
                {"farmer": ["PASS"], "hands": [], "market": []},
                farm,
                private,
                2,
                "CARROT",
                {"shedCapacity": 4, "maxMarketOrdersPerTurn": 1},
            )

    def test_inactive_animal_purchase_no_longer_forces_early_liquidation(self):
        route = [
            {"farmer": ["PASS"], "hands": [], "market": []},
            {"farmer": ["PASS"], "hands": [],
             "market": [[], ["BUY_ANIMAL", "GOOSE", 2]]},
            {"farmer": ["PASS"], "hands": [], "market": []},
        ]
        predecessor_feasible = self._profile(self.predecessor, route)
        self.assertFalse(predecessor_feasible(((0, 0), (2, 3))))
        self.assertTrue(predecessor_feasible(((0, 2), (2, 1))))

        receipt = install(self.fs)
        candidate_feasible = self._profile(self.fs.FrozenSelected, route)
        self.assertTrue(receipt["installed"] or receipt["idempotent"])
        self.assertTrue(candidate_feasible(((0, 0), (2, 3))))

    def test_active_prefix_behavior_is_unchanged(self):
        route = [
            {"farmer": ["PASS"], "hands": [], "market": []},
            {"farmer": ["PASS"], "hands": [],
             "market": [["BUY_ANIMAL", "GOOSE", 2], []]},
            {"farmer": ["PASS"], "hands": [], "market": []},
        ]
        predecessor_feasible = self._profile(self.predecessor, route)
        install(self.fs)
        candidate_feasible = self._profile(self.fs.FrozenSelected, route)
        plans = [
            ((0, 0), (2, 3)),
            ((0, 1), (2, 2)),
            ((0, 2), (2, 1)),
            ((0, 3),),
        ]
        self.assertEqual(
            [predecessor_feasible(plan) for plan in plans],
            [candidate_feasible(plan) for plan in plans],
        )

    def test_preserved_engine_ignores_suffix_and_clips_active_purchase_to_capacity(self):
        engine_path = LAB / "reference" / "engine" / "kaggriculture.py"
        spec = importlib.util.spec_from_file_location("_sol_quoin_engine", engine_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        engine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(engine)

        def state_for(max_orders, rows):
            farms = [engine._new_farm(10, 1000), engine._new_farm(10, 1000)]
            privates = [engine._new_private(), engine._new_private()]
            privates[0]["shed"]["CARROT"] = 3
            market = engine._new_market()
            obs0 = SimpleNamespace(market=market, farms=farms)
            states = [
                SimpleNamespace(
                    action={"market": rows},
                    observation=SimpleNamespace(private=privates[0]),
                ),
                SimpleNamespace(
                    action={"market": []},
                    observation=SimpleNamespace(private=privates[1]),
                ),
            ]
            states[0].observation.market = market
            states[0].observation.farms = farms
            env = SimpleNamespace(configuration={
                "boardSize": 10,
                "maxMarketOrdersPerTurn": max_orders,
                "farmHandCostMult": 1,
                "shedCapacity": 4,
            })
            return states, env, privates

        states, env, privates = state_for(
            1, [[], ["BUY_ANIMAL", "GOOSE", 2]]
        )
        engine._process_market(states, env)
        self.assertEqual(privates[0]["shed"]["GOOSE"], 0)
        self.assertEqual(sum(privates[0]["shed"].values()), 3)

        states, env, privates = state_for(
            2, [[], ["BUY_ANIMAL", "GOOSE", 2]]
        )
        engine._process_market(states, env)
        self.assertEqual(privates[0]["shed"]["GOOSE"], 1)
        self.assertEqual(sum(privates[0]["shed"].values()), 4)


if __name__ == "__main__":
    unittest.main()
