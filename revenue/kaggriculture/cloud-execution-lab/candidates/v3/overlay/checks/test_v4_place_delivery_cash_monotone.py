# SPDX-License-Identifier: Apache-2.0
"""Regression for the one-PLACE-per-worker terminal cash constraint."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_full_router as r04  # noqa: E402
import r04_place_delivery as lane  # noqa: E402


class PlaceDeliveryCashMonotone(unittest.TestCase):
    def test_multi_product_overflow_worker_fails_closed_to_parent_drop(self):
        tiles = [["LOCKED"] * 10 for _ in range(10)]
        farm = {"tiles": tiles, "farmer": [4, 4], "hands": []}
        prices = {product: 10 for product in r04.PRODUCTS}
        prices.update({"CARROT": 30, "WOOL": 20})
        observation = {
            "step": 718,
            "player": 0,
            "farms": [farm],
            "private": {
                "shed": {"WHEAT": 98},
                # Preserve insertion order: official DROP takes CARROT first,
                # then one WOOL into the final free shed slot.
                "inventories": [{"CARROT": 1, "WOOL": 5}],
            },
            "market": {"prices": prices},
        }
        parent = {
            "farmer": ["DROP"],
            "hands": [],
            "market": [
                ["SELL", "WHEAT", 98],
                ["SELL", "CARROT", 1],
                ["SELL", "WOOL", 1],
            ],
        }

        view = r04.FarmView(observation)
        baseline = r04.projected_shed(parent, view)
        self.assertEqual(baseline["CARROT"], 1)
        self.assertEqual(baseline["WOOL"], 1)

        # A single PLACE can name only one product. Choosing CARROT alone would
        # leave one profitable shed slot unused and lose $20 at the terminal
        # market, so the correction must preserve the exact parent DROP.
        out = lane.apply_place_delivery(observation, parent, enabled=True)
        self.assertIs(out, parent)


if __name__ == "__main__":
    unittest.main()
