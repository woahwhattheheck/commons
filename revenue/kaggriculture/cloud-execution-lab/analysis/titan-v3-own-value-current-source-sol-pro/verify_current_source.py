#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed source contract for TITAN's integrated own-value SELL objective."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

OPERATION = "TITAN-V3-OWN-VALUE-CURRENT-SOURCE-INTEGRATION-20260910-01"
PREDECESSOR_BLOB = "f23d3a8b5ee5e82029026e7f8f44eb36c143a5a3"
EVIDENCE_PR = 11965
EVIDENCE_HEAD = "b6b9a8a4ca26152bbfe1a3833380ca885e5c4cae"
EVIDENCE_RUN = 34521455981
EXPECTED_PARAMETERS = ("self", "plan", "quantity", "rival", "alignment", "terminal")
EXPECTED_FIELDS = ("own_cash + carry", "own_cash", "other_cash", "remaining")


class SourceContractError(ValueError):
    """The selected source no longer has the reviewed one-factor objective shape."""


def _git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _only(items: list[Any], label: str) -> Any:
    if len(items) != 1:
        raise SourceContractError(f"expected exactly one {label}, found {len(items)}")
    return items[0]


def _expr(text: str) -> ast.expr:
    return ast.parse(text, mode="eval").body


def _same_expression(left: ast.AST, right: ast.AST) -> bool:
    return ast.dump(left, include_attributes=False) == ast.dump(
        right, include_attributes=False
    )


def verify_source(path: Path) -> dict[str, Any]:
    path = Path(path).resolve(strict=True)
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SourceContractError("selected_sell_core.py is not UTF-8") from exc
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        raise SourceContractError(f"selected_sell_core.py does not parse: {exc}") from exc

    market_path = _only(
        [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MarketPath"],
        "top-level MarketPath class",
    )
    score = _only(
        [node for node in market_path.body if isinstance(node, ast.FunctionDef) and node.name == "score"],
        "MarketPath.score method",
    )

    arguments = score.args
    positional = tuple(
        arg.arg for arg in (*arguments.posonlyargs, *arguments.args)
    )
    if positional != EXPECTED_PARAMETERS:
        raise SourceContractError(
            f"MarketPath.score parameter drift: expected {EXPECTED_PARAMETERS}, got {positional}"
        )
    if arguments.vararg or arguments.kwarg or arguments.kwonlyargs:
        raise SourceContractError("MarketPath.score gained variadic or keyword-only parameters")
    if len(arguments.defaults) != 1:
        raise SourceContractError("MarketPath.score must have exactly one default")
    default = arguments.defaults[0]
    if not isinstance(default, ast.Constant) or default.value is not False:
        raise SourceContractError("MarketPath.score terminal default must remain False")

    returns = [node for node in ast.walk(score) if isinstance(node, ast.Return)]
    returned = _only(returns, "MarketPath.score return")
    if not isinstance(returned.value, ast.Tuple) or len(returned.value.elts) != 4:
        raise SourceContractError("MarketPath.score must return exactly four tuple fields")
    for index, (actual, expected) in enumerate(zip(returned.value.elts, EXPECTED_FIELDS)):
        if not _same_expression(actual, _expr(expected)):
            rendered = ast.unparse(actual) if hasattr(ast, "unparse") else ast.dump(actual)
            raise SourceContractError(
                f"MarketPath.score field {index} drift: expected {expected!r}, got {rendered!r}"
            )

    first_names = {
        node.id for node in ast.walk(returned.value.elts[0]) if isinstance(node, ast.Name)
    }
    if first_names != {"own_cash", "carry"}:
        raise SourceContractError(
            f"objective dependencies drift: expected own_cash/carry only, got {sorted(first_names)}"
        )

    optimize = _only(
        [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "optimize_lot"],
        "top-level optimize_lot function",
    )
    score_calls = sum(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "score"
        for node in ast.walk(optimize)
    )
    score_zero_reads = sum(
        isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.Constant)
        and node.slice.value == 0
        for node in ast.walk(optimize)
    )
    if score_calls < 4 or score_zero_reads < 8:
        raise SourceContractError(
            "optimizer consumption surface shrank unexpectedly: "
            f"score_calls={score_calls}, score_zero_reads={score_zero_reads}"
        )

    return {
        "schema_version": 1,
        "operation": OPERATION,
        "source_path": path.name,
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "source_git_blob_sha1": _git_blob_sha1(data),
        "predecessor_git_blob_sha1": PREDECESSOR_BLOB,
        "evidence_pr": EVIDENCE_PR,
        "evidence_head": EVIDENCE_HEAD,
        "evidence_run": EVIDENCE_RUN,
        "method": "MarketPath.score",
        "parameters": list(EXPECTED_PARAMETERS),
        "objective_field": EXPECTED_FIELDS[0],
        "diagnostic_fields": list(EXPECTED_FIELDS[1:]),
        "objective_dependencies": sorted(first_names),
        "optimizer_score_calls": score_calls,
        "optimizer_zero_index_reads": score_zero_reads,
        "one_factor_source_contract": True,
        "promotion_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = verify_source(args.source)
    except (OSError, SourceContractError) as exc:
        print(f"source contract error: {exc}", file=__import__("sys").stderr)
        return 2
    payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
