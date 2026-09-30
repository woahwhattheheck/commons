#!/usr/bin/env python3
"""Source-bound census for zero-age non-ongoing crop harvest economics.

Research only. This module does not install policy or modify TITAN runtime state.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
from typing import Any

EXPECTED_ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
LAST_STEP = 718
CYCLE_CALLBACKS = 4  # PLANT -> HARVEST -> DROP(+SELL) -> DIG


def git_blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _safe_literal(node: ast.AST, env: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name) and node.id in env:
        return env[node.id]
    if isinstance(node, ast.Dict):
        return {_safe_literal(k, env): _safe_literal(v, env) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.List):
        return [_safe_literal(v, env) for v in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_safe_literal(v, env) for v in node.elts)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_safe_literal(node.operand, env)
    raise ValueError(f"non-literal source expression: {ast.dump(node, include_attributes=False)}")


def _assignment(tree: ast.Module, name: str) -> Any:
    env: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        target = node.targets[0].id
        try:
            value = _safe_literal(node.value, env)
        except ValueError:
            continue
        env[target] = value
        if target == name:
            return value
    raise ValueError(f"missing literal assignment: {name}")


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise ValueError(f"missing function: {name}")


def _op_branch(fn: ast.FunctionDef, opname: str) -> ast.If:
    for node in ast.walk(fn):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not isinstance(test, ast.Compare) or len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
            continue
        left = test.left
        right = test.comparators[0]
        if isinstance(left, ast.Name) and left.id == "op" and isinstance(right, ast.Constant) and right.value == opname:
            return node
    raise ValueError(f"missing op branch: {opname}")


def _dict_value(return_node: ast.Return, key: str) -> ast.AST:
    if not isinstance(return_node.value, ast.Dict):
        raise ValueError("expected dict return")
    for k, v in zip(return_node.value.keys, return_node.value.values):
        if isinstance(k, ast.Constant) and k.value == key:
            return v
    raise ValueError(f"missing returned key: {key}")


def _initial_yield_contract(tree: ast.Module) -> None:
    fn = _function(tree, "_new_plant")
    returns = [n for n in ast.walk(fn) if isinstance(n, ast.Return)]
    if len(returns) != 1:
        raise ValueError("_new_plant return topology drift")
    value = _dict_value(returns[0], "yield_units")
    if not isinstance(value, ast.IfExp):
        raise ValueError("yield_units no longer conditional")
    if not (isinstance(value.body, ast.Constant) and value.body.value == 0):
        raise ValueError("ongoing initial yield drift")
    if not (isinstance(value.orelse, ast.Constant) and value.orelse.value == 1):
        raise ValueError("non-ongoing initial yield is not one")
    test = value.test
    if not (
        isinstance(test, ast.Subscript)
        and isinstance(test.value, ast.Name)
        and test.value.id == "cd"
        and isinstance(test.slice, ast.Constant)
        and test.slice.value == "ongoing"
    ):
        raise ValueError("yield_units condition drift")


def _harvest_contract(tree: ast.Module) -> None:
    branch = _op_branch(_function(tree, "_apply_unit_action"), "HARVEST")
    dumped = ast.dump(ast.Module(body=branch.body, type_ignores=[]), include_attributes=False)
    for forbidden in ("planted_day", "first_yield_day", "max_yield_day"):
        if forbidden in dumped:
            raise ValueError(f"HARVEST gained age gate: {forbidden}")
    if "_inv_add" not in dumped or "yield_units" not in dumped or "crop" not in dumped:
        raise ValueError("HARVEST crop transfer contract drift")


def _dig_contract(tree: ast.Module) -> None:
    branch = _op_branch(_function(tree, "_apply_unit_action"), "DIG")
    dumped = ast.dump(ast.Module(body=branch.body, type_ignores=[]), include_attributes=False)
    if "animal" not in dumped or "tiles" not in dumped:
        raise ValueError("DIG replacement contract drift")
    if "Constant(value=None)" not in dumped:
        raise ValueError("DIG no longer clears non-animal tile to None")


def _unit_before_market_contract(tree: ast.Module) -> str:
    """Return the interpreter-like function proving unit actions precede market."""
    for fn in (n for n in tree.body if isinstance(n, ast.FunctionDef)):
        unit_idx = market_idx = None
        for idx, stmt in enumerate(fn.body):
            calls = [n for n in ast.walk(stmt) if isinstance(n, ast.Call)]
            names = {c.func.id for c in calls if isinstance(c.func, ast.Name)}
            if "_apply_unit_action" in names and unit_idx is None:
                unit_idx = idx
            if "_process_market" in names and market_idx is None:
                market_idx = idx
        if unit_idx is not None and market_idx is not None:
            if unit_idx >= market_idx:
                raise ValueError("market now resolves before unit actions")
            return fn.name
    raise ValueError("could not bind unit-before-market ordering")


def _shape(func: str, x: float, T: float) -> float:
    x = max(0.0, x)
    if func == "linear":
        return x
    if func == "sq":
        return x * x
    if func == "sqrt":
        return math.sqrt(x)
    if func == "log":
        return math.log(1.0 + x)
    if func == "log10":
        return math.log10(1.0 + x)
    if func == "hinge":
        u = x / T
        return u + 8.0 * max(0.0, u - 1.0) ** 2
    raise ValueError(f"unsupported market shape: {func}")


def market_price(item: str, inventory: int, params: dict[str, dict[str, Any]]) -> int:
    p = params[item]
    base, I0, T = p["base"], p["I0"], p["T"]
    if inventory < I0:
        f, target = p["below_func"], p["below_target"]
        amp = target * base / _shape(f, T, T)
        value = base + amp * _shape(f, I0 - inventory, T)
    else:
        f, target = p["above_func"], p["above_target"]
        amp = target * base / _shape(f, T, T)
        value = base - amp * _shape(f, inventory - I0, T)
    return max(1, int(round(value)))


def analyze_engine_bytes(data: bytes) -> dict[str, Any]:
    blob = git_blob_id(data)
    if blob != EXPECTED_ENGINE_BLOB:
        raise ValueError(f"engine Git blob drift: {blob}")
    tree = ast.parse(data.decode("utf-8"))
    _initial_yield_contract(tree)
    _harvest_contract(tree)
    _dig_contract(tree)
    interpreter_fn = _unit_before_market_contract(tree)
    crops = _assignment(tree, "CROPS")
    market_params = _assignment(tree, "MARKET_PARAMS")

    candidates = [name for name, c in crops.items() if c.get("ongoing") is False]
    max_single_worker_cycles = LAST_STEP // CYCLE_CALLBACKS  # reserve step 0 for initial seed buy
    rows = []
    for crop in candidates:
        seed_cost = int(crops[crop]["seed"])
        I0 = int(market_params[crop]["I0"])
        profitable = 0
        profit = 0
        quote_path = []
        for sold in range(LAST_STEP + 1):
            quote = market_price(crop, I0 + sold, market_params)
            if sold < 12:
                quote_path.append(quote)
            if quote <= seed_cost:
                break
            profitable += 1
            if profitable <= max_single_worker_cycles:
                profit += quote - seed_cost
        executable_units = min(max_single_worker_cycles, profitable)
        rows.append({
            "crop": crop,
            "seed_cost": seed_cost,
            "base_price": market_price(crop, I0, market_params),
            "base_spread": market_price(crop, I0, market_params) - seed_cost,
            "profitable_consecutive_quotes_capped_719": profitable,
            "single_worker_cycle_cap": max_single_worker_cycles,
            "single_worker_profitable_units": executable_units,
            "market_only_gross_profit_at_cycle_cap": profit,
            "first_quotes": quote_path,
        })
    rows.sort(key=lambda r: (-r["market_only_gross_profit_at_cycle_cap"], r["crop"]))
    return {
        "schema": "titan-v4-sproutloop/v1",
        "decision_authority": False,
        "engine_git_blob": blob,
        "interpreter_function": interpreter_fn,
        "mechanism": {
            "non_ongoing_new_plant_initial_yield": 1,
            "harvest_age_gate": False,
            "unit_actions_resolve_before_market": True,
            "cycle": ["PLANT", "HARVEST", "DROP+SELL", "DIG"],
            "callbacks_per_unit": CYCLE_CALLBACKS,
            "step0_reserved_for_seed_buy": True,
        },
        "crops": rows,
        "limits": [
            "market-only arithmetic ignores rival sales, town consumption, weeds, travel, and opportunity cost",
            "single-worker cap assumes one owned shed-adjacent empty tile and pre-positioning",
            "research receipt is not native-current engagement, economics, default activation, or promotion evidence",
        ],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--engine", required=True)
    p.add_argument("--pretty", action="store_true")
    args = p.parse_args()
    report = analyze_engine_bytes(Path(args.engine).read_bytes())
    print(json.dumps(report, sort_keys=True, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
