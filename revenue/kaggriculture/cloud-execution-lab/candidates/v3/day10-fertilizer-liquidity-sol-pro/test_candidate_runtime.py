# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

from candidate_runtime import install_final_boundary
from fertilizer_liquidity import ITEM, LiquiditySettings


def observation(*, step=240, money=4000, inventory=1000):
    return {
        "step": step,
        "player": 0,
        "farms": [{"money": money}, {"money": 5000}],
        "market": {"inventory": {ITEM: inventory}, "params": {"token": "p"}},
    }


class Consumer:
    selected_post_units = None
    selected_post_units_binding = None


class FakeInstance:
    def __init__(
        self,
        guard_reason="sale_already_leaves_required_stock",
        guard_quantity=None,
        *,
        append_hire=True,
    ):
        self.diagnostics = {"status": "completed"}
        self.consumer = Consumer()
        self.selected = {"farmer": ["PASS"], "hands": [], "market": []}
        self.events = []
        self.guard_reason = guard_reason
        self.guard_quantity = guard_quantity
        self.append_hire = append_hire
        self.guard_inputs = []

    def _early_capital_selected(self, _obs, _cfg, selected):
        self.events.append("canonical_final_pressure")
        result = copy.deepcopy(selected)
        if self.append_hire:
            result["market"].append(["HIRE"])
        return result

    def _operating_stock_selected(self, _obs, _cfg, selected):
        self.events.append("operating_stock_certificate")
        self.guard_inputs.append(copy.deepcopy(selected))
        result = copy.deepcopy(selected)
        if self.guard_quantity is not None:
            for index, row in enumerate(result["market"]):
                if row and row[:2] == ["SELL", ITEM]:
                    result["market"][index] = (
                        ["SELL", ITEM, self.guard_quantity] if self.guard_quantity else []
                    )
        self.diagnostics["operating_stock"] = {
            "changed": self.guard_quantity is not None,
            "reason": self.guard_reason,
        }
        return result


def post_units(_obs, _action, _cfg):
    return ({"money": 4000}, {"shed": {ITEM: 100}})


def quote(_item, _inventory, _params):
    return 60


class CandidateRuntimeTests(unittest.TestCase):
    def settings(self):
        return LiquiditySettings(
            reserve_units=24,
            minimum_unit_price=55,
            max_units_per_turn=64,
            liquidity_target=12000,
            rival_stress_units=32,
        )

    def install(self, instance):
        return install_final_boundary(
            instance, post_units=post_units, quote=quote, settings=self.settings()
        )

    def test_runs_after_canonical_final_pressure_and_before_certificate(self):
        instance = self.install(FakeInstance())
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        result = instance._early_capital_selected(observation(), {}, action)
        self.assertEqual(
            instance.events, ["canonical_final_pressure", "operating_stock_certificate"]
        )
        self.assertEqual(result["market"][0], ["HIRE"])
        self.assertEqual(result["market"][1][:2], ["SELL", ITEM])
        self.assertEqual(
            instance.diagnostics["day10_fertilizer_liquidity"]["reason"],
            "certified_fertilizer_liquidity_sale",
        )

    def test_existing_certificate_can_reduce_candidate_lot(self):
        instance = self.install(
            FakeInstance(guard_reason="reserve_reachable_fertilizer", guard_quantity=7)
        )
        result = instance._early_capital_selected(
            observation(), {}, {"farmer": ["PASS"], "hands": [], "market": []}
        )
        self.assertEqual(result["market"][-1], ["SELL", ITEM, 7])
        report = instance.diagnostics["day10_fertilizer_liquidity"]
        self.assertGreater(report["proposed_quantity"], 7)
        self.assertEqual(report["final_quantity"], 7)


    def test_operating_stock_sees_only_executable_prefix_and_suffix_is_exact(self):
        instance = self.install(FakeInstance(append_hire=False))
        suffix = [["SELL", ITEM, 90], ["BUY_SEED", "WHEAT", 2]]
        result = instance._early_capital_selected(
            observation(),
            {"maxMarketOrdersPerTurn": 1, "turnsPerDay": 24},
            {"farmer": ["PASS"], "hands": [], "market": [[], *copy.deepcopy(suffix)]},
        )
        self.assertEqual(len(instance.guard_inputs), 1)
        self.assertEqual(len(instance.guard_inputs[0]["market"]), 1)
        self.assertEqual(instance.guard_inputs[0]["market"][0][:2], ["SELL", ITEM])
        self.assertEqual(result["market"][1:], suffix)
        report = instance.diagnostics["day10_fertilizer_liquidity"]
        self.assertEqual(report["inactive_suffix_rows_quarantined"], 2)
        self.assertTrue(report["inactive_suffix_preserved"])

    def test_certificate_reduction_cannot_rewrite_inactive_suffix_sale(self):
        instance = self.install(
            FakeInstance(
                guard_reason="reserve_reachable_fertilizer",
                guard_quantity=7,
                append_hire=False,
            )
        )
        suffix = [["SELL", ITEM, 90]]
        result = instance._early_capital_selected(
            observation(),
            {"maxMarketOrdersPerTurn": 1, "turnsPerDay": 24},
            {"farmer": ["PASS"], "hands": [], "market": [[], *copy.deepcopy(suffix)]},
        )
        self.assertEqual(result["market"][0], ["SELL", ITEM, 7])
        self.assertEqual(result["market"][1:], suffix)
        self.assertEqual(instance.guard_inputs[0]["market"], [["SELL", ITEM, 64]])

    def test_uncertified_guard_withdraws_invented_sale(self):
        instance = self.install(FakeInstance(guard_reason="requires_one_unambiguous_pickup"))
        original = {"farmer": ["PASS"], "hands": [], "market": []}
        result = instance._early_capital_selected(observation(), {}, original)
        self.assertEqual(result["market"], [["HIRE"]])
        report = instance.diagnostics["day10_fertilizer_liquidity"]
        self.assertFalse(report["changed"])
        self.assertEqual(
            report["reason"],
            "operating_stock_not_certified:requires_one_unambiguous_pickup",
        )
        self.assertIsNone(instance.consumer.selected_post_units)
        self.assertIsNone(instance.consumer.selected_post_units_binding)

    def test_certificate_that_reserves_every_unit_withdraws(self):
        instance = self.install(
            FakeInstance(guard_reason="reserve_reachable_fertilizer", guard_quantity=0)
        )
        result = instance._early_capital_selected(
            observation(), {}, {"farmer": ["PASS"], "hands": [], "market": []}
        )
        self.assertEqual(result["market"], [["HIRE"]])
        self.assertEqual(
            instance.diagnostics["day10_fertilizer_liquidity"]["reason"],
            "operating_stock_fully_reserved",
        )

    def test_completed_action_is_required(self):
        instance = self.install(FakeInstance())
        instance.diagnostics["status"] = "deadline_fallback"
        result = instance._early_capital_selected(
            observation(), {}, {"farmer": ["PASS"], "hands": [], "market": []}
        )
        self.assertEqual(result["market"], [["HIRE"]])
        self.assertEqual(instance.events, ["canonical_final_pressure"])
        self.assertEqual(
            instance.diagnostics["day10_fertilizer_liquidity"]["reason"],
            "completed_action_required",
        )

    def test_install_is_idempotent(self):
        instance = FakeInstance()
        self.install(instance)
        first = instance._early_capital_selected
        self.install(instance)
        self.assertIs(instance._early_capital_selected, first)
        instance._early_capital_selected(
            observation(), {}, {"farmer": ["PASS"], "hands": [], "market": []}
        )
        self.assertEqual(instance.events.count("canonical_final_pressure"), 1)

    def test_exception_restores_prior_snapshot(self):
        instance = FakeInstance()
        prior_pair = ({"old": 1}, {"shed": {ITEM: 1}})
        prior_binding = (1, 0, ["PASS"], [])
        instance.consumer.selected_post_units = prior_pair
        instance.consumer.selected_post_units_binding = prior_binding

        def exploding_post_units(_obs, _action, _cfg):
            raise ValueError("projection failed")

        install_final_boundary(
            instance,
            post_units=exploding_post_units,
            quote=quote,
            settings=self.settings(),
        )
        result = instance._early_capital_selected(
            observation(), {}, {"farmer": ["PASS"], "hands": [], "market": []}
        )
        self.assertEqual(result["market"], [["HIRE"]])
        self.assertIs(instance.consumer.selected_post_units, prior_pair)
        self.assertEqual(instance.consumer.selected_post_units_binding, prior_binding)
        self.assertIn(
            "projection failed",
            instance.diagnostics["day10_fertilizer_liquidity"]["reason"],
        )

    def test_accepted_snapshot_binds_exact_units(self):
        instance = self.install(FakeInstance())
        result = instance._early_capital_selected(
            observation(),
            {},
            {"farmer": ["WEST"], "hands": [["EAST"]], "market": []},
        )
        self.assertEqual(result["farmer"], ["WEST"])
        self.assertEqual(result["hands"], [["EAST"]])
        binding = instance.consumer.selected_post_units_binding
        self.assertEqual(binding[:2], (240, 0))
        self.assertEqual(binding[2], ["WEST"])
        self.assertEqual(binding[3], [["EAST"]])


if __name__ == "__main__":
    unittest.main()
