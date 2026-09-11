# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import contract  # noqa: E402


def winning_config(**patch):
    cfg = {
        "r04_sale_window": False,
        "r04_sale_horizon": 8,
        "r04_open_roundtrip": 0,
        "r04_row_order": True,
        "r04_evening_flush": True,
        "r04_sale_fertilizer": True,
        "r04_cattle_early": False,
        "r04_kill_late_water": False,
        "r04_strawberry_endgame": False,
        "r04_strawberry_max_plants": 8,
        "r04_strawberry_topup": True,
        "r04_no_late_sale_advance": True,
        "r04_no_late_sale_advance_step": 648,
        "r04_b5_carrot_fertilizer": True,
        "r04_b5_jit_fertilize": True,
        "r04_row_shed": True,
        "sentinel": {"nested": [1, 2, 3]},
    }
    cfg.update(patch)
    return cfg


class FinalSubmissionTupleContract(unittest.TestCase):
    def test_complete_winning_tuple_transforms_only_score_keys(self):
        before = winning_config()
        snapshot = copy.deepcopy(before)
        after = contract.transform(before)
        self.assertEqual(before, snapshot)
        self.assertIs(after["r04_sale_window"], True)
        self.assertEqual(after["r04_sale_horizon"], 8)
        self.assertIs(after["r04_sale_fertilizer"], True)
        self.assertIs(after["r04_cattle_early"], False)
        for key in contract.PRESERVED_TRUE_KEYS:
            self.assertIs(after[key], True, key)
        for key in contract.PRESERVED_FALSE_KEYS:
            self.assertIs(after[key], False, key)
        self.assertEqual(after["r04_open_roundtrip"], 0)
        self.assertEqual(after["r04_strawberry_max_plants"], 8)
        self.assertEqual(after["r04_no_late_sale_advance_step"], 648)
        self.assertEqual(after["sentinel"], snapshot["sentinel"])
        self.assertIsNot(after["sentinel"], before["sentinel"])
        contract.require_final_output(before, after)

    def test_every_true_winning_lane_is_required_before_transform(self):
        for key in contract.PRESERVED_TRUE_KEYS:
            for bad in (False, None, 1, 1.0, "true", [], {}):
                with self.subTest(key=key, bad=bad):
                    with self.assertRaises(AssertionError):
                        contract.transform(winning_config(**{key: bad}))

    def test_every_false_winning_lane_is_required_before_transform(self):
        for key in contract.PRESERVED_FALSE_KEYS:
            for bad in (True, None, 0, 1, 0.0, "false", [], {}):
                with self.subTest(key=key, bad=bad):
                    with self.assertRaises(AssertionError):
                        contract.transform(winning_config(**{key: bad}))

    def test_cattle_must_already_match_final_off_disposition(self):
        for bad in (True, None, 0, 1, "false"):
            with self.subTest(bad=bad):
                with self.assertRaises(AssertionError):
                    contract.transform(winning_config(r04_cattle_early=bad))

    def test_sale_window_must_still_be_off_before_score_transform(self):
        for bad in (True, None, 0, "false"):
            with self.subTest(bad=bad):
                with self.assertRaises(AssertionError):
                    contract.transform(winning_config(r04_sale_window=bad))

    def test_held_integer_context_is_exact_and_non_bool(self):
        cases = {
            "r04_sale_horizon": (None, True, 8.0, "8", 7, 9),
            "r04_open_roundtrip": (None, True, 0.0, "0", -1, 1),
            "r04_strawberry_max_plants": (None, True, 8.0, "8", 7, 9),
            "r04_no_late_sale_advance_step": (None, True, 648.0, "648", 647, 649),
        }
        for key, bad_values in cases.items():
            for bad in bad_values:
                with self.subTest(key=key, bad=bad):
                    with self.assertRaises(AssertionError):
                        contract.transform(winning_config(**{key: bad}))

    def test_last_transform_cannot_choose_a_different_horizon(self):
        for bad in (True, 0, -1, 5, 9, 8.0, "8"):
            with self.subTest(override=bad):
                with self.assertRaises(AssertionError):
                    contract.transform(winning_config(), bad)
        self.assertEqual(contract.transform(winning_config(), 8)["r04_sale_horizon"], 8)

    def test_missing_new_lane_cannot_be_laundered_by_unknown_key_preservation(self):
        for key in (
            "r04_b5_carrot_fertilizer",
            "r04_b5_jit_fertilize",
            "r04_row_shed",
            "r04_row_order",
            "r04_evening_flush",
            "r04_kill_late_water",
            "r04_strawberry_endgame",
        ):
            with self.subTest(key=key):
                cfg = winning_config()
                del cfg[key]
                with self.assertRaises(AssertionError):
                    contract.transform(cfg)

    def test_non_score_lane_mutation_is_detected(self):
        before = winning_config()
        after = contract.transform(before)
        for key, bad in (
            ("r04_row_shed", False),
            ("r04_row_order", False),
            ("r04_evening_flush", False),
            ("r04_open_roundtrip", 1),
            ("r04_strawberry_max_plants", 9),
        ):
            with self.subTest(key=key):
                poisoned = copy.deepcopy(after)
                poisoned[key] = bad
                with self.assertRaisesRegex(AssertionError, key):
                    contract.require_only_transform_keys_changed(before, poisoned)

    def test_output_tuple_is_explicit_not_just_key_preservation(self):
        before = winning_config()
        after = contract.transform(before)
        poisons = (
            ("r04_sale_window", False),
            ("r04_sale_horizon", 9),
            ("r04_sale_horizon", True),
            ("r04_sale_fertilizer", False),
            ("r04_cattle_early", True),
        )
        for key, bad in poisons:
            with self.subTest(key=key, bad=bad):
                poisoned = copy.deepcopy(after)
                poisoned[key] = bad
                with self.assertRaisesRegex(AssertionError, "final score tuple drift"):
                    contract.require_final_output(before, poisoned)

    def test_key_addition_or_removal_is_detected(self):
        before = winning_config()
        after = contract.transform(before)
        added = copy.deepcopy(after)
        added["surprise"] = True
        with self.assertRaisesRegex(AssertionError, "add or remove"):
            contract.require_final_output(before, added)
        removed = copy.deepcopy(after)
        del removed["sentinel"]
        with self.assertRaisesRegex(AssertionError, "add or remove"):
            contract.require_final_output(before, removed)


if __name__ == "__main__":
    unittest.main()
