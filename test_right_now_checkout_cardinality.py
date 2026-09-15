from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "right_now_revenue_checkout_cardinality",
    ROOT / "host" / "right_now_revenue.py",
)
assert SPEC and SPEC.loader
control = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(control)

FRESH_NOW = datetime(2026, 9, 14, 1, 40, 0, tzinfo=timezone.utc)


class RightNowCheckoutCardinalityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.readback = json.loads(
            control.CHECKOUT_CURRENT_PATH.read_text(encoding="utf-8")
        )

    def test_exact_single_complete_provider_list_is_accepted(self) -> None:
        result = control.validate_current_checkout_readback(
            self.readback,
            current_moment=FRESH_NOW,
        )
        self.assertEqual(result["observed_at_utc"], "2026-09-14T01:30:22Z")

    def test_second_line_item_cardinality_fails_closed(self) -> None:
        value = copy.deepcopy(self.readback)
        value["line_item_count"] = 2
        with self.assertRaisesRegex(control.ControlError, "count drift"):
            control.validate_current_checkout_readback(value, current_moment=FRESH_NOW)

    def test_paginated_line_item_result_fails_closed(self) -> None:
        value = copy.deepcopy(self.readback)
        value["line_items_has_more"] = True
        with self.assertRaisesRegex(control.ControlError, "pagination"):
            control.validate_current_checkout_readback(value, current_moment=FRESH_NOW)

    def test_boolean_cannot_alias_provider_count(self) -> None:
        value = copy.deepcopy(self.readback)
        value["line_item_count"] = True
        with self.assertRaisesRegex(control.ControlError, "count drift"):
            control.validate_current_checkout_readback(value, current_moment=FRESH_NOW)


if __name__ == "__main__":
    unittest.main()
