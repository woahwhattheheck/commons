# SPDX-License-Identifier: Apache-2.0
"""Focused custody checks for the H4 + horizon-10 interaction arm."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent


class H4Horizon10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = HERE / "candidate.py"
        spec = importlib.util.spec_from_file_location("titan_h4_h10_candidate", path)
        if spec is None or spec.loader is None:
            raise AssertionError("cannot load H4+h10 candidate")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.candidate = module

    def test_exact_interaction_config(self):
        self.assertEqual(
            self.candidate.CONFIG,
            {
                "r04_sale_horizon": 10,
                "r04_opening_roundtrip": 0,
                "r04_row_order": True,
                "r04_evening_flush": True,
                "r04_sale_fertilizer": True,
                "r04_cattle_early": True,
                "r04_strawberry_topup": True,
            },
        )

    def test_h4_is_armed_and_horizon_is_ten(self):
        h4 = self.candidate.h4
        self.assertTrue(h4.STRAWBERRY_TOPUP)
        self.assertEqual(h4.base.SALE_HORIZON, 10)
        self.assertTrue(callable(self.candidate.agent))


if __name__ == "__main__":
    unittest.main()
