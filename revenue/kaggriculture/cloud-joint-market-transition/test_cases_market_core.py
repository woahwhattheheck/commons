# SPDX-License-Identifier: Apache-2.0
"""Adversarial contracts for the exact joint transition oracle."""
from test_support import *  # noqa: F403


class JointTransitionContracts(unittest.TestCase):
    def test_003_prefix_shift_predecessor_exact_cash(self):
            baseline = [["SELL", "WHEAT", 78], ["SELL", "WHEAT", 1], ["SELL", "MILK", 1]]
            candidate = [["SELL", "WHEAT", 78], ["SELL", "MILK", 1], ["SELL", "WHEAT", 1]]
            rival = [[], ["SELL", "WHEAT", 100], []]
            checkpoints = [{
                "name": "moved-wheat-one-unit-receipt",
                "baseline_stage": 2,
                "candidate_stage": 3,
                "paths": ["/executions/0/executed_units", "/executions/0/cash_delta"],
            }]
            result = compare(payload(
                own_shed={"WHEAT": 79, "MILK": 1}, rival_shed={"WHEAT": 100},
                baseline=baseline, candidate=candidate, rival=rival,
                inventory={"WHEAT": 10066, "MILK": 9999}, checkpoints=checkpoints,
            ))
            self.assertEqual(result["status"], "complete_conditional")
            self.assertEqual(result["baseline"]["pre_town_state"]["farms"][0]["money"], 1828)
            self.assertEqual(result["baseline"]["pre_town_state"]["farms"][1]["money"], 2075)
            self.assertEqual(result["candidate"]["pre_town_state"]["farms"][0]["money"], 1827)
            self.assertEqual(result["candidate"]["pre_town_state"]["farms"][1]["money"], 2076)
            self.assertEqual(result["comparison"]["own_cash_delta"], -1)
            self.assertEqual(result["comparison"]["rival_cash_delta"], 1)
            self.assertEqual(result["comparison"]["relative_cash_delta"], -2)
            self.assertEqual(result["comparison"]["protection"]["status"], "HOLD")
    def test_004_prefix_shift_is_seat_symmetric(self):
            baseline = [["SELL", "WHEAT", 78], ["SELL", "WHEAT", 1], ["SELL", "MILK", 1]]
            candidate = [["SELL", "WHEAT", 78], ["SELL", "MILK", 1], ["SELL", "WHEAT", 1]]
            rival = [[], ["SELL", "WHEAT", 100], []]
            result = compare(payload(
                seat=1, own_shed={"WHEAT": 79, "MILK": 1}, rival_shed={"WHEAT": 100},
                baseline=baseline, candidate=candidate, rival=rival,
                inventory={"WHEAT": 10066, "MILK": 9999},
            ))
            self.assertEqual(result["comparison"]["own_cash_delta"], -1)
            self.assertEqual(result["comparison"]["rival_cash_delta"], 1)
    def test_005_floor_sales_pay_but_do_not_add_supply(self):
            result = compare(payload(
                own_shed={"MILK": 3}, baseline=[], candidate=[["SELL", "MILK", 3]],
                inventory={"MILK": 100000},
            ))
            candidate = result["candidate"]["pre_town_state"]
            self.assertEqual(candidate["farms"][0]["money"], 3)
            self.assertEqual(candidate["market"]["inventory"]["MILK"], 100000)
            self.assertEqual(result["candidate"]["prefixes"][1]["executions"][0]["executed_units"], 3)
    def test_006_town_runs_after_market(self):
            result = compare(payload(
                step=0, own_shed={"WHEAT": 1}, baseline=[], candidate=[["SELL", "WHEAT", 1]],
                shops=["BAKERY"] * 8,
            ))
            self.assertEqual(result["candidate"]["pre_town_state"]["market"]["inventory"]["WHEAT"], 10001)
            self.assertEqual(result["candidate"]["post_town_state"]["market"]["inventory"]["WHEAT"], 9992)
            self.assertEqual(result["candidate"]["town_effect"]["inventory_delta"]["WHEAT"], -9)
    def test_007_duplicate_shops_and_center_each_consume(self):
            result = compare(payload(step=0, shops=["BAKERY"] * 8))
            post = result["baseline"]["post_town_state"]["market"]["inventory"]
            self.assertEqual(post["WHEAT"], 9991)
            self.assertEqual(post["EGG"], 9991)
            self.assertEqual(post["CARROT"], 9999)
            self.assertEqual(post["FERTILIZER"], 10000)
    def test_008_town_funding_boundary_reaches_quote_32(self):
            state = oracle._state_from_inputs(
                [farm(31), farm(0)],
                [private(shed={"MILK": 1}), private()],
                market({"WHEAT": 10000}),
                {"unlocked_shops": ["BAKERY"] * 8},
            )
            cfg = config()
            actions = [action([["SELL", "MILK", 1]]), action([])]
            # Step 0 market sale is retained, then six exact shop events occur at
            # 0/4/8/12/16/20. No omitted phase mutates WHEAT in this constructed proof.
            state = oracle._simulate_prefix(ENGINE, state, actions, cfg, step=0, prefix_length=1, apply_town=True)
            for step in (4, 8, 12, 16, 20):
                state = oracle._simulate_prefix(ENGINE, state, [action([]), action([])], cfg,
                                                step=step, prefix_length=0, apply_town=True)
            self.assertEqual(state["market"]["inventory"]["WHEAT"], 9951)
            self.assertEqual(ENGINE.market_price("WHEAT", 9950, state["market"].get("params")), 32)
            purchase = oracle._simulate_prefix(
                ENGINE, state, [action([["BUY_PRODUCT", "WHEAT", 1]]), action([])], cfg,
                step=22, prefix_length=1, apply_town=False,
            )
            self.assertEqual(purchase["farms"][0]["money"], 159)  # $31 + $160 MILK - $32 WHEAT.
            no_sale = copy.deepcopy(state)
            no_sale["farms"][0]["money"] = 31
            no_sale["privates"][0]["shed"]["MILK"] = 1
            failed = oracle._simulate_prefix(
                ENGINE, no_sale, [action([["BUY_PRODUCT", "WHEAT", 1]]), action([])], cfg,
                step=22, prefix_length=1, apply_town=False,
            )
            self.assertEqual(failed["farms"][0]["money"], 31)
            self.assertEqual(failed["privates"][0]["shed"]["WHEAT"], 0)
    def test_009_identical_active_prefix_ignores_arbitrary_suffix(self):
            base = [["SELL", "WHEAT", 1], ["BUY_SEED", "CARROT", 1], ["HIRE"]]
            cand = [["SELL", "WHEAT", 1], ["BUY_SEED", "CARROT", 1], ["SELL", "MILK", 99999], ["BUY_LAND"]]
            result = compare(payload(
                own_cash=100, own_shed={"WHEAT": 1, "MILK": 1},
                baseline=base, candidate=cand, configuration={"maxMarketOrdersPerTurn": 2},
            ))
            self.assertTrue(result["comparison"]["pre_town_state_equal"])
            self.assertTrue(result["comparison"]["post_town_state_equal"])
            self.assertEqual(result["baseline"]["active_action_hash"], result["candidate"]["active_action_hash"])
            self.assertNotEqual(result["baseline"]["ignored_suffix_hash"], result["candidate"]["ignored_suffix_hash"])
    def test_010_zero_config_limit_matches_engine_minimum_one(self):
            result = compare(payload(
                own_cash=100, baseline=[], candidate=[["BUY_SEED", "WHEAT", 1], ["HIRE"]],
                configuration={"maxMarketOrdersPerTurn": 0},
            ))
            self.assertEqual(result["candidate"]["pre_town_state"]["farms"][0]["money"], 90)
            self.assertEqual(len(result["candidate"]["active_queues"][0]), 1)
