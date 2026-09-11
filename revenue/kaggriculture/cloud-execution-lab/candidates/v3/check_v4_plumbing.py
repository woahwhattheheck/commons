#!/usr/bin/env python3
"""Fail closed if a V4 recomposition drops a landed key or its runtime plumbing.

The current PR's ``apply_v4.KEYS`` is compared with the target branch copy supplied
by CI.  Every key already present on the target must survive.  The candidate is then
materialised through the real V3/V4 build recipe and each head key is required to be
present in config and ``Features`` with a default-OFF source landing.  R04 keys also
must retain their router flag, install parameter/setter, stack seam, and TitanAgent
install wiring.

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


def _top_level_false_names(tree: ast.AST) -> set[str]:
    out: set[str] = set()
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
        if not (isinstance(value, ast.Constant) and value.value is False):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                out.add(target.id)
    return out


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"materialized r04_full_router.py has no {name}()")


def _assert_r04_router_contract(router_tree: ast.AST, runtime_tree: ast.AST, key: str) -> None:
    suffix = key.removeprefix("r04_")
    flag = suffix.upper()
    module = "r04_" + suffix

    assert flag in _top_level_false_names(router_tree), f"{key}: router {flag} must source-land False"

    install = _find_function(router_tree, "install")
    install_args = {arg.arg for arg in (*install.args.posonlyargs, *install.args.args, *install.args.kwonlyargs)}
    assert suffix in install_args, f"{key}: router install() missing {suffix} parameter"
    assert any(isinstance(node, ast.Name) and node.id == flag and isinstance(node.ctx, ast.Store)
               for node in ast.walk(install)), f"{key}: router install() never sets {flag}"

    stack = _find_function(router_tree, "_v3_stack")
    assert any(isinstance(node, ast.Name) and node.id == flag and isinstance(node.ctx, ast.Load)
               for node in ast.walk(stack)), f"{key}: _v3_stack() never reads {flag}"
    assert any(isinstance(node, ast.Import)
               and any(alias.name == module for alias in node.names)
               for node in ast.walk(stack)), f"{key}: _v3_stack() never imports {module}"

    assert _runtime_install_wired(runtime_tree, key, suffix), (
        f"{key}: TitanAgent does not pass self.features.{key} to router install({suffix}=...)"
    )


def check(base_apply_v4: Path) -> None:
    base_keys = _literal_keys(base_apply_v4)
    head_keys = _literal_keys(APPLY_V4)
    removed = sorted(set(base_keys) - set(head_keys))
    assert not removed, "V4 recomposition removed already-landed key(s): " + ", ".join(removed)

    files = build_v3.package_files()
    for required in ("TITAN-CONFIG.json", "titan_runtime.py", "r04_full_router.py"):
        assert required in files, f"materialized package missing {required}"

    config = json.loads(files["TITAN-CONFIG.json"].decode("utf-8"))
    runtime_tree = ast.parse(files["titan_runtime.py"].decode("utf-8"), filename="titan_runtime.py")
    router_tree = ast.parse(files["r04_full_router.py"].decode("utf-8"), filename="r04_full_router.py")
    feature_defaults = _feature_defaults(runtime_tree)

    for key in head_keys:
        assert key in config, f"{key}: missing from materialized TITAN-CONFIG.json"
        assert config[key] is False, f"{key}: source landing must remain default-OFF"
        assert key in feature_defaults, f"{key}: missing from materialized Features"
        assert feature_defaults[key] is False, f"{key}: Features default must remain False"
        assert _contains_feature_ref(runtime_tree, key), f"{key}: TitanAgent never references self.features.{key}"
        if key.startswith("r04_"):
            _assert_r04_router_contract(router_tree, runtime_tree, key)

    print("V4 PLUMBING OK", "base", list(base_keys), "head", list(head_keys))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-apply-v4", type=Path, required=True)
    args = parser.parse_args()
    check(args.base_apply_v4)


if __name__ == "__main__":
    main()
