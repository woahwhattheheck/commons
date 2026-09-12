# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import itertools
from pathlib import Path
import random
import unittest

import mirror_collision_value as C

HERE = Path(__file__).resolve().parent
MARKET_BASELINE_PATH = HERE.parents[2] / "research" / "market-baseline" / "market_baseline.py"
SPEC = importlib.util.spec_from_file_location("rowshed_market_baseline", MARKET_BASELINE_PATH)
M = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(M)


class MirrorCollisionValueTests(unittest.TestCase):
    def test_price_authority_is_same_official_engine_blob(self):
        self.assertEqual(M.ENGINE_BLOB_SHA, C.ENGINE_GIT_BLOB)
        self.assertEqual(
            C.ENGINE_GIT_BLOB, "3c202c7ee921da239356789e266b694635103fc4"
        )

    def test_carrot_exact_serial_and_aligned_values(self):
        got = C.mirror_collision_score(
            item="CARROT", public_inventory=10_000, fillable=5, price_fn=M.market_price
        )
        self.assertEqual(got["early_cash"], 168)
        self.assertEqual(got["aligned_cash"], 165)
        self.assertEqual(got["late_cash"], 160)
        self.assertEqual(got["exact_mirror_collision_value"], 8)
        self.assertEqual(got["promotion_gain"], 3)
        self.assertEqual(got["demotion_loss"], 5)
        self.assertEqual(got["incumbent_endpoint_score"], 15)

    def test_wool_exact_serial_and_aligned_values(self):
        got = C.mirror_collision_score(
            item="WOOL", public_inventory=10_000, fillable=5, price_fn=M.market_price
        )
        self.assertEqual(got["early_cash"], 998)
        self.assertEqual(got["aligned_cash"], 993)
        self.assertEqual(got["late_cash"], 985)
        self.assertEqual(got["exact_mirror_collision_value"], 13)
        self.assertEqual(got["promotion_gain"], 5)
        self.assertEqual(got["demotion_loss"], 8)
        self.assertEqual(got["incumbent_endpoint_score"], 5)

    def test_carrot_wool_serial_rank_swap_has_zero_aligned_edge(self):
        report = C.analyze_rows(
            [
                {"item": "CARROT", "public_inventory": 10_000, "fillable": 5},
                {"item": "WOOL", "public_inventory": 10_000, "fillable": 5},
            ],
            price_fn=M.market_price,
        )
        self.assertEqual(report["incumbent_rank_indices"], [0, 1])
        self.assertEqual(report["mirror_rank_indices"], [1, 0])
        assignment = report["mirror_assignment"]
        self.assertTrue(assignment["certified"])
        self.assertEqual(assignment["promotion_gains"], [3, 5])
        self.assertEqual(assignment["demotion_losses"], [5, 8])
        self.assertEqual(assignment["optimal_permutation_indices"], [0, 1])
        self.assertEqual(assignment["predicted_mirror_edge"], 0)
        self.assertEqual(assignment["descending_serial_permutation_indices"], [1, 0])
        self.assertEqual(assignment["descending_serial_predicted_edge"], 0)
        self.assertFalse(assignment["descending_serial_is_optimal"])

    def test_loss_forensics_melon_wool_serial_inversion(self):
        report = C.analyze_rows(
            [
                {"item": "MELON", "public_inventory": 10_025, "fillable": 60},
                {"item": "WOOL", "public_inventory": 10_025, "fillable": 30},
            ],
            price_fn=M.market_price,
        )
        melon, wool = report["scores"]
        self.assertEqual(melon["incumbent_endpoint_score"], 3960)
        self.assertEqual(melon["early_cash"], 13040)
        self.assertEqual(melon["aligned_cash"], 10052)
        self.assertEqual(melon["late_cash"], 6957)
        self.assertEqual(melon["exact_mirror_collision_value"], 6083)
        self.assertEqual(melon["promotion_gain"], 2988)
        self.assertEqual(melon["demotion_loss"], 3095)

        self.assertEqual(wool["incumbent_endpoint_score"], 4200)
        self.assertEqual(wool["early_cash"], 3155)
        self.assertEqual(wool["aligned_cash"], 1660)
        self.assertEqual(wool["late_cash"], 84)
        self.assertEqual(wool["exact_mirror_collision_value"], 3071)
        self.assertEqual(wool["promotion_gain"], 1495)
        self.assertEqual(wool["demotion_loss"], 1576)

        self.assertEqual(report["incumbent_rank_indices"], [1, 0])
        self.assertEqual(report["mirror_rank_indices"], [0, 1])

    def test_loss_forensics_incumbent_baseline_has_1412_assignment_edge(self):
        report = C.analyze_rows(
            [
                {"item": "WOOL", "public_inventory": 10_025, "fillable": 30},
                {"item": "MELON", "public_inventory": 10_025, "fillable": 60},
            ],
            price_fn=M.market_price,
        )
        assignment = report["mirror_assignment"]
        self.assertTrue(assignment["certified"])
        self.assertEqual(assignment["promotion_gains"], [1495, 2988])
        self.assertEqual(assignment["demotion_losses"], [1576, 3095])
        self.assertEqual(assignment["serial_collision_values"], [3071, 6083])
        self.assertEqual(assignment["optimal_permutation_indices"], [1, 0])
        self.assertEqual(assignment["predicted_mirror_edge"], 1412)
        self.assertEqual(assignment["descending_serial_permutation_indices"], [1, 0])
        self.assertEqual(assignment["descending_serial_predicted_edge"], 1412)

    def test_serial_collision_decomposes_into_promote_plus_demote(self):
        for item, inventory, quantity in (
            ("CARROT", 10_000, 5),
            ("WOOL", 10_000, 5),
            ("MELON", 10_025, 60),
            ("WOOL", 10_025, 30),
        ):
            with self.subTest(item=item, inventory=inventory, quantity=quantity):
                got = C.mirror_collision_score(
                    item=item,
                    public_inventory=inventory,
                    fillable=quantity,
                    price_fn=M.market_price,
                )
                self.assertEqual(
                    got["promotion_gain"] + got["demotion_loss"],
                    got["exact_mirror_collision_value"],
                )

    def test_exact_asymmetric_assignment_matches_bruteforce(self):
        rng = random.Random(13078)
        for n in range(2, 7):
            for _ in range(25):
                promote = [rng.randrange(0, 500) for _ in range(n)]
                demote = [rng.randrange(0, 500) for _ in range(n)]
                permutation, edge = C.optimal_mirror_assignment(promote, demote)
                brute = max(
                    C.mirror_edge_for_permutation(promote, demote, candidate)
                    for candidate in itertools.permutations(range(n))
                )
                self.assertEqual(edge, max(0, brute))
                self.assertEqual(
                    C.mirror_edge_for_permutation(promote, demote, permutation), edge
                )

    def test_assignment_safety_bound_and_index_poison_fail_closed(self):
        with self.assertRaises(C.MirrorCollisionInputError):
            C.optimal_mirror_assignment([1] * 11, [1] * 11)
        with self.assertRaises(C.MirrorCollisionInputError):
            C.optimal_mirror_assignment([1, 2], [1])
        with self.assertRaises(C.MirrorCollisionInputError):
            C.mirror_edge_for_permutation([1, 2], [1, 2], [True, 0])
        with self.assertRaises(C.MirrorCollisionInputError):
            C.mirror_edge_for_permutation([1, 2], [1, 2], [0, 0])

    def test_duplicate_product_keeps_scores_but_assignment_is_uncertified(self):
        rows = [
            {"item": "WHEAT", "public_inventory": 10_000, "fillable": 3},
            {"item": "WHEAT", "public_inventory": 10_000, "fillable": 3},
        ]
        report = C.analyze_rows(rows, price_fn=M.market_price)
        self.assertEqual(report["incumbent_rank_indices"], [0, 1])
        self.assertEqual(report["mirror_rank_indices"], [0, 1])
        assignment = report["mirror_assignment"]
        self.assertFalse(assignment["certified"])
        self.assertEqual(
            assignment["reason"], "duplicate_product_rows_outside_assignment_theorem"
        )
        self.assertIsNone(assignment["optimal_permutation_indices"])
        self.assertIsNone(assignment["predicted_mirror_edge"])

    def test_price_floor_sales_do_not_advance_inventory(self):
        def floor_price(_item, inventory):
            return 2 if inventory < 5 else 1

        got = C.mirror_collision_score(
            item="X", public_inventory=4, fillable=3, price_fn=floor_price
        )
        self.assertEqual(got["early_cash"], 4)
        self.assertEqual(got["aligned_cash"], 4)
        self.assertEqual(got["late_cash"], 3)
        self.assertEqual(got["after_our_lot_inventory"], 5)
        self.assertEqual(got["after_aligned_inventory"], 6)
        self.assertEqual(got["promotion_gain"], 0)
        self.assertEqual(got["demotion_loss"], 1)
        self.assertEqual(got["exact_mirror_collision_value"], 1)

    def test_bool_and_zero_poison_fail_closed(self):
        for inventory, fillable in ((True, 1), (10_000, True), (10_000, 0)):
            with self.subTest(inventory=inventory, fillable=fillable):
                with self.assertRaises(C.MirrorCollisionInputError):
                    C.mirror_collision_score(
                        item="WHEAT",
                        public_inventory=inventory,
                        fillable=fillable,
                        price_fn=M.market_price,
                    )

    def test_unit_loop_escape_bound_fails_closed(self):
        self.assertEqual(C.MAX_EXECUTABLE_UNITS_PER_MARKET_ORDER, 99_999)
        with self.assertRaises(C.MirrorCollisionInputError):
            C.mirror_collision_score(
                item="WHEAT",
                public_inventory=10_000,
                fillable=100_000,
                price_fn=M.market_price,
            )

    def test_unknown_product_fails_closed(self):
        with self.assertRaises(C.MirrorCollisionInputError):
            C.mirror_collision_score(
                item="NOT_A_PRODUCT",
                public_inventory=10_000,
                fillable=1,
                price_fn=M.market_price,
            )

    def test_non_integer_price_fails_closed(self):
        with self.assertRaises(C.MirrorCollisionInputError):
            C.mirror_collision_score(
                item="X",
                public_inventory=0,
                fillable=1,
                price_fn=lambda _item, _inventory: 1.5,
            )

    def test_row_schema_drift_fails_closed(self):
        with self.assertRaises(C.MirrorCollisionInputError):
            C.analyze_rows(
                [
                    {
                        "item": "WHEAT",
                        "public_inventory": 10_000,
                        "fillable": 3,
                        "extra": 1,
                    },
                    {"item": "WOOL", "public_inventory": 10_000, "fillable": 3},
                ],
                price_fn=M.market_price,
            )

    def test_reports_are_research_only_and_never_mutate_actions(self):
        report = C.analyze_rows(
            [
                {"item": "CARROT", "public_inventory": 10_000, "fillable": 5},
                {"item": "WOOL", "public_inventory": 10_000, "fillable": 5},
            ],
            price_fn=M.market_price,
        )
        self.assertTrue(report["research_only"])
        self.assertFalse(report["decision_authority"])
        self.assertFalse(report["action_mutation_authority"])
        self.assertFalse(report["rival_action_prediction"])
        self.assertEqual(
            report["mirror_rank_semantics"],
            "descending serial early-vs-late evidence only; not aligned queue assignment",
        )
        self.assertEqual(
            report["mirror_assignment"]["schema"],
            "titan.v4.rowshed.mirror-assignment.v2",
        )
        self.assertNotIn("action", report)
        self.assertNotIn("action", report["mirror_assignment"])


if __name__ == "__main__":
    unittest.main()
