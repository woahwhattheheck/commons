# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

import candidate as c


def obs(step=648, player=0, money0=10000, money1=12000):
    return {
        "step": step,
        "player": player,
        "farms": [
            {"money": money0},
            {"money": money1},
        ],
    }


class PublicCashGapTests(unittest.TestCase):
    def test_cash_gap_is_public_and_player_symmetric(self):
        self.assertEqual(c.public_cash_gap(obs(player=0, money0=100, money1=230)), 130)
        self.assertEqual(c.public_cash_gap(obs(player=1, money0=100, money1=230)), 130)

    def test_money_bool_float_and_string_fail_closed(self):
        for malformed in (True, 100.0, "100"):
            with self.subTest(malformed=malformed):
                state = obs(money0=malformed)
                with self.assertRaises(ValueError):
                    c.public_cash_gap(state)
                gate = c.TightCashGate(max_abs_cash_gap=5000)
                self.assertFalse(gate.allow(state))
                self.assertEqual(gate.last_evidence[0]["reason"], "malformed_latch_observation")

    def test_player_bool_float_string_and_out_of_range_fail_closed(self):
        for malformed in (True, 0.0, "0", -1, 2):
            with self.subTest(malformed=malformed):
                state = obs()
                state["player"] = malformed
                gate = c.TightCashGate()
                self.assertFalse(gate.allow(state))
                self.assertEqual(gate.last_evidence, {})

    def test_farm_shape_is_exact_two_player_public_state(self):
        for farms in ([], [{"money": 1}], [{"money": 1}, {"money": 2}, {"money": 3}], [1, 2]):
            with self.subTest(farms=farms):
                state = obs()
                state["farms"] = farms
                gate = c.TightCashGate()
                self.assertFalse(gate.allow(state))
                self.assertEqual(gate.last_evidence[0]["reason"], "malformed_latch_observation")


class TightCashGateTests(unittest.TestCase):
    def test_pre_latch_step_never_arms(self):
        gate = c.TightCashGate(max_abs_cash_gap=5000, latch_step=648)
        self.assertFalse(gate.allow(obs(step=647, money0=10000, money1=10001)))
        self.assertEqual(gate.last_evidence, {})

    def test_tight_cash_gap_latches_true_only_at_exact_step(self):
        gate = c.TightCashGate(max_abs_cash_gap=5000)
        self.assertTrue(gate.allow(obs(step=648, money0=10000, money1=14999)))
        self.assertEqual(gate.last_evidence[0]["cash_gap"], 4999)
        self.assertIs(gate.last_evidence[0]["tight"], True)

    def test_boundary_is_inclusive_and_over_boundary_guards(self):
        gate = c.TightCashGate(max_abs_cash_gap=5000)
        self.assertTrue(gate.allow(obs(step=648, money0=10000, money1=15000)))
        gate = c.TightCashGate(max_abs_cash_gap=5000)
        self.assertFalse(gate.allow(obs(step=648, money0=10000, money1=15001)))
        self.assertIs(gate.last_evidence[0]["tight"], False)

    def test_tight_latch_does_not_oscillate_after_our_market_behavior(self):
        gate = c.TightCashGate(max_abs_cash_gap=5000)
        self.assertTrue(gate.allow(obs(step=648, money0=10000, money1=12000)))
        self.assertTrue(gate.allow(obs(step=649, money0=10000, money1=30000)))
        self.assertEqual(gate.last_evidence[0]["cash_gap"], 2000)

    def test_loose_latch_does_not_turn_on_later(self):
        gate = c.TightCashGate(max_abs_cash_gap=5000)
        self.assertFalse(gate.allow(obs(step=648, money0=10000, money1=20000)))
        self.assertFalse(gate.allow(obs(step=649, money0=10000, money1=10001)))
        self.assertEqual(gate.last_evidence[0]["cash_gap"], 10000)

    def test_rewind_relatches_as_a_new_episode(self):
        gate = c.TightCashGate(max_abs_cash_gap=5000)
        self.assertTrue(gate.allow(obs(step=648, money0=10000, money1=12000)))
        self.assertTrue(gate.allow(obs(step=649, money0=10000, money1=30000)))
        self.assertFalse(gate.allow(obs(step=648, money0=10000, money1=30000)))
        self.assertEqual(gate.last_evidence[0]["cash_gap"], 20000)

    def test_malformed_latch_snapshot_guards_for_rest_of_episode(self):
        gate = c.TightCashGate(max_abs_cash_gap=5000)
        bad = obs(step=648)
        bad["farms"][1]["money"] = True
        self.assertFalse(gate.allow(bad))
        self.assertEqual(gate.last_evidence[0]["reason"], "malformed_latch_observation")
        self.assertFalse(gate.allow(obs(step=649, money0=10000, money1=12000)))
        self.assertFalse(gate.allow(obs(step=700, money0=10000, money1=12000)))
        self.assertEqual(gate.last_evidence[0]["step"], 648)

    def test_skipped_latch_step_guards_for_rest_of_episode(self):
        gate = c.TightCashGate(max_abs_cash_gap=5000)
        self.assertFalse(gate.allow(obs(step=647, money0=10000, money1=10001)))
        self.assertFalse(gate.allow(obs(step=649, money0=10000, money1=10001)))
        self.assertEqual(gate.last_evidence[0]["reason"], "missed_latch_step")
        self.assertFalse(gate.allow(obs(step=700, money0=10000, money1=10001)))

    def test_first_callback_after_latch_step_cannot_classify_late(self):
        gate = c.TightCashGate(max_abs_cash_gap=5000)
        self.assertFalse(gate.allow(obs(step=649, money0=10000, money1=10001)))
        self.assertEqual(gate.last_evidence[0], {
            "step": 649,
            "tight": False,
            "reason": "missed_latch_step",
        })
        self.assertFalse(gate.allow(obs(step=700, money0=10000, money1=10000)))

    def test_malformed_other_seat_does_not_clear_established_latch(self):
        gate = c.TightCashGate(max_abs_cash_gap=5000)
        self.assertTrue(gate.allow(obs(step=648, player=0, money0=10000, money1=12000)))
        bad = obs(step="bad", player=1, money0=10000, money1=12000)
        self.assertFalse(gate.allow(bad))
        self.assertTrue(gate.allow(obs(step=649, player=0, money0=10000, money1=40000)))
        self.assertEqual(gate.last_evidence[0]["cash_gap"], 2000)

    def test_invalid_player_does_not_clear_established_other_seat_latch(self):
        gate = c.TightCashGate(max_abs_cash_gap=5000)
        self.assertTrue(gate.allow(obs(step=648, player=0, money0=10000, money1=12000)))
        bad = obs(step=648, player=2, money0=10000, money1=12000)
        self.assertFalse(gate.allow(bad))
        self.assertTrue(gate.allow(obs(step=649, player=0, money0=10000, money1=40000)))
        self.assertEqual(gate.last_evidence[0]["cash_gap"], 2000)

    def test_parameters_are_type_strict_and_nonnegative(self):
        for malformed in (True, 5000.0, "5000", -1):
            with self.subTest(malformed=malformed):
                with self.assertRaises(ValueError):
                    c.TightCashGate(max_abs_cash_gap=malformed)
        for malformed in (True, 648.0, "648", -1):
            with self.subTest(latch_step=malformed):
                with self.assertRaises(ValueError):
                    c.TightCashGate(latch_step=malformed)


class L3PermissionGateTests(unittest.TestCase):
    def setUp(self):
        c.reset(5000)

    def tearDown(self):
        c._ALLOW_SUPPRESS = False
        c.reset(5000)

    def test_guarded_late_decision_keeps_baseline_e184(self):
        c._ALLOW_SUPPRESS = False
        self.assertFalse(c._conditional_suppressed(648, True, 648))
        self.assertEqual(c.REPORT["late_decisions"], 1)
        self.assertEqual(c.REPORT["guarded"], 1)
        self.assertEqual(c.REPORT["suppressed"], 0)
        self.assertEqual(c.l3.REPORT["suppressed_steps"], 0)

    def test_allowed_late_decision_preserves_l3_telemetry(self):
        c._ALLOW_SUPPRESS = True
        self.assertTrue(c._conditional_suppressed(648, True, 648))
        self.assertEqual(c.REPORT["suppressed"], 1)
        self.assertEqual(c.l3.REPORT, {"suppressed_steps": 1, "last": 648})

    def test_disabled_or_prethreshold_l3_is_unchanged(self):
        c._ALLOW_SUPPRESS = True
        self.assertFalse(c._conditional_suppressed(700, False, 648))
        self.assertFalse(c._conditional_suppressed(647, True, 648))
        self.assertEqual(c.REPORT["late_decisions"], 0)

    def test_malformed_l3_predicate_inputs_fail_closed(self):
        c._ALLOW_SUPPRESS = True
        for step, enabled, threshold in (
            (True, True, 648),
            (648, 1, 648),
            (648, True, 648.0),
            ("648", True, 648),
        ):
            with self.subTest(step=step, enabled=enabled, threshold=threshold):
                self.assertFalse(c._conditional_suppressed(step, enabled, threshold))
        self.assertEqual(c.REPORT["late_decisions"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
