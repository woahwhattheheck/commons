from __future__ import annotations

import ast
import copy
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]  # .../cloud-execution-lab
REPO = HERE.parents[4]
SOURCE = LAB / "frozen_selected.py"
SCHEDULER = LAB / "scheduler.py"
MECHANICS = LAB / "mechanics.py"
ENGINE = LAB / "reference" / "engine" / "kaggriculture.py"

spec = importlib.util.spec_from_file_location("funding_decay_materializer", HERE / "materialize.py")
materializer = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(materializer)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_official_engine():
    package = types.ModuleType("kaggle_environments")
    package.__path__ = []
    utils = types.ModuleType("kaggle_environments.utils")
    utils.resolve_episode_seed = lambda _env: 0
    old_package = sys.modules.get("kaggle_environments")
    old_utils = sys.modules.get("kaggle_environments.utils")
    sys.modules["kaggle_environments"] = package
    sys.modules["kaggle_environments.utils"] = utils
    try:
        return _load("funding_decay_official_engine", ENGINE)
    finally:
        if old_package is None:
            sys.modules.pop("kaggle_environments", None)
        else:
            sys.modules["kaggle_environments"] = old_package
        if old_utils is None:
            sys.modules.pop("kaggle_environments.utils", None)
        else:
            sys.modules["kaggle_environments.utils"] = old_utils


def _synthetic_source(extra_tail: str = "") -> str:
    tail = f"        {extra_tail}\n" if extra_tail else ""
    return (
        "def _funding_trace(obs, config, farm, private, route, now, end, current_market, stress_units=0):\n"
        "    rows = []\n"
        "    for t in range(now, end + 1):\n"
        "        rows.append(t)\n"
        f"{tail}"
        "    return {'rows': rows}\n"
    )


class StructuralContracts(unittest.TestCase):
    def test_inserts_exactly_once_at_turn_tail(self):
        post, details = materializer.patch_source(_synthetic_source())
        self.assertIn("        m._decay_plants(f, t)\n", post)
        self.assertEqual(details["function"], "_funding_trace")
        self.assertEqual(details["prior_stage_call"], "rows.append")
        tree = ast.parse(post)
        fn = tree.body[0]
        loop = next(node for node in fn.body if isinstance(node, ast.For))
        self.assertEqual(len([n for n in ast.walk(fn) if isinstance(n, ast.Call) and materializer._name(n.func) == "m._decay_plants"]), 1)
        self.assertEqual(materializer._call_expr_name(loop.body[-1]), "m._decay_plants")

    def test_composes_after_town_consumption(self):
        post, details = materializer.patch_source(
            _synthetic_source("_funding_apply_town_consumption(inventory, shops, config, t)")
        )
        self.assertEqual(details["prior_stage_call"], "_funding_apply_town_consumption")
        self.assertLess(post.index("_funding_apply_town_consumption"), post.index("m._decay_plants"))

    def test_runtime_binding_accepts_exact_semantics(self):
        source = "from scheduler import *\n" + _synthetic_source()
        scheduler = "import mechanics as m\nVALUE = 1\n"
        decay = "def _decay_plants(farm, step):\n    farm['n'] -= step\n"
        details = materializer.verify_runtime_decay_binding(
            source, scheduler, decay, decay
        )
        self.assertTrue(details["implicit_wildcard_export"])
        self.assertFalse(details["scheduler_rebinds_m"])

    def test_runtime_binding_rejects_mechanics_semantic_drift(self):
        source = "from scheduler import *\n" + _synthetic_source()
        scheduler = "import mechanics as m\n"
        runtime = "def _decay_plants(farm, step):\n    farm['n'] -= step\n"
        official = "def _decay_plants(farm, step):\n    farm['n'] += step\n"
        with self.assertRaisesRegex(
            materializer.MaterializationError, "differs from the official engine"
        ):
            materializer.verify_runtime_decay_binding(
                source, scheduler, runtime, official
            )

    def test_runtime_binding_rejects_scheduler_alias_rebind(self):
        source = "from scheduler import *\n" + _synthetic_source()
        scheduler = "import mechanics as m\nm = object()\n"
        decay = "def _decay_plants(farm, step):\n    farm['n'] -= step\n"
        with self.assertRaisesRegex(
            materializer.MaterializationError, "rebinds mechanics alias"
        ):
            materializer.verify_runtime_decay_binding(
                source, scheduler, decay, decay
            )

    def test_rejects_duplicate_decay(self):
        with self.assertRaisesRegex(materializer.MaterializationError, "already contains"):
            materializer.patch_source(_synthetic_source("m._decay_plants(f, t)"))

    def test_rejects_ambiguous_outer_loop(self):
        source = _synthetic_source().replace(
            "    return {'rows': rows}\n",
            "    for t in range(now, end + 1):\n        rows.append(t)\n    return {'rows': rows}\n",
        )
        with self.assertRaisesRegex(materializer.MaterializationError, "expected one outer funding loop"):
            materializer.patch_source(source)

    def test_rejects_loop_not_followed_by_return(self):
        source = _synthetic_source().replace(
            "    return {'rows': rows}\n",
            "    rows.append('later')\n    return {'rows': rows}\n",
        )
        with self.assertRaisesRegex(materializer.MaterializationError, "immediately followed"):
            materializer.patch_source(source)


@unittest.skipUnless(
    all(path.is_file() for path in (SOURCE, SCHEDULER, MECHANICS, ENGINE)),
    "repository source tree is required",
)
class ExactRepositoryContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LAB))
        cls.temp = tempfile.TemporaryDirectory()
        cls.temp_path = Path(cls.temp.name)
        cls.candidate_path = cls.temp_path / "frozen_selected_decay.py"
        cls.receipt_path = cls.temp_path / "receipt.json"
        cls.source_before = SOURCE.read_bytes()
        cls.scheduler_before = SCHEDULER.read_bytes()
        cls.mechanics_before = MECHANICS.read_bytes()
        cls.engine_before = ENGINE.read_bytes()
        cls.receipt = materializer.materialize(
            SOURCE,
            SCHEDULER,
            MECHANICS,
            ENGINE,
            cls.candidate_path,
            cls.receipt_path,
        )
        cls.canonical = _load("funding_decay_canonical", SOURCE)
        cls.candidate = _load("funding_decay_candidate", cls.candidate_path)
        cls.engine = _load_official_engine()

    @classmethod
    def tearDownClass(cls):
        if sys.path and sys.path[0] == str(LAB):
            sys.path.pop(0)
        cls.temp.cleanup()

    def _plant(self, yield_units=2, max_lifespan_step=120):
        return {
            "kind": "PLANT",
            "crop": "WHEAT",
            "planted_day": 0,
            "watered_today": False,
            "consecutive_unwatered": 0,
            "yield_units": yield_units,
            "max_lifespan_step": max_lifespan_step,
            "fertilized_until_day": -1,
        }

    def _farm(self, yield_units=2):
        tiles = [
            [None if x < 5 and y < 5 else "LOCKED" for x in range(10)]
            for y in range(10)
        ]
        tiles[4][4] = self._plant(yield_units)
        return {
            "money": 300,
            "tiles": tiles,
            "farmer": [4, 4],
            "hands": [],
            "unlocked_quadrants": ["NW"],
            "hires_today": 0,
        }

    def _private(self, module):
        shed = {name: 0 for name in [*module.m.PRODUCTS, *module.m.ANIMALS]}
        shed["MILK"] = 1
        return {
            "shed": shed,
            "seeds": {name: 0 for name in module.m.CROPS},
            "inventories": [{}],
        }

    def _fixture(self, module):
        farm = self._farm()
        private = self._private(module)
        inventory = {name: 10000 for name in module.m.PRODUCTS}
        obs = {
            "step": 120,
            "player": 0,
            "market": {"inventory": inventory, "prices": {name: module.m.market_price(name, 10000) for name in module.m.PRODUCTS}},
            "town": {"unlocked_shops": []},
        }
        route = [{"farmer": ["PASS"], "hands": [], "market": []} for _ in range(124)]
        route[121] = {"farmer": ["HARVEST"], "hands": [], "market": []}
        route[122] = {"farmer": ["DROP"], "hands": [], "market": []}
        route[123] = {"farmer": ["PASS"], "hands": [], "market": [["BUY_ANIMAL", "GOOSE", 1]]}
        config = {
            "shedCapacity": 2,
            "maxMarketOrdersPerTurn": 10,
            "turnsPerDay": 24,
            "episodeSteps": 720,
            "townShopSellInterval": 1000,
            "townCenterSellInterval": 1000,
        }
        base = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "MILK", 1]]}
        current = {"MILK": 1}
        targets = {"MILK": 1}
        return obs, config, base, farm, private, route, current, targets

    def _minimum(self, module):
        obs, config, base, farm, private, route, current, targets = self._fixture(module)
        return module.funded_minimum_now(
            obs, config, base, farm, private, route, 123,
            current, targets, "MILK", stress_units=32,
        )

    def _official_purchase_units(self, sell_quantity):
        engine = self.engine
        config = {
            "shedCapacity": 2,
            "maxMarketOrdersPerTurn": 10,
            "turnsPerDay": 24,
            "farmHandCostMult": 1,
            "townShopSellInterval": 1000,
            "townCenterSellInterval": 1000,
        }
        farm0 = self._farm()
        farm1 = engine._new_farm(10, 300)
        private0 = {
            "shed": {name: 0 for name in [*engine.PRODUCTS, *engine.ANIMALS]},
            "seeds": {name: 0 for name in engine.CROPS},
            "inventories": [{}],
        }
        private0["shed"]["MILK"] = 1
        private1 = engine._new_private()
        market = engine._new_market()
        town = engine._new_town()
        observations = [
            types.SimpleNamespace(
                farms=[farm0, farm1], market=market, town=town, private=private0, player=0
            ),
            types.SimpleNamespace(
                farms=[farm0, farm1], market=market, town=town, private=private1, player=1
            ),
        ]
        states = [
            types.SimpleNamespace(observation=observations[0], action={}),
            types.SimpleNamespace(observation=observations[1], action={}),
        ]
        env = types.SimpleNamespace(configuration=config)
        actions = {
            120: {"farmer": ["PASS"], "hands": [],
                  "market": [["SELL", "MILK", sell_quantity]] if sell_quantity else [[]]},
            121: {"farmer": ["HARVEST"], "hands": [], "market": []},
            122: {"farmer": ["DROP"], "hands": [], "market": []},
            123: {"farmer": ["PASS"], "hands": [],
                  "market": [["BUY_ANIMAL", "GOOSE", 1]]},
        }
        for step in range(120, 124):
            action = actions[step]
            engine._apply_unit_action(
                farm0, private0, 0, action["farmer"], 10, step // 24, 24, 2
            )
            states[0].action = action
            states[1].action = {"farmer": ["PASS"], "hands": [], "market": []}
            engine._process_market(states, env)
            engine._town_consume(env, states, step)
            for farm in observations[0].farms:
                engine._decay_plants(farm, step)
        return private0["shed"].get("GOOSE", 0)

    def test_exact_decay_binding_git_blobs(self):
        self.assertEqual(materializer.git_blob_sha1(self.source_before), materializer.SOURCE_GIT_BLOB)
        self.assertEqual(materializer.git_blob_sha1(self.scheduler_before), materializer.SCHEDULER_GIT_BLOB)
        self.assertEqual(materializer.git_blob_sha1(self.mechanics_before), materializer.MECHANICS_GIT_BLOB)
        self.assertEqual(materializer.git_blob_sha1(self.engine_before), materializer.ENGINE_GIT_BLOB)

    def test_runtime_decay_binding_contract(self):
        details = materializer.verify_runtime_decay_binding(
            self.source_before.decode("utf-8"),
            self.scheduler_before.decode("utf-8"),
            self.mechanics_before.decode("utf-8"),
            self.engine_before.decode("utf-8"),
        )
        self.assertTrue(details["implicit_wildcard_export"])
        self.assertFalse(details["scheduler_rebinds_m"])
        self.assertEqual(
            Path(self.candidate.m.__file__).resolve(),
            MECHANICS.resolve(),
        )

    def test_official_engine_chronology_contract(self):
        details = materializer.verify_engine(self.engine_before.decode("utf-8"))
        self.assertLess(details["market_statement_index"], details["town_statement_index"])
        self.assertLess(details["town_statement_index"], details["decay_statement_index"])
        self.assertLess(details["decay_statement_index"], details["end_of_day_statement_index"])

    def test_witness_plant_metadata_is_engine_reachable(self):
        generated = self.engine._new_plant("WHEAT", 0, 24)
        witness = self._plant()
        self.assertEqual(generated["max_lifespan_step"], 120)
        self.assertEqual(witness["max_lifespan_step"], generated["max_lifespan_step"])
        self.assertEqual(witness["planted_day"], generated["planted_day"])
        self.assertLessEqual(witness["yield_units"], self.engine.CROPS["WHEAT"]["max_yield"])
        self.assertEqual(witness["consecutive_unwatered"], 0)

    def test_runtime_decay_matches_official_boundaries(self):
        for step, expected in ((119, 2), (120, 1), (121, 2), (122, 1)):
            official_farm = self._farm()
            runtime_farm = copy.deepcopy(official_farm)
            self.engine._decay_plants(official_farm, step)
            self.candidate.m._decay_plants(runtime_farm, step)
            self.assertEqual(official_farm, runtime_farm)
            self.assertEqual(official_farm["tiles"][4][4]["yield_units"], expected)

    def test_zero_yield_becomes_weed_and_animals_do_not_decay(self):
        farm = self._farm(yield_units=1)
        farm["tiles"][4][5] = {
            "kind": "COOP", "animal": "GOOSE", "yield_units": 2,
            "placed_day": 0, "consecutive_unfed": 0, "fed_today": False,
            "cared_today": False, "fertilizer_available": False,
            "pending_care_bonus": 0,
        }
        expected = copy.deepcopy(farm)
        self.engine._decay_plants(expected, 120)
        actual = copy.deepcopy(farm)
        self.candidate.m._decay_plants(actual, 120)
        self.assertEqual(actual, expected)
        self.assertEqual(actual["tiles"][4][4], {"kind": "WEED"})
        self.assertEqual(actual["tiles"][4][5]["yield_units"], 2)

    def test_capacity_killer_changes_minimum_zero_to_one(self):
        old_minimum, old_receipt = self._minimum(self.canonical)
        new_minimum, new_receipt = self._minimum(self.candidate)
        self.assertEqual(old_minimum, 0)
        self.assertEqual(new_minimum, 1)
        self.assertEqual(old_receipt["reference_acquisitions"], 0)
        self.assertEqual(new_receipt["reference_acquisitions"], 1)
        self.assertFalse(new_receipt["fallback"])

    def test_official_transition_reproduces_capacity_killer(self):
        self.assertEqual(self._official_purchase_units(1), 1)
        self.assertEqual(self._official_purchase_units(0), 0)

    def test_exact_trace_explains_capacity_boundary(self):
        obs, config, base, farm, private, route, current, targets = self._fixture(self.candidate)
        baseline_market = self.candidate.materialize_sales(base["market"], current, private["shed"], targets, 10)
        withheld_market = self.candidate.materialize_sales(base["market"], {"MILK": 0}, private["shed"], targets, 10)
        baseline = self.candidate._funding_trace(obs, config, farm, private, route, 120, 123, baseline_market)
        withheld = self.candidate._funding_trace(obs, config, farm, private, route, 120, 123, withheld_market)
        key = (123, 0, "BUY_ANIMAL", "GOOSE")
        self.assertEqual(dict(baseline["acquisitions"])[key], 1)
        self.assertEqual(dict(withheld["acquisitions"])[key], 0)

    def test_canonical_inputs_are_not_modified(self):
        self.assertEqual(SOURCE.read_bytes(), self.source_before)
        self.assertEqual(SCHEDULER.read_bytes(), self.scheduler_before)
        self.assertEqual(MECHANICS.read_bytes(), self.mechanics_before)
        self.assertEqual(ENGINE.read_bytes(), self.engine_before)
        self.assertTrue(self.candidate_path.is_file())

    def test_receipt_is_strict_and_deterministic(self):
        parsed = json.loads(self.receipt_path.read_text("utf-8"))
        self.assertEqual(parsed, self.receipt)
        self.assertEqual(parsed["operation"], materializer.OPERATION)
        self.assertEqual(parsed["status"], "PASS")
        self.assertFalse(parsed["mutation_boundary"]["canonical_source_modified"])
        self.assertEqual(
            parsed["runtime_decay_binding"]["contract"]["decay_semantic_sha256"],
            materializer._semantic_function_digest(
                materializer._single_function(ast.parse(self.engine_before.decode("utf-8")), "_decay_plants")
            ),
        )
        with tempfile.TemporaryDirectory() as second_dir:
            out2 = Path(second_dir) / "candidate.py"
            receipt2 = Path(second_dir) / "receipt.json"
            materializer.materialize(SOURCE, SCHEDULER, MECHANICS, ENGINE, out2, receipt2)
            self.assertEqual(out2.read_bytes(), self.candidate_path.read_bytes())
            self.assertEqual(receipt2.read_bytes(), self.receipt_path.read_bytes())

    def test_source_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad = root / "frozen_selected.py"
            bad.write_bytes(self.source_before + b"\n")
            with self.assertRaisesRegex(materializer.MaterializationError, "source Git blob mismatch"):
                materializer.materialize(
                    bad, SCHEDULER, MECHANICS, ENGINE,
                    root / "out.py", root / "receipt.json",
                )

    def test_scheduler_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad = root / "scheduler.py"
            bad.write_bytes(self.scheduler_before + b"\n")
            with self.assertRaisesRegex(materializer.MaterializationError, "scheduler Git blob mismatch"):
                materializer.materialize(
                    SOURCE, bad, MECHANICS, ENGINE,
                    root / "out.py", root / "receipt.json",
                )

    def test_mechanics_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad = root / "mechanics.py"
            bad.write_bytes(self.mechanics_before + b"\n")
            with self.assertRaisesRegex(materializer.MaterializationError, "mechanics Git blob mismatch"):
                materializer.materialize(
                    SOURCE, SCHEDULER, bad, ENGINE,
                    root / "out.py", root / "receipt.json",
                )

    def test_engine_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad = root / "kaggriculture.py"
            bad.write_bytes(self.engine_before + b"\n")
            with self.assertRaisesRegex(materializer.MaterializationError, "engine Git blob mismatch"):
                materializer.materialize(
                    SOURCE, SCHEDULER, MECHANICS, bad,
                    root / "out.py", root / "receipt.json",
                )

    def test_output_alias_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "receipt.json"
            with self.assertRaisesRegex(materializer.MaterializationError, "must be distinct"):
                materializer.materialize(
                    SOURCE, SCHEDULER, MECHANICS, ENGINE, SOURCE, receipt
                )

    def test_input_symlink_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            alias = root / "source.py"
            alias.symlink_to(SOURCE)
            with self.assertRaisesRegex(materializer.MaterializationError, "non-symlink"):
                materializer.materialize(
                    alias, SCHEDULER, MECHANICS, ENGINE,
                    root / "out.py", root / "receipt.json",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
