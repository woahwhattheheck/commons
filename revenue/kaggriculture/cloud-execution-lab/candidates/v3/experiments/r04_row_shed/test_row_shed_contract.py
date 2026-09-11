from __future__ import annotations

import copy
import importlib
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve()
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
sys.path.insert(0, str(V3))
sys.path.insert(0, str(OVERLAY))

import apply_v3  # noqa: E402
import r04_full_router as r04  # noqa: E402


class RowShedContract(unittest.TestCase):
    def setUp(self):
        self.saved = {
            "ROW_ORDER": r04.ROW_ORDER,
            "ROW_SHED": r04.ROW_SHED,
            "EVENING_FLUSH": r04.EVENING_FLUSH,
            "OPEN_ROUNDTRIP": r04.OPEN_ROUNDTRIP,
            "STRAWBERRY_TOPUP": r04.STRAWBERRY_TOPUP,
            "KILL_LATE_WATER": r04.KILL_LATE_WATER,
            "STRAWBERRY_ENDGAME": r04.STRAWBERRY_ENDGAME,
            "B5_CARROT_FERTILIZER": r04.B5_CARROT_FERTILIZER,
            "B5_JIT_FERTILIZE": r04.B5_JIT_FERTILIZE,
            "POLICY_AGENT": r04.POLICY_AGENT,
        }

    def tearDown(self):
        for name, value in self.saved.items():
            setattr(r04, name, value)

    @staticmethod
    def market_rows():
        return [
            ["SELL", "WHEAT", 1000],
            ["SELL", "CARROT", 1],
            ["HIRE"],
            ["SELL", "MELON", 9],
        ]

    @staticmethod
    def observation():
        tiles = [[None for _ in range(10)] for _ in range(10)]
        return {
            "step": 300,
            "player": 0,
            "farms": [
                {"tiles": tiles, "farmer": [4, 4], "hands": [], "money": 10000},
                {"tiles": copy.deepcopy(tiles), "farmer": [0, 0], "hands": [], "money": 10000},
            ],
            "private": {
                "shed": {"WHEAT": 1, "CARROT": 1},
                "inventories": [{}],
            },
            "market": {
                "inventory": {"WHEAT": 9800, "CARROT": 9800, "MELON": 9800},
                "prices": {"WHEAT": 25, "CARROT": 35, "MELON": 250},
            },
            "town": {"unlocked_shops": []},
        }

    def test_disabled_is_exact_pre_s33_ordering(self):
        rows = self.market_rows()
        before = copy.deepcopy(rows)
        result = r04.order_sells(rows, {"WHEAT": 9800, "CARROT": 9800})
        self.assertEqual(result[:2], [["SELL", "WHEAT", 1000], ["SELL", "CARROT", 1]])
        self.assertEqual(rows, before)
        self.assertEqual(result[2:], before[2:])

    def test_projected_shed_caps_only_the_ranking_quantity(self):
        rows = self.market_rows()
        result = r04.order_sells(
            rows,
            {"WHEAT": 9800, "CARROT": 9800},
            {"WHEAT": 1, "CARROT": 1},
        )
        self.assertEqual(result[:2], [["SELL", "CARROT", 1], ["SELL", "WHEAT", 1000]])
        self.assertEqual(result[1][2], 1000, "row-shed must not rewrite requested quantity")
        self.assertEqual(result[2:], rows[2:], "non-leading rows and the post-barrier SELL stay fixed")

    def test_zero_projected_stock_cannot_gain_fake_priority(self):
        rows = [["SELL", "WHEAT", 1000], ["SELL", "CARROT", 1]]
        result = r04.order_sells(
            rows,
            {"WHEAT": 9800, "CARROT": 9800},
            {"WHEAT": 0, "CARROT": 1},
        )
        self.assertEqual(result, [["SELL", "CARROT", 1], ["SELL", "WHEAT", 1000]])

    def test_v3_agent_uses_current_projected_shed_only_when_enabled(self):
        action = {"farmer": ["PASS"], "hands": [], "market": self.market_rows()}
        r04.POLICY_AGENT = lambda observation, configuration=None: copy.deepcopy(action)
        r04.ROW_ORDER = True
        r04.EVENING_FLUSH = False
        r04.OPEN_ROUNDTRIP = 0
        r04.STRAWBERRY_TOPUP = False
        r04.KILL_LATE_WATER = False
        r04.STRAWBERRY_ENDGAME = False
        r04.B5_CARROT_FERTILIZER = False
        r04.B5_JIT_FERTILIZE = False

        obs = self.observation()
        r04.ROW_SHED = False
        control = r04.v3_agent(obs, None)
        self.assertEqual(control["market"][:2], [["SELL", "WHEAT", 1000], ["SELL", "CARROT", 1]])

        r04.ROW_SHED = True
        candidate = r04.v3_agent(obs, None)
        self.assertEqual(candidate["market"][:2], [["SELL", "CARROT", 1], ["SELL", "WHEAT", 1000]])
        self.assertEqual(candidate["market"][2:], action["market"][2:])

    def test_install_and_apply_v3_wire_default_off_key(self):
        r04.install(row_shed=True)
        self.assertIs(r04.ROW_SHED, True)
        r04.install(row_shed=False)
        self.assertIs(r04.ROW_SHED, False)

        self.assertIs(apply_v3.PARAMS["r04_row_shed"], False)
        self.assertIn('r04_row_shed: bool = False', apply_v3.FIELDS)
        self.assertIn('bool(self.features.r04_row_shed)', apply_v3.RUNTIME_METHODS)
        self.assertIn("self.diagnostics['row_shed']", apply_v3.RUNTIME_METHODS)

    def test_custom_market_params_still_bypass_row_order_in_v3_agent(self):
        action = {"farmer": ["PASS"], "hands": [], "market": self.market_rows()}
        r04.POLICY_AGENT = lambda observation, configuration=None: copy.deepcopy(action)
        r04.ROW_ORDER = True
        r04.ROW_SHED = True
        r04.EVENING_FLUSH = False
        r04.OPEN_ROUNDTRIP = 0
        r04.STRAWBERRY_TOPUP = False
        r04.KILL_LATE_WATER = False
        r04.STRAWBERRY_ENDGAME = False
        r04.B5_CARROT_FERTILIZER = False
        r04.B5_JIT_FERTILIZE = False
        output = r04.v3_agent(self.observation(), {"marketParams": {"custom": True}})
        self.assertEqual(output["market"], action["market"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
