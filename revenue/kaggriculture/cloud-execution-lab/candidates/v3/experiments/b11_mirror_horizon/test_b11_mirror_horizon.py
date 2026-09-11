#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest import mock

HERE = Path(__file__).resolve()
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
for path in (HERE.parent, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import b11_mirror_horizon as b11  # noqa: E402


def farm(*, money=3000.0, x=4, hand_count=1, hires=1):
    return {
        "money": money,
        "tiles": [[None, None], [None, {"kind": "PLANT", "crop": "WHEAT"}]],
        "farmer": [x, 4],
        "hands": [[4, 4] for _ in range(hand_count)],
        "unlocked_quadrants": ["NW"],
        "hires_today": hires,
    }


def obs(step, left=None, right=None, player=0):
    return {
        "step": step,
        "player": player,
        "farms": [left or farm(), right or farm()],
    }


class B11MirrorTests(unittest.TestCase):
    def setUp(self):
        b11.reset_state()
        self.old_horizon = b11.r04.SALE_HORIZON
        b11.r04.SALE_HORIZON = 8

    def tearDown(self):
        b11.r04.SALE_HORIZON = self.old_horizon
        b11.reset_state()

    def test_money_is_deliberately_not_part_of_structural_mirror(self):
        left = farm(money=1000.0)
        right = farm(money=99999.0)
        for step in range(7):
            certified, streak, _ = b11.mirror_certificate(obs(step, left, right))
            self.assertFalse(certified)
            self.assertEqual(streak, step + 1)
        certified, streak, reason = b11.mirror_certificate(obs(7, left, right))
        self.assertTrue(certified)
        self.assertEqual(streak, 8)
        self.assertEqual(reason, "mirror")

    def test_structural_mismatch_fails_closed_and_resets_streak(self):
        for step in range(7):
            b11.mirror_certificate(obs(step))
        rival = farm(x=5)
        certified, streak, reason = b11.mirror_certificate(obs(7, right=rival))
        self.assertFalse(certified)
        self.assertEqual(streak, 0)
        self.assertEqual(reason, "mismatch")
        self.assertEqual(b11.REPORT["mismatch_observations"], 1)

    def test_gap_or_rewind_breaks_continuity_even_when_structure_matches(self):
        for step in range(6):
            b11.mirror_certificate(obs(step))
        certified, streak, _ = b11.mirror_certificate(obs(8))
        self.assertFalse(certified)
        self.assertEqual(streak, 1)
        certified, streak, _ = b11.mirror_certificate(obs(3))
        self.assertFalse(certified)
        self.assertEqual(streak, 1)
        self.assertEqual(b11.REPORT["gap_resets"], 2)

    def test_bool_or_string_player_and_step_fail_closed(self):
        bad = [
            {"step": True, "player": 0, "farms": [farm(), farm()]},
            {"step": "7", "player": 0, "farms": [farm(), farm()]},
            {"step": 7, "player": False, "farms": [farm(), farm()]},
            {"step": 7, "player": "0", "farms": [farm(), farm()]},
        ]
        for observation in bad:
            certified, streak, _ = b11.mirror_certificate(observation)
            self.assertFalse(certified)
            self.assertEqual(streak, 0)
        self.assertEqual(b11.REPORT["malformed_observations"], 4)

    def test_missing_signature_field_fails_closed(self):
        rival = farm()
        rival.pop("hands")
        certified, streak, reason = b11.mirror_certificate(obs(0, right=rival))
        self.assertFalse(certified)
        self.assertEqual(streak, 0)
        self.assertEqual(reason, "malformed-farm")

    def test_json_comparator_is_type_strict(self):
        self.assertFalse(b11._json_equal({"hires_today": True}, {"hires_today": 1}))
        self.assertFalse(b11._json_equal([0], [False]))
        self.assertTrue(b11._json_equal({"x": [1, "1", None]}, {"x": [1, "1", None]}))

    def test_adaptive_agent_uses_h10_only_inside_certified_callbacks(self):
        seen = []

        def parent(observation, configuration=None):
            seen.append(b11.r04.SALE_HORIZON)
            return {"farmer": ["PASS"], "hands": [], "market": []}

        with mock.patch.object(b11.r04, "install", return_value=parent):
            agent = b11.install(enabled=True)
        for step in range(10):
            agent(obs(step))
            self.assertEqual(b11.r04.SALE_HORIZON, 8)
        self.assertEqual(seen[:7], [8] * 7)
        self.assertEqual(seen[7:], [10] * 3)
        self.assertEqual(b11.REPORT["h8_callbacks"], 7)
        self.assertEqual(b11.REPORT["h10_callbacks"], 3)

    def test_h10_callback_does_not_contaminate_shared_module_control(self):
        seen = []

        def parent(observation, configuration=None):
            seen.append(b11.r04.SALE_HORIZON)
            return None

        with mock.patch.object(b11.r04, "install", return_value=parent):
            agent = b11.install(enabled=True)
        for step in range(8):
            agent(obs(step))
        self.assertEqual(seen[-1], 10)
        control_observed_horizon = b11.r04.SALE_HORIZON
        self.assertEqual(control_observed_horizon, 8)

    def test_parent_exception_restores_prior_shared_horizon(self):
        calls = {"n": 0}

        def parent(observation, configuration=None):
            calls["n"] += 1
            if calls["n"] == 8:
                self.assertEqual(b11.r04.SALE_HORIZON, 10)
                raise RuntimeError("parent boom")
            return None

        with mock.patch.object(b11.r04, "install", return_value=parent):
            agent = b11.install(enabled=True)
        for step in range(7):
            agent(obs(step))
        self.assertEqual(b11.r04.SALE_HORIZON, 8)
        with self.assertRaisesRegex(RuntimeError, "parent boom"):
            agent(obs(7))
        self.assertEqual(b11.r04.SALE_HORIZON, 8)

    def test_mismatch_immediately_returns_to_h8(self):
        seen = []

        def parent(observation, configuration=None):
            seen.append(b11.r04.SALE_HORIZON)
            return None

        with mock.patch.object(b11.r04, "install", return_value=parent):
            agent = b11.install(enabled=True)
        for step in range(8):
            agent(obs(step))
        agent(obs(8, right=farm(hand_count=2)))
        self.assertEqual(seen[-2:], [10, 8])
        self.assertEqual(b11.r04.SALE_HORIZON, 8)

    def test_disabled_mode_is_exact_parent_and_never_classifies(self):
        sentinel = object()

        def parent(observation, configuration=None):
            return sentinel

        with mock.patch.object(b11.r04, "install", return_value=parent) as install:
            agent = b11.install(enabled=False)
        self.assertIs(agent(obs(0)), sentinel)
        self.assertEqual(b11.REPORT["callbacks"], 0)
        install.assert_called_once()

    def test_nonliteral_baseline_horizon_rejected(self):
        for bad in (10, True, 8.0, "8"):
            with self.assertRaises(ValueError):
                b11.install(enabled=False, horizon=bad)

    def test_signature_copy_is_not_aliased_to_observation(self):
        original = farm()
        sig = b11._signature(original)
        self.assertIsNotNone(sig)
        original["hands"][0][0] = 99
        self.assertEqual(sig["hands"][0][0], 4)


if __name__ == "__main__":
    unittest.main()
