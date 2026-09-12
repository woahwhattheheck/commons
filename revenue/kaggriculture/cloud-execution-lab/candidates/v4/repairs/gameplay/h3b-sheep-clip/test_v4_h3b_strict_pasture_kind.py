# SPDX-License-Identifier: Apache-2.0
"""Regression for H3b strict PASTURE/SHEEP snapshot custody."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_full_router as r04  # noqa: E402
import r04_h3b_sheep_clip as lane  # noqa: E402
from checks.test_v4_h3b_sheep_clip import CONFIG, fixture  # noqa: E402


class H3bStrictPastureKind(unittest.TestCase):
    def setUp(self):
        self.saved_states = r04._V233_STATES
        r04._V233_STATES = {}

    def tearDown(self):
        r04._V233_STATES = self.saved_states

    def test_wrong_structure_kind_fails_closed_and_preserves_state(self):
        for kind in ("COOP", "PLANT", None, 1):
            with self.subTest(kind=kind):
                action, observation, state = fixture()
                target = observation["farms"][0]["tiles"][5][6]
                target["kind"] = kind
                before_action = copy.deepcopy(action)
                before_command = list(state["work"][1]["command"])
                r04._V233_STATES[0] = state
                result = lane.apply_h3b_sheep_clip(
                    action, observation, dict(CONFIG), enabled=True)
                self.assertIs(result, action)
                self.assertEqual(action, before_action)
                self.assertEqual(state["work"][1]["command"], before_command)

    def test_canonical_pasture_sheep_positive_remains_live(self):
        action, observation, state = fixture()
        r04._V233_STATES[0] = state
        result = lane.apply_h3b_sheep_clip(
            action, observation, dict(CONFIG), enabled=True)
        self.assertIsNot(result, action)
        self.assertEqual(result["hands"][0], ["EAST"])
        self.assertEqual(state["work"][1]["command"], ["EAST"])


if __name__ == "__main__":
    unittest.main()
