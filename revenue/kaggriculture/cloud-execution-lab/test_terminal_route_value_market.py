# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import unittest

from terminal_route_value import best_candidate, certify_candidate, quiet_sale_receipts
from terminal_route_value_test_support import M, observation, row


class TerminalRouteValueMarketTests(unittest.TestCase):
    def test_non_sale_final_commitment_is_a_barrier(self):
        obs = observation(step=716, farmer=(4, 4), inventories=[{"MILK": 1}])
        route = [row() for _ in range(720)]; route[716]["market"] = [["BUY_PRODUCT", "WHEAT", 1]]
        candidate, report = certify_candidate(M, obs, {}, route, worker=0,
                                              carried_product="MILK")
        self.assertIsNone(candidate)
        self.assertEqual(report["reason"], "final_market_has_non_sale_commitment")

    def test_full_final_market_has_no_new_terminal_slot(self):
        obs = observation(step=718, farmer=(4, 4), inventories=[{"MILK": 1}])
        route = [row() for _ in range(720)]
        route[718]["market"] = [["SELL", "WHEAT", 1] for _ in range(10)]
        candidate, report = certify_candidate(M, obs, {}, route, worker=0,
                                              carried_product="MILK")
        self.assertIsNone(candidate)
        self.assertEqual(report["reason"], "no_trailing_terminal_market_slot")

    def test_trailing_empty_slot_is_reused_after_commitments(self):
        obs = observation(step=718, farmer=(4, 4), inventories=[{"MILK": 1}], shed={"WHEAT": 1})
        route = [row() for _ in range(720)]; route[718]["market"] = [["SELL", "WHEAT", 1], [], []]
        candidate, report = certify_candidate(M, obs, {}, route, worker=0,
                                              carried_product="MILK")
        self.assertTrue(report["certified"])
        self.assertEqual(candidate.sale_slot, 1)
        self.assertEqual(candidate.market[0], ("SELL", "WHEAT", 1))
        self.assertEqual(candidate.market[1], ("SELL", "MILK", 1))

    def test_inactive_market_tail_is_preserved_byte_for_byte(self):
        obs = observation(step=718, farmer=(4, 4), inventories=[{"MILK": 1}], shed={"WHEAT": 1})
        route = [row() for _ in range(720)]
        # Slot 9 is trailing executable slack. Slot 10 is engine-inactive caller data
        # and must neither block the candidate nor move when the sale is inserted.
        route[718]["market"] = ([["SELL", "WHEAT", 1]] + [[] for _ in range(9)]
                                + [["BUY_PRODUCT", "WHEAT", 7]])
        before = deepcopy(route[718]["market"])
        candidate, report = certify_candidate(M, obs, {}, route, worker=0,
                                              carried_product="MILK")
        self.assertTrue(report["certified"])
        self.assertEqual(candidate.sale_slot, 1)
        self.assertEqual(list(candidate.market[10]), before[10])
        self.assertEqual(len(candidate.market), len(before))

    def test_inactive_preterminal_market_tail_is_not_a_false_barrier(self):
        obs = observation(step=716, farmer=(4, 4), inventories=[{"MILK": 1}])
        route = [row() for _ in range(720)]
        route[716]["market"] = [[] for _ in range(10)] + [["BUY_PRODUCT", "WHEAT", 1]]
        candidate, report = certify_candidate(M, obs, {}, route, worker=0,
                                              carried_product="MILK")
        self.assertTrue(report["certified"])

    def test_missing_worker_inventory_fails_closed(self):
        obs = observation(step=718, farmer=(4, 4), hands=((5, 4),), inventories=[{}])
        route = [row(hands=1) for _ in range(720)]
        candidate, report = best_candidate(M, obs, {}, route)
        self.assertIsNone(candidate)
        self.assertEqual(report["reason"], "worker_inventories_not_observed")

    def test_quiet_receipts_use_unitwise_price_movement(self):
        result = quiet_sale_receipts(M, {"inventory": {"WHEAT": 10000}}, {"WHEAT": 2},
                                     [["SELL", "WHEAT", 2]], 10)
        self.assertEqual(result["cash"], 49)
        self.assertEqual(result["filled"]["WHEAT"], 2)


if __name__ == "__main__":
    unittest.main()
