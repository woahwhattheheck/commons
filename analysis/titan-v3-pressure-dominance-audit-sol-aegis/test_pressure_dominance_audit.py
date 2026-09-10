from __future__ import annotations

import copy
import math
import unittest

from pressure_dominance_audit import (
    bidirectional_flat_invariant,
    false_zero_scan,
    finding,
    make_market,
    proxy_zero_partition,
    raw_bounded_demotion_safe,
    raw_bounded_partition,
    raw_prefix_witness,
    rival_buy_witness,
    same_sized_proxy_loss,
)


class PressureDominanceAuditTests(unittest.TestCase):
    def test_local_zero_plateau_is_not_a_demotion_certificate(self):
        market = make_market({"TOMATO": 9999, "MILK": 9999})
        tomato = ["SELL", "TOMATO", 1]
        milk = ["SELL", "MILK", 1]
        self.assertEqual(same_sized_proxy_loss(tomato, market), 0)
        self.assertEqual(same_sized_proxy_loss(milk, market), 9)
        self.assertFalse(raw_bounded_demotion_safe(tomato, market, 100))

    def test_reviewed_proxy_partition_moves_the_unsafe_plateau(self):
        market = make_market({"TOMATO": 9999, "MILK": 9999})
        parent = [["SELL", "TOMATO", 1], ["SELL", "MILK", 1]]
        before = copy.deepcopy(parent)
        self.assertEqual(proxy_zero_partition(parent, market), parent[::-1])
        self.assertEqual(parent, before)

    def test_first_predecessor_killer_is_exact(self):
        witness = finding()["witness_proxy_zero"]
        self.assertEqual(witness["parent"]["money"], {"own": 229, "rival": 117})
        self.assertEqual(
            witness["proxy_candidate"]["money"],
            {"own": 226, "rival": 120},
        )
        self.assertEqual(witness["proxy_delta"], {"own": -3, "rival": 3, "margin": -6})
        self.assertEqual(witness["raw_bounded_orders"], witness["parent_orders"])
        self.assertEqual(
            witness["raw_bounded_candidate"]["money"],
            witness["parent"]["money"],
        )

    def test_raw_bounded_certificate_ignores_queue_prefix(self):
        witness = raw_prefix_witness()
        self.assertTrue(witness["middle_raw_safe_through_100"])
        self.assertEqual(witness["same_sized_proxy_scores"], [2, 0, 9])
        self.assertEqual(
            witness["raw_bounded_candidate_orders"],
            [
                ["SELL", "WHEAT", 78],
                ["SELL", "MILK", 1],
                ["SELL", "WHEAT", 1],
            ],
        )
        self.assertEqual(witness["parent"]["money"], {"own": 1828, "rival": 2075})
        self.assertEqual(witness["candidate"]["money"], {"own": 1827, "rival": 2076})
        self.assertEqual(witness["delta"], {"own": -1, "rival": 1, "margin": -2})
        self.assertEqual(witness["actual_middle_parent_quote"], 21)
        self.assertEqual(witness["actual_middle_candidate_quote"], 20)

    def test_hidden_rival_buy_defeats_sale_only_certificate(self):
        witness = rival_buy_witness()
        self.assertTrue(witness["egg_raw_safe_through_100"])
        self.assertEqual(witness["same_sized_proxy_scores"], {"EGG": 0, "WHEAT": 1})
        self.assertEqual(
            witness["raw_bounded_candidate_orders"],
            [["SELL", "WHEAT", 1], ["SELL", "EGG", 1]],
        )
        self.assertEqual(witness["quotes"], {
            "egg_public": 41,
            "egg_plus_100": 41,
            "wheat_precommit_sell": 25,
            "wheat_post_buy": 26,
            "wheat_after_sell": 24,
        })
        self.assertEqual(witness["parent"]["money"], {"own": 67, "rival": 974})
        self.assertEqual(witness["candidate"]["money"], {"own": 66, "rival": 974})
        self.assertEqual(witness["delta"], {"own": -1, "rival": 0, "margin": -1})
        self.assertTrue(witness["egg_bidirectional_flat_0_buy_100_sell"])
        self.assertFalse(witness["wheat_bidirectional_flat_1_buy_100_sell"])

    def test_bidirectional_flat_primitive_rejects_nonfinite_quotes(self):
        market = make_market({"EGG": 10139})
        stock = market["inventory"]["EGG"]

        def poisoned_quote(item, inventory, params=None):
            if inventory == stock:
                return market["prices"][item]
            return math.nan

        self.assertFalse(
            raw_bounded_demotion_safe(
                ["SELL", "EGG", 1],
                market,
                1,
                quote=poisoned_quote,
            )
        )
        self.assertFalse(
            bidirectional_flat_invariant(
                ["SELL", "EGG", 1],
                market,
                max_prior_buys=0,
                max_prior_sales=1,
                quote=poisoned_quote,
            )
        )

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

    def test_barriers_split_and_parent_inputs_are_not_mutated(self):
        market = make_market({"WHEAT": 10066, "MILK": 9999})
        orders = [
            ["SELL", "WHEAT", 78],
            ["SELL", "WHEAT", 1],
            ["HIRE"],
            ["SELL", "WHEAT", 1],
            ["SELL", "MILK", 1],
        ]
        before = copy.deepcopy(orders)
        candidate = raw_bounded_partition(orders, market, 100)
        self.assertEqual(candidate[:3], orders[:3])
        self.assertEqual(
            candidate[3:],
            [["SELL", "MILK", 1], ["SELL", "WHEAT", 1]],
        )
        self.assertEqual(orders, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
