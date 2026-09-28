# SPDX-License-Identifier: Apache-2.0
"""Predecessor-discriminating contracts for final stock-prefix isolation."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import MethodType, ModuleType, SimpleNamespace
from unittest.mock import patch
import importlib.util
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for path in (str(HERE), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import early_capital
import mechanics as m
import operating_stock
from active_prefix import protect_final_current_prefix
from final_boundary import INSTALL_MARKER, install_final_boundary


class ActivePrefixTests(unittest.TestCase):
    def setUp(self):
        self.now = 460
        self.farm = {
            "farmer": [4, 4],
            "hands": [[4, 4]],
            "money": 50000,
            "tiles": [[None for _ in range(10)] for _ in range(10)],
        }
        for x in (2, 3):
            self.farm["tiles"][4][x] = {
                "kind": "PLANT",
                "crop": "STRAWBERRY",
                "planted_day": 10,
                "yield_units": 0,
                "fertilized_until_day": -1,
                "max_lifespan_step": -1,
                "consecutive_unwatered": 0,
                "watered_today": True,
            }
        self.private = {
            "inventories": [{}, {}],
            "shed": {"FERTILIZER": 9},
            "seeds": {},
        }
        self.obs = {
            "step": self.now,
            "player": 0,
            "day": 19,
            "market": {
                "inventory": {"FERTILIZER": 10300, "STRAWBERRY": 9900}
            },
        }
        self.selected = {
            "farmer": ["PASS"],
            "hands": [["PASS"]],
            "market": [["SELL", "FERTILIZER", 9]],
        }
        self.route = [
            {"farmer": ["PASS"], "hands": [["PASS"]], "market": []}
            for _ in range(720)
        ]
        self.route[461]["hands"][0] = ["PICKUP", "FERTILIZER", 3]
        self.route[462]["hands"][0] = ["WEST"]
        self.route[463]["hands"][0] = ["FERTILIZE"]
        self.route[464]["hands"][0] = ["WEST"]
        self.route[465]["hands"][0] = ["FERTILIZE"]
        self.checkpoints = (226, 360, 433)

    def predecessor(self, *, selected=None, route=None, config=None):
        return operating_stock.protect_operating_stock(
            m,
            self.obs,
            {} if config is None else config,
            self.selected if selected is None else selected,
            self.farm,
            self.private,
            self.route if route is None else route,
            self.checkpoints,
        )

    def candidate(self, *, selected=None, route=None, config=None):
        return protect_final_current_prefix(
            operating_stock.protect_operating_stock,
            m,
            self.obs,
            {} if config is None else config,
            self.selected if selected is None else selected,
            self.farm,
            self.private,
            self.route if route is None else route,
            self.checkpoints,
        )

    def _boundary_instance(self, *, status="completed"):
        calls = []
        instance = SimpleNamespace(diagnostics={"status": status})

        def original_operating(this, obs, cfg, selected):
            calls.append(("operating", deepcopy(selected)))
            result, report = operating_stock.protect_operating_stock(
                m,
                obs,
                cfg,
                selected,
                self.farm,
                self.private,
                self.route,
                self.checkpoints,
            )
            this.diagnostics["operating_stock"] = report
            return result

        def original_late(this, obs, cfg, selected):
            calls.append(("late", deepcopy(selected)))
            result, report = early_capital.order_early_capital(
                m, obs, cfg, selected, self.route, ()
            )
            this.diagnostics["early_capital"] = report
            return result

        instance._operating_stock_selected = MethodType(original_operating, instance)
        instance._early_capital_selected = MethodType(original_late, instance)
        install_final_boundary(instance, operating_stock)
        return instance, calls

    def test_tail_hire_no_longer_suppresses_final_active_reservation(self):
        selected = deepcopy(self.selected)
        selected["market"] += [["SELL", "WOOL", 1], ["HIRE"]]
        predecessor, old = self.predecessor(
            selected=selected, config={"maxMarketOrdersPerTurn": 2}
        )
        self.assertIs(predecessor, selected)
        self.assertEqual(old["reason"], "current_hiring_boundary")

        result, report = self.candidate(
            selected=selected, config={"maxMarketOrdersPerTurn": 2}
        )
        self.assertEqual(
            result["market"],
            [["SELL", "FERTILIZER", 7], ["SELL", "WOOL", 1], ["HIRE"]],
        )
        self.assertTrue(report["changed"])
        self.assertEqual(report["final_current_prefix"]["limit"], 2)
        self.assertFalse(report["final_current_prefix"]["future_route_trimmed"])

    def test_default_ten_row_final_tail_hire_is_live(self):
        selected = deepcopy(self.selected)
        selected["market"] += [["SELL", "WOOL", 1] for _ in range(9)] + [["HIRE"]]
        raw, raw_report = self.predecessor(selected=selected)
        self.assertIs(raw, selected)
        self.assertEqual(raw_report["reason"], "current_hiring_boundary")

        result, report = self.candidate(selected=selected)
        self.assertEqual(result["market"][0], ["SELL", "FERTILIZER", 7])
        self.assertEqual(result["market"][1:10], selected["market"][1:10])
        self.assertEqual(result["market"][10], ["HIRE"])
        self.assertEqual(report["final_current_prefix"]["limit"], 10)

    def test_active_hire_remains_a_boundary(self):
        selected = deepcopy(self.selected)
        selected["market"] += [["HIRE"], ["SELL", "WOOL", 1]]
        result, report = self.candidate(
            selected=selected, config={"maxMarketOrdersPerTurn": 2}
        )
        self.assertIs(result, selected)
        self.assertEqual(report["reason"], "current_hiring_boundary")

    def test_final_tail_purchase_no_longer_creates_phantom_capacity(self):
        selected = deepcopy(self.selected)
        selected["market"] += [
            ["SELL", "WOOL", 1],
            ["BUY_ANIMAL", "COW", 100],
        ]
        raw, raw_report = self.predecessor(
            selected=selected, config={"maxMarketOrdersPerTurn": 2}
        )
        self.assertIs(raw, selected)
        self.assertEqual(
            raw_report["reason"], "retained_stock_conflicts_with_arrival_room"
        )

        result, report = self.candidate(
            selected=selected, config={"maxMarketOrdersPerTurn": 2}
        )
        self.assertEqual(result["market"][0], ["SELL", "FERTILIZER", 7])
        self.assertEqual(result["market"][2], ["BUY_ANIMAL", "COW", 100])
        self.assertEqual(report["reason"], "reserve_reachable_fertilizer")

    def test_active_purchase_still_blocks_capacity(self):
        selected = deepcopy(self.selected)
        selected["market"] += [
            ["BUY_ANIMAL", "COW", 100],
            ["SELL", "WOOL", 1],
        ]
        result, report = self.candidate(
            selected=selected, config={"maxMarketOrdersPerTurn": 2}
        )
        self.assertIs(result, selected)
        self.assertEqual(
            report["reason"], "retained_stock_conflicts_with_arrival_room"
        )

    def test_final_tail_only_fertilizer_sale_is_not_rewritten(self):
        selected = deepcopy(self.selected)
        selected["market"] = [
            ["SELL", "WOOL", 1],
            ["SELL", "MELON", 1],
            ["SELL", "FERTILIZER", 9],
        ]
        raw, raw_report = self.predecessor(
            selected=selected, config={"maxMarketOrdersPerTurn": 2}
        )
        self.assertTrue(raw_report["changed"])
        self.assertEqual(raw["market"][2], ["SELL", "FERTILIZER", 7])

        result, report = self.candidate(
            selected=selected, config={"maxMarketOrdersPerTurn": 2}
        )
        self.assertIs(result, selected)
        self.assertEqual(result["market"][2], ["SELL", "FERTILIZER", 9])
        self.assertEqual(report["reason"], "no_fertilizer_sale")

    def test_future_tail_hire_remains_conservative(self):
        route = deepcopy(self.route)
        route[462]["market"] = [
            ["SELL", "WOOL", 1],
            ["SELL", "MELON", 1],
            ["HIRE"],
        ]
        raw, raw_report = self.predecessor(
            route=route, config={"maxMarketOrdersPerTurn": 2}
        )
        result, report = self.candidate(
            route=route, config={"maxMarketOrdersPerTurn": 2}
        )
        self.assertIs(raw, self.selected)
        self.assertIs(result, self.selected)
        self.assertEqual(raw_report["reason"], "no_distinct_useful_consumption")
        self.assertEqual(report["reason"], raw_report["reason"])
        self.assertFalse(report["final_current_prefix"]["future_route_trimmed"])

    def test_future_tail_replenishment_remains_conservative(self):
        route = deepcopy(self.route)
        route[462]["market"] = [
            ["SELL", "WOOL", 1],
            ["SELL", "MELON", 1],
            ["BUY_PRODUCT", "FERTILIZER", 1],
        ]
        raw, raw_report = self.predecessor(
            route=route, config={"maxMarketOrdersPerTurn": 2}
        )
        result, report = self.candidate(
            route=route, config={"maxMarketOrdersPerTurn": 2}
        )
        self.assertIs(raw, self.selected)
        self.assertIs(result, self.selected)
        self.assertEqual(raw_report["reason"], "intervening_requested_replenishment")
        self.assertEqual(report["reason"], raw_report["reason"])

    def test_suffix_and_all_inputs_are_preserved(self):
        selected = deepcopy(self.selected)
        selected["market"] += [
            ["SELL", "WOOL", 1],
            ["HIRE"],
            {"opaque": [1, 2]},
        ]
        before = deepcopy((selected, self.obs, self.farm, self.private, self.route))
        result, report = self.candidate(
            selected=selected, config={"maxMarketOrdersPerTurn": 2}
        )
        self.assertEqual(result["market"][2:], before[0]["market"][2:])
        self.assertEqual(
            (selected, self.obs, self.farm, self.private, self.route), before
        )
        self.assertTrue(report["final_current_prefix"]["suffix_preserved"])

    def test_second_application_is_identity(self):
        first, first_report = self.candidate()
        self.assertTrue(first_report["changed"])
        second, second_report = self.candidate(selected=first)
        self.assertIs(second, first)
        self.assertFalse(second_report["changed"])
        self.assertEqual(
            second_report["reason"], "sale_already_leaves_required_stock"
        )

    def test_official_minimum_cap_and_certified_upper_bound(self):
        selected = deepcopy(self.selected)
        selected["market"] += [["HIRE"]]
        result, report = self.candidate(
            selected=selected, config={"maxMarketOrdersPerTurn": 0}
        )
        self.assertIs(result, selected)
        self.assertEqual(report["final_current_prefix"]["limit"], 1)
        self.assertEqual(report["reason"], "reservation_exceeds_obligation_bound")

        result, report = self.candidate(
            selected=selected, config={"maxMarketOrdersPerTurn": 11}
        )
        self.assertIs(result, selected)
        self.assertFalse(report["final_current_prefix"]["accepted"])
        self.assertEqual(
            report["reason"], "final_prefix_market_limit_above_certified_bound"
        )

    def test_invalid_adapter_inputs_fail_closed(self):
        for config in (
            {"maxMarketOrdersPerTurn": True},
            {"maxMarketOrdersPerTurn": "bad"},
            [],
        ):
            result, report = self.candidate(config=config)
            self.assertIs(result, self.selected)
            self.assertFalse(report["changed"])
            self.assertFalse(report["final_current_prefix"]["accepted"])
        malformed = dict(self.selected, market="SELL")
        result, report = self.candidate(selected=malformed)
        self.assertIs(result, malformed)
        self.assertEqual(report["reason"], "final_prefix_market_not_list")

    def test_final_boundary_treats_tail_promoted_by_early_capital_as_active(self):
        selected = deepcopy(self.selected)
        selected["market"] = [
            ["SELL", "FERTILIZER", 9],
            [],
            ["HIRE"],
            ["BUY_LAND"],
        ]
        cfg = {"maxMarketOrdersPerTurn": 2, "episodeSteps": 720, "turnsPerDay": 24}
        instance, calls = self._boundary_instance()
        deferred = instance._operating_stock_selected(self.obs, cfg, selected)
        self.assertIs(deferred, selected)
        self.assertEqual(instance.diagnostics["operating_stock"]["reason"],
                         "deferred_to_final_completed_boundary")

        result = instance._early_capital_selected(self.obs, cfg, selected)
        self.assertEqual(
            result["market"],
            [["SELL", "FERTILIZER", 9], ["HIRE"], ["BUY_LAND"], []],
        )
        self.assertEqual(instance.diagnostics["operating_stock"]["reason"],
                         "current_hiring_boundary")
        self.assertEqual(instance.diagnostics["operating_stock"]
                         ["final_current_prefix"]["limit"], 2)
        self.assertEqual([name for name, _ in calls], ["late", "operating"])

    def test_final_boundary_ignores_only_a_true_final_suffix(self):
        selected = deepcopy(self.selected)
        selected["market"] = [
            ["SELL", "FERTILIZER", 9],
            ["SELL", "WOOL", 1],
            ["SELL", "MELON", 1],
            ["HIRE"],
            ["BUY_LAND"],
        ]
        cfg = {"maxMarketOrdersPerTurn": 2, "episodeSteps": 720, "turnsPerDay": 24}
        instance, _ = self._boundary_instance()
        result = instance._early_capital_selected(self.obs, cfg, selected)
        self.assertEqual(result["market"][0], ["SELL", "FERTILIZER", 7])
        self.assertEqual(result["market"][1:], selected["market"][1:])
        self.assertEqual(instance.diagnostics["operating_stock"]["reason"],
                         "reserve_reachable_fertilizer")

    def test_deadline_fallback_skips_deferred_operating_stock(self):
        selected = deepcopy(self.selected)
        selected["market"] = [
            ["SELL", "FERTILIZER", 9],
            [],
            ["HIRE"],
            ["BUY_LAND"],
        ]
        cfg = {"maxMarketOrdersPerTurn": 2, "episodeSteps": 720, "turnsPerDay": 24}
        expected, _ = early_capital.order_early_capital(
            m, self.obs, cfg, selected, self.route, ()
        )
        instance, calls = self._boundary_instance(status="deadline_fallback")
        result = instance._early_capital_selected(self.obs, cfg, selected)
        self.assertEqual(result, expected)
        self.assertEqual([name for name, _ in calls], ["late"])

    def test_install_is_idempotent_and_fresh_instance_safe(self):
        first, _ = self._boundary_instance()
        early_method = first._operating_stock_selected
        late_method = first._early_capital_selected
        self.assertIs(install_final_boundary(first, operating_stock), first)
        self.assertIs(first._operating_stock_selected, early_method)
        self.assertIs(first._early_capital_selected, late_method)
        self.assertTrue(getattr(first, INSTALL_MARKER))

        second, _ = self._boundary_instance()
        self.assertTrue(getattr(second, INSTALL_MARKER))
        self.assertIsNot(first._operating_stock_selected, second._operating_stock_selected)

    def test_global_guard_is_restored_after_exception(self):
        def exploding_guard(*args, **kwargs):
            raise RuntimeError("sentinel")

        module = SimpleNamespace(protect_operating_stock=exploding_guard)
        instance = SimpleNamespace(diagnostics={"status": "completed"})

        def original_operating(this, obs, cfg, selected):
            return module.protect_operating_stock(
                None, obs, cfg, selected, {}, {}, [], ()
            )[0]

        def original_late(this, obs, cfg, selected):
            return selected

        instance._operating_stock_selected = MethodType(original_operating, instance)
        instance._early_capital_selected = MethodType(original_late, instance)
        install_final_boundary(instance, module)
        selected = {"market": []}
        with self.assertRaisesRegex(RuntimeError, "sentinel"):
            instance._early_capital_selected({}, {}, selected)
        self.assertIs(module.protect_operating_stock, exploding_guard)

    def test_pinned_official_engine_executes_only_first_n_rows(self):
        package = ModuleType("kaggle_environments")
        package.__path__ = []
        utils = ModuleType("kaggle_environments.utils")
        utils.resolve_episode_seed = lambda *args, **kwargs: 0
        package.utils = utils
        engine_path = ROOT / "reference" / "engine" / "kaggriculture.py"
        spec = importlib.util.spec_from_file_location(
            "_titan_final_prefix_official_engine", engine_path
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        engine = importlib.util.module_from_spec(spec)
        with patch.dict(
            sys.modules,
            {
                "kaggle_environments": package,
                "kaggle_environments.utils": utils,
            },
        ):
            spec.loader.exec_module(engine)

        farms = [engine._new_farm(10, 0), engine._new_farm(10, 0)]
        privates = [engine._new_private(), engine._new_private()]
        privates[0]["shed"]["WOOL"] = 1
        privates[0]["shed"]["MELON"] = 1
        privates[0]["shed"]["FERTILIZER"] = 9
        market = engine._new_market()
        observations = [
            SimpleNamespace(farms=farms, market=market, private=privates[0]),
            SimpleNamespace(private=privates[1]),
        ]
        states = [
            SimpleNamespace(
                observation=observations[0],
                action={
                    "market": [
                        ["SELL", "WOOL", 1],
                        ["SELL", "MELON", 1],
                        ["SELL", "FERTILIZER", 9],
                    ]
                },
            ),
            SimpleNamespace(observation=observations[1], action={"market": []}),
        ]
        env = SimpleNamespace(
            configuration={
                "boardSize": 10,
                "maxMarketOrdersPerTurn": 2,
                "farmHandCostMult": 1,
                "shedCapacity": 100,
            }
        )
        fertilizer_market_before = market["inventory"]["FERTILIZER"]
        engine._process_market(states, env)
        self.assertEqual(privates[0]["shed"]["WOOL"], 0)
        self.assertEqual(privates[0]["shed"]["MELON"], 0)
        self.assertEqual(privates[0]["shed"]["FERTILIZER"], 9)
        self.assertEqual(
            market["inventory"]["FERTILIZER"], fertilizer_market_before
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
