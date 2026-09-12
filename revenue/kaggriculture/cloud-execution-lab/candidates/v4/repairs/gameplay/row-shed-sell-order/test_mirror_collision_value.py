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
        self.assertEqual(C.ENGINE_GIT_BLOB, "3c202c7ee921da239356789e266b694635103fc4")

    def test_carrot_lockstep_baseline(self):
        got = C.mirror_collision_score(
            item="CARROT", public_inventory=10_000, fillable=5, price_fn=M.market_price
        )
        self.assertEqual((got["early_cash"], got["aligned_mirror_cash"], got["late_cash"]), (168, 165, 160))
        self.assertEqual(got["promote_gain"], 3)
        self.assertEqual(got["demote_loss"], 5)
        self.assertEqual(got["serial_displacement_span"], 8)
        self.assertFalse(got["serial_displacement_is_assignment_cost"])

    def test_wool_lockstep_baseline(self):
        got = C.mirror_collision_score(
            item="WOOL", public_inventory=10_000, fillable=5, price_fn=M.market_price
        )
        self.assertEqual((got["early_cash"], got["aligned_mirror_cash"], got["late_cash"]), (998, 993, 985))
        self.assertEqual(got["promote_gain"], 5)
        self.assertEqual(got["demote_loss"], 8)
        self.assertEqual(got["serial_displacement_span"], 13)

    def test_carrot_wool_swap_is_zero_not_serial_span_difference(self):
        report = C.analyze_rows(
            [
                {"item": "CARROT", "public_inventory": 10_000, "fillable": 5},
                {"item": "WOOL", "public_inventory": 10_000, "fillable": 5},
            ],
            price_fn=M.market_price,
        )
        assignment = report["mirror_assignment"]
        self.assertTrue(assignment["certified"])
        self.assertEqual(C.mirror_edge_for_permutation(report["scores"], [1, 0]), 0)
        self.assertEqual(assignment["optimal_permutation_indices"], [0, 1])
        self.assertEqual(assignment["predicted_mirror_edge"], 0)

    def test_loss_forensics_melon_wool_lockstep_values(self):
        melon = C.mirror_collision_score(
            item="MELON", public_inventory=10_025, fillable=60, price_fn=M.market_price
        )
        wool = C.mirror_collision_score(
            item="WOOL", public_inventory=10_025, fillable=30, price_fn=M.market_price
        )
        self.assertEqual((melon["early_cash"], melon["aligned_mirror_cash"], melon["late_cash"]), (13040, 10052, 6957))
        self.assertEqual((melon["promote_gain"], melon["demote_loss"]), (2988, 3095))
        self.assertEqual((wool["early_cash"], wool["aligned_mirror_cash"], wool["late_cash"]), (3155, 1660, 84))
        self.assertEqual((wool["promote_gain"], wool["demote_loss"]), (1495, 1576))

    def test_loss_forensics_swap_is_1412_not_3012(self):
        report = C.analyze_rows(
            [
                {"item": "WOOL", "public_inventory": 10_025, "fillable": 30},
                {"item": "MELON", "public_inventory": 10_025, "fillable": 60},
            ],
            price_fn=M.market_price,
        )
        assignment = report["mirror_assignment"]
        self.assertTrue(assignment["certified"])
        self.assertEqual(assignment["optimal_permutation_indices"], [1, 0])
        self.assertEqual(assignment["predicted_mirror_edge"], 1412)
        self.assertEqual(C.mirror_edge_for_permutation(report["scores"], [1, 0]), 1412)

    def test_asymmetric_assignment_matches_bruteforce(self):
        rng = random.Random(13078)
        for n in range(2, 7):
            for _ in range(20):
                rows = [
                    {"promote_gain": rng.randrange(0, 500), "demote_loss": rng.randrange(0, 500)}
                    for _ in range(n)
                ]
                permutation, edge = C.optimal_mirror_assignment(rows)
                brute = max(
                    C.mirror_edge_for_permutation(rows, candidate)
                    for candidate in itertools.permutations(range(n))
                )
                self.assertEqual(edge, max(0, brute))
                self.assertEqual(C.mirror_edge_for_permutation(rows, permutation), edge)

    def test_symmetric_serial_cost_api_is_rejected(self):
        with self.assertRaises(C.MirrorCollisionInputError):
            C.optimal_mirror_assignment([1, 5, 10])
        with self.assertRaises(C.MirrorCollisionInputError):
            C.mirror_edge_for_permutation([1, 5], [1, 0])

    def test_duplicate_product_scores_but_assignment_is_uncertified(self):
        report = C.analyze_rows(
            [
                {"item": "WHEAT", "public_inventory": 10_000, "fillable": 3},
                {"item": "WHEAT", "public_inventory": 10_000, "fillable": 3},
            ],
            price_fn=M.market_price,
        )
        assignment = report["mirror_assignment"]
        self.assertFalse(assignment["certified"])
        self.assertEqual(assignment["reason"], "duplicate_product_rows_require_full_market_simulation")
        self.assertIsNone(assignment["predicted_mirror_edge"])

    def test_assignment_bound_and_index_poison_fail_closed(self):
        rows = [{"promote_gain": 1, "demote_loss": 1}] * 11
        with self.assertRaises(C.MirrorCollisionInputError):
            C.optimal_mirror_assignment(rows)
        valid = [{"promote_gain": 1, "demote_loss": 1}] * 2
        with self.assertRaises(C.MirrorCollisionInputError):
            C.mirror_edge_for_permutation(valid, [True, 0])
        with self.assertRaises(C.MirrorCollisionInputError):
            C.mirror_edge_for_permutation(valid, [0, 0])

    def test_price_floor_aligned_mirror_does_not_advance_supply(self):
        def floor_price(_item, inventory):
            return 2 if inventory < 5 else 1

        got = C.mirror_collision_score(
            item="X", public_inventory=4, fillable=3, price_fn=floor_price
        )
        self.assertEqual(got["early_cash"], 4)
        self.assertEqual(got["aligned_mirror_cash"], 4)
        self.assertEqual(got["late_cash"], 3)
        self.assertEqual(got["after_our_lot_inventory"], 5)
        self.assertEqual(got["after_aligned_mirror_inventory"], 6)
        self.assertEqual(got["promote_gain"], 0)
        self.assertEqual(got["demote_loss"], 1)

    def test_bool_zero_and_horizon_poison_fail_closed(self):
        for inventory, fillable in ((True, 1), (10_000, True), (10_000, 0), (10_000, 100_000)):
            with self.subTest(inventory=inventory, fillable=fillable):
                with self.assertRaises(C.MirrorCollisionInputError):
                    C.mirror_collision_score(
                        item="WHEAT", public_inventory=inventory, fillable=fillable, price_fn=M.market_price
                    )

    def test_unknown_product_and_noninteger_price_fail_closed(self):
        with self.assertRaises(C.MirrorCollisionInputError):
            C.mirror_collision_score(item="NOT_A_PRODUCT", public_inventory=10_000, fillable=1, price_fn=M.market_price)
        with self.assertRaises(C.MirrorCollisionInputError):
            C.mirror_collision_score(item="X", public_inventory=0, fillable=1, price_fn=lambda _i, _n: 1.5)

    def test_row_schema_drift_fails_closed(self):
        with self.assertRaises(C.MirrorCollisionInputError):
            C.analyze_rows(
                [
                    {"item": "WHEAT", "public_inventory": 10_000, "fillable": 3, "extra": 1},
                    {"item": "WOOL", "public_inventory": 10_000, "fillable": 3},
                ],
                price_fn=M.market_price,
            )

    def test_report_marks_serial_span_diagnostic_only(self):
        report = C.analyze_rows(
            [
                {"item": "CARROT", "public_inventory": 10_000, "fillable": 5},
                {"item": "WOOL", "public_inventory": 10_000, "fillable": 5},
            ],
            price_fn=M.market_price,
        )
        self.assertEqual(report["serial_span_rank_indices"], [1, 0])
        self.assertIn("diagnostic only", report["serial_span_rank_semantics"])
        self.assertEqual(report["mirror_assignment"]["serial_span_rank_predicted_edge"], 0)

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
        self.assertNotIn("action", report)
        self.assertNotIn("action", report["mirror_assignment"])

    def test_empty_or_single_row_analysis_fails_closed(self):
        for rows in ([], [{"item": "WHEAT", "public_inventory": 10_000, "fillable": 1}]):
            with self.assertRaises(C.MirrorCollisionInputError):
                C.analyze_rows(rows, price_fn=M.market_price)


if __name__ == "__main__":
    unittest.main()
