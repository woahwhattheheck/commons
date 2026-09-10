#!/usr/bin/env python3
"""Unmocked horizon-caller proof for represented plant decay."""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import repair
import test_repair as support


def repository_root() -> Path:
    for candidate in (HERE, *HERE.parents):
        if (candidate / repair.SOURCE_REL).is_file():
            return candidate
    raise RuntimeError("repository root not found")


REPO = repository_root()
LAB = REPO / "revenue/kaggriculture/cloud-execution-lab"
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))


def observation(module, farm, private):
    inventory = {product: 10_000 for product in module.m.PRODUCTS}
    prices = {
        product: module.m.market_price(product, inventory[product])
        for product in module.m.PRODUCTS
    }
    return {
        "step": 120,
        "player": 0,
        "farms": [copy.deepcopy(farm), copy.deepcopy(farm)],
        "private": copy.deepcopy(private),
        "market": {"inventory": inventory, "prices": prices},
        "town": {"unlocked_shops": []},
    }


class RealRepresentedDecayCallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        built = repair.build(REPO)
        cls.temp = tempfile.TemporaryDirectory(prefix="titan-real-decay-caller-")
        cls.prefix = support.load_module(
            "frozen_selected_real_caller_prefix", built[4], cls.temp
        )
        cls.candidate = support.load_module(
            "frozen_selected_real_caller_candidate", built[5], cls.temp
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def _transform(self, module):
        route = support.route_fixture(240)
        route[129]["farmer"] = ["HARVEST"]
        route[130]["farmer"] = ["DROP"]
        tile = support.annual_carrot(module, yield_units=3, lifespan=120)
        farm, private = support.physical_state(module, tile, milk=2)
        base = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "MILK", 2]],
        }
        obs = observation(module, farm, private)
        bot = support.consumer(module, route)
        before = copy.deepcopy((base, obs, route))

        # Deliberately do not patch event_aware_horizon,
        # represented_shed_event, product_event_dates, or seller_choice_rank.
        with (
            patch.object(
                module,
                "post_units",
                return_value=(copy.deepcopy(farm), copy.deepcopy(private)),
            ),
            patch.object(
                module,
                "funded_minimum_now",
                return_value=(0, {"witness": "real-horizon-decay-caller"}),
            ),
            patch.object(module, "optimize_lot", side_effect=support.horizon_optimizer),
            patch.object(
                module,
                "fund_same_turn_acquisition",
                side_effect=lambda market, *_args, **_kwargs: (market, None),
            ),
            patch.object(module, "seller_public_observation", return_value={}),
        ):
            out = bot.transform(
                obs,
                {
                    "episodeSteps": 240,
                    "turnsPerDay": 24,
                    "maxMarketOrdersPerTurn": 10,
                    "townShopSellInterval": 4,
                    "townCenterSellInterval": 24,
                },
                copy.deepcopy(base),
            )

        self.assertEqual((base, obs, route), before)
        return out, bot

    def test_real_horizon_has_no_other_extension_source(self):
        route = support.route_fixture(240)
        targets = {"MILK": 2}
        for module in (self.prefix, self.candidate):
            with self.subTest(module=module.__name__):
                end, horizon = module.event_aware_horizon(
                    120,
                    238,
                    route,
                    targets,
                    [],
                    {
                        "turnsPerDay": 24,
                        "maxMarketOrdersPerTurn": 10,
                        "townShopSellInterval": 4,
                        "townCenterSellInterval": 24,
                    },
                )
                self.assertEqual(end, 128)
                self.assertEqual(
                    horizon,
                    {
                        "baseline_end": 128,
                        "hard_end": 143,
                        "service_dates": {},
                        "unit_event": None,
                        "extended": False,
                    },
                )

    def test_unmocked_horizon_and_event_change_returned_action(self):
        predecessor_out, predecessor = self._transform(self.prefix)
        candidate_out, candidate = self._transform(self.candidate)

        self.assertEqual(
            predecessor.diagnostics["horizon"],
            {
                "baseline_end": 128,
                "hard_end": 143,
                "service_dates": {},
                "unit_event": 130,
                "extended": True,
            },
        )
        self.assertEqual(
            candidate.diagnostics["horizon"],
            {
                "baseline_end": 128,
                "hard_end": 143,
                "service_dates": {},
                "unit_event": None,
                "extended": False,
            },
        )
        self.assertEqual(predecessor.diagnostics["evaluations"][0]["horizon_end"], 130)
        self.assertEqual(candidate.diagnostics["evaluations"][0]["horizon_end"], 128)
        self.assertEqual(predecessor_out["market"], [["SELL", "MILK", 1]])
        self.assertEqual(candidate_out["market"], [["SELL", "MILK", 2]])
        self.assertEqual(predecessor.planned["MILK"], [(130, 1)])
        self.assertFalse(candidate.planned.get("MILK"))


if __name__ == "__main__":
    unittest.main()
