# SPDX-License-Identifier: Apache-2.0
"""Adversarial contracts for the exact joint transition oracle."""
from test_support import *  # noqa: F403


class JointTransitionContracts(unittest.TestCase):
    def test_011_sale_funds_inherited_hire_and_is_flagged(self):
            result = compare(payload(
                own_cash=0, own_shed={"WHEAT": 2}, own_hands=2, own_hires=2,
                baseline=[[], ["HIRE"]], candidate=[["SELL", "WHEAT", 2], ["HIRE"]],
            ))
            self.assertEqual(len(result["baseline"]["pre_town_state"]["farms"][0]["hands"]), 2)
            self.assertEqual(len(result["candidate"]["pre_town_state"]["farms"][0]["hands"]), 3)
            changes = result["comparison"]["inherited_same_slot_execution_changes"]
            self.assertTrue(any(row["prefix_length"] == 2 and row["player"] == 0 for row in changes))
    def test_012_sale_funds_later_seed_acquisition(self):
            result = compare(payload(
                own_cash=0, own_shed={"CARROT": 3},
                baseline=[["BUY_SEED", "TOMATO", 2], ["SELL", "CARROT", 3]],
                candidate=[["SELL", "CARROT", 3], ["BUY_SEED", "TOMATO", 2]],
            ))
            self.assertEqual(result["baseline"]["pre_town_state"]["privates"][0]["seeds"]["TOMATO"], 0)
            self.assertEqual(result["candidate"]["pre_town_state"]["privates"][0]["seeds"]["TOMATO"], 2)
    def test_013_shed_capacity_changes_animal_fill(self):
            result = compare(payload(
                own_cash=1000, own_shed={"CARROT": 1},
                baseline=[["BUY_ANIMAL", "COW", 1]],
                candidate=[["SELL", "CARROT", 1], ["BUY_ANIMAL", "COW", 1]],
                configuration={"shedCapacity": 1},
            ))
            self.assertEqual(result["baseline"]["pre_town_state"]["privates"][0]["shed"]["COW"], 0)
            self.assertEqual(result["candidate"]["pre_town_state"]["privates"][0]["shed"]["COW"], 1)
    def test_014_repeated_hire_and_land_acquisitions_are_visible(self):
            result = compare(payload(
                own_cash=8000, baseline=[],
                candidate=[["HIRE"], ["HIRE"], ["HIRE"], ["BUY_LAND"], ["BUY_LAND"]],
            ))
            state = result["candidate"]["pre_town_state"]
            self.assertEqual(state["farms"][0]["hires_today"], 3)
            self.assertEqual(state["farms"][0]["unlocked_quadrants"], ["NW", "NE", "SW"])
            self.assertEqual(len(state["privates"][0]["inventories"]), 4)
    def test_015_malformed_orders_are_literal_noops_not_repacked(self):
            result = compare(payload(
                own_cash=100, own_shed={"WHEAT": 1},
                baseline=[], candidate=[None, ["BOGUS"], ["SELL", "WHEAT", "bad"], ["SELL", "WHEAT", 1]],
            ))
            self.assertEqual(len(result["candidate"]["prefixes"]), 5)
            self.assertEqual(result["candidate"]["prefixes"][1]["executions"][0]["executed_units"], 0)
            self.assertEqual(result["candidate"]["prefixes"][2]["executions"][0]["executed_units"], 0)
            self.assertEqual(result["candidate"]["prefixes"][3]["executions"][0]["executed_units"], 0)
            self.assertEqual(result["candidate"]["prefixes"][4]["executions"][0]["executed_units"], 1)
    def test_016_same_slot_shared_precommit_quotes(self):
            result = compare(payload(
                own_shed={"WHEAT": 2}, rival_shed={"WHEAT": 2},
                baseline=[], candidate=[["SELL", "WHEAT", 2]], rival=[["SELL", "WHEAT", 2]],
            ))
            own = result["candidate"]["prefixes"][1]["executions"][0]["cash_delta"]
            rival = result["candidate"]["prefixes"][1]["executions"][1]["cash_delta"]
            self.assertEqual(own, rival)
    def test_017_checkpoint_pass_on_preserved_lot(self):
            checkpoints = [{
                "name": "first-wheat-lot",
                "baseline_stage": 1,
                "candidate_stage": 1,
                "paths": ["/executions/0/executed_units", "/executions/0/cash_delta"],
            }]
            result = compare(payload(
                own_shed={"WHEAT": 1, "MILK": 1},
                baseline=[["SELL", "WHEAT", 1]],
                candidate=[["SELL", "WHEAT", 1], ["SELL", "MILK", 1]],
                checkpoints=checkpoints,
            ))
            self.assertEqual(result["comparison"]["protection"]["status"], "PASS")
    def test_018_no_checkpoints_never_claims_pass(self):
            result = compare(payload())
            self.assertEqual(result["comparison"]["protection"]["status"], "UNSPECIFIED")
