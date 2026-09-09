# SPDX-License-Identifier: Apache-2.0
"""Exact preserved-engine witness for duplicate fixed-price seed rows."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "reference" / "engine" / "kaggriculture.py"


def load_engine():
    spec = importlib.util.spec_from_file_location("_granary_official_engine", ENGINE)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {ENGINE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OfficialEngineWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = load_engine()

    def execute(self, market_rows, *, starting_money=3000):
        engine = self.engine
        farms = [engine._new_farm(10, starting_money), engine._new_farm(10, 3000)]
        private = [engine._new_private(), engine._new_private()]
        market = engine._new_market()
        town = engine._new_town()
        states = [
            SimpleNamespace(
                observation=SimpleNamespace(
                    market=market,
                    farms=farms,
                    private=private[player],
                    town=town,
                ),
                action={"farmer": ["PASS"], "hands": [], "market": rows},
            )
            for player, rows in enumerate((market_rows, []))
        ]
        env = SimpleNamespace(configuration={
            "boardSize": 10,
            "maxMarketOrdersPerTurn": 10,
            "farmHandCostMult": 1,
            "shedCapacity": 100,
        })
        engine._process_market(states, env)
        return farms, private, market

    def test_trailing_cap_preserves_all_prior_execution_and_saves_exact_cash(self):
        baseline = [["BUY_SEED", "MELON", 4], ["BUY_SEED", "MELON", 4]]
        candidate = [["BUY_SEED", "MELON", 4], ["BUY_SEED", "MELON", 1]]
        b_farms, b_private, b_market = self.execute(baseline)
        c_farms, c_private, c_market = self.execute(candidate)

        self.assertEqual(b_private[0]["seeds"]["MELON"], 8)
        self.assertEqual(c_private[0]["seeds"]["MELON"], 5)
        self.assertEqual(c_farms[0]["money"] - b_farms[0]["money"], 3 * 80)
        self.assertEqual(b_farms[1], c_farms[1])
        self.assertEqual(b_private[1], c_private[1])
        self.assertEqual(b_market, c_market)

    def test_partial_funding_stops_first_order_and_leaves_no_surplus(self):
        rows = [["BUY_SEED", "MELON", 4], ["BUY_SEED", "MELON", 4]]
        farms, private, _market = self.execute(rows, starting_money=240)
        # The first order buys exactly three units, aborts on its fourth unit, and
        # the later row sees zero cash. This is the pure gate's no-change case.
        self.assertEqual(private[0]["seeds"]["MELON"], 3)
        self.assertEqual(farms[0]["money"], 0)


if __name__ == "__main__":
    unittest.main()
