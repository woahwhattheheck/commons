# SPDX-License-Identifier: Apache-2.0
"""V5 current-lineage regressions for final returned-action row-shed ordering."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

SPEC = importlib.util.spec_from_file_location("_row_shed_final_main", HERE / "main.py")
main = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(main)


class RowShedFinalBoundaryTests(unittest.TestCase):
    def test_feature_reader_accepts_only_literal_bools(self):
        self.assertIs(main._row_shed_enabled({}), False)
        self.assertIs(main._row_shed_enabled({"row_shed": False}), False)
        self.assertIs(main._row_shed_enabled({"row_shed": True}), True)
        for alias in (0, 1, "false", "true", None, [], {}):
            with self.subTest(alias=alias):
                with self.assertRaises(TypeError):
                    main._row_shed_enabled({"row_shed": alias})

    def test_feature_is_nonterminal_frozen_only(self):
        for feature_data in (
            {"row_shed": True, "consumer": "ordered"},
            {"row_shed": True, "consumer": "parent"},
            {"row_shed": True, "consumer": "frozen", "terminal_route": True},
        ):
            with self.subTest(feature_data=feature_data):
                with self.assertRaisesRegex(
                    ValueError, "row_shed is the tested nonterminal frozen composition"
                ):
                    main._new_instance(HERE, feature_data)

    def test_root_source_is_exact_canonical_row_shed_donor(self):
        canonical = (
            HERE / "candidates/v4/repairs/gameplay/row-shed-sell-order/row_shed_sell_order.py"
        ).read_bytes()
        production = (HERE / "row_shed_sell_order.py").read_bytes()
        self.assertEqual(production, canonical)

    @staticmethod
    def _marked(selected, marker):
        result = deepcopy(selected)
        result["market"] = list(result.get("market", [])) + [[marker]]
        return result

    def test_row_shed_runs_after_capital_pressure_and_town_on_completed_action(self):
        import titan_runtime

        calls = []
        instance = main._new_instance(HERE, {
            "row_shed": True,
            "town_procurement": True,
        })
        instance.diagnostics = {"status": "completed"}

        def capital(_self, _obs, _cfg, selected):
            calls.append("capital")
            return self._marked(selected, "CAPITAL")

        def pressure(_self, _obs, _cfg, selected):
            calls.append("pressure")
            return self._marked(selected, "PRESSURE")

        town = types.ModuleType("town_procurement")
        def town_apply(_obs, selected, _cfg, *, completed):
            self.assertTrue(completed)
            calls.append("town")
            return self._marked(selected, "TOWN"), {"changed": True}
        town.apply = town_apply

        scheduler = types.ModuleType("scheduler")
        def post_units(_obs, selected, _cfg):
            calls.append("post_units")
            self.assertEqual(
                selected["market"][-3:],
                [["CAPITAL"], ["PRESSURE"], ["TOWN"]],
            )
            return {}, {"shed": {"WOOL": 1, "MILK": 6}}
        scheduler.post_units = post_units

        row_module = types.ModuleType("row_shed_sell_order")
        case = self
        class FakeRowShed:
            def __init__(self):
                self.diagnostics = {}

            def transform(self, _obs, _cfg, selected, *, post_unit_shed, fallback_action):
                calls.append("row_shed")
                case.assertIs(fallback_action, selected)
                case.assertEqual(post_unit_shed, {"WOOL": 1, "MILK": 6})
                self.diagnostics = {
                    "status": "applied",
                    "reason": "test",
                    "market_prefix_limit": 10,
                }
                return RowShedFinalBoundaryTests._marked(selected, "ROWSHED")
        row_module.RowShedSellOrder = FakeRowShed

        selected = {"farmer": ["PASS"], "hands": [], "market": [["BASE"]]}
        obs = {"step": 10, "player": 0}
        with mock.patch.object(titan_runtime.TitanAgent, "_early_capital_selected", capital), \
                mock.patch.object(titan_runtime.TitanAgent, "_market_pressure_selected", pressure), \
                mock.patch.dict(sys.modules, {
                    "town_procurement": town,
                    "scheduler": scheduler,
                    "row_shed_sell_order": row_module,
                }):
            returned = instance._early_capital_selected(obs, {}, selected)

        self.assertEqual(calls, ["capital", "pressure", "town", "post_units", "row_shed"])
        self.assertEqual(returned["market"][-1], ["ROWSHED"])
        self.assertTrue(instance.diagnostics["row_shed"]["returned_action_bound"])
        self.assertEqual(instance._finalizer_checkpoint["stage"], "row_shed")
        self.assertEqual(instance._finalizer_checkpoint["action"], returned)

    def test_deadline_fallback_does_not_start_row_shed(self):
        import titan_runtime

        calls = []
        instance = main._new_instance(HERE, {"row_shed": True})
        instance.diagnostics = {"status": "deadline_fallback"}

        def capital(_self, _obs, _cfg, selected):
            calls.append("capital")
            return selected

        def pressure(*_args, **_kwargs):
            calls.append("pressure")
            raise AssertionError("pressure must not run on fallback")

        row_module = types.ModuleType("row_shed_sell_order")
        class ForbiddenRowShed:
            def __init__(self):
                raise AssertionError("row-shed must not start on fallback")
        row_module.RowShedSellOrder = ForbiddenRowShed

        selected = {"farmer": ["PASS"], "hands": [], "market": []}
        with mock.patch.object(titan_runtime.TitanAgent, "_early_capital_selected", capital), \
                mock.patch.object(titan_runtime.TitanAgent, "_market_pressure_selected", pressure), \
                mock.patch.dict(sys.modules, {"row_shed_sell_order": row_module}):
            returned = instance._early_capital_selected({"step": 2, "player": 0}, {}, selected)
        self.assertIs(returned, selected)
        self.assertEqual(calls, ["capital"])
        self.assertNotIn("row_shed", instance.diagnostics)

    def test_release_default_stays_off_until_matched_strength_gate(self):
        config = json.loads((HERE / "TITAN-CONFIG.json").read_text())
        self.assertIn("row_shed", config)
        self.assertIs(config["row_shed"], False)


if __name__ == "__main__":
    unittest.main()
