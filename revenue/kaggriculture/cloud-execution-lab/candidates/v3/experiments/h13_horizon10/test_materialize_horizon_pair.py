from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from materialize_horizon_pair import (
    BASELINE_R04,
    CarrierError,
    build_arm_configs,
    config_delta,
    validate_base_config,
)


def valid_config():
    cfg = {
        "r03_full_router": False,
        "r01_shop_router": False,
        "r02_route_bank": False,
        "unrelated_nested": {"keep": [1, 2, 3]},
    }
    cfg.update(copy.deepcopy(BASELINE_R04))
    return cfg


class HorizonPairTests(unittest.TestCase):
    def test_exact_arm_delta_and_input_nonmutation(self):
        base = valid_config()
        before = copy.deepcopy(base)
        h8, h10 = build_arm_configs(base)
        self.assertEqual(base, before)
        self.assertIs(h8["r04_sale_window"], True)
        self.assertEqual(type(h8["r04_sale_horizon"]), int)
        self.assertEqual(h8["r04_sale_horizon"], 8)
        self.assertEqual(h10["r04_sale_horizon"], 10)
        self.assertEqual(
            config_delta(h8, h10),
            {"r04_sale_horizon": {"left": 8, "right": 10}},
        )
        self.assertEqual(h8["unrelated_nested"], base["unrelated_nested"])
        self.assertEqual(h10["unrelated_nested"], base["unrelated_nested"])

    def test_source_to_control_is_only_sale_window(self):
        base = valid_config()
        h8, _h10 = build_arm_configs(base)
        self.assertEqual(
            config_delta(base, h8),
            {"r04_sale_window": {"left": False, "right": True}},
        )

    def test_missing_live_key_fails_closed(self):
        base = valid_config()
        del base["r04_cattle_early"]
        with self.assertRaises(CarrierError):
            validate_base_config(base)

    def test_horizon_bool_int_confusion_fails_closed(self):
        base = valid_config()
        base["r04_sale_horizon"] = True
        with self.assertRaises(CarrierError):
            validate_base_config(base)

    def test_opening_bool_int_confusion_fails_closed(self):
        base = valid_config()
        base["r04_open_roundtrip"] = False
        with self.assertRaises(CarrierError):
            validate_base_config(base)

    def test_all_boolean_impostors_fail_closed(self):
        for key in (
            "r04_sale_window",
            "r04_row_order",
            "r04_evening_flush",
            "r04_sale_fertilizer",
            "r04_cattle_early",
        ):
            with self.subTest(key=key):
                base = valid_config()
                base[key] = int(BASELINE_R04[key])
                with self.assertRaises(CarrierError):
                    validate_base_config(base)

    def test_submission_mode_source_fails_closed(self):
        base = valid_config()
        base["r04_sale_window"] = True
        with self.assertRaises(CarrierError):
            validate_base_config(base)

    def test_any_live_tuple_drift_fails_closed(self):
        cases = {
            "r04_sale_horizon": 9,
            "r04_open_roundtrip": 1,
            "r04_row_order": False,
            "r04_evening_flush": False,
            "r04_sale_fertilizer": False,
            "r04_cattle_early": False,
        }
        for key, value in cases.items():
            with self.subTest(key=key):
                base = valid_config()
                base[key] = value
                with self.assertRaises(CarrierError):
                    validate_base_config(base)

    def test_config_key_set_drift_fails_closed(self):
        left = valid_config()
        right = copy.deepcopy(left)
        right["surprise"] = True
        with self.assertRaises(CarrierError):
            config_delta(left, right)

    def test_nested_config_is_independently_copied(self):
        base = valid_config()
        h8, h10 = build_arm_configs(base)
        h8["unrelated_nested"]["keep"].append(4)
        self.assertEqual(base["unrelated_nested"]["keep"], [1, 2, 3])
        self.assertEqual(h10["unrelated_nested"]["keep"], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
