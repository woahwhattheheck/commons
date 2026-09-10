# SPDX-License-Identifier: Apache-2.0
"""Adversarial contracts for the exact joint transition oracle."""
from test_support import *  # noqa: F403


class JointTransitionContracts(unittest.TestCase):
    def test_019_missing_checkpoint_path_fails_closed(self):
            result = compare(payload(checkpoints=[{
                "name": "bad", "baseline_stage": 0, "candidate_stage": 0,
                "paths": ["/state/no_such_component"],
            }]))
            self.assertEqual(result["status"], "unknown")
            self.assertIn("missing_pointer", result["reason"])

    def test_020_duplicate_checkpoint_names_fail_closed(self):
            row = {"name": "same", "baseline_stage": 0, "candidate_stage": 0, "paths": ["/state_hash"]}
            result = compare(payload(checkpoints=[row, row]))
            self.assertEqual(result["status"], "unknown")

    def test_021_rival_action_mismatch_fails_closed(self):
            value = payload()
            value["candidate_actions"][1]["market"] = [["HIRE"]]
            result = compare(value)
            self.assertEqual(result["status"], "unknown")
            self.assertIn("rival_action_must_be_identical", result["reason"])

    def test_022_unit_action_change_fails_closed(self):
            value = payload()
            value["candidate_actions"][0]["farmer"] = ["NORTH"]
            result = compare(value)
            self.assertEqual(result["status"], "unknown")
            self.assertIn("candidate_may_only_change_tested_market_queue", result["reason"])

    def test_023_nonfinite_money_fails_closed(self):
            value = payload()
            value["farms"][0]["money"] = math.inf
            result = compare(value)
            self.assertEqual(result["status"], "unknown")
            self.assertIn("nonfinite", result["reason"])

    def test_024_bool_configuration_fails_closed(self):
            value = payload(configuration={"shedCapacity": True})
            result = compare(value)
            self.assertEqual(result["status"], "unknown")
            self.assertIn("shedCapacity_must_be_int", result["reason"])

    def test_025_unknown_shop_fails_closed(self):
            result = compare(payload(shops=["NOT_A_SHOP"]))
            self.assertEqual(result["status"], "unknown")
            self.assertIn("unknown_town_shop", result["reason"])

    def test_026_work_budget_fails_before_engine_execution(self):
            result = compare(payload(
                own_shed={"WHEAT": 100}, candidate=[["SELL", "WHEAT", 100]],
            ), max_work_units=1)
            self.assertEqual(result["status"], "unknown")
            self.assertEqual(result["reason"], "unit_work_budget")

    def test_027_expired_deadline_fails_closed(self):
            result = compare(payload(), deadline=time.monotonic() - 1)
            self.assertEqual(result["status"], "unknown")
            self.assertEqual(result["reason"], "deadline")

    def test_028_order_budget_fails_closed(self):
            result = compare(payload(configuration={"maxMarketOrdersPerTurn": 129}), max_orders_budget=128)
            self.assertEqual(result["status"], "unknown")
            self.assertEqual(result["reason"], "order_budget")

    def test_029_input_objects_are_not_mutated_or_aliased(self):
            value = payload(own_shed={"WHEAT": 2}, candidate=[["SELL", "WHEAT", 2]])
            before = copy.deepcopy(value)
            result = oracle.compare_joint_transition(ENGINE, **value)
            self.assertEqual(value, before)
            self.assertTrue(result["input_unchanged"])
            result["candidate"]["post_town_state"]["farms"][0]["money"] = -999
            self.assertEqual(value, before)

    def test_030_hashes_are_deterministic(self):
            value = payload(own_shed={"WHEAT": 2}, candidate=[["SELL", "WHEAT", 2]])
            first = compare(value)
            second = compare(value)
            for arm in ("baseline", "candidate"):
                self.assertEqual(first[arm]["pre_town_state_hash"], second[arm]["pre_town_state_hash"])
                self.assertEqual(first[arm]["post_town_state_hash"], second[arm]["post_town_state_hash"])
            self.assertEqual(first["input_hash"], second["input_hash"])

    def test_031_full_market_inventory_and_price_are_hashed(self):
            result = compare(payload(own_shed={"WHEAT": 1}, candidate=[["SELL", "WHEAT", 1]]))
            state = result["candidate"]["pre_town_state"]
            self.assertEqual(result["candidate"]["pre_town_state_hash"], oracle.canonical_sha256(state))
            self.assertIn("WHEAT", state["market"]["prices"])

