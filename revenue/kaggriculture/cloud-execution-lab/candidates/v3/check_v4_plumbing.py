#!/usr/bin/env python3
"""Fail closed if a V4 recomposition drops a landed key or its runtime plumbing.

The current PR's ``apply_v4.KEYS`` is compared with the target branch copy supplied
by CI. Every key already present on the target must survive. The candidate is then
materialised through the real V3/V4 build recipe. Every head key must retain complete
runtime plumbing and source-land default-OFF. R04 keys must retain their router flag,
install parameter/setter, a reachable production read (or a proven install-time
callable selector), and TitanAgent install wiring reachable from ``TitanAgent.act``.

Reachability checks deliberately ignore nested scopes and statically dead branches.
Top-level router bindings are processed in source order so a later non-function or
non-boolean reassignment invalidates an earlier trusted binding instead of leaving a
stale proof behind.

Failures use explicit exceptions so ``python -O`` cannot strip the contract.
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

_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def _fail(message: str) -> NoReturn:
    raise SystemExit(message)


def _require(cond: object, message: str) -> None:
    if not cond:
        _fail(message)


def _static_truth(node: ast.AST) -> bool | None:
    """Return the compile-time truth of a literal expression, else unknown."""
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError):
        return None
    try:
        return bool(value)
    except Exception:
        return None


def _visit_live(node: ast.AST, out: list[ast.AST]) -> None:
    """Collect executable descendants, stopping at nested scopes/dead literals."""
    if isinstance(node, _SCOPE_NODES):
        return

    out.append(node)

    if isinstance(node, ast.If):
        _visit_live(node.test, out)
        truth = _static_truth(node.test)
        if truth is True:
            branches = node.body
        elif truth is False:
            branches = node.orelse
        else:
            branches = (*node.body, *node.orelse)
        for child in branches:
            _visit_live(child, out)
        return

    if isinstance(node, ast.IfExp):
        _visit_live(node.test, out)
        truth = _static_truth(node.test)
        if truth is True:
            _visit_live(node.body, out)
        elif truth is False:
            _visit_live(node.orelse, out)
        else:
            _visit_live(node.body, out)
            _visit_live(node.orelse, out)
        return

    if isinstance(node, ast.While):
        _visit_live(node.test, out)
        truth = _static_truth(node.test)
        if truth is False:
            for child in node.orelse:
                _visit_live(child, out)
        else:
            for child in node.body:
                _visit_live(child, out)
            for child in node.orelse:
                _visit_live(child, out)
        return

    if isinstance(node, ast.BoolOp):
        is_and = isinstance(node.op, ast.And)
        is_or = isinstance(node.op, ast.Or)
        for value in node.values:
            _visit_live(value, out)
            truth = _static_truth(value)
            if (is_and and truth is False) or (is_or and truth is True):
                break
        return

    for child in ast.iter_child_nodes(node):
        _visit_live(child, out)


def _live_subtree_nodes(node: ast.AST) -> list[ast.AST]:
    out: list[ast.AST] = []
    _visit_live(node, out)
    return out


def _direct_body_nodes(function: ast.AST) -> list[ast.AST]:
    """Executable nodes in a function, excluding nested scopes/dead branches."""
    out: list[ast.AST] = []
    for statement in getattr(function, "body", []):
        _visit_live(statement, out)
    return out


def _literal_keys(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    value: object = None
    seen = False
    for node in tree.body:
        targets: tuple[ast.AST, ...] = ()
        assigned: ast.AST | None = None
        if isinstance(node, ast.Assign):
            targets = tuple(node.targets)
            assigned = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = (node.target,)
            assigned = node.value
        elif isinstance(node, ast.AugAssign):
            targets = (node.target,)
        elif isinstance(node, ast.Delete):
            targets = tuple(node.targets)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == "KEYS":
                seen = True
                value = None
            continue
        else:
            continue

        if not any(isinstance(target, ast.Name) and target.id == "KEYS" for target in targets):
            continue
        seen = True
        if assigned is None:
            value = None
            continue
        try:
            value = ast.literal_eval(assigned)
        except (ValueError, TypeError):
            value = None

    _require(seen and isinstance(value, (tuple, list)), f"{path}: KEYS must be a literal tuple/list")
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
            targets: tuple[ast.AST, ...] = ()
            value: ast.AST | None = None
            if isinstance(stmt, ast.AnnAssign):
                targets = (stmt.target,)
                value = stmt.value
            elif isinstance(stmt, ast.Assign):
                targets = tuple(stmt.targets)
                value = stmt.value
            elif isinstance(stmt, ast.AugAssign):
                targets = (stmt.target,)
            elif isinstance(stmt, ast.Delete):
                targets = tuple(stmt.targets)
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defaults.pop(stmt.name, None)
                continue
            else:
                continue

            names = [target.id for target in targets if isinstance(target, ast.Name)]
            if value is None:
                for name in names:
                    defaults.pop(name, None)
                continue
            try:
                literal = ast.literal_eval(value)
            except (ValueError, TypeError):
                for name in names:
                    defaults.pop(name, None)
                continue
            for name in names:
                defaults[name] = literal
        return defaults
    _fail("materialized titan_runtime.py has no Features class")


def _titan_agent_class(tree: ast.AST) -> ast.ClassDef:
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.ClassDef) and node.name == "TitanAgent":
            return node
    _fail("materialized titan_runtime.py has no TitanAgent class")


def _contains_feature_ref(node: ast.AST, key: str) -> bool:
    for child in _live_subtree_nodes(node):
        if not isinstance(child, ast.Attribute) or child.attr != key:
            continue
        owner = child.value
        if (
            isinstance(owner, ast.Attribute)
            and owner.attr == "features"
            and isinstance(owner.value, ast.Name)
            and owner.value.id == "self"
        ):
            return True
    return False


def _agent_methods(agent: ast.ClassDef) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {
        node.name: node
        for node in agent.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _reachable_agent_methods(agent: ast.ClassDef) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
    """Return TitanAgent methods reachable from act via direct live self.method calls."""
    methods = _agent_methods(agent)
    root = methods.get("act")
    _require(root is not None, "materialized TitanAgent has no act() method")
    reachable: set[ast.FunctionDef | ast.AsyncFunctionDef] = set()
    stack = [root]
    while stack:
        function = stack.pop()
        if function in reachable:
            continue
        reachable.add(function)
        for node in _direct_body_nodes(function):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "self"
            ):
                continue
            target = methods.get(func.attr)
            if target is not None and target not in reachable:
                stack.append(target)
    return tuple(reachable)


def _reachable_agent_feature_ref(
    reachable: Iterable[ast.FunctionDef | ast.AsyncFunctionDef], key: str
) -> bool:
    for function in reachable:
        for child in _direct_body_nodes(function):
            if not isinstance(child, ast.Attribute) or child.attr != key:
                continue
            owner = child.value
            if (
                isinstance(owner, ast.Attribute)
                and owner.attr == "features"
                and isinstance(owner.value, ast.Name)
                and owner.value.id == "self"
            ):
                return True
    return False


def _runtime_install_wired(
    reachable: Iterable[ast.FunctionDef | ast.AsyncFunctionDef], key: str, suffix: str
) -> bool:
    for function in reachable:
        for node in _direct_body_nodes(function):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                (isinstance(func, ast.Attribute) and func.attr == "install")
                or (isinstance(func, ast.Name) and func.id == "install")
            ):
                continue
            for keyword in node.keywords:
                if keyword.arg == suffix and _contains_feature_ref(keyword.value, key):
                    return True
    return False


def _top_level_bool_names(tree: ast.AST) -> dict[str, bool]:
    """Track trusted literal bool bindings; later nonliteral rebinds invalidate them."""
    out: dict[str, bool] = {}
    for node in getattr(tree, "body", []):
        targets: tuple[ast.AST, ...] = ()
        value: ast.AST | None = None
        if isinstance(node, ast.Assign):
            targets = tuple(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = (node.target,)
            value = node.value
        elif isinstance(node, ast.AugAssign):
            targets = (node.target,)
        elif isinstance(node, ast.Delete):
            targets = tuple(node.targets)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.pop(node.name, None)
            continue
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            aliases = node.names
            for alias in aliases:
                bound = alias.asname or alias.name.split(".", 1)[0]
                out.pop(bound, None)
            continue
        else:
            continue

        names = [target.id for target in targets if isinstance(target, ast.Name)]
        literal_bool = (
            value.value
            if isinstance(value, ast.Constant) and type(value.value) is bool
            else None
        )
        for name in names:
            if literal_bool is None:
                out.pop(name, None)
            else:
                out[name] = literal_bool
    return out


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef:
    found: ast.FunctionDef | None = None
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            found = node
        elif isinstance(node, (ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
            found = None
        elif isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                found = None
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            found = None
        elif isinstance(node, ast.Delete):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                found = None
    if found is not None:
        return found
    _fail(f"materialized r04_full_router.py has no live top-level {name}()")


def _global_names(function: ast.FunctionDef) -> set[str]:
    return {
        name
        for node in _direct_body_nodes(function)
        if isinstance(node, ast.Global)
        for name in node.names
    }


def _stores_name(function: ast.FunctionDef, name: str) -> bool:
    return any(
        isinstance(node, ast.Name)
        and node.id == name
        and isinstance(node.ctx, ast.Store)
        for node in _direct_body_nodes(function)
    )


def _loads_name(node: ast.AST, name: str) -> bool:
    return any(
        isinstance(child, ast.Name)
        and child.id == name
        and isinstance(child.ctx, ast.Load)
        for child in _live_subtree_nodes(node)
    )


def _top_level_function_bindings(router_tree: ast.AST) -> dict[str, ast.AST]:
    """Resolve simple top-level function aliases, invalidating later unknown rebinds."""
    bindings: dict[str, ast.AST] = {}
    for node in getattr(router_tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bindings[node.name] = node
            continue
        if isinstance(node, ast.ClassDef):
            bindings.pop(node.name, None)
            continue
        if isinstance(node, ast.Assign):
            source = bindings.get(node.value.id) if isinstance(node.value, ast.Name) else None
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    continue
                if source is None:
                    bindings.pop(target.id, None)
                else:
                    bindings[target.id] = source
            continue
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            source = bindings.get(node.value.id) if isinstance(node.value, ast.Name) else None
            if source is None:
                bindings.pop(node.target.id, None)
            else:
                bindings[node.target.id] = source
            continue
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            bindings.pop(node.target.id, None)
            continue
        if isinstance(node, ast.Delete):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bindings.pop(target.id, None)
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".", 1)[0]
                bindings.pop(bound, None)
    return bindings


def _production_function_nodes(router_tree: ast.AST) -> set[ast.AST]:
    """Return top-level router functions actually invoked from live ``v3_agent`` code."""
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
        for child in _direct_body_nodes(function):
            if not isinstance(child, ast.Call) or not isinstance(child.func, ast.Name):
                continue
            target = bindings.get(child.func.id)
            if target is not None and target not in reachable:
                stack.append(target)
    return reachable


def _router_flag_reader(router_tree: ast.AST, flag: str) -> str | None:
    for function in _production_function_nodes(router_tree):
        if any(
            isinstance(child, ast.Name)
            and child.id == flag
            and isinstance(child.ctx, ast.Load)
            for child in _direct_body_nodes(function)
        ):
            return getattr(function, "name", "<anonymous>")
    return None


def _install_selects_callable_on_flag(install: ast.FunctionDef, flag: str) -> bool:
    for node in _direct_body_nodes(install):
        if not isinstance(node, ast.If) or not _loads_name(node.test, flag):
            continue
        for statement in node.body:
            for child in _live_subtree_nodes(statement):
                if not isinstance(child, ast.Return) or child.value is None:
                    continue
                if isinstance(child.value, ast.Name) and child.value.id == "v3_agent":
                    continue
                return True
    return False


def _assert_r04_router_contract(
    router_tree: ast.AST,
    reachable_agent: Iterable[ast.FunctionDef | ast.AsyncFunctionDef],
    key: str,
) -> None:
    suffix = key.removeprefix("r04_")
    flag = suffix.upper()

    router_defaults = _top_level_bool_names(router_tree)
    _require(flag in router_defaults, f"{key}: router {flag} must be a live literal boolean")
    _require(router_defaults[flag] is False, f"{key}: router {flag} must source-land False")

    install = _find_function(router_tree, "install")
    install_args = {
        arg.arg
        for arg in (*install.args.posonlyargs, *install.args.args, *install.args.kwonlyargs)
    }
    _require(suffix in install_args, f"{key}: router install() missing {suffix} parameter")
    _require(flag in _global_names(install), f"{key}: router install() does not directly declare {flag} global")
    _require(
        _stores_name(install, flag),
        f"{key}: router install() never live-sets {flag} outside nested/dead scope",
    )

    reader = _router_flag_reader(router_tree, flag)
    install_selector = _install_selects_callable_on_flag(install, flag)
    _require(
        reader is not None or install_selector,
        f"{key}: router flag {flag} is neither read on the live production v3_agent chain "
        "nor used by install() to select a non-baseline runtime callable",
    )
    _require(
        _runtime_install_wired(reachable_agent, key, suffix),
        f"{key}: TitanAgent.act chain does not pass self.features.{key} "
        f"to router install({suffix}=...)",
    )


def _self_test_agent_reachability() -> None:
    live_tree = ast.parse(
        """
class TitanAgent:
    def act(self):
        return self._v3_r03_act()
    def _v3_r03_act(self):
        return install(place_delivery=self.features.r04_place_delivery)
    def _dead_poison(self):
        return install(place_delivery=self.features.r04_place_delivery)
"""
    )
    live_agent = _titan_agent_class(live_tree)
    live_reachable = _reachable_agent_methods(live_agent)
    _require(
        _reachable_agent_feature_ref(live_reachable, "r04_place_delivery"),
        "internal reachability regression: live feature reference was not found",
    )
    _require(
        _runtime_install_wired(live_reachable, "r04_place_delivery", "place_delivery"),
        "internal reachability regression: live install wiring was not found",
    )

    poison_tree = ast.parse(
        """
class TitanAgent:
    def act(self):
        def dead_local():
            self._dead_poison()
            return install(place_delivery=self.features.r04_place_delivery)
        if False:
            return install(place_delivery=self.features.r04_place_delivery)
        return self._v3_r03_act()
    def _v3_r03_act(self):
        return None
    def _dead_poison(self):
        marker = self.features.r04_place_delivery
        return install(place_delivery=self.features.r04_place_delivery)
"""
    )
    poison_agent = _titan_agent_class(poison_tree)
    poison_reachable = _reachable_agent_methods(poison_agent)
    _require(
        not _reachable_agent_feature_ref(poison_reachable, "r04_place_delivery"),
        "internal reachability regression: nested/dead feature reference false-passed",
    )
    _require(
        not _runtime_install_wired(poison_reachable, "r04_place_delivery", "place_delivery"),
        "internal reachability regression: nested/dead install wiring false-passed",
    )


def _self_test_router_reachability() -> None:
    live = ast.parse(
        """
PLACE_DELIVERY = False

def helper(observation, configuration=None):
    return observation

def v3_agent(observation, configuration=None):
    if PLACE_DELIVERY:
        return helper(observation, configuration)
    return observation

def install(*, place_delivery=None):
    global PLACE_DELIVERY
    if place_delivery is not None:
        PLACE_DELIVERY = bool(place_delivery)
    return v3_agent
"""
    )
    install = _find_function(live, "install")
    _require(
        _top_level_bool_names(live).get("PLACE_DELIVERY") is False,
        "internal router regression: live false default missing",
    )
    _require(
        "PLACE_DELIVERY" in _global_names(install) and _stores_name(install, "PLACE_DELIVERY"),
        "internal router regression: live install setter missing",
    )
    _require(
        _router_flag_reader(live, "PLACE_DELIVERY") == "v3_agent",
        "internal router regression: live production flag read missing",
    )

    called_helper = ast.parse(
        """
PLACE_DELIVERY = False
def live_helper(observation, configuration=None):
    if PLACE_DELIVERY:
        return observation
    return observation
def v3_agent(observation, configuration=None):
    return live_helper(observation, configuration)
"""
    )
    _require(
        _router_flag_reader(called_helper, "PLACE_DELIVERY") == "live_helper",
        "internal router regression: directly called helper was not reachable",
    )

    uncalled_helper = ast.parse(
        """
PLACE_DELIVERY = False
def dead_helper(observation, configuration=None):
    return PLACE_DELIVERY
def v3_agent(observation, configuration=None):
    dead_helper
    return observation
"""
    )
    _require(
        _router_flag_reader(uncalled_helper, "PLACE_DELIVERY") is None,
        "internal router regression: uncalled helper flag read false-passed",
    )

    nested_setter = ast.parse(
        """
PLACE_DELIVERY = False
def v3_agent(observation, configuration=None):
    return observation
def install(*, place_delivery=None):
    def dead():
        global PLACE_DELIVERY
        PLACE_DELIVERY = bool(place_delivery)
    return v3_agent
"""
    )
    nested_install = _find_function(nested_setter, "install")
    _require(
        "PLACE_DELIVERY" not in _global_names(nested_install)
        and not _stores_name(nested_install, "PLACE_DELIVERY"),
        "internal router regression: nested install setter false-passed",
    )

    dead_setter = ast.parse(
        """
PLACE_DELIVERY = False
def v3_agent(observation, configuration=None):
    return observation
def install(*, place_delivery=None):
    global PLACE_DELIVERY
    if False:
        PLACE_DELIVERY = bool(place_delivery)
    return v3_agent
"""
    )
    dead_install = _find_function(dead_setter, "install")
    _require(
        not _stores_name(dead_install, "PLACE_DELIVERY"),
        "internal router regression: statically dead install setter false-passed",
    )

    dead_reader = ast.parse(
        """
PLACE_DELIVERY = False
def v3_agent(observation, configuration=None):
    def dead():
        return PLACE_DELIVERY
    if False:
        return PLACE_DELIVERY
    return observation
def install(*, place_delivery=None):
    global PLACE_DELIVERY
    PLACE_DELIVERY = bool(place_delivery)
    return v3_agent
"""
    )
    _require(
        _router_flag_reader(dead_reader, "PLACE_DELIVERY") is None,
        "internal router regression: nested/dead production read false-passed",
    )

    stale_function = ast.parse(
        """
PLACE_DELIVERY = False
def live_agent(observation, configuration=None):
    return PLACE_DELIVERY
v3_agent = live_agent
v3_agent = object()
"""
    )
    _require(
        not _production_function_nodes(stale_function),
        "internal router regression: stale v3_agent function binding survived reassignment",
    )

    stale_flag = ast.parse(
        """
PLACE_DELIVERY = False
PLACE_DELIVERY = object()
"""
    )
    _require(
        "PLACE_DELIVERY" not in _top_level_bool_names(stale_flag),
        "internal router regression: stale false flag binding survived reassignment",
    )


def check(base_apply_v4: Path) -> None:
    _self_test_agent_reachability()
    _self_test_router_reachability()

    base_keys = _literal_keys(base_apply_v4)
    head_keys = _literal_keys(APPLY_V4)
    base_key_set = set(base_keys)
    removed = sorted(base_key_set - set(head_keys))
    _require(not removed, "V4 recomposition removed already-landed key(s): " + ", ".join(removed))

    files = build_v3.package_files()
    for required in ("TITAN-CONFIG.json", "titan_runtime.py", "r04_full_router.py"):
        _require(required in files, f"materialized package missing {required}")

    config = json.loads(files["TITAN-CONFIG.json"].decode("utf-8"))
    runtime_tree = ast.parse(
        files["titan_runtime.py"].decode("utf-8"), filename="titan_runtime.py"
    )
    router_tree = ast.parse(
        files["r04_full_router.py"].decode("utf-8"), filename="r04_full_router.py"
    )
    feature_defaults = _feature_defaults(runtime_tree)
    agent = _titan_agent_class(runtime_tree)
    reachable_agent = _reachable_agent_methods(agent)

    for key in head_keys:
        _require(key in config, f"{key}: missing from materialized TITAN-CONFIG.json")
        _require(type(config[key]) is bool, f"{key}: materialized config value must be boolean")
        _require(config[key] is False, f"{key}: materialized config must source-land False")
        _require(key in feature_defaults, f"{key}: missing from materialized Features")
        _require(type(feature_defaults[key]) is bool, f"{key}: Features default must be boolean")
        _require(feature_defaults[key] is False, f"{key}: Features default must remain False")
        _require(
            _reachable_agent_feature_ref(reachable_agent, key),
            f"{key}: TitanAgent.act chain never references self.features.{key}",
        )
        if key.startswith("r04_"):
            _assert_r04_router_contract(router_tree, reachable_agent, key)

    print(
        "V4 PLUMBING OK",
        "base", list(base_keys),
        "head", list(head_keys),
        "reachable_agent_methods",
        sorted(getattr(node, "name", "<anonymous>") for node in reachable_agent),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-apply-v4", type=Path, required=True)
    args = parser.parse_args()
    check(args.base_apply_v4)


if __name__ == "__main__":
    main()
