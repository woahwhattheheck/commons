# SPDX-License-Identifier: Apache-2.0
import unittest

from terminal_route_value import best_candidate, certify_candidate
from terminal_route_value_test_support import M, observation, row


class TerminalRouteValueRouteTests(unittest.TestCase):
    def test_near_wheat_route_certifies_before_terminal(self):
        obs = observation(step=712, farmer=(4, 4))
        obs["farms"][0]["tiles"][4][3] = {"kind": "PLANT", "crop": "WHEAT",
                                               "planted_day": 1, "yield_units": 2}
        route = [row() for _ in range(720)]
        candidate, report = certify_candidate(M, obs, {}, route, worker=0, target=(3, 4))
        self.assertTrue(report["certified"])
        self.assertEqual(candidate.product, "WHEAT")
        self.assertEqual(candidate.terminal_step, 715)
        self.assertEqual(candidate.unit_actions,
                         (("WEST",), ("HARVEST",), ("EAST",), ("DROP",)))
        self.assertEqual(candidate.market, (("SELL", "WHEAT", 2),))

    def test_richer_far_harvest_after_718_is_rejected(self):
        obs = observation(step=712, farmer=(4, 4))
        obs["farms"][0]["tiles"][0][0] = {"kind": "PLANT", "crop": "MELON",
                                               "planted_day": 0, "yield_units": 6}
        route = [row() for _ in range(720)]
        candidate, report = certify_candidate(M, obs, {}, route, worker=0, target=(0, 0))
        self.assertIsNone(candidate)
        self.assertEqual(report["reason"], "route_finishes_after_terminal")

    def test_drop_overflow_cannot_be_rescued_by_same_turn_sale(self):
        obs = observation(step=716, farmer=(4, 4), shed={"WHEAT": 100})
        obs["private"]["inventories"][0] = {"MILK": 1}
        route = [row() for _ in range(720)]
        route[716]["market"] = [["SELL", "WHEAT", 1]]
        candidate, report = certify_candidate(M, obs, {}, route, worker=0,
                                              carried_product="MILK")
        self.assertIsNone(candidate)
        self.assertEqual(report["reason"], "drop_would_overflow_before_market")

    def test_step_718_carried_good_can_drop_and_sell(self):
        obs = observation(step=718, farmer=(4, 4), inventories=[{"MILK": 1}])
        route = [row() for _ in range(720)]
        candidate, report = certify_candidate(M, obs, {}, route, worker=0,
                                              carried_product="MILK")
        self.assertTrue(report["certified"])
        self.assertEqual(candidate.terminal_step, 718)
        self.assertEqual(candidate.unit_actions, (("DROP",),))
        self.assertEqual(candidate.quiet_incremental_cash, 160)

    def test_step_718_harvest_needs_unavailable_later_drop(self):
        obs = observation(step=718, farmer=(3, 4))
        obs["farms"][0]["tiles"][4][3] = {"kind": "PLANT", "crop": "WHEAT",
                                               "planted_day": 1, "yield_units": 1}
        route = [row() for _ in range(720)]
        candidate, report = certify_candidate(M, obs, {}, route, worker=0, target=(3, 4))
        self.assertIsNone(candidate)
        self.assertEqual(report["reason"], "route_finishes_after_terminal")

    def test_existing_worker_commitment_is_not_displaced(self):
        obs = observation(step=712, farmer=(4, 4))
        obs["farms"][0]["tiles"][4][3] = {"kind": "PLANT", "crop": "WHEAT",
                                               "planted_day": 1, "yield_units": 1}
        route = [row() for _ in range(720)]; route[713]["farmer"] = ["CARE"]
        candidate, report = certify_candidate(M, obs, {}, route, worker=0, target=(3, 4))
        self.assertIsNone(candidate)
        self.assertEqual(report["reason"], "worker_has_existing_commitment")

    def test_other_worker_drop_collision_fails_closed(self):
        obs = observation(step=712, farmer=(4, 4), hands=((5, 4),))
        obs["farms"][0]["tiles"][4][3] = {"kind": "PLANT", "crop": "WHEAT",
                                               "planted_day": 1, "yield_units": 1}
        route = [row(hands=1) for _ in range(720)]; route[714]["hands"][0] = ["DROP"]
        candidate, report = certify_candidate(M, obs, {}, route, worker=0, target=(3, 4))
        self.assertIsNone(candidate)
        self.assertEqual(report["reason"], "other_actor_shed_collision")

    def test_preterminal_market_mutation_fails_closed(self):
        obs = observation(step=712, farmer=(4, 4))
        obs["farms"][0]["tiles"][4][3] = {"kind": "PLANT", "crop": "WHEAT",
                                               "planted_day": 1, "yield_units": 1}
        route = [row() for _ in range(720)]; route[713]["market"] = [["SELL", "WHEAT", 1]]
        candidate, report = certify_candidate(M, obs, {}, route, worker=0, target=(3, 4))
        self.assertIsNone(candidate)
        self.assertEqual(report["reason"], "preterminal_market_mutation_out_of_scope")
    def test_unmatured_plant_is_not_terminal_value(self):
        obs = observation(step=712, farmer=(3, 4))
        obs["farms"][0]["tiles"][4][3] = {"kind": "PLANT", "crop": "WHEAT",
                                               "planted_day": 29, "yield_units": 1}
        route = [row() for _ in range(720)]
        candidate, report = certify_candidate(M, obs, {}, route, worker=0, target=(3, 4))
        self.assertIsNone(candidate)
        self.assertEqual(report["reason"], "crop_not_mature")

    def test_best_candidate_prefers_reachable_positive_cash(self):
        obs = observation(step=712, farmer=(4, 4))
        obs["farms"][0]["tiles"][4][3] = {"kind": "PLANT", "crop": "WHEAT",
                                               "planted_day": 1, "yield_units": 2}
        obs["farms"][0]["tiles"][0][0] = {"kind": "PLANT", "crop": "MELON",
                                               "planted_day": 0, "yield_units": 6}
        route = [row() for _ in range(720)]
        winner, report = best_candidate(M, obs, {}, route)
        self.assertTrue(report["certified"])
        self.assertEqual(winner.product, "WHEAT")
        self.assertEqual(winner.target, (3, 4))


if __name__ == "__main__":
    unittest.main()
