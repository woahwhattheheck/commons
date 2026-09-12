# SPDX-License-Identifier: Apache-2.0
"""Fail-closed activation contract for the A4 crew-resync gameplay donor."""
from __future__ import annotations

import unittest

import a4_second_melons as a4


def _observation():
    tiles = [[None for _ in range(10)] for _ in range(10)]
    farm = {
        "tiles": tiles,
        "farmer": [4, 4],
        "hands": [],
        "money": 5000,
        "hires_today": 0,
    }
    return {
        "step": 12 * 24 + 1,
        "player": 0,
        "farms": [farm],
        "private": {
            "inventories": [{}],
            "seeds": {"MELON": a4.DEFAULT_COUNT},
        },
    }


def _action():
    return {"farmer": ["PASS"], "hands": [], "market": []}


class ExactEnableTests(unittest.TestCase):
    def setUp(self):
        a4.reset()

    def tearDown(self):
        a4.reset()

    def test_truthy_non_bool_tokens_preserve_identity_and_state(self):
        for token in (1, "true", "false", [True], {"enabled": True}):
            with self.subTest(token=token):
                action = _action()
                out = a4.apply_a4(_observation(), action, enabled=token)
                self.assertIs(out, action)
                self.assertFalse(a4.REPORT["enabled"])
                self.assertFalse(a4._STATES)

    def test_literal_true_still_engages(self):
        action = _action()
        out = a4.apply_a4(_observation(), action, enabled=True)
        self.assertIsNot(out, action)
        self.assertEqual(out["market"], [["HIRE"]])
        self.assertTrue(a4.REPORT["enabled"])
        self.assertTrue(a4._STATES)


if __name__ == "__main__":
    unittest.main()
