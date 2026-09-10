#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Adversarial contracts for E13 future-sale solvency closure."""
from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any

_THIS = Path(__file__).resolve()
_HERE = _THIS.parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


materializer = _load("titan_v3_e13_solvency_materializer", _HERE / "materialize.py")
route_scanner = _load("titan_v3_e13_solvency_scanner", _HERE / "scan_routes.py")
_REPO = materializer.find_repo_root(_THIS)
_LAB = _REPO / "revenue/kaggriculture/cloud-execution-lab"
for _path in (
    _LAB,
    _LAB.parent / "cloud-runtime-pulse",
    _LAB.parent / "cloud-quickstep",
):
    _text = str(_path)
    if _text not in sys.path:
        sys.path.insert(0, _text)

import frozen_selected as predecessor  # noqa: E402


class FutureSaleSolvencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temporary = tempfile.TemporaryDirectory()
        temp = Path(cls._temporary.name)
        cls.candidate_path = temp / "frozen_selected_candidate.py"
        cls.receipt_path = temp / "materialization.json"
        cls.record = materializer.materialize(
            _REPO, cls.candidate_path, cls.receipt_path
        )
        cls.candidate = _load(
            "titan_v3_e13_future_sale_solvency_candidate",
            cls.candidate_path,
        )
        # The pinned engine imports resolve_episode_seed for initialization.
        # These tests execute only its exact market interpreter; provide the
        # uncalled import symbol when kaggle-environments is absent.
        try:
            import kaggle_environments.utils  # type: ignore  # noqa: F401
        except ModuleNotFoundError:
            import types

            package = types.ModuleType("kaggle_environments")
            package.__path__ = []
            utils = types.ModuleType("kaggle_environments.utils")
            utils.resolve_episode_seed = lambda _env: 0
            package.utils = utils
            sys.modules["kaggle_environments"] = package
            sys.modules["kaggle_environments.utils"] = utils
        cls.engine = _load(
            "titan_v3_e13_future_sale_solvency_engine",
            _REPO / materializer.ENGINE_REL,
        )

    @classmethod
    def tearDownClass(cls):
        cls._temporary.cleanup()

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
        shed = {
            item: 0 for item in module.m.PRODUCTS + list(module.m.ANIMALS)
        }
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
            fixture["obs"],
            fixture["config"],
            fixture["base"],
            fixture["farm"],
            fixture["private"],
            fixture["route"],
            end,
            fixture["current"],
            targets,
            "MILK",
        )

    def test_floor_price_future_sale_does_not_erase_later_cow_cost(self):
        old = self.fixture(predecessor, wool=1, wool_inventory=10100)
        new = self.fixture(self.candidate, wool=1, wool_inventory=10100)
        for fixture in (old, new):
            fixture["route"][fixture["now"] + 1] = {
                "market": [["SELL", "WOOL", 1]]
            }
            fixture["route"][fixture["now"] + 2] = {
                "market": [["BUY_ANIMAL", "COW", 1]]
            }

        predecessor_minimum, predecessor_certificate = self.minimum(
            predecessor, old, end=old["now"] + 2
        )
        candidate_minimum, candidate_certificate = self.minimum(
            self.candidate, new, end=new["now"] + 2
        )

        self.assertEqual(predecessor_minimum, 0)
        self.assertEqual(predecessor_certificate["funding_turn"], old["now"] + 1)
        self.assertEqual(candidate_minimum, 3)
        self.assertEqual(candidate_certificate["funding_turn"], new["now"] + 1)
        self.assertEqual(candidate_certificate["comparison_end"], new["now"] + 2)
        self.assertEqual(candidate_certificate["post_funding_acquisitions"], 1)
        self.assertEqual(candidate_certificate["reference_acquisitions"], 1)
        self.assertFalse(candidate_certificate["fallback"])

    def test_sufficient_future_receipt_still_releases_all_current_sale(self):
        fixture = self.fixture(
            self.candidate, wool=2, wool_inventory=10000
        )
        fixture["route"][fixture["now"] + 1] = {
            "market": [["SELL", "WOOL", 2]]
        }
        fixture["route"][fixture["now"] + 2] = {
            "market": [["BUY_ANIMAL", "COW", 1]]
        }
        minimum, certificate = self.minimum(
            self.candidate, fixture, end=fixture["now"] + 2
        )
        self.assertEqual(minimum, 0)
        self.assertEqual(certificate["post_funding_acquisitions"], 1)
        self.assertGreaterEqual(
            certificate["scenario_terminal_cash"][0], 0
        )
        self.assertFalse(certificate["fallback"])

    def test_same_turn_order_aware_escrow_scope_is_unchanged(self):
        for market in (
            [["BUY_ANIMAL", "COW", 1], ["SELL", "WOOL", 1]],
            [["SELL", "WOOL", 1], ["BUY_ANIMAL", "COW", 1]],
        ):
            with self.subTest(market=market):
                old = self.fixture(predecessor, wool=1, wool_inventory=10100)
                new = self.fixture(self.candidate, wool=1, wool_inventory=10100)
                old["route"][old["now"] + 1] = {"market": copy.deepcopy(market)}
                new["route"][new["now"] + 1] = {"market": copy.deepcopy(market)}
                old_result = self.minimum(
                    predecessor, old, end=old["now"] + 1
                )
                new_result = self.minimum(
                    self.candidate, new, end=new["now"] + 1
                )
                self.assertEqual(new_result[0], old_result[0])
                self.assertEqual(new_result[0], 0)
                self.assertEqual(
                    new_result[1]["post_funding_acquisitions"], 0
                )
                self.assertEqual(
                    new_result[1]["comparison_end"],
                    old_result[1]["prefix_end"],
                )

    def test_zero_fill_future_sale_keeps_existing_full_horizon_contract(self):
        old = self.fixture(predecessor, wool=0)
        new = self.fixture(self.candidate, wool=0)
        for fixture in (old, new):
            fixture["route"][fixture["now"] + 1] = {
                "market": [["SELL", "WOOL", 1]]
            }
            fixture["route"][fixture["now"] + 2] = {
                "market": [["BUY_ANIMAL", "COW", 1]]
            }
        old_result = self.minimum(predecessor, old, end=old["now"] + 2)
        new_result = self.minimum(
            self.candidate, new, end=new["now"] + 2
        )
        self.assertEqual(old_result[0], 3)
        self.assertEqual(new_result[0], old_result[0])
        self.assertIsNone(new_result[1]["funding_turn"])
        self.assertEqual(new_result[1]["comparison_end"], new["now"] + 2)

    def test_no_later_acquisition_retains_legacy_cutoff(self):
        old = self.fixture(predecessor, wool=1, wool_inventory=10100)
        new = self.fixture(self.candidate, wool=1, wool_inventory=10100)
        for fixture in (old, new):
            fixture["route"][fixture["now"] + 1] = {
                "market": [["SELL", "WOOL", 1]]
            }
        old_result = self.minimum(predecessor, old, end=old["now"] + 2)
        new_result = self.minimum(
            self.candidate, new, end=new["now"] + 2
        )
        self.assertEqual(new_result[0], old_result[0])
        self.assertEqual(new_result[0], 0)
        self.assertEqual(new_result[1]["post_funding_acquisitions"], 0)
        self.assertEqual(new_result[1]["comparison_end"], new["now"])

    def test_partial_multiunit_acquisition_is_preserved(self):
        fixture = self.fixture(
            self.candidate, wool=1, wool_inventory=10100
        )
        fixture["route"][fixture["now"] + 1] = {
            "market": [["SELL", "WOOL", 1]]
        }
        fixture["route"][fixture["now"] + 2] = {
            "market": [["BUY_ANIMAL", "COW", 2]]
        }
        minimum, certificate = self.minimum(
            self.candidate, fixture, end=fixture["now"] + 2
        )
        self.assertGreater(minimum, 3)
        self.assertLessEqual(minimum, 10)
        self.assertEqual(certificate["post_funding_acquisitions"], 2)
        self.assertEqual(certificate["protected_acquisition_rows"], 1)

    def _run_official_market_sequence(
        self, current_milk: int, future_wool: int, wool_inventory: int
    ) -> int:
        engine = self.engine
        config = {
            "boardSize": 10,
            "shedCapacity": 100,
            "maxMarketOrdersPerTurn": 10,
            "farmHandCostMult": 1,
        }
        market = engine._new_market()
        market["inventory"]["WOOL"] = wool_inventory
        engine._refresh_prices(market)
        farms = [engine._new_farm(10, 0), engine._new_farm(10, 0)]
        privates = [engine._new_private(), engine._new_private()]
        privates[0]["shed"]["MILK"] = 10
        privates[0]["shed"]["WOOL"] = future_wool
        state = [
            SimpleNamespace(
                observation=SimpleNamespace(
                    market=market, farms=farms, private=privates[0]
                ),
                action={},
            ),
            SimpleNamespace(
                observation=SimpleNamespace(
                    market=market, farms=farms, private=privates[1]
                ),
                action={},
            ),
        ]
        env = SimpleNamespace(configuration=config)

        def market_stage(first: list[Any], second: list[Any] | None = None):
            state[0].action = {"market": copy.deepcopy(first)}
            state[1].action = {"market": copy.deepcopy(second or [])}
            engine._process_market(state, env)

        market_stage(
            [["SELL", "MILK", current_milk]] if current_milk else []
        )
        market_stage(
            [["SELL", "WOOL", future_wool]] if future_wool else []
        )
        market_stage([["BUY_ANIMAL", "COW", 1]])
        return int(privates[0]["shed"]["COW"])

    def test_pinned_interpreter_confirms_three_unit_boundary(self):
        self.assertEqual(
            materializer.git_blob_sha(
                (_REPO / materializer.ENGINE_REL).read_bytes()
            ),
            materializer.EXPECTED_ENGINE_GIT_BLOB,
        )
        self.assertEqual(
            self._run_official_market_sequence(0, 1, 10100), 0
        )
        self.assertEqual(
            self._run_official_market_sequence(2, 1, 10100), 0
        )
        self.assertEqual(
            self._run_official_market_sequence(3, 1, 10100), 1
        )

    def test_pinned_interpreter_confirms_sufficient_future_sale(self):
        self.assertEqual(
            self._run_official_market_sequence(0, 2, 10000), 1
        )


class MaterializerCustodyTests(unittest.TestCase):
    def test_deterministic_output_and_canonical_nonmutation(self):
        source_path = _REPO / materializer.SOURCE_REL
        engine_path = _REPO / materializer.ENGINE_REL
        source_before = source_path.read_bytes()
        engine_before = engine_path.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            outputs = []
            receipts = []
            for index in range(2):
                output = temporary / f"candidate-{index}.py"
                receipt = temporary / f"receipt-{index}.json"
                materializer.materialize(_REPO, output, receipt)
                outputs.append(output.read_bytes())
                receipts.append(receipt.read_bytes())
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(receipts[0], receipts[1])
            record = json.loads(receipts[0])
            self.assertEqual(record["custody"]["replacement_count"], 1)
            self.assertFalse(record["custody"]["canonical_source_mutated"])
            self.assertFalse(record["claims"]["gameplay_strength"])
        self.assertEqual(source_path.read_bytes(), source_before)
        self.assertEqual(engine_path.read_bytes(), engine_before)

    def _copy_exact_inputs(self, destination: Path):
        for relative in (materializer.SOURCE_REL, materializer.ENGINE_REL):
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_REPO / relative, target)

    def test_source_drift_fails_before_candidate_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            self._copy_exact_inputs(temporary)
            source = temporary / materializer.SOURCE_REL
            source.write_bytes(source.read_bytes() + b"\n")
            output = temporary / "candidate.py"
            receipt = temporary / "receipt.json"
            with self.assertRaisesRegex(
                materializer.MaterializationError, "source Git blob mismatch"
            ):
                materializer.materialize(temporary, output, receipt)
            self.assertFalse(output.exists())
            self.assertFalse(receipt.exists())

    def test_engine_drift_fails_before_candidate_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            self._copy_exact_inputs(temporary)
            engine = temporary / materializer.ENGINE_REL
            engine.write_bytes(engine.read_bytes() + b"\n")
            output = temporary / "candidate.py"
            receipt = temporary / "receipt.json"
            with self.assertRaisesRegex(
                materializer.MaterializationError, "engine Git blob mismatch"
            ):
                materializer.materialize(temporary, output, receipt)
            self.assertFalse(output.exists())
            self.assertFalse(receipt.exists())

    def test_canonical_paths_are_never_valid_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary) / "receipt.json"
            with self.assertRaisesRegex(
                materializer.MaterializationError, "refusing to overwrite"
            ):
                materializer.materialize(
                    _REPO, _REPO / materializer.SOURCE_REL, receipt
                )


class RouteCensusTests(unittest.TestCase):
    @staticmethod
    def action(*rows):
        return {"market": [list(row) for row in rows]}

    def test_strictly_later_acquisition_is_counted(self):
        route = [
            self.action(("SELL", "MILK", 3)),
            self.action(("SELL", "WOOL", 1)),
            self.action(("BUY_ANIMAL", "COW", 1)),
            {},
        ]
        report = route_scanner.scan_routes(
            {"MAIN": route}, ["MILK", "WOOL", "WHEAT", "FERTILIZER"]
        )
        self.assertEqual(report["named_exposure_count"], 1)
        example = report["examples"][0]
        self.assertEqual(example["first_future_requested_sale_turn"], 1)
        self.assertEqual(
            example["strictly_later_fixed_acquisitions"][0]["turn"], 2
        )
        self.assertFalse(report["returned_action_activation_proven"])

    def test_same_turn_acquisition_is_excluded_for_escrow_owner(self):
        route = [
            self.action(("SELL", "MILK", 3)),
            self.action(("SELL", "WOOL", 1), ("BUY_ANIMAL", "COW", 1)),
            {},
        ]
        report = route_scanner.scan_routes(
            {"MAIN": route}, ["MILK", "WOOL"]
        )
        self.assertEqual(report["named_exposure_count"], 0)

    def test_engine_inactive_suffix_sale_does_not_open_window(self):
        route = [
            self.action(("SELL", "MILK", 3)),
            self.action((), ("SELL", "WOOL", 1)),
            self.action(("BUY_ANIMAL", "COW", 1)),
        ]
        report = route_scanner.scan_routes(
            {"MAIN": route}, ["MILK", "WOOL"], max_orders=1
        )
        self.assertEqual(report["named_exposure_count"], 0)

    def test_aliases_report_named_and_unique_counts_separately(self):
        route = [
            self.action(("SELL", "MILK", 3)),
            self.action(("SELL", "WOOL", 1)),
            self.action(("HIRE",)),
        ]
        report = route_scanner.scan_routes(
            {"A": copy.deepcopy(route), "B": copy.deepcopy(route)},
            ["MILK", "WOOL"],
        )
        self.assertEqual(report["named_exposure_count"], 2)
        self.assertEqual(report["unique_route_step_exposure_count"], 1)
        self.assertEqual(report["unique_route_body_count"], 1)


if __name__ == "__main__":
    unittest.main()
