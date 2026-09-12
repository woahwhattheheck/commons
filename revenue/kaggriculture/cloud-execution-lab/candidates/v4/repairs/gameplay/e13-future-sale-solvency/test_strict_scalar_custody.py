# SPDX-License-Identifier: Apache-2.0
"""Focused scalar-custody regressions for the E13 generated candidate."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("e13_port", HERE / "port_current_runtime.py")
assert SPEC is not None and SPEC.loader is not None
PORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PORT)


def load_candidate_function(*, materialize_sales=None, funding_trace=None):
    namespace = {
        "materialize_sales": materialize_sales or (
            lambda market, current, shed, targets, max_orders: []
        ),
        "_funding_trace": funding_trace or (
            lambda *args, **kwargs: {"acquisitions": [], "cash": 0}
        ),
        "_funding_prefix_end": lambda scout, now, end: (end, None),
    }
    exec(PORT.REPLACEMENT_FUNCTION, namespace)
    return namespace["funded_minimum_now"]


class StrictScalarCustodyTests(unittest.TestCase):
    def setUp(self):
        self.fn = load_candidate_function()
        self.base = {"market": []}
        self.private = {"shed": {}}
        self.current = {"MELON": 3}
        self.config = {"maxMarketOrdersPerTurn": 10}
        self.obs = {"step": 100}

    def call(self, *, obs=None, config=None, current=None, end=110, stress_units=32, fn=None):
        return (fn or self.fn)(
            self.obs if obs is None else obs,
            self.config if config is None else config,
            self.base,
            {},
            self.private,
            [],
            end,
            self.current if current is None else current,
            {},
            "MELON",
            stress_units=stress_units,
        )

    def test_plain_integers_preserve_positive_control(self):
        minimum, certificate = self.call()
        self.assertEqual(minimum, 0)
        self.assertFalse(certificate["fallback"])
        self.assertEqual(certificate["baseline_now"], 3)
        self.assertEqual(certificate["stress_units"], 32)

    def test_market_limit_one_preserves_positive_control(self):
        minimum, certificate = self.call(config={"maxMarketOrdersPerTurn": 1})
        self.assertEqual(minimum, 0)
        self.assertFalse(certificate["fallback"])

    def test_market_limit_zero_fails_closed_before_helpers(self):
        helper_calls = []

        def forbidden_materialize(*args, **kwargs):
            helper_calls.append("materialize")
            raise AssertionError("cap-zero must fail closed before materialize_sales")

        def forbidden_trace(*args, **kwargs):
            helper_calls.append("trace")
            raise AssertionError("cap-zero must fail closed before _funding_trace")

        fn = load_candidate_function(
            materialize_sales=forbidden_materialize,
            funding_trace=forbidden_trace,
        )
        minimum, certificate = self.call(
            config={"maxMarketOrdersPerTurn": 0},
            fn=fn,
        )
        self.assertEqual(minimum, 3)
        self.assertTrue(certificate["fallback"])
        self.assertEqual(certificate["minimum_now"], 3)
        self.assertEqual(certificate["reason"], "unsupported-market-order-cap")
        self.assertEqual(helper_calls, [])

    def test_step_bool_rejected(self):
        with self.assertRaises(ValueError):
            self.call(obs={"step": True})

    def test_step_string_rejected(self):
        with self.assertRaises(ValueError):
            self.call(obs={"step": "100"})

    def test_step_float_rejected(self):
        with self.assertRaises(ValueError):
            self.call(obs={"step": 100.0})

    def test_baseline_bool_rejected(self):
        with self.assertRaises(ValueError):
            self.call(current={"MELON": True})

    def test_baseline_string_rejected(self):
        with self.assertRaises(ValueError):
            self.call(current={"MELON": "3"})

    def test_baseline_float_rejected(self):
        with self.assertRaises(ValueError):
            self.call(current={"MELON": 3.0})

    def test_market_limit_bool_rejected(self):
        with self.assertRaises(ValueError):
            self.call(config={"maxMarketOrdersPerTurn": True})

    def test_market_limit_string_rejected(self):
        with self.assertRaises(ValueError):
            self.call(config={"maxMarketOrdersPerTurn": "10"})

    def test_market_limit_float_rejected(self):
        with self.assertRaises(ValueError):
            self.call(config={"maxMarketOrdersPerTurn": 10.0})

    def test_stress_units_bool_rejected(self):
        with self.assertRaises(ValueError):
            self.call(stress_units=True)

    def test_stress_units_string_rejected(self):
        with self.assertRaises(ValueError):
            self.call(stress_units="32")

    def test_stress_units_float_rejected(self):
        with self.assertRaises(ValueError):
            self.call(stress_units=32.0)

    def test_end_bool_rejected(self):
        with self.assertRaises(ValueError):
            self.call(end=True)

    def test_end_string_rejected(self):
        with self.assertRaises(ValueError):
            self.call(end="110")

    def test_end_float_rejected(self):
        with self.assertRaises(ValueError):
            self.call(end=110.0)

    def test_end_before_step_rejected(self):
        with self.assertRaises(ValueError):
            self.call(end=99)


if __name__ == "__main__":
    unittest.main()
