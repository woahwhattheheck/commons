# SPDX-License-Identifier: Apache-2.0
"""Adversarial contracts for the exact joint transition oracle."""
from test_support import *  # noqa: F403


class JointTransitionContracts(unittest.TestCase):
    def test_034_custom_market_params_flow_through_official_functions(self):
            value = payload(own_shed={"WHEAT": 1}, candidate=[["SELL", "WHEAT", 1]])
            custom = copy.deepcopy(ENGINE.MARKET_PARAMS)
            custom["WHEAT"]["base"] = 77
            value["market"]["params"] = custom
            ENGINE._refresh_prices(value["market"])
            result = compare(value)
            self.assertEqual(result["candidate"]["prefixes"][1]["executions"][0]["cash_delta"], 77)
    def test_035_rival_sale_can_change_inherited_own_receipt(self):
            # Rival sells one unit in row 0 under both arms. Baseline also sells
            # there, crossing 10065->10066; candidate does not. The unchanged own
            # row-1 lot therefore receives $21 in baseline and $22 in candidate.
            result = compare(payload(
                own_shed={"WHEAT": 2}, rival_shed={"WHEAT": 1},
                baseline=[["SELL", "WHEAT", 1], ["SELL", "WHEAT", 1]],
                candidate=[[], ["SELL", "WHEAT", 1]],
                rival=[["SELL", "WHEAT", 1], []], inventory={"WHEAT": 10064},
            ))
            changes = result["comparison"]["inherited_same_slot_execution_changes"]
            self.assertTrue(any(row["prefix_length"] == 2 for row in changes))
    def test_047_rival_buy_demand_changes_promoted_wheat_receipt(self):
            parent = [["SELL", "EGG", 1], ["SELL", "WHEAT", 1]]
            reordered = [["SELL", "WHEAT", 1], ["SELL", "EGG", 1]]
            rival = [["BUY_PRODUCT", "WHEAT", 1], []]
            checkpoints = [{
                "name": "promoted-wheat-receipt",
                "baseline_stage": 2,
                "candidate_stage": 1,
                "paths": ["/executions/0/executed_units", "/executions/0/cash_delta"],
            }]
            result = compare(payload(
                own_shed={"EGG": 1, "WHEAT": 1}, rival_cash=26,
                baseline=parent, candidate=reordered, rival=rival,
                inventory={"EGG": 10139, "WHEAT": 10000}, checkpoints=checkpoints,
            ))
            self.assertEqual(result["baseline"]["pre_town_state"]["farms"][0]["money"], 67)
            self.assertEqual(result["candidate"]["pre_town_state"]["farms"][0]["money"], 66)
            self.assertEqual(result["baseline"]["pre_town_state"]["farms"][1]["money"], 0)
            self.assertEqual(result["candidate"]["pre_town_state"]["farms"][1]["money"], 0)
            self.assertEqual(result["comparison"]["own_cash_delta"], -1)
            self.assertEqual(result["comparison"]["relative_cash_delta"], -1)
            self.assertEqual(result["comparison"]["protection"]["status"], "HOLD")
    def test_048_same_product_tranche_rewrite_moves_rival_buy_quote(self):
            parent = [["SELL", "WHEAT", 1], [], ["SELL", "WHEAT", 1]]
            rewritten = [["SELL", "WHEAT", 2], [], ["SELL", "WHEAT", 1]]
            rival = [[], ["BUY_PRODUCT", "WHEAT", 1], []]
            result = compare(payload(
                own_shed={"WHEAT": 2}, rival_cash=1000, baseline=parent,
                candidate=rewritten, rival=rival, inventory={"WHEAT": 10219},
            ))
            self.assertEqual(result["baseline"]["pre_town_state"]["farms"][0]["money"], 42)
            self.assertEqual(result["candidate"]["pre_town_state"]["farms"][0]["money"], 41)
            self.assertEqual(result["baseline"]["pre_town_state"]["farms"][1]["money"], 979)
            self.assertEqual(result["candidate"]["pre_town_state"]["farms"][1]["money"], 980)
            self.assertEqual(result["comparison"]["own_cash_delta"], -1)
            self.assertEqual(result["comparison"]["rival_cash_delta"], 1)
            self.assertEqual(result["comparison"]["relative_cash_delta"], -2)
