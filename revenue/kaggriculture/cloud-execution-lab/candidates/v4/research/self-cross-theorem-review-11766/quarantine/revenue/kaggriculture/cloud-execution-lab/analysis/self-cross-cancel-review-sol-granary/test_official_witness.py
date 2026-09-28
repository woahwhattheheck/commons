# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

from official_witness import EXPECTED_ENGINE_GIT_BLOB, build_report


class SelfCrossOfficialWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_exact_engine_is_bound(self):
        self.assertEqual(
            self.report["engine"]["git_blob"],
            EXPECTED_ENGINE_GIT_BLOB,
        )
        self.assertEqual(len(self.report["engine"]["raw_sha256"]), 64)
        self.assertGreater(self.report["engine"]["bytes"], 1_000)

    def test_intervening_rival_buy_makes_cancellation_beneficial(self):
        for own_player in (0, 1):
            with self.subTest(own_player=own_player):
                case = self.report["cases"][f"seat{own_player}_rival_buy"]
                self.assertTrue(case["terminal_non_money_state_equal"])
                self.assertEqual(case["verdict"], "REPLAY_BENEFIT")
                self.assertEqual(case["cancelled_minus_baseline"]["own_money"], 1.0)
                self.assertEqual(case["cancelled_minus_baseline"]["rival_money"], -1.0)
                self.assertEqual(case["baseline"]["own_wheat"], case["cancelled"]["own_wheat"])
                self.assertEqual(case["baseline"]["market_wheat"], case["cancelled"]["market_wheat"])

    def test_intervening_rival_sell_reverses_the_sign(self):
        for own_player in (0, 1):
            with self.subTest(own_player=own_player):
                case = self.report["cases"][f"seat{own_player}_rival_sell"]
                self.assertTrue(case["terminal_non_money_state_equal"])
                self.assertEqual(case["verdict"], "REPLAY_HARM")
                self.assertEqual(case["cancelled_minus_baseline"]["own_money"], -1.0)
                self.assertEqual(case["cancelled_minus_baseline"]["rival_money"], 1.0)
                self.assertEqual(case["baseline"]["own_wheat"], case["cancelled"]["own_wheat"])
                self.assertEqual(case["baseline"]["market_wheat"], case["cancelled"]["market_wheat"])

    def test_player_order_does_not_rescue_hidden_action_uncertainty(self):
        seat0_buy = self.report["cases"]["seat0_rival_buy"]["cancelled_minus_baseline"]
        seat1_buy = self.report["cases"]["seat1_rival_buy"]["cancelled_minus_baseline"]
        seat0_sell = self.report["cases"]["seat0_rival_sell"]["cancelled_minus_baseline"]
        seat1_sell = self.report["cases"]["seat1_rival_sell"]["cancelled_minus_baseline"]
        self.assertEqual(seat0_buy, seat1_buy)
        self.assertEqual(seat0_sell, seat1_sell)

    def test_price_floor_breaks_market_inventory_equivalence(self):
        case = self.report["price_floor_case"]
        self.assertFalse(case["terminal_non_money_state_equal"])
        self.assertEqual(case["baseline_own_wheat"], case["cancelled_own_wheat"])
        self.assertEqual(case["baseline_own_money"], case["cancelled_own_money"])
        self.assertEqual(
            case["cancelled_market_wheat"] - case["baseline_market_wheat"],
            1,
        )

    def test_machine_verdict_separates_replay_from_runtime(self):
        conclusion = self.report["conclusion"]
        self.assertTrue(conclusion["opponent_contingent"])
        self.assertEqual(conclusion["verdict"], "OPPONENT_CONTINGENT")
        self.assertFalse(conclusion["runtime_dominance_proven"])
        self.assertIn("BOUND_TAPE", conclusion["observed_replay_counterfactual_can_prove"])
        self.assertIn("all-rival-action", conclusion["runtime_requirement"])


if __name__ == "__main__":
    unittest.main()
