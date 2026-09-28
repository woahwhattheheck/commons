# SPDX-License-Identifier: Apache-2.0
"""Exact installed-engine witnesses for raw-cap and index-lockstep semantics."""
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

    @staticmethod
    def _after_pair(first_market, second_market):
        env = make(
            "kaggriculture",
            configuration={"maxMarketOrdersPerTurn": 3, "episodeSteps": 4, "seed": 20260909},
            debug=True,
        )
        env.step([
            {"farmer": ["PASS"], "market": first_market},
            {"farmer": ["PASS"], "market": second_market},
        ])
        state = env.state[0]
        farm = state.observation.farms[0]
        rival = state.observation.farms[1]
        private = state.observation.private
        return {
            "money": float(farm["money"]),
            "rival_money": float(rival["money"]),
            "seeds": dict(private["seeds"]),
            "shed": dict(private["shed"]),
            "hands": len(farm["hands"]),
        }

    def test_exact_blank_consumes_raw_cap_and_suffix_rescue_promotes_tail_buy(self):
        stranded = {"farmer": ["PASS"], "market": [[], ["BUY_SEED", "WHEAT", 1]]}
        rescued, report = rescue_market_prefix(stranded, {"maxMarketOrdersPerTurn": 1})
        self.assertTrue(report["changed"])
        self.assertEqual(report["activation_class"], "suffix_only")
        before_seeds, before_money = self._after_one_step(stranded["market"])
        after_seeds, after_money = self._after_one_step(rescued["market"])
        self.assertEqual(before_seeds.get("WHEAT", 0), 0)
        self.assertEqual(before_money, 3000.0)
        self.assertEqual(after_seeds.get("WHEAT", 0), 1)
        self.assertEqual(after_money, 2990.0)

    def test_interior_stable_pack_retimes_live_purchase_against_rival(self):
        """Prove absolute queue index is economic, not a cosmetic list position."""
        original = {
            "farmer": ["PASS"],
            "market": [
                [],
                ["BUY_PRODUCT", "WHEAT", 1],
                ["HIRE"],
                ["BUY_SEED", "WHEAT", 1],
            ],
        }
        unchanged, report = rescue_market_prefix(original, {"maxMarketOrdersPerTurn": 3})
        self.assertIs(unchanged, original)
        self.assertEqual(report["reason"], "interior_blank_would_retime_active_order")

        # This is the predecessor's broad stable pack. It moves the already-live
        # WHEAT purchase from index 1 to index 0.
        broad_stable_pack = [
            ["BUY_PRODUCT", "WHEAT", 1],
            ["HIRE"],
            ["BUY_SEED", "WHEAT", 1],
            [],
        ]
        # Same candidate order multiset, but the fixed-price rescued seed fills
        # the blank while the existing WHEAT purchase and HIRE stay at 1 and 2.
        index_preserving_control = [
            ["BUY_SEED", "WHEAT", 1],
            ["BUY_PRODUCT", "WHEAT", 1],
            ["HIRE"],
        ]
        rival = [["BUY_PRODUCT", "WHEAT", 100]]
        broad = self._after_pair(broad_stable_pack, rival)
        control = self._after_pair(index_preserving_control, rival)

        # Both candidate variants execute the same useful operations and end
        # with the same owned goods/workers. Their cash differs only because the
        # broad pack quotes the WHEAT purchase at an earlier rival-lockstep index.
        self.assertEqual(broad["seeds"].get("WHEAT", 0), 1)
        self.assertEqual(control["seeds"].get("WHEAT", 0), 1)
        self.assertEqual(broad["shed"].get("WHEAT", 0), 1)
        self.assertEqual(control["shed"].get("WHEAT", 0), 1)
        self.assertEqual(broad["hands"], 1)
        self.assertEqual(control["hands"], 1)
        self.assertGreater(broad["money"], control["money"])
        self.assertNotEqual(broad["rival_money"], control["rival_money"])


if __name__ == "__main__":
    unittest.main()
