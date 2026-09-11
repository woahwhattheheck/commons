# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib
import unittest

import candidate
import b11_mirror_horizon as b11
import r04_full_router as r04


class CurrentA612CompositionTest(unittest.TestCase):
    def setUp(self):
        b11.reset_state()

    def test_exact_current_only_globals_survive_donor_install(self):
        self.assertEqual(r04.SALE_HORIZON, 8)
        self.assertTrue(r04.NO_LATE_SALE_ADVANCE)
        self.assertEqual(r04.NO_LATE_SALE_ADVANCE_STEP, 648)
        self.assertTrue(r04.STRAWBERRY_TOPUP)
        self.assertFalse(r04.KILL_LATE_WATER)
        self.assertFalse(r04.STRAWBERRY_ENDGAME)
        self.assertEqual(r04.STRAWBERRY_MAX_PLANTS, 8)
        self.assertEqual(candidate.B11_CURRENT_STACK, candidate.CURRENT_A612_CONFIG)

    def test_exact_reviewed_classifier_constants(self):
        self.assertEqual(b11.BASE_HORIZON, 8)
        self.assertEqual(b11.MIRROR_HORIZON, 10)
        self.assertEqual(b11.MIRROR_STREAK_REQUIRED, 8)

    def test_malformed_certificate_fails_closed(self):
        self.assertEqual(b11.mirror_certificate(None), (False, 0, "malformed-observation"))
        self.assertEqual(b11.REPORT["malformed_observations"], 1)

    def test_eight_identical_public_structures_certify(self):
        farm = {
            "tiles": [[None, None], [None, None]],
            "farmer": [0, 0],
            "hands": [],
            "unlocked_quadrants": ["NW"],
            "hires_today": 0,
        }
        for step in range(7):
            certified, streak, reason = b11.mirror_certificate(
                {"step": step, "player": 0, "farms": [farm, farm]}
            )
            self.assertFalse(certified)
            self.assertEqual(streak, step + 1)
            self.assertEqual(reason, "warming")
        self.assertEqual(
            b11.mirror_certificate({"step": 7, "player": 0, "farms": [farm, farm]}),
            (True, 8, "mirror"),
        )

    def test_gap_resets_streak(self):
        farm = {
            "tiles": [[None, None], [None, None]],
            "farmer": [0, 0],
            "hands": [],
            "unlocked_quadrants": ["NW"],
            "hires_today": 0,
        }
        self.assertEqual(
            b11.mirror_certificate({"step": 1, "player": 0, "farms": [farm, farm]})[1], 1
        )
        self.assertEqual(
            b11.mirror_certificate({"step": 3, "player": 0, "farms": [farm, farm]})[1], 1
        )
        self.assertEqual(b11.REPORT["gap_resets"], 1)


if __name__ == "__main__":
    unittest.main()
