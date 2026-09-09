# SPDX-License-Identifier: Apache-2.0
"""Exact installed-engine witness for the raw-prefix-before-parse behavior."""
from __future__ import annotations

import unittest

from market_prefix_rescue import rescue_market_prefix

try:
    from kaggle_environments import make
except ImportError:  # Local connector shells may not have the 59 MB package.
    make = None


@unittest.skipIf(make is None, "kaggle-environments not installed")
class OfficialEngineContractTests(unittest.TestCase):
    @staticmethod
    def _after_one_step(market):
        env = make(
            "kaggriculture",
            configuration={"maxMarketOrdersPerTurn": 1, "episodeSteps": 4, "seed": 20260909},
            debug=True,
        )
        env.step([
            {"farmer": ["PASS"], "market": market},
            {"farmer": ["PASS"], "market": []},
        ])
        state = env.state[0]
        seeds = dict(state.observation.private["seeds"])
        money = float(state.observation.farms[0]["money"])
        return seeds, money

    def test_exact_blank_consumes_raw_cap_and_rescue_promotes_tail_buy(self):
        stranded = {"farmer": ["PASS"], "market": [[], ["BUY_SEED", "WHEAT", 1]]}
        rescued, report = rescue_market_prefix(stranded, {"maxMarketOrdersPerTurn": 1})
        self.assertTrue(report["changed"])
        before_seeds, before_money = self._after_one_step(stranded["market"])
        after_seeds, after_money = self._after_one_step(rescued["market"])
        self.assertEqual(before_seeds.get("WHEAT", 0), 0)
        self.assertEqual(before_money, 3000.0)
        self.assertEqual(after_seeds.get("WHEAT", 0), 1)
        self.assertEqual(after_money, 2990.0)


if __name__ == "__main__":
    unittest.main()
