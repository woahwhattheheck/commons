from __future__ import annotations

import ast
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest

import materialize as mat


HERE = Path(__file__).resolve().parent
LAB = HERE.parent.parent
SOURCE = LAB / "scheduler.py"
ENGINE = LAB / "reference" / "engine" / "kaggriculture.py"


def _load_official_engine():
    package = ModuleType("kaggle_environments")
    package.__path__ = []
    utils = ModuleType("kaggle_environments.utils")
    utils.resolve_episode_seed = lambda _env: 0
    previous_package = sys.modules.get("kaggle_environments")
    previous_utils = sys.modules.get("kaggle_environments.utils")
    sys.modules["kaggle_environments"] = package
    sys.modules["kaggle_environments.utils"] = utils
    try:
        spec = importlib.util.spec_from_file_location(
            "_receipt_prefix_official_engine", ENGINE
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load pinned official engine")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if previous_package is None:
            sys.modules.pop("kaggle_environments", None)
        else:
            sys.modules["kaggle_environments"] = previous_package
        if previous_utils is None:
            sys.modules.pop("kaggle_environments.utils", None)
        else:
            sys.modules["kaggle_environments.utils"] = previous_utils


def _method_node(text: str, method_name: str) -> ast.FunctionDef:
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "SellScheduler":
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == method_name:
                    return copy.deepcopy(child)
    raise AssertionError(f"missing SellScheduler.{method_name}")


def _top_level_function(text: str, function_name: str) -> ast.FunctionDef:
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return copy.deepcopy(node)
    raise AssertionError(f"missing {function_name}")


def _compile_receipt_profile(text: str, engine):
    body = []
    if "def _engine_market_prefix(" in text:
        body.append(_top_level_function(text, "_engine_market_prefix"))
    body.append(_method_node(text, "receipt_profile"))
    module = ast.fix_missing_locations(ast.Module(body=body, type_ignores=[]))

    def post_units(obs, _action, _config, *, shed_capacity=None):
        del shed_capacity
        return copy.deepcopy(obs["_farm"]), copy.deepcopy(obs["_private"])

    namespace = {
        "m": engine,
        "parent": SimpleNamespace(
            PASS={"farmer": ["PASS"], "hands": [], "market": []}
        ),
        "post_units": post_units,
    }
    exec(compile(module, "<receipt-profile-extract>", "exec"), namespace)
    return namespace.get("_engine_market_prefix"), namespace["receipt_profile"]


def _cash_reserve_source(text: str) -> str:
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "SellScheduler":
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == "cash_reserve":
                    segment = ast.get_source_segment(text, child)
                    if segment is None:
                        raise AssertionError("cash_reserve source segment unavailable")
                    return segment
    raise AssertionError("cash_reserve missing")


def _base_state(engine, *, shed: dict[str, int], inventory: dict[str, int] | None = None):
    farm = engine._new_farm(2, 3000)
    farm["farmer"] = [0, 0]
    private = engine._new_private()
    for item in private["shed"]:
        private["shed"][item] = 0
    private["shed"].update(shed)
    private["inventories"][0].update(inventory or {})
    return farm, private


def _profile_self(route):
    return SimpleNamespace(controller=SimpleNamespace(R=[route], cur=0))


def _official_market(engine, farm, private, action, *, limit=1):
    rival_farm = engine._new_farm(2, 3000)
    rival_private = engine._new_private()
    farms = [farm, rival_farm]
    market = engine._new_market()
    town = engine._new_town()
    observations = [
        SimpleNamespace(
            farms=farms,
            market=market,
            town=town,
            private=private,
            player=0,
        ),
        SimpleNamespace(
            farms=farms,
            market=market,
            town=town,
            private=rival_private,
            player=1,
        ),
    ]
    state = [
        SimpleNamespace(observation=observations[0], action=copy.deepcopy(action)),
        SimpleNamespace(
            observation=observations[1],
            action={"farmer": ["PASS"], "hands": [], "market": []},
        ),
    ]
    env = SimpleNamespace(
        configuration={
            "boardSize": 2,
            "maxMarketOrdersPerTurn": limit,
            "farmHandCostMult": 1,
            "shedCapacity": 100,
        }
    )
    engine._process_market(state, env)
    return state


class ExactSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_bytes = SOURCE.read_bytes()
        cls.engine_bytes = ENGINE.read_bytes()
        cls.engine = _load_official_engine()
        cls.candidate_bytes, cls.receipt = mat.materialize_bytes(
            cls.source_bytes, cls.engine_bytes
        )
        cls.source_text = cls.source_bytes.decode("utf-8")
        cls.candidate_text = cls.candidate_bytes.decode("utf-8")
        cls.legacy_prefix, cls.legacy_profile = _compile_receipt_profile(
            cls.source_text, cls.engine
        )
        cls.prefix, cls.candidate_profile = _compile_receipt_profile(
            cls.candidate_text, cls.engine
        )

    def test_exact_source_and_engine_blobs(self):
        self.assertEqual(mat.git_blob_sha(self.source_bytes), mat.SOURCE_GIT_BLOB)
        self.assertEqual(mat.git_blob_sha(self.engine_bytes), mat.ENGINE_GIT_BLOB)
        self.assertEqual(self.receipt["source"]["git_blob"], mat.SOURCE_GIT_BLOB)
        self.assertEqual(self.receipt["engine"]["git_blob"], mat.ENGINE_GIT_BLOB)

    def test_patch_is_one_helper_and_one_receipt_callsite(self):
        self.assertEqual(
            self.candidate_text.count("def _engine_market_prefix("), 1
        )
        self.assertEqual(
            self.candidate_text.count(mat.CALLSITE_REPLACEMENT), 1
        )
        self.assertNotIn(mat.CALLSITE_PREIMAGE, self.candidate_text)
        self.assertEqual(
            _cash_reserve_source(self.source_text),
            _cash_reserve_source(self.candidate_text),
        )
        compile(self.candidate_text, "<candidate>", "exec")

    def test_prefix_exactly_matches_official_queue_construction(self):
        action = {"market": [["SELL", "MELON", 1], ["HIRE"], []]}
        for raw_limit, expected in (
            (-9, action["market"][:1]),
            (0, action["market"][:1]),
            (1, action["market"][:1]),
            (2, action["market"][:2]),
            (99, action["market"]),
        ):
            with self.subTest(raw_limit=raw_limit):
                got = self.prefix(
                    action, {"maxMarketOrdersPerTurn": raw_limit}
                )
                self.assertEqual(got, expected)
                self.assertIsNot(got, action["market"])
        self.assertEqual(self.prefix({"market": tuple(action["market"])}, {}), [])
        self.assertEqual(self.prefix(None, {}), [])
        with self.assertRaises(ValueError):
            self.prefix(action, {"maxMarketOrdersPerTurn": "not-an-int"})

    def test_current_suffix_sell_capacity_inversion_matches_official_engine(self):
        farm, private = _base_state(
            self.engine,
            shed={"CARROT": 1, "MELON": 98},
            inventory={"WHEAT": 1},
        )
        obs = {"step": 0, "_farm": farm, "_private": private}
        base = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [[], ["SELL", "MELON", 1]],
        }
        route = [
            {"farmer": ["PASS"], "hands": [], "market": []},
            {"farmer": ["DROP"], "hands": [], "market": []},
        ]
        owner = _profile_self(route)
        config = {"shedCapacity": 100, "maxMarketOrdersPerTurn": 1}
        plan = ((0, 0), (1, 1))

        predecessor = self.legacy_profile(
            owner, obs, base, farm, private, 1, "CARROT", config
        )
        repaired = self.candidate_profile(
            owner, obs, base, farm, private, 1, "CARROT", config
        )
        self.assertTrue(predecessor(plan))
        self.assertFalse(repaired(plan))

        official_farm, official_private = _base_state(
            self.engine,
            shed={"CARROT": 1, "MELON": 98},
            inventory={"WHEAT": 1},
        )
        _official_market(self.engine, official_farm, official_private, base, limit=1)
        self.assertEqual(sum(official_private["shed"].values()), 99)
        self.engine._apply_unit_action(
            official_farm,
            official_private,
            0,
            ["DROP"],
            2,
            0,
            24,
            100,
        )
        self.assertEqual(sum(official_private["shed"].values()), 100)

    def test_future_suffix_sell_is_also_inert(self):
        farm, private = _base_state(
            self.engine,
            shed={"CARROT": 1, "MELON": 98},
            inventory={"WHEAT": 1},
        )
        obs = {"step": 0, "_farm": farm, "_private": private}
        base = {"farmer": ["PASS"], "hands": [], "market": []}
        route = [
            {"farmer": ["PASS"], "hands": [], "market": []},
            {
                "farmer": ["PASS"],
                "hands": [],
                "market": [[], ["SELL", "MELON", 1]],
            },
            {"farmer": ["DROP"], "hands": [], "market": []},
        ]
        owner = _profile_self(route)
        config = {"shedCapacity": 100, "maxMarketOrdersPerTurn": 1}
        plan = ((0, 0), (2, 1))
        self.assertTrue(
            self.legacy_profile(
                owner, obs, base, farm, private, 2, "CARROT", config
            )(plan)
        )
        self.assertFalse(
            self.candidate_profile(
                owner, obs, base, farm, private, 2, "CARROT", config
            )(plan)
        )

    def test_suffix_product_and_animal_buys_do_not_create_phantom_stock(self):
        for order in (
            ["BUY_PRODUCT", "WHEAT", 2],
            ["BUY_ANIMAL", "COW", 2],
        ):
            with self.subTest(order=order):
                farm, private = _base_state(
                    self.engine, shed={"CARROT": 1, "MELON": 98}
                )
                obs = {"step": 0, "_farm": farm, "_private": private}
                base = {
                    "farmer": ["PASS"],
                    "hands": [],
                    "market": [[], order],
                }
                route = [
                    {"farmer": ["PASS"], "hands": [], "market": []}
                ]
                owner = _profile_self(route)
                config = {
                    "shedCapacity": 100,
                    "maxMarketOrdersPerTurn": 1,
                }
                plan = ((0, 0),)
                self.assertFalse(
                    self.legacy_profile(
                        owner, obs, base, farm, private, 0, "CARROT", config
                    )(plan)
                )
                self.assertTrue(
                    self.candidate_profile(
                        owner, obs, base, farm, private, 0, "CARROT", config
                    )(plan)
                )

                official_farm, official_private = _base_state(
                    self.engine, shed={"CARROT": 1, "MELON": 98}
                )
                _official_market(
                    self.engine,
                    official_farm,
                    official_private,
                    base,
                    limit=1,
                )
                self.assertEqual(sum(official_private["shed"].values()), 99)
                self.assertEqual(official_private["shed"].get(order[1], 0), 0)

    def test_suffix_hire_cannot_create_a_phantom_future_actor(self):
        farm, private = _base_state(
            self.engine,
            shed={"CARROT": 1, "MELON": 98},
            inventory={"WHEAT": 1},
        )
        obs = {"step": 0, "_farm": farm, "_private": private}
        base = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [[], ["HIRE"]],
        }
        route = [
            {"farmer": ["PASS"], "hands": [], "market": []},
            {
                "farmer": ["PASS"],
                "hands": [["PICKUP", "MELON", 1]],
                "market": [],
            },
            {"farmer": ["DROP"], "hands": [], "market": []},
        ]
        owner = _profile_self(route)
        config = {"shedCapacity": 100, "maxMarketOrdersPerTurn": 1}
        plan = ((0, 0), (2, 1))
        self.assertTrue(
            self.legacy_profile(
                owner, obs, base, farm, private, 2, "CARROT", config
            )(plan)
        )
        self.assertFalse(
            self.candidate_profile(
                owner, obs, base, farm, private, 2, "CARROT", config
            )(plan)
        )

        official_farm, official_private = _base_state(
            self.engine,
            shed={"CARROT": 1, "MELON": 98},
            inventory={"WHEAT": 1},
        )
        _official_market(self.engine, official_farm, official_private, base, limit=1)
        self.assertEqual(official_farm["hands"], [])
        self.engine._apply_unit_action(
            official_farm,
            official_private,
            1,
            ["PICKUP", "MELON", 1],
            2,
            0,
            24,
            100,
        )
        self.engine._apply_unit_action(
            official_farm,
            official_private,
            0,
            ["DROP"],
            2,
            0,
            24,
            100,
        )
        self.assertEqual(sum(official_private["shed"].values()), 100)

    def test_active_prefix_sale_is_preserved_including_zero_limit_clamp(self):
        for limit in (0, 1):
            with self.subTest(limit=limit):
                farm, private = _base_state(
                    self.engine,
                    shed={"CARROT": 1, "MELON": 98},
                    inventory={"WHEAT": 1},
                )
                obs = {"step": 0, "_farm": farm, "_private": private}
                base = {
                    "farmer": ["PASS"],
                    "hands": [],
                    "market": [["SELL", "MELON", 1]],
                }
                route = [
                    {"farmer": ["PASS"], "hands": [], "market": []},
                    {"farmer": ["DROP"], "hands": [], "market": []},
                ]
                owner = _profile_self(route)
                config = {
                    "shedCapacity": 100,
                    "maxMarketOrdersPerTurn": limit,
                }
                plan = ((0, 0), (1, 1))
                self.assertTrue(
                    self.candidate_profile(
                        owner, obs, base, farm, private, 1, "CARROT", config
                    )(plan)
                )

                official_farm, official_private = _base_state(
                    self.engine,
                    shed={"CARROT": 1, "MELON": 98},
                    inventory={"WHEAT": 1},
                )
                _official_market(
                    self.engine,
                    official_farm,
                    official_private,
                    base,
                    limit=limit,
                )
                self.engine._apply_unit_action(
                    official_farm,
                    official_private,
                    0,
                    ["DROP"],
                    2,
                    0,
                    24,
                    100,
                )
                self.assertEqual(sum(official_private["shed"].values()), 99)


class MaterializerBoundaryTests(unittest.TestCase):
    def test_deterministic_candidate_and_path_free_receipt(self):
        source_before = SOURCE.read_bytes()
        engine_before = ENGINE.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_a = root / "a" / "scheduler.py"
            output_b = root / "b" / "scheduler.py"
            receipt_a = mat.materialize(SOURCE, ENGINE, output_a)
            receipt_b = mat.materialize(SOURCE, ENGINE, output_b)
            self.assertEqual(output_a.read_bytes(), output_b.read_bytes())
            self.assertEqual(receipt_a, receipt_b)
            rendered = json.dumps(receipt_a, sort_keys=True)
            self.assertNotIn(str(root), rendered)
            self.assertEqual(
                mat.git_blob_sha(output_a.read_bytes()),
                receipt_a["candidate"]["git_blob"],
            )
        self.assertEqual(SOURCE.read_bytes(), source_before)
        self.assertEqual(ENGINE.read_bytes(), engine_before)

    def test_source_or_engine_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "scheduler.py"
            engine = root / "engine.py"
            source.write_bytes(SOURCE.read_bytes() + b"\n")
            engine.write_bytes(ENGINE.read_bytes())
            with self.assertRaisesRegex(mat.MaterializationError, "scheduler blob mismatch"):
                mat.materialize(source, engine, root / "out.py")

            source.write_bytes(SOURCE.read_bytes())
            engine.write_bytes(ENGINE.read_bytes() + b"\n")
            with self.assertRaisesRegex(mat.MaterializationError, "engine blob mismatch"):
                mat.materialize(source, engine, root / "out.py")

    def test_output_cannot_alias_source_or_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "scheduler.py"
            engine = root / "engine.py"
            source.write_bytes(SOURCE.read_bytes())
            engine.write_bytes(ENGINE.read_bytes())
            for output in (source, engine):
                with self.subTest(output=output.name):
                    with self.assertRaisesRegex(
                        mat.MaterializationError, "output aliases"
                    ):
                        mat.materialize(source, engine, output)

            hardlink = root / "hardlink.py"
            os.link(source, hardlink)
            with self.assertRaisesRegex(mat.MaterializationError, "output aliases"):
                mat.materialize(source, engine, hardlink)

    def test_symlink_inputs_and_output_fail_closed(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "scheduler.py"
            engine = root / "engine.py"
            source.write_bytes(SOURCE.read_bytes())
            engine.write_bytes(ENGINE.read_bytes())
            source_link = root / "scheduler-link.py"
            source_link.symlink_to(source)
            with self.assertRaisesRegex(mat.MaterializationError, "non-symlink"):
                mat.materialize(source_link, engine, root / "out.py")
            target = root / "target.py"
            target.write_text("sentinel", encoding="utf-8")
            output_link = root / "out-link.py"
            output_link.symlink_to(target)
            with self.assertRaisesRegex(mat.MaterializationError, "symlink"):
                mat.materialize(source, engine, output_link)
            self.assertEqual(target.read_text(encoding="utf-8"), "sentinel")


if __name__ == "__main__":
    unittest.main(verbosity=2)
