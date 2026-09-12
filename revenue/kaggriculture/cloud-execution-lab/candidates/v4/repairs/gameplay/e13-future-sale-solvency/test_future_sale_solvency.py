#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Current-V4 adversarial contracts for E13 future-sale solvency."""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


port = _load("titan_v4_e13_port", HERE / "port_current_runtime.py")
ROOT = port.find_repo_root(Path(__file__))
LAB = ROOT / "revenue/kaggriculture/cloud-execution-lab"
for extra in (LAB, LAB.parent / "cloud-runtime-pulse", LAB.parent / "cloud-quickstep"):
    text = str(extra)
    if text not in sys.path:
        sys.path.insert(0, text)

import frozen_selected as predecessor  # noqa: E402


class E13CurrentV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        temp = Path(cls.temp.name)
        cls.candidate_path = temp / "frozen_selected_candidate.py"
        cls.receipt_path = temp / "receipt.json"
        cls.record = port.materialize(ROOT, cls.candidate_path, cls.receipt_path)
        cls.candidate = _load("titan_v4_e13_candidate", cls.candidate_path)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def fixture(
        self,
        module,
        *,
        money: int = 0,
        milk: int = 10,
        wool: int = 1,
        wool_inventory: int = 10100,
    ) -> dict[str, Any]:
        config = {
            "shedCapacity": 100,
            "farmHandCostMult": 1,
            "maxMarketOrdersPerTurn": 10,
            "turnsPerDay": 24,
            "episodeSteps": 720,
        }
        now = 5
        inventory = {item: 10000 for item in module.m.PRODUCTS}
        inventory["WOOL"] = wool_inventory
        farm = {
            "money": money,
            "farmer": [4, 4],
            "unlocked_quadrants": ["NW"],
            "hires_today": 0,
            "tiles": [[None for _ in range(10)] for _ in range(10)],
            "hands": [],
        }
        shed = {item: 0 for item in module.m.PRODUCTS + list(module.m.ANIMALS)}
        shed["MILK"] = milk
        shed["WOOL"] = wool
        private = {
            "shed": shed,
            "seeds": {item: 0 for item in module.m.CROPS},
            "inventories": [{}],
        }
        return {
            "config": config,
            "now": now,
            "farm": farm,
            "private": private,
            "obs": {
                "step": now,
                "player": 0,
                "market": {"inventory": inventory, "params": None},
            },
            "route": [{} for _ in range(32)],
            "base": {"market": [["SELL", "MILK", milk]]},
            "current": {"MILK": milk},
        }

    def minimum(self, module, fixture: dict[str, Any], *, end: int):
        targets = {
            item: max(0, int(quantity))
            for item, quantity in fixture["private"]["shed"].items()
            if item in module.PRODUCTS and quantity > 0
        }
        return module.funded_minimum_now(
            fixture["obs"], fixture["config"], fixture["base"], fixture["farm"],
            fixture["private"], fixture["route"], end, fixture["current"],
            targets, "MILK",
        )

    def test_source_and_engine_are_exact_current_bindings(self):
        source = (ROOT / port.SOURCE_REL).read_bytes()
        engine = (ROOT / port.ENGINE_REL).read_bytes()
        self.assertEqual(port.git_blob_sha(source), port.EXPECTED_SOURCE_GIT_BLOB)
        self.assertEqual(port.git_blob_sha(engine), port.EXPECTED_ENGINE_GIT_BLOB)
        self.assertEqual(self.record["candidate"]["function_replaced"], "funded_minimum_now")
        self.assertFalse(self.record["claims"]["production_promotion"])

    def test_killer_floor_sale_does_not_erase_later_cow_cost(self):
        old = self.fixture(predecessor, wool=1, wool_inventory=10100)
        new = self.fixture(self.candidate, wool=1, wool_inventory=10100)
        for fixture in (old, new):
            fixture["route"][fixture["now"] + 1] = {"market": [["SELL", "WOOL", 1]]}
            fixture["route"][fixture["now"] + 2] = {"market": [["BUY_ANIMAL", "COW", 1]]}
        old_min, old_cert = self.minimum(predecessor, old, end=old["now"] + 2)
        new_min, cert = self.minimum(self.candidate, new, end=new["now"] + 2)
        self.assertEqual(old_min, 0)
        self.assertEqual(old_cert["funding_turn"], old["now"] + 1)
        self.assertEqual(new_min, 3)
        self.assertEqual(cert["funding_turn"], new["now"] + 1)
        self.assertEqual(cert["comparison_end"], new["now"] + 2)
        self.assertEqual(cert["post_funding_acquisitions"], 1)
        self.assertFalse(cert["fallback"])

    def test_sufficient_future_receipt_still_releases_current_sale(self):
        fixture = self.fixture(self.candidate, wool=2, wool_inventory=10000)
        fixture["route"][fixture["now"] + 1] = {"market": [["SELL", "WOOL", 2]]}
        fixture["route"][fixture["now"] + 2] = {"market": [["BUY_ANIMAL", "COW", 1]]}
        minimum, cert = self.minimum(self.candidate, fixture, end=fixture["now"] + 2)
        self.assertEqual(minimum, 0)
        self.assertEqual(cert["post_funding_acquisitions"], 1)
        self.assertFalse(cert["fallback"])

    def test_same_turn_escrow_boundary_is_unchanged(self):
        markets = (
            [["BUY_ANIMAL", "COW", 1], ["SELL", "WOOL", 1]],
            [["SELL", "WOOL", 1], ["BUY_ANIMAL", "COW", 1]],
        )
        for market in markets:
            with self.subTest(market=market):
                old = self.fixture(predecessor, wool=1, wool_inventory=10100)
                new = self.fixture(self.candidate, wool=1, wool_inventory=10100)
                old["route"][old["now"] + 1] = {"market": copy.deepcopy(market)}
                new["route"][new["now"] + 1] = {"market": copy.deepcopy(market)}
                old_result = self.minimum(predecessor, old, end=old["now"] + 1)
                new_result = self.minimum(self.candidate, new, end=new["now"] + 1)
                self.assertEqual(new_result[0], old_result[0])
                self.assertEqual(new_result[1]["post_funding_acquisitions"], 0)
                self.assertEqual(new_result[1]["comparison_end"], old_result[1]["prefix_end"])

    def test_zero_fill_future_sale_retains_full_horizon_behavior(self):
        old = self.fixture(predecessor, wool=0)
        new = self.fixture(self.candidate, wool=0)
        for fixture in (old, new):
            fixture["route"][fixture["now"] + 1] = {"market": [["SELL", "WOOL", 1]]}
            fixture["route"][fixture["now"] + 2] = {"market": [["BUY_ANIMAL", "COW", 1]]}
        old_result = self.minimum(predecessor, old, end=old["now"] + 2)
        new_result = self.minimum(self.candidate, new, end=new["now"] + 2)
        self.assertEqual(new_result[0], old_result[0])
        self.assertEqual(new_result[0], 3)
        self.assertIsNone(new_result[1]["funding_turn"])
        self.assertEqual(new_result[1]["comparison_end"], new["now"] + 2)

    def test_no_later_acquisition_retains_legacy_cutoff(self):
        old = self.fixture(predecessor, wool=1, wool_inventory=10100)
        new = self.fixture(self.candidate, wool=1, wool_inventory=10100)
        for fixture in (old, new):
            fixture["route"][fixture["now"] + 1] = {"market": [["SELL", "WOOL", 1]]}
        old_result = self.minimum(predecessor, old, end=old["now"] + 2)
        new_result = self.minimum(self.candidate, new, end=new["now"] + 2)
        self.assertEqual(new_result[0], old_result[0])
        self.assertEqual(new_result[0], 0)
        self.assertEqual(new_result[1]["post_funding_acquisitions"], 0)

    def test_partial_multiunit_acquisition_is_preserved(self):
        fixture = self.fixture(self.candidate, wool=1, wool_inventory=10100)
        fixture["route"][fixture["now"] + 1] = {"market": [["SELL", "WOOL", 1]]}
        fixture["route"][fixture["now"] + 2] = {"market": [["BUY_ANIMAL", "COW", 2]]}
        minimum, cert = self.minimum(self.candidate, fixture, end=fixture["now"] + 2)
        self.assertGreater(minimum, 3)
        self.assertLessEqual(minimum, 10)
        self.assertEqual(cert["post_funding_acquisitions"], 2)
        self.assertEqual(cert["protected_acquisition_rows"], 1)

    def test_materialization_is_deterministic_and_nonmutating(self):
        source_path = ROOT / port.SOURCE_REL
        engine_path = ROOT / port.ENGINE_REL
        source_before = source_path.read_bytes()
        engine_before = engine_path.read_bytes()
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            outputs = []
            receipts = []
            for index in range(2):
                output = td / f"candidate-{index}.py"
                receipt = td / f"receipt-{index}.json"
                port.materialize(ROOT, output, receipt)
                outputs.append(output.read_bytes())
                receipts.append(receipt.read_bytes())
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(receipts[0], receipts[1])
            record = json.loads(receipts[0])
            self.assertEqual(record["custody"]["replacement_count"], 1)
            self.assertFalse(record["custody"]["canonical_source_mutated"])
        self.assertEqual(source_path.read_bytes(), source_before)
        self.assertEqual(engine_path.read_bytes(), engine_before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
