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
        "r04_sale_fertilizer": True,
        "r04_cattle_early": False,
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
        for key in (
            "r04_strawberry_topup",
            "r04_no_late_sale_advance",
            "r04_b5_carrot_fertilizer",
            "r04_b5_jit_fertilize",
            "r04_row_shed",
        ):
            self.assertIs(after[key], True, key)
        self.assertEqual(after["r04_no_late_sale_advance_step"], 648)
        self.assertEqual(after["sentinel"], snapshot["sentinel"])
        self.assertIsNot(after["sentinel"], before["sentinel"])
        contract.require_only_transform_keys_changed(before, after)

    def test_each_winning_lane_is_required_before_transform(self):
        for key in contract.PRESERVED_TRUE_KEYS:
            for bad in (False, None, 1, 1.0, "true", [], {}):
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

    def test_l3_threshold_is_literal_exact_integer_648(self):
        for bad in (None, True, 648.0, "648", 647, 649):
            with self.subTest(bad=bad):
                with self.assertRaises(AssertionError):
                    contract.transform(winning_config(r04_no_late_sale_advance_step=bad))

    def test_base_horizon_and_override_are_positive_non_bool_integers(self):
        for bad in (None, True, 0, -1, 8.0, "8"):
            with self.subTest(base=bad):
                with self.assertRaises(AssertionError):
                    contract.transform(winning_config(r04_sale_horizon=bad))
        for bad in (True, 0, -1, 5.0, "5"):
            with self.subTest(override=bad):
                with self.assertRaises(AssertionError):
                    contract.transform(winning_config(), bad)
        self.assertEqual(contract.transform(winning_config(), 5)["r04_sale_horizon"], 5)

    def test_missing_new_lane_cannot_be_laundered_by_unknown_key_preservation(self):
        for key in ("r04_b5_carrot_fertilizer", "r04_b5_jit_fertilize", "r04_row_shed"):
            with self.subTest(key=key):
                cfg = winning_config()
                del cfg[key]
                with self.assertRaises(AssertionError):
                    contract.transform(cfg)

    def test_non_score_lane_mutation_is_detected(self):
        before = winning_config()
        after = contract.transform(before)
        after["r04_row_shed"] = False
        with self.assertRaisesRegex(AssertionError, "r04_row_shed"):
            contract.require_only_transform_keys_changed(before, after)

    def test_key_addition_or_removal_is_detected(self):
        before = winning_config()
        after = contract.transform(before)
        after["surprise"] = True
        with self.assertRaisesRegex(AssertionError, "add or remove"):
            contract.require_only_transform_keys_changed(before, after)


if __name__ == "__main__":
    unittest.main()
