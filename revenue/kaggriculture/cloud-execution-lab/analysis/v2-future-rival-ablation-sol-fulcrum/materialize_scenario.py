# SPDX-License-Identifier: Apache-2.0
"""AST/source contract for the exact two-scenario frozen-V2 ablation."""
from __future__ import annotations

import ast

from materialize_custody import (
    ABLATION_SCENARIOS,
    FUTURE_SCENARIO_BLOCK,
    MaterializeError,
    V2_SCENARIOS,
)

def _literal_scenario_name(node: ast.AST) -> str:
    if not isinstance(node, (ast.Tuple, ast.List)) or not node.elts:
        raise MaterializeError("scenario row is not a nonempty tuple/list")
    first = node.elts[0]
    if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
        raise MaterializeError("scenario name is not a literal string")
    return first.value


def scenario_names(source: str) -> tuple[str, ...]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise MaterializeError(f"scheduler does not parse: {exc}") from exc
    function = next(
        (node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "optimize_lot"),
        None,
    )
    if function is None:
        raise MaterializeError("scheduler lacks optimize_lot")

    names: list[str] | None = None
    for node in function.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "scenarios" for target in node.targets
        ):
            if names is not None or not isinstance(node.value, (ast.List, ast.Tuple)):
                raise MaterializeError("ambiguous scenarios initialization")
            names = [_literal_scenario_name(row) for row in node.value.elts]
        elif isinstance(node, ast.If):
            for child in node.body:
                if not isinstance(child, ast.Expr) or not isinstance(child.value, ast.Call):
                    continue
                call = child.value
                func = call.func
                if (
                    isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "scenarios"
                    and func.attr == "append"
                ):
                    if names is None or len(call.args) != 1 or call.keywords:
                        raise MaterializeError("malformed scenarios.append")
                    names.append(_literal_scenario_name(call.args[0]))
    if names is None:
        raise MaterializeError("scheduler lacks scenarios initialization")
    if len(names) != len(set(names)):
        raise MaterializeError(f"duplicate scenario names: {names}")
    return tuple(names)


def patch_scheduler(source: str) -> str:
    count = source.count(FUTURE_SCENARIO_BLOCK)
    if count != 1:
        raise MaterializeError(
            f"expected exactly one future-rival scenario block, found {count}"
        )
    if scenario_names(source) != V2_SCENARIOS:
        raise MaterializeError(
            f"unexpected frozen V2 scenario sequence: {scenario_names(source)}"
        )
    patched = source.replace(FUTURE_SCENARIO_BLOCK, "", 1)
    if FUTURE_SCENARIO_BLOCK in patched:
        raise MaterializeError("future-rival scenario block survived patch")
    if scenario_names(patched) != ABLATION_SCENARIOS:
        raise MaterializeError(
            f"unexpected ablation scenario sequence: {scenario_names(patched)}"
        )
    try:
        compile(patched, "scheduler.py", "exec")
    except SyntaxError as exc:
        raise MaterializeError(f"patched scheduler does not compile: {exc}") from exc
    return patched
