#!/usr/bin/env python3
"""Fail closed if a V4 recomposition drops a landed key or its runtime plumbing.

The current PR's ``apply_v4.KEYS`` is compared with the target branch copy supplied
by CI. Every key already present on the target must survive. The candidate is then
materialised through the real V3/V4 build recipe. Every head key must retain complete
runtime plumbing; keys newly introduced relative to the target must additionally
source-land default-OFF. R04 keys must retain their router flag, install
parameter/setter, a reachable production read (or a proven install-time callable
selector), and TitanAgent install wiring.

The checker deliberately does *not* prescribe where an R04 key must act. V4 contains
legitimate inner, outer/final-action, inline repairs, and install-selected wrappers;
monotonic plumbing should protect those seams without forcing every key through one
helper-import pattern.

This checker intentionally derives the contract from the moving target branch rather
than maintaining a second key ledger.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Iterable

import build_v3

HERE = Path(__file__).resolve().parent
APPLY_V4 = HERE / "apply_v4.py"


def _literal_keys(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    value = None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "KEYS" for target in node.targets):
            value = ast.literal_eval(node.value)
            break
    assert isinstance(value, (tuple, list)), f"{path}: KEYS must be a literal tuple/list"
    keys = tuple(value)
    assert keys, f"{path}: KEYS must not be empty"
    assert all(type(key) is str and key for key in keys), f"{path}: KEYS must contain nonempty strings"
    assert len(keys) == len(set(keys)), f"{path}: KEYS contains duplicates"
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
    raise AssertionError("materialized titan_runtime.py has no Features class")


def _contains_feature_ref(node: ast.AST, key: str) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Attribute) or child.attr != key:
            continue
        owner = child.value
        if (isinstance(owner, ast.Attribute) and owner.attr == "features"
                and isinstance(owner.value, ast.Name) and owner.value.id == "self"):
            return True
    return False


def _runtime_install_wired(tree: ast.AST, key: str, suffix: str) -> bool:
    for node in ast.walk(tree):
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
    raise AssertionError(f"materialized r04_full_router.py has no {name}()")


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


def _top_level_function_bindings(router_tree: ast.AST) -> dict[str, ast.AST]:
    """Approximate final module bindings for top-level functions and aliases.

    R04 builds its policy as a chain of repeated ``agent`` definitions captured into
    stable ``*_PARENT`` aliases before the name is rebound. Walking the top-level
    statements in execution order preserves those captures well enough to distinguish
    a function that participates in the final production chain from an unreferenced
    helper that merely happens to mention a feature flag.
    """
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
    """Return top-level function objects reachable from the installed ``v3_agent``.

    Name loads in a function are resolved through final module bindings. Captured
    wrapper aliases (``_FOO_PARENT = agent``) retain the specific earlier function
    object because the sequential binding pass records the alias before ``agent`` is
    rebound. This is a structural reachability proof, not semantic execution, but it
    rejects a dead helper that has no path from the runtime entry point.
    """
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
    """Return one production-reachable function that reads ``flag``."""
    for function in _production_function_nodes(router_tree):
        if _loads_name(function, flag):
            return getattr(function, "name", "<anonymous>")
    return None


def _install_selects_callable_on_flag(install: ast.FunctionDef, flag: str) -> bool:
    """Accept a flag consumed by install only when it selects a non-baseline callable.

    Setter-only reads/stores do not count. A legitimate outer wrapper may instead be
    constructed/cached in ``install()`` and returned as the runtime agent (for example
    a hidden-hand observation wrapper). In that case the flag itself appears in an
    ``if`` test and the guarded branch returns a callable other than bare ``v3_agent``.
    """
    for node in ast.walk(install):
        if not isinstance(node, ast.If) or not _loads_name(node.test, flag):
            continue
        for statement in node.body:
            for child in ast.walk(statement):
                if not isinstance(child, ast.Return) or child.value is None:
                    continue
                if isinstance(child.value, ast.Name) and child.value.id == "v3_agent":
                    continue
                return True
    return False


def _assert_r04_router_contract(
    router_tree: ast.AST,
    runtime_tree: ast.AST,
    key: str,
    *,
    require_default_off: bool,
) -> None:
    suffix = key.removeprefix("r04_")
    flag = suffix.upper()

    router_defaults = _top_level_bool_names(router_tree)
    assert flag in router_defaults, f"{key}: router {flag} must be a literal boolean"
    if require_default_off:
        assert router_defaults[flag] is False, f"{key}: newly landed router {flag} must source-land False"

    install = _find_function(router_tree, "install")
    install_args = {arg.arg for arg in (*install.args.posonlyargs, *install.args.args, *install.args.kwonlyargs)}
    assert suffix in install_args, f"{key}: router install() missing {suffix} parameter"
    assert flag in _global_names(install), f"{key}: router install() does not declare {flag} global"
    assert any(isinstance(node, ast.Name) and node.id == flag and isinstance(node.ctx, ast.Store)
               for node in ast.walk(install)), f"{key}: router install() never sets {flag}"

    reader = _router_flag_reader(router_tree, flag)
    install_selector = _install_selects_callable_on_flag(install, flag)
    assert reader is not None or install_selector, (
        f"{key}: router flag {flag} is neither read on the production v3_agent chain "
        "nor used by install() to select a non-baseline runtime callable"
    )

    assert _runtime_install_wired(runtime_tree, key, suffix), (
        f"{key}: TitanAgent does not pass self.features.{key} to router install({suffix}=...)"
    )


def check(base_apply_v4: Path) -> None:
    base_keys = _literal_keys(base_apply_v4)
    head_keys = _literal_keys(APPLY_V4)
    base_key_set = set(base_keys)
    removed = sorted(base_key_set - set(head_keys))
    assert not removed, "V4 recomposition removed already-landed key(s): " + ", ".join(removed)
    new_keys = set(head_keys) - base_key_set

    files = build_v3.package_files()
    for required in ("TITAN-CONFIG.json", "titan_runtime.py", "r04_full_router.py"):
        assert required in files, f"materialized package missing {required}"

    config = json.loads(files["TITAN-CONFIG.json"].decode("utf-8"))
    runtime_tree = ast.parse(files["titan_runtime.py"].decode("utf-8"), filename="titan_runtime.py")
    router_tree = ast.parse(files["r04_full_router.py"].decode("utf-8"), filename="r04_full_router.py")
    feature_defaults = _feature_defaults(runtime_tree)

    for key in head_keys:
        assert key in config, f"{key}: missing from materialized TITAN-CONFIG.json"
        assert type(config[key]) is bool, f"{key}: materialized config value must be boolean"
        assert key in feature_defaults, f"{key}: missing from materialized Features"
        assert type(feature_defaults[key]) is bool, f"{key}: Features default must be boolean"
        if key in new_keys:
            assert config[key] is False, f"{key}: new source landing must remain default-OFF"
            assert feature_defaults[key] is False, f"{key}: new Features default must remain False"
        assert _contains_feature_ref(runtime_tree, key), f"{key}: TitanAgent never references self.features.{key}"
        if key.startswith("r04_"):
            _assert_r04_router_contract(
                router_tree,
                runtime_tree,
                key,
                require_default_off=key in new_keys,
            )

    print("V4 PLUMBING OK", "base", list(base_keys), "head", list(head_keys))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-apply-v4", type=Path, required=True)
    args = parser.parse_args()
    check(args.base_apply_v4)


if __name__ == "__main__":
    main()
