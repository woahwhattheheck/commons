# SPDX-License-Identifier: Apache-2.0
"""Adversarial contracts for the exact joint transition oracle."""
from test_support import *  # noqa: F403


class JointTransitionContracts(unittest.TestCase):
    def test_001_source_identity_is_exact(self):
            self.assertEqual(ENGINE.git_blob_sha1, oracle.ENGINE_GIT_BLOB)
            self.assertEqual(ENGINE.source_sha256, oracle.ENGINE_SHA256)

    def test_002_modified_engine_is_rejected(self):
            with tempfile.TemporaryDirectory() as directory:
                modified = Path(directory) / "kaggriculture.py"
                modified.write_bytes(Path(ENGINE_SOURCE).read_bytes() + b"\n")
                with self.assertRaisesRegex(ValueError, "engine_git_blob_mismatch"):
                    oracle.load_transition_engine(modified)

    def test_036_unbound_engine_object_fails_closed(self):
            fake = copy.copy(ENGINE)
            fake.git_blob_sha1 = "0" * 40
            result = oracle.compare_joint_transition(fake, **payload())
            self.assertEqual(result["status"], "unknown")
            self.assertIn("unbound_engine_git_blob", result["reason"])

    def test_037_inconsistent_observed_price_fails_closed(self):
            value = payload()
            value["market"]["prices"]["WHEAT"] += 1
            result = compare(value)
            self.assertEqual(result["status"], "unknown")
            self.assertIn("market_price_state_mismatch:WHEAT", result["reason"])

    def test_038_negative_market_inventory_fails_closed(self):
            value = payload()
            value["market"]["inventory"]["WHEAT"] = -1
            value["market"]["prices"]["WHEAT"] = ENGINE.market_price("WHEAT", -1)
            result = compare(value)
            self.assertEqual(result["status"], "unknown")
            self.assertIn("market_inventory_WHEAT_negative", result["reason"])

    def test_039_unreachable_ninth_shop_fails_closed(self):
            result = compare(payload(shops=["BAKERY"] * 9))
            self.assertEqual(result["status"], "unknown")
            self.assertIn("too_many_town_shop_instances", result["reason"])

    def test_040_board_shape_mismatch_fails_closed(self):
            value = payload()
            value["farms"][0]["tiles"].pop()
            result = compare(value)
            self.assertEqual(result["status"], "unknown")
            self.assertIn("board_shape_mismatch", result["reason"])

    def test_041_nonmarket_candidate_field_change_fails_closed(self):
            value = payload()
            value["baseline_actions"][0]["audit"] = {"tag": "parent"}
            value["candidate_actions"][0]["audit"] = {"tag": "candidate"}
            result = compare(value)
            self.assertEqual(result["status"], "unknown")
            self.assertIn("candidate_may_only_change_tested_market_queue", result["reason"])

    def test_042_hire_fibonacci_work_is_bounded(self):
            value = payload(own_cash=10**30, own_hands=50, own_hires=50,
                            baseline=[["HIRE"]], candidate=[["HIRE"]])
            result = compare(value, max_work_units=100)
            self.assertEqual(result["status"], "unknown")
            self.assertEqual(result["reason"], "unit_work_budget")

    def test_043_hire_count_must_match_live_hands(self):
            value = payload(own_hires=1, own_hands=0)
            result = compare(value)
            self.assertEqual(result["status"], "unknown")
            self.assertIn("hire_hand_count_mismatch", result["reason"])

    def test_044_market_iteration_guard_is_never_exercised(self):
            result = compare(payload(
                own_cash=10**9, baseline=[], candidate=[["BUY_SEED", "WHEAT", 99_999]],
            ), max_work_units=10**9)
            self.assertEqual(result["status"], "unknown")
            self.assertEqual(result["reason"], "official_market_iteration_guard")

    def test_045_direct_api_bounds_and_deadline_are_typed(self):
            value = payload()
            bad_budget = compare(value, max_work_units=True)
            self.assertEqual(bad_budget["status"], "unknown")
            self.assertIn("max_work_units_must_be_int", bad_budget["reason"])
            bad_deadline = compare(value, deadline=math.nan)
            self.assertEqual(bad_deadline["status"], "unknown")
            self.assertIn("deadline_must_be_finite_absolute_time", bad_deadline["reason"])

    def test_046_extracted_transition_matches_full_official_module(self):
            reference = load_full_reference(Path(ENGINE_SOURCE))
            cases = [
                payload(
                    step=0, own_cash=5000, rival_cash=5000,
                    own_shed={"WHEAT": 79, "MILK": 1}, rival_shed={"WHEAT": 100},
                    baseline=[["SELL", "WHEAT", 78], ["SELL", "WHEAT", 1], ["SELL", "MILK", 1]],
                    candidate=[["SELL", "WHEAT", 78], ["SELL", "MILK", 1], ["SELL", "WHEAT", 1]],
                    rival=[[], ["SELL", "WHEAT", 100], []],
                    inventory={"WHEAT": 10066, "MILK": 9999}, shops=["BAKERY"] * 8,
                ),
                payload(
                    step=24, own_cash=6000, rival_cash=6000, own_hands=1, own_hires=1,
                    own_shed={"WHEAT": 2}, rival_shed={"FERTILIZER": 2},
                    baseline=[["HIRE"], ["BUY_LAND"], ["BUY_SEED", "CARROT", 2]],
                    candidate=[["HIRE"], ["BUY_LAND"], ["BUY_PRODUCT", "WHEAT", 2]],
                    rival=[["SELL", "FERTILIZER", 2]], shops=["YARN_STORE", "PIZZA_SHOP"],
                ),
            ]
            for value in cases:
                prestate = oracle._state_from_inputs(value["farms"], value["privates"], value["market"], value["town"])
                for actions in (value["baseline_actions"], value["candidate_actions"]):
                    extracted = oracle._simulate_prefix(
                        ENGINE, prestate, actions, value["configuration"], step=value["step"],
                        prefix_length=10, apply_town=True,
                    )
                    full = oracle._simulate_prefix(
                        reference, prestate, actions, value["configuration"], step=value["step"],
                        prefix_length=10, apply_town=True,
                    )
                    self.assertEqual(extracted, full)

