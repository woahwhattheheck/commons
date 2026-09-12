# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import rng_steering as rs


class RngSteeringTests(unittest.TestCase):
    def test_day2_tail_fill_flips_public_shop_and_preserves_earlier_draws(self):
        cf = rs.tail_fill_counterfactual(5, 2, (25, 25), seat=1)
        self.assertEqual(cf["baseline"]["shop"], "PIZZA_SHOP")
        self.assertEqual(cf["variant"]["shop"], "BRUNCH_SPOT")
        self.assertTrue(cf["prior_seat_weeds_preserved"])
        self.assertTrue(cf["own_remaining_weeds_preserved"])

    def test_seat0_tail_fill_can_shift_later_seat_weed_mapping(self):
        cf = rs.tail_fill_counterfactual(5, 2, (25, 25), seat=0)
        self.assertTrue(cf["own_remaining_weeds_preserved"])
        self.assertEqual(cf["later_seats_changed"], [1])
        self.assertTrue(cf["shop_changed"])

    def test_zero_weed_chance_is_not_rng_entropy_ablation(self):
        cf = rs.tail_fill_counterfactual(5, 2, (25, 25), seat=1, weed_chance=0.0)
        self.assertEqual(cf["baseline"]["weed_hits"], [[False] * 25, [False] * 25])
        self.assertEqual(cf["variant"]["weed_hits"], [[False] * 25, [False] * 24])
        self.assertEqual(cf["baseline"]["shop"], "PIZZA_SHOP")
        self.assertEqual(cf["variant"]["shop"], "BRUNCH_SPOT")

    def test_shop_draw_depends_on_total_empty_draw_count_not_seat_for_same_total(self):
        left = rs.stream_snapshot(5, 2, (24, 25))
        right = rs.stream_snapshot(5, 2, (25, 24))
        self.assertEqual(left["rng_draws_before_shop"], 49)
        self.assertEqual(right["rng_draws_before_shop"], 49)
        self.assertEqual(left["shop"], right["shop"])

    def test_unlock_predicate_matches_day_and_cap(self):
        self.assertTrue(rs.unlocks_shop_after_eod(2, unlocked_instances=0))
        self.assertFalse(rs.unlocks_shop_after_eod(1, unlocked_instances=0))
        self.assertFalse(rs.unlocks_shop_after_eod(2, unlocked_instances=8))

    def test_shop_demand_vector_preserves_single_product_multiplier(self):
        self.assertEqual(rs.shop_demand_vector("YARN_STORE"), {"WOOL": 2})
        self.assertEqual(
            rs.shop_demand_vector("PIZZA_SHOP"),
            {"MILK": 1, "TOMATO": 1, "WHEAT": 1},
        )

    def test_fixed_panel_receipt(self):
        report = rs.panel_report()
        self.assertEqual(report["cells"], 2048)
        self.assertEqual(report["shop_flips"], 1336)
        self.assertEqual(report["shop_unchanged"], 712)
        self.assertEqual(report["per_day"]["2"]["shop_flips"], 164)
        witness = report["first_shop_flip_witness"]
        self.assertEqual((witness["seed"], witness["day"]), (5, 2))
        self.assertEqual(witness["baseline_shop"], "PIZZA_SHOP")
        self.assertEqual(witness["variant_shop"], "BRUNCH_SPOT")

    def test_panel_is_json_deterministic(self):
        left = json.dumps(rs.panel_report(seed_count=16), sort_keys=True)
        right = json.dumps(rs.panel_report(seed_count=16), sort_keys=True)
        self.assertEqual(left, right)

    def test_source_authentication_checks_hash_and_anchors(self):
        text = "\n".join(rs.REQUIRED_ENGINE_ANCHORS) + "\n"
        raw = text.encode("utf-8")
        expected = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "engine.py"
            path.write_bytes(raw)
            result = rs.authenticate_engine(path, expected_sha256=expected)
            self.assertEqual(result["sha256"], expected)
            path.write_text(text + "# tamper\n", encoding="utf-8")
            with self.assertRaises(rs.SourceDrift):
                rs.authenticate_engine(path, expected_sha256=expected)

    def test_source_authentication_rejects_anchor_loss_even_with_matching_hash(self):
        text = "\n".join(rs.REQUIRED_ENGINE_ANCHORS[:-1]) + "\n"
        raw = text.encode("utf-8")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "engine.py"
            path.write_bytes(raw)
            with self.assertRaises(rs.SourceDrift):
                rs.authenticate_engine(path, expected_sha256=hashlib.sha256(raw).hexdigest())

    def test_type_poison_and_bounds_fail_closed(self):
        with self.assertRaises(TypeError):
            rs.stream_snapshot(True, 2, (25, 25))
        with self.assertRaises(TypeError):
            rs.tail_fill_counterfactual(5, 2, (25, 25), seat=True)
        with self.assertRaises(ValueError):
            rs.tail_fill_counterfactual(5, 2, (25, 0), seat=1)
        with self.assertRaises(ValueError):
            rs.stream_snapshot(5, 2, (-1, 25))
        with self.assertRaises(ValueError):
            rs.stream_snapshot(5, 2, (25, 25), weed_chance=1.1)


if __name__ == "__main__":
    unittest.main()
