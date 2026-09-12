# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ast
import copy
import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve()
V3 = HERE.parents[2]
OVERLAY = HERE.parents[1]
DOCS = V3 / "docs"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


materializer = _load("v4_salvage_fast_clone", DOCS / "v4_salvage_fast_clone.py")
r01_tapes = _load("v4_fast_clone_tapes", OVERLAY / "r01_tapes.py")


def _candidate_helpers(candidate: bytes):
    tree = ast.parse(candidate.decode("utf-8"))
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if "_R04_JSON_SCALAR_TYPES" in names:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in {
            "_r04_is_fast_tape_action", "_r04_clone_tape_action"
        }:
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"copy": copy}
    exec(compile(module, "<fast-clone-helpers>", "exec"), namespace)
    return namespace["_r04_is_fast_tape_action"], namespace["_r04_clone_tape_action"]


class V4FastCloneSalvageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (OVERLAY / "r04_full_router.py").read_bytes()
        cls.candidate = materializer.materialize_bytes(cls.source)
        cls.is_fast, cls.clone = _candidate_helpers(cls.candidate)

    def test_materializer_is_exact_current_root_and_two_hunks_only(self):
        self.assertEqual(materializer.git_blob_sha(self.source), materializer.SOURCE_GIT_BLOB)
        before = self.source.decode("utf-8")
        after = self.candidate.decode("utf-8")
        self.assertEqual(before.count(materializer.CLONE_PREIMAGE), 1)
        self.assertEqual(after.count(materializer.CLONE_POSTIMAGE), 1)
        self.assertNotIn(materializer.CLONE_PREIMAGE, after)
        self.assertEqual(after.count("def _r04_clone_tape_action("), 1)
        self.assertEqual(after.count("def _r04_is_fast_tape_action("), 1)
        self.assertEqual(
            len(after) - len(before),
            len(materializer.HELPERS) + len(materializer.CLONE_POSTIMAGE)
            - len(materializer.CLONE_PREIMAGE),
        )

    def test_all_9347_frozen_tape_actions_equal_deepcopy_without_aliases(self):
        tapes = r01_tapes.load_tapes()
        self.assertEqual(len(tapes), 13)
        count = 0
        for tape_index, tape in enumerate(tapes):
            self.assertEqual(len(tape), 719)
            for step, template in enumerate(tape):
                with self.subTest(tape=tape_index, step=step):
                    snapshot = copy.deepcopy(template)
                    self.assertTrue(self.is_fast(template))
                    got = self.clone(template)
                    self.assertEqual(got, snapshot)
                    self.assertIsNot(got, template)
                    self.assertIsNot(got["farmer"], template["farmer"])
                    self.assertIsNot(got["hands"], template["hands"])
                    self.assertIsNot(got["market"], template["market"])
                    self.assertEqual(len(got["hands"]), len(template["hands"]))
                    self.assertEqual(len(got["market"]), len(template["market"]))
                    for left, right in zip(got["hands"], template["hands"]):
                        self.assertIsNot(left, right)
                    for left, right in zip(got["market"], template["market"]):
                        self.assertIsNot(left, right)
                    # Mutation of every mutable first-level child must stay private.
                    got["farmer"].append("__probe__")
                    if got["hands"]:
                        got["hands"][0].append("__probe__")
                    if got["market"]:
                        got["market"][0].append("__probe__")
                    self.assertEqual(template, snapshot)
                    count += 1
        self.assertEqual(count, 9347)

    def test_future_schema_fails_closed_to_real_deepcopy(self):
        cases = [
            {"farmer": ["PASS"], "hands": [], "market": [], "future": {"x": [1]}},
            {"farmer": ["PASS", {"future": [1]}], "hands": [], "market": []},
            {"farmer": ["PASS"], "hands": [["PASS", {"x": 1}]], "market": []},
            {"farmer": ["PASS"], "hands": [], "market": [("SELL", "WOOL", 1)]},
        ]
        for value in cases:
            with self.subTest(value=value):
                snapshot = copy.deepcopy(value)
                self.assertFalse(self.is_fast(value))
                got = self.clone(value)
                self.assertEqual(got, snapshot)
                self.assertIsNot(got, value)
                # Prove nested mutable state is detached on the fallback path.
                if "future" in got:
                    got["future"]["x"].append(2)
                    self.assertEqual(value, snapshot)
                elif isinstance(got["farmer"][-1], dict):
                    got["farmer"][-1]["future"].append(2)
                    self.assertEqual(value, snapshot)

    def test_bool_and_none_are_valid_json_scalars(self):
        value = {"farmer": ["PASS", True, None, 1, 1.5, "x"], "hands": [], "market": []}
        self.assertTrue(self.is_fast(value))
        self.assertEqual(self.clone(value), copy.deepcopy(value))

    def test_source_drift_fails_closed_before_transformation(self):
        bad = self.source + b"\n# drift\n"
        with self.assertRaises(materializer.MaterializationError):
            materializer.materialize_bytes(bad)


if __name__ == "__main__":
    unittest.main()
