#!/usr/bin/env python3
from __future__ import annotations

import ast
import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import repair


def repository_root() -> Path:
    for candidate in (HERE, *HERE.parents):
        if (candidate / repair.SOURCE_REL).is_file():
            return candidate
    raise RuntimeError("repository root not found")


REPO = repository_root()
LAB = REPO / "revenue/kaggriculture/cloud-execution-lab"
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))


def load_module(name: str, source: bytes, temp: tempfile.TemporaryDirectory[str]) -> ModuleType:
    path = Path(temp.name) / f"{name}.py"
    path.write_bytes(source)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def route_fixture(length: int = 240):
    return [
        {"farmer": ["PASS"], "hands": [], "market": []}
        for _ in range(length)
    ]


def annual_carrot(module: ModuleType, *, yield_units: int = 3, lifespan: int = 120):
    planted_day = 1
    expected = (
        planted_day + int(module.m.CROPS["CARROT"]["max_yield_day"]) + 1
    ) * 24
    if lifespan == 120:
        assert lifespan == expected
    return {
        "kind": "PLANT",
        "crop": "CARROT",
        "planted_day": planted_day,
        "watered_today": False,
        "consecutive_unwatered": 0,
        "yield_units": yield_units,
        "max_lifespan_step": lifespan,
        "fertilized_until_day": -1,
    }


def ongoing_tomato():
    return {
        "kind": "PLANT",
        "crop": "TOMATO",
        "planted_day": -10,
        "watered_today": False,
        "consecutive_unwatered": 0,
        "yield_units": 2,
        "max_lifespan_step": -1,
        "fertilized_until_day": -1,
    }


def physical_state(module: ModuleType, tile=None, *, milk: int = 2):
    products = [*module.m.PRODUCTS, *module.m.ANIMALS]
    shed = {item: 0 for item in products}
    shed["MILK"] = milk
    tiles = [[None] * 10 for _ in range(10)]
    if tile is not None:
        tiles[4][4] = copy.deepcopy(tile)
    farm = {
        "tiles": tiles,
        "farmer": [4, 4],
        "hands": [],
        "money": 100_000,
        "hires_today": 0,
        "unlocked_quadrants": ["NW"],
    }
    private = {
        "shed": shed,
        "seeds": {crop: 0 for crop in module.m.CROPS},
        "inventories": [{}],
    }
    return farm, private


def consumer(module: ModuleType, route):
    bot = module.FrozenSelected.__new__(module.FrozenSelected)
    bot.controller = SimpleNamespace(R={"test": route}, cur="test")
    bot.mode = "candidate"
    bot.planned = {}
    bot.pending = {}
    bot.previous = None
    bot.observed_harvests = {}
    bot.diagnostics = {}
    bot.observe = lambda _obs: None
    bot.cash_reserve = lambda *_args, **_kwargs: 0
    bot.receipt_profile = lambda *_args, **_kwargs: (lambda _plan: True)
    bot.rival_supply = lambda *_args, **_kwargs: 0
    return bot


def horizon_optimizer(**kwargs):
    now = int(kwargs["now"])
    dates = [int(t) for t in kwargs["dates"]]
    quantity = int(kwargs["quantity"])
    reference = tuple(tuple(row) for row in kwargs["reference"])
    horizon_end = max(dates)
    false_extension = horizon_end > now + 8
    plan = (
        ((now, quantity - 1), (horizon_end, 1))
        if false_extension
        else reference
    )
    gain = 1.0 if false_extension else 0.0
    scenarios = {
        name: {
            "reference_relative_value": 0.0,
            "relative_value": gain,
        }
        for name in ("no_rival", "observed_paired", "observed_later_order")
    }
    report = {
        "item": kwargs["item"],
        "quantity": quantity,
        "plan": list(plan),
        "reference": list(reference),
        "worst_relative_gain": gain,
        "feasible": True,
        "forced_feasibility": False,
        "accepted": false_extension,
        "acceptance_score": gain,
        "scenarios": scenarios,
    }
    return plan, report


class RepresentedHorizonPlantDecayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        built = repair.build(REPO)
        cls.source = built[0]
        cls.engine = built[1]
        cls.mechanics = built[2]
        cls.prefix_source = built[4]
        cls.candidate_source = built[5]
        cls.temp = tempfile.TemporaryDirectory(prefix="titan-represented-decay-")
        cls.prefix = load_module(
            "frozen_selected_prefix_candidate", cls.prefix_source, cls.temp
        )
        cls.candidate = load_module(
            "frozen_selected_prefix_decay_candidate", cls.candidate_source, cls.temp
        )

        current_only = cls.prefix_source.decode("utf-8").replace(
            repair.OLD_CURRENT_STAGE, repair.NEW_CURRENT_STAGE, 1
        )
        future_only = cls.prefix_source.decode("utf-8").replace(
            repair.OLD_FUTURE_STAGE, repair.NEW_FUTURE_STAGE, 1
        )
        cls.current_only = load_module(
            "frozen_selected_current_decay_only",
            current_only.encode("utf-8"),
            cls.temp,
        )
        cls.future_only = load_module(
            "frozen_selected_future_decay_only",
            future_only.encode("utf-8"),
            cls.temp,
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_exact_source_prefix_mechanics_and_engine_are_bound(self):
        record = repair.receipt(REPO)
        self.assertEqual(
            record["source"]["git_blob"], repair.EXPECTED_SOURCE_GIT_BLOB
        )
        self.assertEqual(
            record["prefix_materializer"]["git_blob"],
            repair.EXPECTED_PREFIX_REPAIR_GIT_BLOB,
        )
        self.assertEqual(
            record["mechanics"]["git_blob"], repair.EXPECTED_MECHANICS_GIT_BLOB
        )
        self.assertEqual(
            record["engine"]["git_blob"], repair.EXPECTED_ENGINE_GIT_BLOB
        )
        self.assertEqual(record["engine"]["chronology"], "unit -> market -> town -> decay")
        self.assertTrue(record["composition"]["consumes_prefix_donor"])
        self.assertFalse(record["composition"]["canonical_source_mutated"])

    def test_patch_is_two_insertion_reversible_closure(self):
        restored = self.candidate_source.decode("utf-8")
        for _name, old, new in reversed(repair.REPLACEMENTS):
            self.assertEqual(restored.count(new), 1)
            restored = restored.replace(new, old, 1)
        self.assertEqual(restored, self.prefix_source.decode("utf-8"))
        self.assertEqual(repair.receipt(REPO)["candidate"]["replacement_count"], 2)
        ast.parse(self.candidate_source.decode("utf-8"))
        self.assertNotEqual(self.prefix_source, self.candidate_source)

    def test_candidate_adds_exactly_current_and_future_decay_boundaries(self):
        prefix = self.prefix_source.decode("utf-8")
        candidate = self.candidate_source.decode("utf-8")
        self.assertNotIn("m._decay_plants(f,now)", prefix)
        self.assertNotIn("m._decay_plants(f,t)", prefix)
        self.assertEqual(candidate.count("m._decay_plants(f,now)"), 1)
        self.assertEqual(candidate.count("m._decay_plants(f,t)"), 1)

    def _event(
        self,
        module: ModuleType,
        *,
        tile,
        harvest: int,
        drop: int,
        baseline_end: int,
        hard_end: int,
    ):
        route = route_fixture()
        route[harvest]["farmer"] = ["HARVEST"]
        route[drop]["farmer"] = ["DROP"]
        farm, private = physical_state(module, tile)
        before = copy.deepcopy((farm, private, route))
        result = module.represented_shed_event(
            120,
            baseline_end,
            hard_end,
            route,
            farm,
            private,
            {"turnsPerDay": 24, "maxMarketOrdersPerTurn": 10},
            [],
        )
        self.assertEqual((farm, private, route), before)
        return result

    def test_metadata_valid_expired_crop_cannot_fabricate_harvest_drop_event(self):
        tile = annual_carrot(self.prefix, yield_units=3, lifespan=120)
        self.assertEqual(
            self._event(
                self.prefix,
                tile=tile,
                harvest=129,
                drop=130,
                baseline_end=128,
                hard_end=130,
            ),
            130,
        )
        self.assertIsNone(
            self._event(
                self.candidate,
                tile=tile,
                harvest=129,
                drop=130,
                baseline_end=128,
                hard_end=130,
            )
        )

    def test_current_step_decay_boundary_is_required(self):
        tile = annual_carrot(self.prefix, yield_units=1, lifespan=120)
        self.assertEqual(
            self._event(
                self.future_only,
                tile=tile,
                harvest=121,
                drop=122,
                baseline_end=121,
                hard_end=122,
            ),
            122,
        )
        self.assertIsNone(
            self._event(
                self.candidate,
                tile=tile,
                harvest=121,
                drop=122,
                baseline_end=121,
                hard_end=122,
            )
        )

    def test_future_step_decay_boundary_is_required(self):
        tile = annual_carrot(self.prefix, yield_units=2, lifespan=120)
        self.assertEqual(
            self._event(
                self.current_only,
                tile=tile,
                harvest=123,
                drop=124,
                baseline_end=123,
                hard_end=124,
            ),
            124,
        )
        self.assertIsNone(
            self._event(
                self.candidate,
                tile=tile,
                harvest=123,
                drop=124,
                baseline_end=123,
                hard_end=124,
            )
        )

    def test_preexpiry_harvest_event_is_preserved(self):
        tile = annual_carrot(self.prefix, yield_units=3, lifespan=140)
        expected = self._event(
            self.prefix,
            tile=tile,
            harvest=129,
            drop=130,
            baseline_end=128,
            hard_end=130,
        )
        self.assertEqual(expected, 130)
        self.assertEqual(
            self._event(
                self.candidate,
                tile=tile,
                harvest=129,
                drop=130,
                baseline_end=128,
                hard_end=130,
            ),
            expected,
        )

    def test_ongoing_crop_event_is_preserved(self):
        tile = ongoing_tomato()
        expected = self._event(
            self.prefix,
            tile=tile,
            harvest=129,
            drop=130,
            baseline_end=128,
            hard_end=130,
        )
        self.assertEqual(expected, 130)
        self.assertEqual(
            self._event(
                self.candidate,
                tile=tile,
                harvest=129,
                drop=130,
                baseline_end=128,
                hard_end=130,
            ),
            expected,
        )

    def test_no_plant_control_is_identical(self):
        self.assertEqual(
            self._event(
                self.prefix,
                tile=None,
                harvest=129,
                drop=130,
                baseline_end=128,
                hard_end=130,
            ),
            self._event(
                self.candidate,
                tile=None,
                harvest=129,
                drop=130,
                baseline_end=128,
                hard_end=130,
            ),
        )

    @staticmethod
    def _obs(farm, private, module):
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

    def _transform(self, module: ModuleType):
        route = route_fixture()
        route[129]["farmer"] = ["HARVEST"]
        route[130]["farmer"] = ["DROP"]
        tile = annual_carrot(module, yield_units=3, lifespan=120)
        farm, private = physical_state(module, tile, milk=2)
        base = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "MILK", 2]],
        }
        obs = self._obs(farm, private, module)
        bot = consumer(module, route)
        horizon = {
            "baseline_end": 128,
            "hard_end": 130,
            "service_dates": {},
            "unit_event": None,
            "extended": False,
        }
        before = copy.deepcopy((base, obs, route))
        with (
            patch.object(
                module,
                "post_units",
                return_value=(copy.deepcopy(farm), copy.deepcopy(private)),
            ),
            patch.object(
                module,
                "event_aware_horizon",
                return_value=(128, copy.deepcopy(horizon)),
            ),
            patch.object(
                module,
                "funded_minimum_now",
                return_value=(0, {"witness": "represented-plant-decay"}),
            ),
            patch.object(module, "optimize_lot", side_effect=horizon_optimizer),
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
                },
                copy.deepcopy(base),
            )
        self.assertEqual((base, obs, route), before)
        return out, bot

    def test_returned_action_witness_false_decay_horizon_withholds_sale(self):
        predecessor_out, predecessor = self._transform(self.prefix)
        candidate_out, candidate = self._transform(self.candidate)

        self.assertEqual(predecessor.diagnostics["horizon"]["unit_event"], 130)
        self.assertIsNone(candidate.diagnostics["horizon"]["unit_event"])
        self.assertEqual(predecessor_out["market"][0], ["SELL", "MILK", 1])
        self.assertEqual(candidate_out["market"][0], ["SELL", "MILK", 2])
        self.assertEqual(predecessor.planned["MILK"], [(130, 1)])
        self.assertFalse(candidate.planned.get("MILK"))

    def test_receipt_locks_exact_predecessor_and_returned_action_discriminator(self):
        witness = repair.receipt(REPO)["witness"]
        self.assertEqual(witness["decay_steps"], [120, 122, 124])
        self.assertEqual(witness["predecessor_unit_event"], 130)
        self.assertIsNone(witness["candidate_unit_event"])
        self.assertEqual(
            witness["returned_action_discriminator"], "SELL MILK 1 -> SELL MILK 2"
        )

    def test_apply_patch_rejects_missing_or_duplicate_preimages(self):
        prefix = self.prefix_source.decode("utf-8")
        missing = prefix.replace(repair.OLD_CURRENT_STAGE, "", 1)
        with self.assertRaises(repair.IntegrityError):
            repair.apply_patch(missing)
        duplicate = prefix + "\n" + repair.OLD_FUTURE_STAGE
        with self.assertRaises(repair.IntegrityError):
            repair.apply_patch(duplicate)

    def test_receipt_and_patch_are_deterministic(self):
        first = repair.receipt(REPO)
        second = repair.receipt(REPO)
        self.assertEqual(first, second)
        self.assertEqual(json.loads(json.dumps(first, sort_keys=True)), first)
        self.assertEqual(repair.build(REPO)[-1], repair.build(REPO)[-1])
        self.assertTrue(first["patch_sha256"])
        self.assertEqual(
            first["strength_claim"], "SOURCE_REAL_RETURNED_ACTION_WITNESS_ONLY"
        )


if __name__ == "__main__":
    unittest.main()
