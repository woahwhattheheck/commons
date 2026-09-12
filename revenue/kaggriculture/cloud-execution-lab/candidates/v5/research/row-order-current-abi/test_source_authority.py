# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import subprocess
import unittest

import row_order_current as current

HERE = Path(__file__).resolve().parent
REPO = HERE
while REPO != REPO.parent and not (REPO / ".git").exists():
    REPO = REPO.parent


def git_blob(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def donor_bytes() -> bytes:
    return subprocess.run(
        [
            "git",
            "show",
            f"{current.SUBMITTED_V31_SOURCE}:{current.SUBMITTED_R04_PATH}",
        ],
        cwd=REPO,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def donor_namespace(source: bytes) -> dict:
    tree = ast.parse(source.decode("utf-8"), filename=current.SUBMITTED_R04_PATH)
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            if names & {"_RO_PARAMS", "_RO_I0"}:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in {
            "_ro_shape",
            "_ro_price",
            "order_sells",
        }:
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace: dict = {}
    exec(compile(module, current.SUBMITTED_R04_PATH, "exec"), namespace)
    return namespace


class SubmittedRowOrderAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = donor_bytes()
        cls.donor = donor_namespace(cls.source)

    def test_exact_submitted_source_blob(self):
        self.assertEqual(git_blob(self.source), current.SUBMITTED_R04_GIT_BLOB)

    def test_curve_constants_are_exact(self):
        self.assertEqual(self.donor["_RO_I0"], current.RO_I0)
        self.assertEqual(self.donor["_RO_PARAMS"], current.RO_PARAMS)

    def test_price_curve_is_exact_on_boundary_vectors(self):
        for item in sorted(current.RO_PARAMS):
            for inventory in (0, 9877, 9999, 10000, 10001, 10123, 12000):
                with self.subTest(item=item, inventory=inventory):
                    self.assertEqual(
                        current._price(item, inventory),
                        self.donor["_ro_price"](item, inventory),
                    )

    def test_valid_requested_quantity_order_matches_exact_donor(self):
        vectors = [
            (
                [
                    ["SELL", "WHEAT", 10],
                    ["SELL", "MILK", 10],
                    ["BUY_PRODUCT", "CARROT", 1],
                ],
                {"WHEAT": 10000, "MILK": 10000},
            ),
            (
                [
                    ["SELL", "MELON", 4],
                    ["SELL", "STRAWBERRY", 3],
                    ["SELL", "WOOL", 8],
                ],
                {"MELON": 9990, "STRAWBERRY": 10005, "WOOL": 10000},
            ),
            (
                [
                    ["SELL", "UNKNOWN_PUBLIC_PRODUCT", 3],
                    ["SELL", "CARROT", 5],
                ],
                {"CARROT": 10000},
            ),
        ]
        for market, inventory in vectors:
            with self.subTest(market=market):
                donor = self.donor["order_sells"](
                    [list(row) for row in market],
                    dict(inventory),
                )
                full_inventory = {item: 10000 for item in current.RO_PARAMS}
                full_inventory.update(inventory)
                selected = {"farmer": ["PASS"], "hands": [], "market": market}
                result = current.transform(
                    {"market": {"inventory": full_inventory}},
                    None,
                    selected,
                )
                self.assertEqual(result["market"], donor)

    def test_submitted_composition_order_places_row_order_before_evening_and_b5(self):
        text = self.source.decode("utf-8")
        stack_start = text.index("def _v3_stack(")
        stack_end = text.index("\n\ndef _v3_core(", stack_start)
        stack = text[stack_start:stack_end]
        row_order = stack.index("if ROW_ORDER and ROW_SHED:")
        evening = stack.index("if EVENING_FLUSH:")
        b5 = stack.index("if B5_CARROT_FERTILIZER or B5_JIT_FERTILIZE:")
        self.assertLess(row_order, evening)
        self.assertLess(evening, b5)

    def test_row_order_and_row_shed_are_distinct_submitted_flags(self):
        text = self.source.decode("utf-8")
        self.assertIn("ROW_ORDER = False", text)
        self.assertIn("ROW_SHED = False", text)
        self.assertIn("if ROW_ORDER and ROW_SHED:", text)
        self.assertIn("elif ROW_ORDER", text)


if __name__ == "__main__":
    unittest.main()
