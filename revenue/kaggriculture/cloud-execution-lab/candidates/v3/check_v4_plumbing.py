#!/usr/bin/env python3
"""Fail closed if a V4 recomposition drops a landed key or its runtime plumbing.

The current PR's ``apply_v4.KEYS`` is compared with the target branch copy supplied
by CI. Every key already present on the target must survive. The candidate is then
materialised through the real V3/V4 build recipe. This guard intentionally treats
all current V4 keys as source-landed safety switches: every key must remain OFF in
TITAN-CONFIG, Features, and (for r04 keys) the router until a future promotion
changes this contract explicitly.

Runtime wiring checks are production-rooted. TitanAgent references are accepted only
from methods reachable from ``TitanAgent.act`` through ``self.<method>(...)`` calls;
a dead helper cannot satisfy the contract. Router flag reads are likewise rooted at
``v3_agent``. Failures use explicit exceptions so ``python -O`` cannot strip them.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Iterable, NoReturn

import build_v3

HERE = Path(__file__).resolve().parent
APPLY_V4 = HERE / "apply_v4.py"


def _fail(message: str) -> NoReturn:
    raise SystemExit(message)


def _require(cond: object, message: str) -> None:
    if not cond:
        _fail(message)


def _literal_keys(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    value = None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "KEYS" for target in node.targets):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                value = None
            break
    _require(isinstance(value, (tuple, list)), f"{path}: KEYS must be a literal tuple/list")
    keys = tuple(value)
    _require(keys, f"{path}: KEYS must not be empty")
    _require(all(type(key) is str and key for key in keys), f"{path}: KEYS must contain nonempty strings")
    _require(len(keys) == len(set(keys)), f"{path}: KEYS contains duplicates")
    return keys


def _feature_defaults(tree: ast.AST) -> dict[str, object]:
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.ClassDef) or node.name != "Features":
            continue
        defaults: dict[str, object] = {}
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.value is not None:
                try:
                    defaults[stmt.target.id] = ast.literal_eval(stmt.value)
                except (ValueError, TypeError):
                    pass
            elif isinstance(stmt, ast.Assign):
                try:
                    literal = ast.literal_eval(stmt.value)
                except (ValueError, TypeError):
                    continue
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        defaults[target.id] = literal
        return defaults
    _fail("materialized titan_runtime.py has no Features class")


def _titan_agent_class(tree: ast.AST) -> ast.ClassDef:
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.ClassDef) and node.name == "TitanAgent":
            return node
    _fail("materialized titan_runtime.py has no TitanAgent class")


def _contains_feature_ref(node: ast.AST, key: str) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Attribute) or child.attr != key:
            continue
        owner = child.value
        if (isinstance(owner, ast.Attribute) and owner.attr == "features"
                and isinstance(owner.value, ast.Name) and owner.value.id == "self"):
            return True
    return False


def _agent_methods(agent: ast.ClassDef) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {
        node.name: node
        for node in agent.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _reachable_agent_methods(agent: ast.ClassDef) -> set[ast.AST]:
    """Methods reachable from production ``act`` via direct ``self.method()`` calls."""
    methods = _agent_methods(agent)
    root = methods.get("act")
    _require(root is not None, "materialized TitanAgent has no act() production root")
    reachable: set[ast.AST] = set()
    stack: list[ast.AST] = [root]
    while stack:
        method = stack.pop()
        if method in reachable:
            continue
        reachable.add(method)
        for node in ast.walk(method):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "self"):
                continue
            target = methods.get(func.attr)
            if target is not None and target not in reachable:
                stack.append(target)
    return reachable


def _reachable_feature_ref(methods: set[ast.AST], key: str) -> bool:
    return any(_contains_feature_ref(method, key) for method in methods)


def _runtime_install_wired(methods: set[ast.AST], key: str, suffix: str) -> bool:
    for method in methods:
        for node in ast.walk(method):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not ((isinstance(func, ast.Attribute) and func.attr == "install")
                    or (isinstance(func, ast.Name) and func.id == "install")):
                continue
            for keyword in node.keywords:
                if keyword.arg == suffix and _contains_feature_ref(keyword.value, key):
                    return True
    return False


def _top_level_bool_names(tree: ast.AST) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for node in getattr(tree, "body", []):
        targets: Iterable[ast.AST]
        value = None
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = (node.target,)
            value = node.value
        else:
            continue
        if not (isinstance(value, ast.Constant) and type(value.value) is bool):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                out[target.id] = value.value
    return out


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    _fail(f"materialized r04_full_router.py has no {name}()")


def _global_names(function: ast.FunctionDef) -> set[str]:
    return {
        name
        for node in ast.walk(function)
        if isinstance(node, ast.Global)
        for name in node.names
    }


def _loads_name(node: ast.AST, name: str) -> bool:
    return any(
        isinstance(child, ast.Name)
        and child.id == name
        and isinstance(child.ctx, ast.Load)
        for child in ast.walk(node)
    )


def _direct_body_nodes(function: ast.AST) -> list[ast.AST]:
    """Nodes in *function* excluding nested function/class/lambda bodies."""
    skip: set[int] = set()
    for child in ast.walk(function):
        if child is function:
            continue
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            for nested in ast.walk(child):
                if nested is not child:
                    skip.add(id(nested))
    return [child for child in ast.walk(function) if id(child) not in skip]


def _top_level_function_bindings(router_tree: ast.AST) -> dict[str, ast.AST]:
    bindings: dict[str, ast.AST] = {}
    for node in getattr(router_tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bindings[node.name] = node
            continue
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name):
            source = bindings.get(node.value.id)
            if source is not None:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        bindings[target.id] = source
            continue
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and isinstance(node.value, ast.Name):
            source = bindings.get(node.value.id)
            if source is not None:
                bindings[node.target.id] = source
            continue
        if isinstance(node, ast.Delete):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bindings.pop(target.id, None)
    return bindings


def _production_function_nodes(router_tree: ast.AST) -> set[ast.AST]:
    bindings = _top_level_function_bindings(router_tree)
    root = bindings.get("v3_agent")
    if root is None:
        return set()
    reachable: set[ast.AST] = set()
    stack = [root]
    while stack:
        function = stack.pop()
        if function in reachable:
            continue
        reachable.add(function)
        for child in ast.walk(function):
            if not isinstance(child, ast.Name) or not isinstance(child.ctx, ast.Load):
                continue
            target = bindings.get(child.id)
            if target is not None and target not in reachable:
                stack.append(target)
    return reachable


def _router_flag_reader(router_tree: ast.AST, flag: str) -> str | None:
    for function in _production_function_nodes(router_tree):
        if _loads_name(function, flag):
            return getattr(function, "name", "<anonymous>")
    return None


def _install_selects_callable_on_flag(install: ast.FunctionDef, flag: str) -> bool:
    for node in _direct_body_nodes(install):
        if not isinstance(node, ast.If) or not _loads_name(node.test, flag):
            continue
        for statement in node.body:
            for child in _direct_body_nodes(statement):
                if not isinstance(child, ast.Return) or child.value is None:
                    continue
                if isinstance(child.value, ast.Name) and child.value.id == "v3_agent":
                    continue
                return True
    return False


def _assert_r04_router_contract(
    router_tree: ast.AST,
    reachable_agent: set[ast.AST],
    key: str,
) -> None:
    suffix = key.removeprefix("r04_")
    flag = suffix.upper()

    router_defaults = _top_level_bool_names(router_tree)
    _require(flag in router_defaults, f"{key}: router {flag} must be a literal boolean")
    _require(router_defaults[flag] is False, f"{key}: V4 router {flag} must remain source-default False")

    install = _find_function(router_tree, "install")
    install_args = {arg.arg for arg in (*install.args.posonlyargs, *install.args.args, *install.args.kwonlyargs)}
    _require(suffix in install_args, f"{key}: router install() missing {suffix} parameter")
    _require(flag in _global_names(install), f"{key}: router install() does not declare {flag} global")
    _require(
        any(isinstance(node, ast.Name) and node.id == flag and isinstance(node.ctx, ast.Store)
            for node in ast.walk(install)),
        f"{key}: router install() never sets {flag}",
    )

    reader = _router_flag_reader(router_tree, flag)
    install_selector = _install_selects_callable_on_flag(install, flag)
    _require(
        reader is not None or install_selector,
        f"{key}: router flag {flag} is neither read on the production v3_agent chain "
        "nor used by install() to select a non-baseline runtime callable",
    )
    _require(
        _runtime_install_wired(reachable_agent, key, suffix),
        f"{key}: production-reachable TitanAgent does not pass self.features.{key} "
        f"to router install({suffix}=...)",
    )


def check(base_apply_v4: Path) -> None:
    base_keys = _literal_keys(base_apply_v4)
    head_keys = _literal_keys(APPLY_V4)
    removed = sorted(set(base_keys) - set(head_keys))
    _require(not removed, "V4 recomposition removed already-landed key(s): " + ", ".join(removed))

    files = build_v3.package_files()
    for required in ("TITAN-CONFIG.json", "titan_runtime.py", "r04_full_router.py"):
        _require(required in files, f"materialized package missing {required}")

    config = json.loads(files["TITAN-CONFIG.json"].decode("utf-8"))
    runtime_tree = ast.parse(files["titan_runtime.py"].decode("utf-8"), filename="titan_runtime.py")
    router_tree = ast.parse(files["r04_full_router.py"].decode("utf-8"), filename="r04_full_router.py")
    feature_defaults = _feature_defaults(runtime_tree)
    agent = _titan_agent_class(runtime_tree)
    reachable_agent = _reachable_agent_methods(agent)

    for key in head_keys:
        _require(key in config, f"{key}: missing from materialized TITAN-CONFIG.json")
        _require(type(config[key]) is bool, f"{key}: materialized config value must be boolean")
        _require(config[key] is False, f"{key}: V4 config default must remain False")
        _require(key in feature_defaults, f"{key}: missing from materialized Features")
        _require(type(feature_defaults[key]) is bool, f"{key}: Features default must be boolean")
        _require(feature_defaults[key] is False, f"{key}: V4 Features default must remain False")
        _require(
            _reachable_feature_ref(reachable_agent, key),
            f"{key}: production-reachable TitanAgent never references self.features.{key}",
        )
        if key.startswith("r04_"):
            _assert_r04_router_contract(router_tree, reachable_agent, key)

    print(
        "V4 PLUMBING OK",
        "base", list(base_keys),
        "head", list(head_keys),
        "reachable_agent_methods", sorted(getattr(node, "name", "<anonymous>") for node in reachable_agent),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-apply-v4", type=Path, required=True)
    args = parser.parse_args()
    check(args.base_apply_v4)


if __name__ == "__main__":
    main()
