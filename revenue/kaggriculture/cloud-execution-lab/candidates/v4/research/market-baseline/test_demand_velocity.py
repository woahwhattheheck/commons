#!/usr/bin/env python3
import unittest

import demand_velocity as d


class DemandVelocityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel = d.panel_absorption()

    def test_antigravity_per_shop_ratios_are_source_exact(self):
        self.assertEqual(d.per_shop_instance_velocity(), {
            "WHEAT": 0.625,
            "CARROT": 0.375,
            "TOMATO": 0.25,
            "STRAWBERRY": 0.5,
            "MELON": 0.0,
            "EGG": 0.25,
            "MILK": 0.375,
            "WOOL": 0.25,
            "FERTILIZER": 0.0,
        })

    def test_closed_form_adds_unlock_horizon_and_town_center(self):
        self.assertEqual(d.unlock_days(), (3, 6, 9, 12, 15, 18, 21, 24))
        self.assertEqual(d.closed_form_expected_depletion(), {
            "WHEAT": 525.0,
            "CARROT": 327.0,
            "TOMATO": 228.0,
            "STRAWBERRY": 426.0,
            "MELON": 30.0,
            "EGG": 228.0,
            "MILK": 327.0,
            "WOOL": 228.0,
            "FERTILIZER": 0.0,
        })

    def test_100_seed_means_match_existing_baseline_receipt(self):
        expected = {
            "WHEAT": 536.16,
            "CARROT": 363.18,
            "TOMATO": 231.96,
            "STRAWBERRY": 393.60,
            "MELON": 30.0,
            "EGG": 240.42,
            "MILK": 303.24,
            "WOOL": 217.20,
            "FERTILIZER": 0.0,
        }
        for item, value in expected.items():
            with self.subTest(item=item):
                self.assertAlmostEqual(self.panel[item]["mean"], value, places=8)

    def test_p10_exposes_tail_risk_hidden_by_mean_velocity(self):
        expected_p10 = {
            "WHEAT": 354.0,
            "CARROT": 30.0,
            "TOMATO": 66.0,
            "STRAWBERRY": 174.0,
            "MELON": 30.0,
            "EGG": 84.0,
            "MILK": 100.2,
            "WOOL": 30.0,
            "FERTILIZER": 0.0,
        }
        for item, value in expected_p10.items():
            with self.subTest(item=item):
                self.assertAlmostEqual(self.panel[item]["p10"], value, places=8)

    def test_headroom_is_not_decision_or_timing_authority(self):
        within = d.conservative_headroom("WHEAT", 354)
        over = d.conservative_headroom("WHEAT", 355)
        self.assertEqual(within["disposition"], "PANEL_NPC_HEADROOM_NOT_EXCEEDED")
        self.assertEqual(over["disposition"], "PANEL_NPC_HEADROOM_EXCEEDED")
        for result in (within, over):
            self.assertFalse(result["decision_authority"])
            self.assertFalse(result["timing_authority"])
            self.assertFalse(result["opponent_supply_accounted"])

    def test_fertilizer_has_zero_npc_absorption(self):
        self.assertEqual(d.conservative_headroom("FERTILIZER", 0)["npc_absorption_budget_units"], 0)
        self.assertEqual(
            d.conservative_headroom("FERTILIZER", 1)["disposition"],
            "PANEL_NPC_HEADROOM_EXCEEDED",
        )

    def test_bad_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            d.conservative_headroom("NOPE", 1)
        with self.assertRaises(TypeError):
            d.conservative_headroom("WHEAT", True)
        with self.assertRaises(ValueError):
            d.conservative_headroom("WHEAT", -1)
        with self.assertRaises(ValueError):
            d.conservative_headroom("WHEAT", 1, q=1.1)
        with self.assertRaises(ValueError):
            d.panel_absorption(())


if __name__ == "__main__":
    unittest.main()
