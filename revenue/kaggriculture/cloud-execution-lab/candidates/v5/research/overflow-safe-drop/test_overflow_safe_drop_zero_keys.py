# SPDX-License-Identifier: Apache-2.0
"""Post-merge predecessor for DROP zero-key state equivalence."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from overflow_safe_drop import transform


def observation(inventory):
    farm = {
        "farmer": [4, 4],
        "hands": [],
        "tiles": [[None for _ in range(10)] for _ in range(10)],
        "money": 10000,
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }
    return {
        "step": 500,
        "player": 0,
        "farms": [farm, deepcopy(farm)],
        "private": {
            "shed": {"MELON": 99},
            "inventories": [deepcopy(inventory)],
            "seeds": {},
        },
        "market": {"inventory": {}, "prices": {}},
    }


class OverflowSafeDropZeroKeyPredecessor(unittest.TestCase):
    def test_positive_stack_plus_zero_key_is_identity(self):
        obs = observation({"MELON": 4, "WOOL": 0})
        selected = {
            "farmer": ["DROP"],
            "hands": [],
            "market": [["SELL", "MELON", 2]],
        }
        before = deepcopy((obs, selected))
        result, report = transform(selected, obs, {})
        self.assertIs(result, selected)
        self.assertEqual(report["reason"], "ambiguous_worker_inventory")
        self.assertEqual((obs, selected), before)

    def test_exact_one_positive_key_remains_eligible(self):
        obs = observation({"MELON": 4})
        selected = {
            "farmer": ["DROP"],
            "hands": [],
            "market": [["SELL", "MELON", 2]],
        }
        result, report = transform(selected, obs, {})
        self.assertTrue(report["changed"])
        self.assertEqual(result["farmer"], ["PLACE", "MELON", 1])
        self.assertEqual(report["preserved_in_pocket_lower_bound"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
