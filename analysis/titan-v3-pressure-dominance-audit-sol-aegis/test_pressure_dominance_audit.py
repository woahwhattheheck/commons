from __future__ import annotations

import copy
import unittest

from pressure_dominance_audit import (
    bounded_demotion_safe,
    certified_partition,
    false_zero_scan,
    finding,
    make_market,
    proxy_zero_partition,
    same_sized_proxy_loss,
)


class PressureDominanceAuditTests(unittest.TestCase):
    def setUp(self):
        self.market = make_market({"TOMATO": 9999, "MILK": 9999})
        self.parent = [["SELL", "TOMATO", 1], ["SELL", "MILK", 1]]

    def test_local_zero_plateau_is_not_a_demotion_certificate(self):
        self.assertEqual(same_sized_proxy_loss(self.parent[0], self.market), 0)
        self.assertEqual(same_sized_proxy_loss(self.parent[1], self.market), 9)
        self.assertFalse(bounded_demotion_safe(self.parent[0], self.market, 100))

    def test_reviewed_proxy_partition_moves_the_unsafe_plateau(self):
        before = copy.deepcopy(self.parent)
        self.assertEqual(proxy_zero_partition(self.parent, self.market), self.parent[::-1])
        self.assertEqual(self.parent, before)

    def test_bounded_certificate_retains_the_parent_order(self):
        self.assertEqual(certified_partition(self.parent, self.market, 100), self.parent)

    def test_pinned_engine_predecessor_killer_is_exact(self):
        result = finding()["witness"]
        self.assertEqual(result["parent_cash"], {"own": 229, "rival": 117})
        self.assertEqual(
            result["proxy_candidate_cash"],
            {"own": 226, "rival": 120},
        )
        self.assertEqual(result["certified_candidate_cash"], result["parent_cash"])
        self.assertEqual(result["proxy_delta"], {"own": -3, "margin": -6})

    def test_false_zero_surface_is_not_a_single_corner(self):
        scan = false_zero_scan()
        self.assertEqual(scan["false_zero_cells"], 1426)
        self.assertEqual(
            scan["by_product"],
            {
                "WHEAT": 410,
                "CARROT": 255,
                "TOMATO": 143,
                "STRAWBERRY": 9,
                "MELON": 72,
                "EGG": 370,
                "MILK": 8,
                "WOOL": 38,
                "FERTILIZER": 121,
            },
        )
        self.assertEqual(
            scan["worst_cell"],
            {
                "item": "WOOL",
                "inventory": 9962,
                "quantity": 2,
                "loss_at_bound": 460,
            },
        )

    def test_barriers_split_and_relative_protected_order_is_stable(self):
        orders = [
            ["SELL", "TOMATO", 1],
            ["SELL", "MILK", 1],
            ["HIRE"],
            ["SELL", "TOMATO", 1],
            ["SELL", "MILK", 1],
        ]
        self.assertEqual(certified_partition(orders, self.market, 100), orders)


if __name__ == "__main__":
    unittest.main(verbosity=2)
