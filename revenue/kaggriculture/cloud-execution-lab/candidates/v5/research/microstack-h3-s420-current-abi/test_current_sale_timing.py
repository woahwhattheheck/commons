# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
from pathlib import Path
import types
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "microstack_current_sale_timing", HERE / "current_sale_timing.py"
)
M = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(M)


class CurrentSaleTimingTest(unittest.TestCase):
    def test_cumulative_advance_detects_true_prefix_advance(self):
        self.assertEqual(
            M.cumulative_advance(((420, 2), (423, 8)), ((420, 5), (423, 5))),
            {
                "step": 420,
                "candidate_cumulative": 5,
                "reference_cumulative": 2,
                "delta": 3,
            },
        )
        self.assertIsNone(
            M.cumulative_advance(((420, 5), (423, 5)), ((420, 2), (423, 8)))
        )

    def test_s420_is_identity_before_threshold(self):
        candidate = ((419, 5), (423, 5))
        selected, info = M.suppress_optional_late_advance(
            419, ((419, 2), (423, 8)), candidate, {"accepted": True}
        )
        self.assertIs(selected, candidate)
        self.assertFalse(info["microstack_s420"]["blocked"])

    def test_s420_blocks_optional_advance_to_exact_reference(self):
        reference = ((420, 2), (423, 8))
        candidate = ((420, 5), (423, 5))
        selected, info = M.suppress_optional_late_advance(
            420,
            reference,
            candidate,
            {"accepted": True, "acceptance_score": 17.0, "forced_feasibility": False},
        )
        self.assertEqual(selected, reference)
        self.assertFalse(info["accepted"])
        self.assertEqual(info["acceptance_score"], 0.0)
        self.assertEqual(info["acceptance_rule"], "microstack_s420_block")
        self.assertTrue(info["microstack_s420"]["blocked"])

    def test_s420_preserves_forced_feasibility(self):
        reference = ((500, 2), (503, 8))
        candidate = ((500, 5), (503, 5))
        selected, info = M.suppress_optional_late_advance(
            500,
            reference,
            candidate,
            {"accepted": True, "forced_feasibility": True},
        )
        self.assertIs(selected, candidate)
        self.assertEqual(
            info["microstack_s420"]["reason"], "forced-feasibility-bypass"
        )

    def test_noncomparable_total_fails_open(self):
        candidate = ((500, 6),)
        selected, info = M.suppress_optional_late_advance(
            500, ((500, 2), (503, 8)), candidate, {"accepted": True}
        )
        self.assertIs(selected, candidate)
        self.assertEqual(info["microstack_s420"]["reason"], "no-temporal-advance")

    def test_h3_install_patches_only_current_horizon(self):
        def optimize(*_args, **_kwargs):
            return ((10, 1),), {"accepted": True}

        fake = types.SimpleNamespace(HORIZON=8, optimize_lot=optimize)
        handle = M.install(fake, baseline_horizon=3)
        self.assertEqual(fake.HORIZON, 3)
        self.assertIs(fake.optimize_lot, optimize)
        handle.restore()
        self.assertEqual(fake.HORIZON, 8)
        self.assertIs(fake.optimize_lot, optimize)

    def test_h3_s420_wraps_current_optimizer_and_restores(self):
        calls = []

        def optimize(*_args, **kwargs):
            calls.append(kwargs)
            return ((420, 5), (423, 5)), {
                "accepted": True,
                "acceptance_score": 11.0,
                "forced_feasibility": False,
            }

        fake = types.SimpleNamespace(HORIZON=8, optimize_lot=optimize)
        handle = M.install(fake, baseline_horizon=3, suppress_after_step=420)
        selected, info = fake.optimize_lot(
            now=420, reference=((420, 2), (423, 8))
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(selected, ((420, 2), (423, 8)))
        self.assertFalse(info["accepted"])
        handle.restore()
        self.assertEqual(fake.HORIZON, 8)
        self.assertIs(fake.optimize_lot, optimize)

    def test_install_rejects_bool_or_out_of_range_controls(self):
        fake = types.SimpleNamespace(HORIZON=8, optimize_lot=lambda: None)
        for value in (True, 0, 9):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    M.install(fake, baseline_horizon=value)
        with self.assertRaises(ValueError):
            M.install(fake, suppress_after_step=True)


if __name__ == "__main__":
    unittest.main()
