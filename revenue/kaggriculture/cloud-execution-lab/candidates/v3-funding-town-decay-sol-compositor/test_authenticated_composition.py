from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
REPO = HERE.parents[4]
SOURCE = LAB / "frozen_selected.py"
SCHEDULER = LAB / "scheduler.py"
MECHANICS = LAB / "mechanics.py"
ENGINE = LAB / "reference" / "engine" / "kaggriculture.py"
RUNTIME = LAB / "titan_runtime.py"
CONFIG = LAB / "TITAN-CONFIG.json"
TOWN_MATERIALIZER = (
    LAB
    / "candidates/v3-funding-town-consumption-sol-atlas/town_consumption_closure.py"
)
DECAY_MATERIALIZER = (
    LAB / "candidates/v3-funding-plant-decay-sol-chronos/materialize.py"
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(name)
    try:
        sys.modules[name] = module
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
    return module


composer = _load("titan_town_decay_composer", HERE / "compose.py")


def _pass_action():
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _town_fixture(module):
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
    obs = {
        "step": 0,
        "player": 0,
        "market": {
            "inventory": {item: 10000 for item in module.m.PRODUCTS},
            "prices": {},
        },
        "town": {"unlocked_shops": ["BAKERY"] * 8},
    }
    config = {
        "shedCapacity": 100,
        "maxMarketOrdersPerTurn": 10,
        "turnsPerDay": 24,
        "townShopSellInterval": 4,
        "townCenterSellInterval": 24,
    }
    base = {
        "farmer": ["PASS"],
        "hands": [],
        "market": [["SELL", "MILK", 1]],
    }
    return obs, config, base, farm, private, route


def _decay_plant(yield_units: int = 2):
    return {
        "kind": "PLANT",
        "crop": "WHEAT",
        "planted_day": 0,
        "watered_today": False,
        "consecutive_unwatered": 0,
        "yield_units": yield_units,
        "max_lifespan_step": 120,
        "fertilized_until_day": -1,
    }


def _decay_fixture(module):
    tiles = [
        [None if x < 5 and y < 5 else "LOCKED" for x in range(10)]
        for y in range(10)
    ]
    tiles[4][4] = _decay_plant()
    farm = {
        "money": 300,
        "tiles": tiles,
        "farmer": [4, 4],
        "hands": [],
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }
    shed = {name: 0 for name in [*module.m.PRODUCTS, *module.m.ANIMALS]}
    shed["MILK"] = 1
    private = {
        "shed": shed,
        "seeds": {name: 0 for name in module.m.CROPS},
        "inventories": [{}],
    }
    inventory = {name: 10000 for name in module.m.PRODUCTS}
    obs = {
        "step": 120,
        "player": 0,
        "market": {
            "inventory": inventory,
            "prices": {
                name: module.m.market_price(name, 10000)
                for name in module.m.PRODUCTS
            },
        },
        "town": {"unlocked_shops": []},
    }
    route = [_pass_action() for _ in range(124)]
    route[121] = {"farmer": ["HARVEST"], "hands": [], "market": []}
    route[122] = {"farmer": ["DROP"], "hands": [], "market": []}
    route[123] = {
        "farmer": ["PASS"],
        "hands": [],
        "market": [["BUY_ANIMAL", "GOOSE", 1]],
    }
    config = {
        "shedCapacity": 2,
        "maxMarketOrdersPerTurn": 10,
        "turnsPerDay": 24,
        "episodeSteps": 720,
        "townShopSellInterval": 1000,
        "townCenterSellInterval": 1000,
    }
    base = {
        "farmer": ["PASS"],
        "hands": [],
        "market": [["SELL", "MILK", 1]],
    }
    return obs, config, base, farm, private, route


class PureContracts(unittest.TestCase):
    def test_reversed_chronology_is_rejected(self):
        source = """
def _funding_require_static_shop_lifecycle(now, end, config):
    return None

def _funding_apply_town_consumption(inventory, shops, config, step):
    return None

def _funding_trace(obs, config, farm, private, route, now, end, current_market, stress_units=0):
    _funding_require_static_shop_lifecycle(now, end, config)
    for t in range(now, end + 1):
        m._decay_plants(f, t)
        _funding_apply_town_consumption(inventory, shops, config, t)
    return {}
""".lstrip()
        with self.assertRaisesRegex(
            composer.CompositionError,
            "town consumption must be immediately followed by plant decay",
        ):
            composer.inspect_composed_postimage(source)

    def test_decay_not_at_turn_tail_is_rejected(self):
        source = """
def _funding_require_static_shop_lifecycle(now, end, config):
    return None

def _funding_apply_town_consumption(inventory, shops, config, step):
    return None

def _funding_trace(obs, config, farm, private, route, now, end, current_market, stress_units=0):
    _funding_require_static_shop_lifecycle(now, end, config)
    for t in range(now, end + 1):
        _funding_apply_town_consumption(inventory, shops, config, t)
        m._decay_plants(f, t)
        rows.append(t)
    return {}
""".lstrip()
        with self.assertRaisesRegex(composer.CompositionError, "final projected stage"):
            composer.inspect_composed_postimage(source)

    def test_static_selected_consumer_binding(self):
        runtime = """
class Features:
    consumer: str = 'frozen'
class TitanAgent:
    def _initialize(self):
        from frozen_selected import FrozenSelected
        self.consumer = FrozenSelected()
""".lstrip()
        result = composer.verify_selected_consumer(
            runtime, {"consumer": "frozen", "terminal_route": False}
        )
        self.assertEqual(result["runtime_constructor"], "FrozenSelected()")
        with self.assertRaisesRegex(composer.CompositionError, "does not select"):
            composer.verify_selected_consumer(
                runtime, {"consumer": "ordered", "terminal_route": False}
            )

    def test_duplicate_json_keys_fail_closed(self):
        with self.assertRaisesRegex(composer.CompositionError, "duplicate key"):
            composer._strict_json_object(
                b'{"consumer":"frozen","consumer":"ordered"}', "config"
            )

    def test_nonfinite_json_fails_closed(self):
        with self.assertRaisesRegex(composer.CompositionError, "non-finite"):
            composer._strict_json_object(b'{"value":NaN}', "config")


@unittest.skipUnless(
    all(
        path.is_file()
        for path in (
            SOURCE,
            SCHEDULER,
            MECHANICS,
            ENGINE,
            RUNTIME,
            CONFIG,
            TOWN_MATERIALIZER,
            DECAY_MATERIALIZER,
        )
    )
    and (REPO / ".git").exists(),
    "exact repository checkout is required",
)
class ExactRepositoryContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LAB))
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.output = cls.root / "composition"
        cls.before = {
            path: path.read_bytes()
            for path in (
                SOURCE,
                SCHEDULER,
                MECHANICS,
                ENGINE,
                RUNTIME,
                CONFIG,
                TOWN_MATERIALIZER,
                DECAY_MATERIALIZER,
            )
        }
        cls.receipt = composer.compose(
            repo_root=REPO,
            source_path=SOURCE,
            scheduler_path=SCHEDULER,
            mechanics_path=MECHANICS,
            engine_path=ENGINE,
            runtime_path=RUNTIME,
            config_path=CONFIG,
            town_materializer_path=TOWN_MATERIALIZER,
            decay_materializer_path=DECAY_MATERIALIZER,
            output_dir=cls.output,
        )
        cls.town = _load("town_donor_exact_test", TOWN_MATERIALIZER)
        cls.decay = _load("decay_donor_exact_test", DECAY_MATERIALIZER)
        cls.canonical = _load("town_decay_canonical_test", SOURCE)
        cls.candidate = _load(
            "town_decay_composed_candidate_test",
            cls.output / composer.OUTPUT_FINAL_SOURCE,
        )
        cls.source_text = SOURCE.read_text(encoding="utf-8")
        cls.engine_text = ENGINE.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        if sys.path and sys.path[0] == str(LAB):
            sys.path.pop(0)
        cls.temp.cleanup()

    def _town_minimum(self, module):
        obs, config, base, farm, private, route = _town_fixture(module)
        return module.funded_minimum_now(
            obs,
            config,
            base,
            farm,
            private,
            route,
            22,
            {"MILK": 1},
            {"MILK": 1},
            "MILK",
            stress_units=32,
        )

    def _decay_minimum(self, module):
        obs, config, base, farm, private, route = _decay_fixture(module)
        return module.funded_minimum_now(
            obs,
            config,
            base,
            farm,
            private,
            route,
            123,
            {"MILK": 1},
            {"MILK": 1},
            "MILK",
            stress_units=32,
        )

    def test_git_custody_binds_both_exact_donor_heads(self):
        custody = self.receipt["git_custody"]
        self.assertTrue(custody["ancestors"]["base_main"])
        self.assertTrue(custody["ancestors"]["town_head"])
        self.assertTrue(custody["ancestors"]["decay_head"])
        self.assertEqual(
            custody["donor_head_blobs"]["town"],
            composer.TOWN_MATERIALIZER_GIT_BLOB,
        )
        self.assertEqual(
            custody["donor_head_blobs"]["decay"],
            composer.DECAY_MATERIALIZER_GIT_BLOB,
        )

    def test_unmodified_donor_materializers_reject_each_others_postimages(self):
        town_postimage = self.town.materialize(self.source_text)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            town_path = root / "town.py"
            town_path.write_text(town_postimage, encoding="utf-8")
            with self.assertRaisesRegex(
                self.decay.MaterializationError, "source Git blob mismatch"
            ):
                self.decay.materialize(
                    town_path,
                    SCHEDULER,
                    MECHANICS,
                    ENGINE,
                    root / "out.py",
                    root / "receipt.json",
                )
        decay_postimage, _ = self.decay.patch_source(self.source_text)
        with self.assertRaisesRegex(ValueError, "source drift"):
            self.town.materialize(decay_postimage)

    def test_combined_carrier_closes_the_rejection_boundary(self):
        final = (self.output / composer.OUTPUT_FINAL_SOURCE).read_text(encoding="utf-8")
        details = composer.inspect_composed_postimage(final)
        self.assertTrue(details["town_immediately_before_decay"])
        self.assertTrue(details["decay_is_final_stage"])
        self.assertLess(details["town_line"], details["decay_line"])
        self.assertEqual(
            self.receipt["composition"]["town_receipt_postimage_sha256"],
            self.receipt["composition"]["decay_authenticated_input_sha256"],
        )

    def test_final_postimage_retains_town_funding_killer(self):
        old_minimum, old_report = self._town_minimum(self.canonical)
        new_minimum, new_report = self._town_minimum(self.candidate)
        self.assertEqual(old_minimum, 0)
        self.assertFalse(old_report["fallback"])
        self.assertEqual(new_minimum, 1)
        self.assertFalse(new_report["fallback"])

    def test_final_postimage_retains_decay_capacity_killer(self):
        old_minimum, old_report = self._decay_minimum(self.canonical)
        new_minimum, new_report = self._decay_minimum(self.candidate)
        self.assertEqual(old_minimum, 0)
        self.assertEqual(old_report["reference_acquisitions"], 0)
        self.assertEqual(new_minimum, 1)
        self.assertEqual(new_report["reference_acquisitions"], 1)
        self.assertFalse(new_report["fallback"])

    def test_selected_runtime_reaches_the_final_postimage(self):
        dynamic = self.receipt["selected_consumer"]["dynamic"]
        self.assertEqual(dynamic["consumer_class"], "FrozenSelected")
        self.assertEqual(dynamic["consumer_module"], "frozen_selected")
        self.assertEqual(dynamic["funding_trace_module"], "frozen_selected")
        self.assertTrue(dynamic["selected_postimage"])
        static = self.receipt["selected_consumer"]["static"]
        self.assertEqual(static["config_consumer"], "frozen")
        self.assertFalse(static["config_terminal_route"])

    def test_tampered_intermediate_receipt_is_rejected(self):
        town_postimage = self.town.materialize(self.source_text)
        receipt = self.town.receipt(
            self.source_text, town_postimage, self.engine_text
        )
        receipt["patched_source_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            composer.CompositionError, "postimage SHA-256 mismatch"
        ):
            composer.consume_authenticated_town_postimage(
                town_postimage=town_postimage,
                town_receipt=receipt,
                pristine_source=self.before[SOURCE],
                scheduler_text=SCHEDULER.read_text(encoding="utf-8"),
                mechanics_text=MECHANICS.read_text(encoding="utf-8"),
                engine_text=self.engine_text,
                engine_source=self.before[ENGINE],
                decay_module=self.decay,
            )

    def test_reversed_real_donor_order_is_rejected(self):
        decay_first, _ = self.decay.patch_source(self.source_text)
        wrong = self.town.materialize(decay_first, require_expected_source=False)
        with self.assertRaises(composer.CompositionError):
            composer.inspect_composed_postimage(wrong)

    def test_receipt_is_strict_and_deterministic(self):
        parsed = json.loads(
            (self.output / composer.OUTPUT_RECEIPT).read_text(encoding="utf-8")
        )
        self.assertEqual(parsed, self.receipt)
        self.assertEqual(parsed["schema"], composer.SCHEMA)
        self.assertEqual(parsed["status"], "PASS")
        body = dict(parsed)
        seal = body.pop("body_sha256")
        expected = composer.sha256_bytes(
            json.dumps(
                body, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
        )
        self.assertEqual(seal, expected)

        second = self.root / "composition-second"
        composer.compose(
            repo_root=REPO,
            source_path=SOURCE,
            scheduler_path=SCHEDULER,
            mechanics_path=MECHANICS,
            engine_path=ENGINE,
            runtime_path=RUNTIME,
            config_path=CONFIG,
            town_materializer_path=TOWN_MATERIALIZER,
            decay_materializer_path=DECAY_MATERIALIZER,
            output_dir=second,
        )
        for filename in (
            composer.OUTPUT_TOWN_SOURCE,
            composer.OUTPUT_TOWN_RECEIPT,
            composer.OUTPUT_FINAL_SOURCE,
            composer.OUTPUT_RECEIPT,
        ):
            self.assertEqual(
                (self.output / filename).read_bytes(),
                (second / filename).read_bytes(),
            )

    def test_fault_rolls_back_the_entire_publication(self):
        target = self.root / "faulted-composition"
        with self.assertRaisesRegex(composer.CompositionError, "injected publication fault"):
            composer.compose(
                repo_root=REPO,
                source_path=SOURCE,
                scheduler_path=SCHEDULER,
                mechanics_path=MECHANICS,
                engine_path=ENGINE,
                runtime_path=RUNTIME,
                config_path=CONFIG,
                town_materializer_path=TOWN_MATERIALIZER,
                decay_materializer_path=DECAY_MATERIALIZER,
                output_dir=target,
                fault_after="probe",
            )
        self.assertFalse(target.exists())
        self.assertFalse(target.is_symlink())

    def test_output_parent_symlink_fails_closed(self):
        real_parent = self.root / "real-parent"
        real_parent.mkdir()
        alias_parent = self.root / "alias-parent"
        try:
            alias_parent.symlink_to(real_parent, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaisesRegex(composer.CompositionError, "symlink component"):
            composer.compose(
                repo_root=REPO,
                source_path=SOURCE,
                scheduler_path=SCHEDULER,
                mechanics_path=MECHANICS,
                engine_path=ENGINE,
                runtime_path=RUNTIME,
                config_path=CONFIG,
                town_materializer_path=TOWN_MATERIALIZER,
                decay_materializer_path=DECAY_MATERIALIZER,
                output_dir=alias_parent / "output",
            )

    def test_donor_byte_drift_fails_closed_before_import(self):
        bad = self.root / "bad-town-materializer.py"
        bad.write_bytes(self.before[TOWN_MATERIALIZER] + b"\n")
        with self.assertRaisesRegex(composer.CompositionError, "Git blob mismatch"):
            composer._load_exact_module(
                bad, "bad_town_materializer", composer.TOWN_MATERIALIZER_GIT_BLOB
            )

    def test_canonical_checkout_remains_byte_identical(self):
        for path, before in self.before.items():
            self.assertEqual(path.read_bytes(), before, path)
        self.assertFalse(
            self.receipt["publication"]["canonical_repository_modified"]
        )
        self.assertFalse(self.receipt["publication"]["game_or_seed_spend"])
        self.assertFalse(
            self.receipt["publication"]["promotion_or_submission_claim"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
