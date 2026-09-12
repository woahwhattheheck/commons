# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ast
import importlib.util
from itertools import product
from pathlib import Path
import unittest


HERE = Path(__file__).resolve()
V3 = HERE.parents[2]
LAB = HERE.parents[4]
DOCS = V3 / "docs"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


materializer = _load(
    "v4_salvage_scheduler_prefix", DOCS / "v4_salvage_scheduler_prefix.py"
)


def _extract_prefix_helper(candidate: bytes):
    tree = ast.parse(candidate.decode("utf-8"))
    funcs = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_engine_market_prefix"
    ]
    if len(funcs) != 1:
        raise AssertionError(f"expected one prefix helper, got {len(funcs)}")
    module = ast.Module(body=funcs, type_ignores=[])
    ast.fix_missing_locations(module)
    ns = {}
    exec(compile(module, "<scheduler-prefix-helper>", "exec"), ns)
    return ns["_engine_market_prefix"]


class V4SchedulerPrefixSalvageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scheduler = (LAB / "scheduler.py").read_bytes()
        cls.engine = (LAB / "reference" / "engine" / "kaggriculture.py").read_bytes()
        cls.candidate = materializer.materialize_bytes(cls.scheduler, cls.engine)
        cls.prefix = _extract_prefix_helper(cls.candidate)

    def test_exact_current_scheduler_and_official_engine_are_bound(self):
        self.assertEqual(
            materializer.git_blob_sha(self.scheduler), materializer.SCHEDULER_GIT_BLOB
        )
        self.assertEqual(materializer.git_blob_sha(self.engine), materializer.ENGINE_GIT_BLOB)
        engine_text = self.engine.decode("utf-8")
        for anchor in materializer.ENGINE_ANCHORS:
            self.assertEqual(engine_text.count(anchor), 1)

    def test_only_three_current_consumers_are_rewired(self):
        before = self.scheduler.decode("utf-8")
        after = self.candidate.decode("utf-8")
        self.assertEqual(before.count("def _engine_market_prefix("), 0)
        self.assertEqual(after.count("def _engine_market_prefix("), 1)
        self.assertEqual(after.count("_engine_market_prefix("), 4)
        for old, new in (
            (materializer.CASH_OLD, materializer.CASH_NEW),
            (materializer.RECEIPT_INITIAL_OLD, materializer.RECEIPT_INITIAL_NEW),
            (materializer.RECEIPT_LOOP_OLD, materializer.RECEIPT_LOOP_NEW),
        ):
            self.assertEqual(before.count(old), 1)
            self.assertEqual(after.count(old), 0)
            self.assertEqual(after.count(new), 1)

    def test_prefix_helper_matches_official_raw_queue_rule(self):
        rows = ([], None, False, ["HIRE"], ["SELL", "CARROT", 2], ("HIRE",))
        checked = 0
        for layout in product(rows, repeat=3):
            for cap in (-5, -1, 0, 1, 2, 3, 9):
                with self.subTest(layout=layout, cap=cap):
                    action = {"market": list(layout)}
                    expected = list(layout)[:max(1, cap)]
                    self.assertEqual(
                        self.prefix(action, {"maxMarketOrdersPerTurn": cap}), expected
                    )
                    checked += 1
        self.assertEqual(checked, 1512)

    def test_default_cap_and_nonlist_queue_match_engine_normalization(self):
        action = {"market": [["SELL", "CARROT", 1]] for _ in range(11)}
        self.assertEqual(len(self.prefix(action, {})), 10)
        for value in (None, {}, "SELL", (["HIRE"],), 7):
            with self.subTest(value=value):
                self.assertEqual(self.prefix({"market": value}, {}), [])
        self.assertEqual(self.prefix(object(), {}), [])

    def test_inert_suffix_spend_and_receipt_rows_are_excluded_by_same_boundary(self):
        # Both repaired consumers now receive this identical executable prefix.
        action = {
            "market": [
                [],
                ["HIRE"],
                ["BUY_PRODUCT", "WHEAT", 1],
                ["SELL", "MELON", 1],
            ]
        }
        self.assertEqual(
            self.prefix(action, {"maxMarketOrdersPerTurn": 1}),
            [[]],
        )
        self.assertEqual(
            self.prefix(action, {"maxMarketOrdersPerTurn": 3}),
            [[], ["HIRE"], ["BUY_PRODUCT", "WHEAT", 1]],
        )

    def test_source_or_engine_drift_fails_closed(self):
        with self.assertRaises(materializer.MaterializationError):
            materializer.materialize_bytes(self.scheduler + b"\n# drift\n", self.engine)
        with self.assertRaises(materializer.MaterializationError):
            materializer.materialize_bytes(self.scheduler, self.engine + b"\n# drift\n")


if __name__ == "__main__":
    unittest.main()
