# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

from town_consumption_closure import (
    EXPECTED_ENGINE_BLOB_SHA1,
    EXPECTED_SOURCE_BLOB_SHA1,
    apply_public_town_consumption,
    materialize,
    receipt,
    git_blob_sha1,
)

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
SOURCE = LAB / "frozen_selected.py"
ENGINE = LAB / "reference" / "engine" / "kaggriculture.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _pass_action():
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _fixture(module):
    route = [_pass_action() for _ in range(23)]
    route[22]["market"] = [["BUY_PRODUCT", "WHEAT", 1]]
    farm = {
        "money": 31,
        "tiles": [[None for _ in range(10)] for _ in range(10)],
        "farmer": [4, 4],
        "hands": [],
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }
    shed = {item: 0 for item in module.m.PRODUCTS + list(module.m.ANIMALS)}
    shed["MILK"] = 1
    private = {
        "shed": shed,
        "seeds": {crop: 0 for crop in module.m.CROPS},
        "inventories": [{}],
    }
    inventory = {item: 10000 for item in module.m.PRODUCTS}
    obs = {
        "step": 0,
        "player": 0,
        "market": {"inventory": inventory, "prices": {}},
        "town": {"unlocked_shops": ["BAKERY"] * 8},
    }
    config = {
        "shedCapacity": 100,
        "maxMarketOrdersPerTurn": 10,
        "townShopSellInterval": 4,
        "townCenterSellInterval": 24,
    }
    base = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "MILK", 1]]}
    return obs, config, base, farm, private, route


class TownConsumptionClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE.is_file():
            raise unittest.SkipTest("run from repository candidate directory")
        sys.path.insert(0, str(LAB))
        cls.source_text = SOURCE.read_text(encoding="utf-8")
        cls.patched_text = materialize(cls.source_text)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.patched_path = Path(cls.tmp.name) / "frozen_selected_town.py"
        cls.patched_path.write_text(cls.patched_text, encoding="utf-8")
        cls.original = _load("frozen_selected_town_predecessor", SOURCE)
        cls.patched = _load("frozen_selected_town_successor", cls.patched_path)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "tmp"):
            cls.tmp.cleanup()

    def test_exact_source_and_engine_closure(self):
        self.assertEqual(git_blob_sha1(self.source_text), EXPECTED_SOURCE_BLOB_SHA1)
        self.assertEqual(
            git_blob_sha1(ENGINE.read_text(encoding="utf-8")),
            EXPECTED_ENGINE_BLOB_SHA1,
        )
        self.assertEqual(self.patched_text.count("def _funding_apply_town_consumption("), 1)
        self.assertEqual(self.patched_text.count("        _funding_apply_town_consumption(\n"), 1)
        compile(self.patched_text, str(self.patched_path), "exec")

    def test_predecessor_false_minimum_zero_becomes_one(self):
        args = _fixture(self.original)
        obs, config, base, farm, private, route = args
        current = {"MILK": 1}
        targets = {"MILK": 1}
        old_minimum, old_receipt = self.original.funded_minimum_now(
            obs, config, base, farm, private, route, 22,
            current, targets, "MILK", stress_units=32,
        )

        args = _fixture(self.patched)
        obs, config, base, farm, private, route = args
        new_minimum, new_receipt = self.patched.funded_minimum_now(
            obs, config, base, farm, private, route, 22,
            current, targets, "MILK", stress_units=32,
        )
        self.assertFalse(old_receipt["fallback"])
        self.assertFalse(new_receipt["fallback"])
        self.assertEqual(old_minimum, 0)
        self.assertEqual(new_minimum, 1)

    def test_official_public_wheat_quote_is_32_not_projected_31(self):
        inventory = {item: 10000 for item in self.original.m.PRODUCTS}
        config = {"townShopSellInterval": 4, "townCenterSellInterval": 24}
        for step in range(23):
            apply_public_town_consumption(
                inventory,
                ["BAKERY"] * 8,
                config,
                step,
                shop_products=self.original.m.SHOPS,
                products=self.original.m.PRODUCTS,
            )
        self.assertEqual(inventory["WHEAT"], 9951)
        exact_price = self.original.m.market_price("WHEAT", inventory["WHEAT"] - 1, None)
        projected_stress_price = self.original.m.market_price("WHEAT", 10000 - 32 - 1, None)
        self.assertEqual(projected_stress_price, 31)
        self.assertEqual(exact_price, 32)
        self.assertLess(31, exact_price)

    def test_duplicate_and_single_product_shops_are_counted_exactly(self):
        inventory = {item: 100 for item in self.original.m.PRODUCTS}
        apply_public_town_consumption(
            inventory,
            ["BAKERY", "YARN_STORE", "YARN_STORE"],
            {"townShopSellInterval": 4, "townCenterSellInterval": 24},
            4,
            shop_products=self.original.m.SHOPS,
            products=self.original.m.PRODUCTS,
        )
        self.assertEqual(inventory["WHEAT"], 99)
        self.assertEqual(inventory["EGG"], 99)
        self.assertEqual(inventory["WOOL"], 96)
        self.assertEqual(inventory["FERTILIZER"], 100)

    def test_town_center_excludes_fertilizer(self):
        inventory = {item: 100 for item in self.original.m.PRODUCTS}
        apply_public_town_consumption(
            inventory,
            [],
            {"townShopSellInterval": 99, "townCenterSellInterval": 6},
            6,
            shop_products=self.original.m.SHOPS,
            products=self.original.m.PRODUCTS,
        )
        self.assertEqual(inventory["WHEAT"], 99)
        self.assertEqual(inventory["FERTILIZER"], 100)

    def test_no_town_event_preserves_trace_exactly(self):
        obs, config, _base, farm, private, route = _fixture(self.original)
        obs["step"] = 1
        route = route[:4]
        old = self.original._funding_trace(
            obs, config, farm, private, route, 1, 3, [], stress_units=0
        )
        obs, config, _base, farm, private, route = _fixture(self.patched)
        obs["step"] = 1
        route = route[:4]
        new = self.patched._funding_trace(
            obs, config, farm, private, route, 1, 3, [], stress_units=0
        )
        self.assertEqual(old, new)

    def test_unknown_public_shop_fails_closed_to_parent_minimum(self):
        obs, config, base, farm, private, route = _fixture(self.patched)
        obs["town"]["unlocked_shops"] = ["NOT_A_SHOP"]
        minimum, report = self.patched.funded_minimum_now(
            obs, config, base, farm, private, route, 22,
            {"MILK": 1}, {"MILK": 1}, "MILK", stress_units=32,
        )
        self.assertEqual(minimum, 1)
        self.assertTrue(report["fallback"])
        self.assertIn("KeyError", report["error"])

    def test_receipt_is_strict_json_and_default_off(self):
        data = receipt(self.source_text, self.patched_text)
        self.assertTrue(data["complete"])
        self.assertFalse(data["canonical_runtime_modified"])
        self.assertFalse(data["hosted_strength_claim"])
        self.assertFalse(data["release_selection_claim"])
        json.dumps(data, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
