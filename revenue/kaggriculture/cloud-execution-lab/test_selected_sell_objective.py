# SPDX-License-Identifier: Apache-2.0
"""Contract tests for the score-active selected SELL objective."""
from __future__ import annotations

import ast
import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCES = (
    ROOT / "selected_sell_core.py",
    ROOT / "reference/titan-current/latest/selected_sell_core.py",
)


def _score_return(path: Path) -> ast.Tuple:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MarketPath"]
    if len(classes) != 1:
        raise AssertionError(f"{path}: expected one MarketPath class, found {len(classes)}")
    methods = [
        node
        for node in classes[0].body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "score"
    ]
    if len(methods) != 1:
        raise AssertionError(f"{path}: expected one MarketPath.score, found {len(methods)}")
    returns = [node for node in ast.walk(methods[0]) if isinstance(node, ast.Return)]
    if len(returns) != 1 or not isinstance(returns[0].value, ast.Tuple):
        raise AssertionError(f"{path}: MarketPath.score must have one tuple return")
    value = returns[0].value
    if len(value.elts) != 4:
        raise AssertionError(f"{path}: expected four score fields, found {len(value.elts)}")
    return value


class SelectedSellObjectiveContract(unittest.TestCase):
    def test_source_and_packaged_source_are_identical(self) -> None:
        blobs = [path.read_bytes() for path in SOURCES]
        self.assertEqual(
            blobs[0],
            blobs[1],
            msg=(
                "selected SELL source mirrors diverged: "
                + ", ".join(f"{path}={hashlib.sha256(blob).hexdigest()}" for path, blob in zip(SOURCES, blobs))
            ),
        )

    def test_primary_score_is_own_terminal_value(self) -> None:
        expected = ast.dump(ast.parse("own_cash + carry", mode="eval").body, include_attributes=False)
        for path in SOURCES:
            score = _score_return(path)
            self.assertEqual(expected, ast.dump(score.elts[0], include_attributes=False), str(path))
            self.assertEqual(
                ["own_cash", "other_cash", "remaining"],
                [ast.unparse(node) for node in score.elts[1:]],
                str(path),
            )


if __name__ == "__main__":
    unittest.main()
