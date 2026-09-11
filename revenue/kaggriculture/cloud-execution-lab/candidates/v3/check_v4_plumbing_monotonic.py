#!/usr/bin/env python3
"""Promotion-aware, value-preserving CI entry point for the V4 plumbing guard.

``check_v4_plumbing`` owns broad structural/reachability proof. This wrapper adds
the invariants that need exact base/head state or stricter Python semantics:

* genuinely new keys must source-land OFF;
* an existing OFF key may remain OFF or be intentionally promoted ON;
* an existing ON key may never silently regress OFF during recomposition;
* Features and router source defaults remain OFF for every key;
* router install setters must preserve the matching parameter value;
* TitanAgent must call the live ``r04_full_router.install`` and pass the exact
  matching ``self.features.<key>`` boolean, not an expression that merely
  mentions it;
* production reachability ignores nested scopes, literal-dead branches, and
  statements after an unconditional terminator.

Failures use ``check_v4_plumbing._require`` so the contract survives ``python -O``.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Iterable

import check_v4_plumbing as core


_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def _load_apply(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("_v4_target_apply", path)
    core._require(
        spec is not None and spec.loader is not None,
        f"cannot load target apply layer: {path}",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _package_with_apply(module: ModuleType) -> dict[str, bytes]:
    original = core.build_v3.apply_v4
    try:
        core.build_v3.apply_v4 = module
        return core.build_v3.package_files()
    finally:
        core.build_v3.apply_v4 = original


def _config_transition_ok(*, is_new: bool, base_value: object, head_value: object) -> bool:
    if type(head_value) is not bool:
        return False
    if is_new:
        return head_value is False
    if type(base_value) is not bool:
        return False
    return not (base_value is True and head_value is False)


def _self_test_config_transitions() -> None:
    cases = (
        (True, None, False, True, "new OFF"),
        (True, None, True, False, "new ON poison"),
        (False, False, False, True, "existing OFF stays OFF"),
        (False, False, True, True, "promotion OFF to ON"),
        (False, True, True, True, "promoted ON stays ON"),
        (False, True, False, False, "promoted ON regression"),
        (False, None, False, False, "missing base state"),
    )
    for is_new, base_value, head_value, expected, label in cases:
        actual = _config_transition_ok(
            is_new=is_new,
            base_value=base_value,
            head_value=head_value,
        )
        core._require(actual is expected, f"internal config-transition regression: {label}")


def _literal_truth(node: ast.AST) -> bool | None:
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError):
        return None
    try:
        return bool(value)
    except Exception:
        return None


def _walk_expr(node: ast.AST, out: list[ast.AST]) -> None:
    """Walk one executable expression without entering nested lexical scopes."""
    if isinstance(node, _SCOPE_NODES):
        return
    out.append(node)

    if isinstance(node, ast.IfExp):
        _walk_expr(node.test, out)
        truth = _literal_truth(node.test)
        if truth is True:
            _walk_expr(node.body, out)
        elif truth is False:
            _walk_expr(node.orelse, out)
        else:
            _walk_expr(node.body, out)
            _walk_expr(node.orelse, out)
        return

    if isinstance(node, ast.BoolOp):
        is_and = isinstance(node.op, ast.And)
        is_or = isinstance(node.op, ast.Or)
        for value in node.values:
            _walk_expr(value, out)
            truth = _literal_truth(value)
            if (is_and and truth is False) or (is_or and truth is True):
                break
        return

    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.stmt):
            continue
        _walk_expr(child, out)


def _walk_block(
    statements: Iterable[ast.stmt],
    out: list[ast.AST],
    *,
    in_loop: bool = False,
) -> bool:
    """Collect live nodes in statement order; return whether the block definitely exits."""
    for statement in statements:
        if _walk_stmt(statement, out, in_loop=in_loop):
            return True
    return False


def _walk_stmt(statement: ast.stmt, out: list[ast.AST], *, in_loop: bool) -> bool:
    """Collect live nodes for a statement and report definite block termination."""
    if isinstance(statement, _SCOPE_NODES):
        return False

    out.append(statement)

    if isinstance(statement, (ast.Return, ast.Raise)):
        if getattr(statement, "value", None) is not None:
            _walk_expr(statement.value, out)
        if isinstance(statement, ast.Raise):
            if statement.exc is not None:
                _walk_expr(statement.exc, out)
            if statement.cause is not None:
                _walk_expr(statement.cause, out)
        return True

    if isinstance(statement, (ast.Break, ast.Continue)):
        return in_loop

    if isinstance(statement, ast.If):
        _walk_expr(statement.test, out)
        truth = _literal_truth(statement.test)
        if truth is True:
            return _walk_block(statement.body, out, in_loop=in_loop)
        if truth is False:
            return _walk_block(statement.orelse, out, in_loop=in_loop)
        body_out: list[ast.AST] = []
        else_out: list[ast.AST] = []
        body_term = _walk_block(statement.body, body_out, in_loop=in_loop)
        else_term = _walk_block(statement.orelse, else_out, in_loop=in_loop)
        out.extend(body_out)
        out.extend(else_out)
        return bool(statement.orelse) and body_term and else_term

    if isinstance(statement, ast.While):
        _walk_expr(statement.test, out)
        truth = _literal_truth(statement.test)
        if truth is False:
            return _walk_block(statement.orelse, out, in_loop=in_loop)
        _walk_block(statement.body, out, in_loop=True)
        _walk_block(statement.orelse, out, in_loop=in_loop)
        return False

    if isinstance(statement, (ast.For, ast.AsyncFor)):
        _walk_expr(statement.target, out)
        _walk_expr(statement.iter, out)
        _walk_block(statement.body, out, in_loop=True)
        _walk_block(statement.orelse, out, in_loop=in_loop)
        return False

    if isinstance(statement, (ast.With, ast.AsyncWith)):
        for item in statement.items:
            _walk_expr(item.context_expr, out)
            if item.optional_vars is not None:
                _walk_expr(item.optional_vars, out)
        return _walk_block(statement.body, out, in_loop=in_loop)

    try_types = (ast.Try, getattr(ast, "TryStar", ast.Try))
    if isinstance(statement, try_types):
        body_term = _walk_block(statement.body, out, in_loop=in_loop)
        for handler in statement.handlers:
            if handler.type is not None:
                _walk_expr(handler.type, out)
            _walk_block(handler.body, out, in_loop=in_loop)
        _walk_block(statement.orelse, out, in_loop=in_loop)
        final_term = _walk_block(statement.finalbody, out, in_loop=in_loop)
        if final_term:
            return True
        return body_term and not statement.handlers and not statement.finalbody

    if isinstance(statement, ast.Match):
        _walk_expr(statement.subject, out)
        for case in statement.cases:
            if case.guard is not None:
                _walk_expr(case.guard, out)
            _walk_block(case.body, out, in_loop=in_loop)
        return False

    for child in ast.iter_child_nodes(statement):
        if isinstance(child, ast.stmt):
            continue
        _walk_expr(child, out)
    return False


def _live_function_nodes(function: ast.AST) -> list[ast.AST]:
    out: list[ast.AST] = []
    _walk_block(getattr(function, "body", []), out)
    return out


def _final_class(tree: ast.AST, name: str) -> ast.ClassDef:
    """Resolve Python's final top-level binding for a required class."""
    binding: ast.ClassDef | None = None
    seen = False
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.ClassDef) and node.name == name:
            seen = True
            binding = node
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            seen = True
            binding = None
            continue
        targets: tuple[ast.AST, ...] = ()
        if isinstance(node, ast.Assign):
            targets = tuple(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = (node.target,)
        elif isinstance(node, ast.AugAssign):
            targets = (node.target,)
        elif isinstance(node, ast.Delete):
            targets = tuple(node.targets)
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            seen = True
            binding = None
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".", 1)[0]
                if bound == name:
                    seen = True
                    binding = None
    core._require(seen and binding is not None, f"materialized titan_runtime.py has no final live {name} class")
    return binding


def _class_literal_defaults(cls: ast.ClassDef) -> dict[str, object]:
    """Resolve final literal direct class-body bindings."""
    defaults: dict[str, object] = {}
    for stmt in cls.body:
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


def _class_methods(cls: ast.ClassDef) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Resolve final direct method bindings; non-method rebinds invalidate a method name."""
    methods: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in cls.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods[node.name] = node
            continue
        if isinstance(node, ast.ClassDef):
            methods.pop(node.name, None)
            continue
        targets: tuple[ast.AST, ...] = ()
        if isinstance(node, ast.Assign):
            targets = tuple(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = (node.target,)
        elif isinstance(node, ast.AugAssign):
            targets = (node.target,)
        elif isinstance(node, ast.Delete):
            targets = tuple(node.targets)
        for target in targets:
            if isinstance(target, ast.Name):
                methods.pop(target.id, None)
    return methods


def _reachable_agent_methods(agent: ast.ClassDef) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
    methods = _class_methods(agent)
    root = methods.get("act")
    core._require(root is not None, "materialized TitanAgent has no final live act() method")
    reachable: set[ast.FunctionDef | ast.AsyncFunctionDef] = set()
    stack = [root]
    while stack:
        function = stack.pop()
        if function in reachable:
            continue
        reachable.add(function)
        for node in _live_function_nodes(function):
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


def _is_self_feature(node: ast.AST, key: str) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == key
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "features"
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "self"
    )


def _is_exact_feature_bool(node: ast.AST, key: str) -> bool:
    if _is_self_feature(node, key):
        return True
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "bool"
        and len(node.args) == 1
        and not node.keywords
        and _is_self_feature(node.args[0], key)
    )


def _is_exact_param_bool(node: ast.AST, suffix: str) -> bool:
    if isinstance(node, ast.Name) and node.id == suffix:
        return True
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "bool"
        and len(node.args) == 1
        and not node.keywords
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == suffix
    )


def _assigned_value(statement: ast.AST, name: str) -> ast.AST | None:
    if isinstance(statement, ast.Assign):
        for target in statement.targets:
            if isinstance(target, ast.Name) and target.id == name:
                return statement.value
    elif isinstance(statement, ast.AnnAssign):
        if isinstance(statement.target, ast.Name) and statement.target.id == name:
            return statement.value
    return None


def _strict_router_setter(install: ast.FunctionDef, suffix: str, flag: str) -> bool:
    """Require every live direct assignment to FLAG in install() to preserve suffix value."""
    values: list[ast.AST | None] = []
    for node in _live_function_nodes(install):
        value = _assigned_value(node, flag)
        if value is not None:
            values.append(value)
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id == flag:
            values.append(None)
        elif isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name) and node.target.id == flag:
            values.append(node.value)
    return bool(values) and all(value is not None and _is_exact_param_bool(value, suffix) for value in values)


def _strict_router_reachable_functions(router_tree: ast.AST) -> set[ast.AST]:
    bindings = core._top_level_function_bindings(router_tree)
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
        for node in _live_function_nodes(function):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            target = bindings.get(node.func.id)
            if target is not None and target not in reachable:
                stack.append(target)
    return reachable


def _strict_router_flag_reader(router_tree: ast.AST, flag: str) -> str | None:
    for function in _strict_router_reachable_functions(router_tree):
        for node in _live_function_nodes(function):
            if isinstance(node, ast.Name) and node.id == flag and isinstance(node.ctx, ast.Load):
                return getattr(function, "name", "<anonymous>")
    return None


def _strict_install_selector(install: ast.FunctionDef, flag: str) -> bool:
    """Permit install-time callable selection only from live code that reads FLAG."""
    for node in _live_function_nodes(install):
        if not isinstance(node, ast.If):
            continue
        test_nodes: list[ast.AST] = []
        _walk_expr(node.test, test_nodes)
        if not any(
            isinstance(child, ast.Name)
            and child.id == flag
            and isinstance(child.ctx, ast.Load)
            for child in test_nodes
        ):
            continue
        for statement in node.body:
            branch_nodes: list[ast.AST] = []
            _walk_stmt(statement, branch_nodes, in_loop=False)
            for child in branch_nodes:
                if not isinstance(child, ast.Return) or child.value is None:
                    continue
                if isinstance(child.value, ast.Name) and child.value.id == "v3_agent":
                    continue
                return True
    return False


def _live_r04_install_binding(function: ast.AST, call: ast.Call) -> bool:
    """Prove Name install at CALL is imported from r04_full_router and not rebound."""
    call_line = getattr(call, "lineno", 10**9)
    bound = False
    for node in _live_function_nodes(function):
        line = getattr(node, "lineno", -1)
        if line < 0 or line >= call_line:
            continue
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                if name != "install":
                    continue
                bound = node.module == "r04_full_router" and alias.name == "install"
            continue
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound_name = alias.asname or alias.name.split(".", 1)[0]
                if bound_name == "install":
                    bound = False
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == "install":
            bound = False
            continue
        targets: tuple[ast.AST, ...] = ()
        if isinstance(node, ast.Assign):
            targets = tuple(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = (node.target,)
        elif isinstance(node, ast.AugAssign):
            targets = (node.target,)
        elif isinstance(node, ast.Delete):
            targets = tuple(node.targets)
        if any(isinstance(target, ast.Name) and target.id == "install" for target in targets):
            bound = False
    return bound


def _strict_runtime_install_wired(
    reachable: Iterable[ast.FunctionDef | ast.AsyncFunctionDef],
    key: str,
    suffix: str,
) -> bool:
    for function in reachable:
        for node in _live_function_nodes(function):
            if not isinstance(node, ast.Call):
                continue
            if not (isinstance(node.func, ast.Name) and node.func.id == "install"):
                continue
            if not _live_r04_install_binding(function, node):
                continue
            for keyword in node.keywords:
                if keyword.arg == suffix and _is_exact_feature_bool(keyword.value, key):
                    return True
    return False


def _strict_feature_ref(
    reachable: Iterable[ast.FunctionDef | ast.AsyncFunctionDef],
    key: str,
) -> bool:
    for function in reachable:
        for node in _live_function_nodes(function):
            if _is_self_feature(node, key):
                return True
    return False


def _root_self_features_target(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "features"
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    )


def _no_reachable_features_rebind(
    reachable: Iterable[ast.FunctionDef | ast.AsyncFunctionDef],
) -> bool:
    """Reject act-chain mutation/rebinding of the feature object before router install."""
    for function in reachable:
        for node in _live_function_nodes(function):
            targets: tuple[ast.AST, ...] = ()
            if isinstance(node, ast.Assign):
                targets = tuple(node.targets)
            elif isinstance(node, ast.AnnAssign):
                targets = (node.target,)
            elif isinstance(node, ast.AugAssign):
                targets = (node.target,)
            elif isinstance(node, ast.Delete):
                targets = tuple(node.targets)
            elif isinstance(node, ast.NamedExpr):
                targets = (node.target,)
            if any(_root_self_features_target(target) for target in targets):
                return False
    return True


def _strict_r04_contract(
    router_tree: ast.AST,
    reachable_agent: tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...],
    key: str,
) -> None:
    suffix = key.removeprefix("r04_")
    flag = suffix.upper()
    router_defaults = core._top_level_bool_names(router_tree)
    core._require(
        router_defaults.get(flag) is False,
        f"{key}: router source flag {flag} must remain literal False",
    )

    install = core._find_function(router_tree, "install")
    install_args = {
        arg.arg
        for arg in (*install.args.posonlyargs, *install.args.args, *install.args.kwonlyargs)
    }
    core._require(suffix in install_args, f"{key}: router install() missing {suffix} parameter")
    core._require(
        flag in core._global_names(install),
        f"{key}: router install() does not directly declare {flag} global",
    )
    core._require(
        _strict_router_setter(install, suffix, flag),
        f"{key}: router install() does not value-preservingly set {flag} from {suffix}",
    )
    core._require(
        _strict_router_flag_reader(router_tree, flag) is not None
        or _strict_install_selector(install, flag),
        f"{key}: {flag} is not read on an executable production path",
    )
    core._require(
        _strict_runtime_install_wired(reachable_agent, key, suffix),
        f"{key}: live TitanAgent path does not call r04_full_router.install("
        f"{suffix}=bool(self.features.{key}))",
    )


def _self_test_strict_value_flow() -> None:
    live_router = ast.parse(
        """
PLACE_DELIVERY = False
def _v3_core(observation, configuration=None):
    return observation
def v3_agent(observation, configuration=None):
    if PLACE_DELIVERY:
        return _v3_core(observation, configuration)
    return observation
def install(*, place_delivery=None):
    global PLACE_DELIVERY
    if place_delivery is not None:
        PLACE_DELIVERY = bool(place_delivery)
    return v3_agent
"""
    )
    install = core._find_function(live_router, "install")
    core._require(
        _strict_router_setter(install, "place_delivery", "PLACE_DELIVERY"),
        "internal strict-value regression: canonical router setter rejected",
    )
    core._require(
        _strict_router_flag_reader(live_router, "PLACE_DELIVERY") == "v3_agent",
        "internal strict-value regression: canonical router read rejected",
    )

    constant_setter = ast.parse(
        """
PLACE_DELIVERY = False
def v3_agent(observation, configuration=None):
    if PLACE_DELIVERY:
        return observation
    return observation
def install(*, place_delivery=None):
    global PLACE_DELIVERY
    PLACE_DELIVERY = False
    return v3_agent
"""
    )
    core._require(
        not _strict_router_setter(
            core._find_function(constant_setter, "install"),
            "place_delivery",
            "PLACE_DELIVERY",
        ),
        "internal strict-value regression: constant router setter false-passed",
    )

    wrong_param = ast.parse(
        """
PLACE_DELIVERY = False
def v3_agent(observation, configuration=None):
    return observation
def install(*, place_delivery=None, other=None):
    global PLACE_DELIVERY
    PLACE_DELIVERY = bool(other)
    return v3_agent
"""
    )
    core._require(
        not _strict_router_setter(
            core._find_function(wrong_param, "install"),
            "place_delivery",
            "PLACE_DELIVERY",
        ),
        "internal strict-value regression: wrong-parameter router setter false-passed",
    )

    dead_reader = ast.parse(
        """
PLACE_DELIVERY = False
def v3_agent(observation, configuration=None):
    return observation
    if PLACE_DELIVERY:
        return observation
"""
    )
    core._require(
        _strict_router_flag_reader(dead_reader, "PLACE_DELIVERY") is None,
        "internal strict-value regression: post-return router read false-passed",
    )

    runtime_live = ast.parse(
        """
class TitanAgent:
    def act(self):
        return self._v3_r03_act()
    def _v3_r03_act(self):
        from r04_full_router import install
        return install(place_delivery=bool(self.features.r04_place_delivery))
"""
    )
    agent = _final_class(runtime_live, "TitanAgent")
    reachable = _reachable_agent_methods(agent)
    core._require(
        _strict_runtime_install_wired(reachable, "r04_place_delivery", "place_delivery"),
        "internal strict-value regression: canonical runtime wiring rejected",
    )

    runtime_expr_poison = ast.parse(
        """
class TitanAgent:
    def act(self):
        return self._v3_r03_act()
    def _v3_r03_act(self):
        from r04_full_router import install
        return install(place_delivery=(self.features.r04_place_delivery and False))
"""
    )
    poison_reachable = _reachable_agent_methods(_final_class(runtime_expr_poison, "TitanAgent"))
    core._require(
        not _strict_runtime_install_wired(
            poison_reachable, "r04_place_delivery", "place_delivery"
        ),
        "internal strict-value regression: feature-and-False wiring false-passed",
    )

    runtime_import_poison = ast.parse(
        """
class TitanAgent:
    def act(self):
        return self._v3_r03_act()
    def _v3_r03_act(self):
        from unrelated import install
        return install(place_delivery=bool(self.features.r04_place_delivery))
"""
    )
    import_reachable = _reachable_agent_methods(_final_class(runtime_import_poison, "TitanAgent"))
    core._require(
        not _strict_runtime_install_wired(
            import_reachable, "r04_place_delivery", "place_delivery"
        ),
        "internal strict-value regression: unrelated install import false-passed",
    )

    runtime_dead_poison = ast.parse(
        """
class TitanAgent:
    def act(self):
        return self._v3_r03_act()
    def _v3_r03_act(self):
        return None
        from r04_full_router import install
        return install(place_delivery=bool(self.features.r04_place_delivery))
"""
    )
    dead_reachable = _reachable_agent_methods(_final_class(runtime_dead_poison, "TitanAgent"))
    core._require(
        not _strict_runtime_install_wired(
            dead_reachable, "r04_place_delivery", "place_delivery"
        ),
        "internal strict-value regression: post-return runtime wiring false-passed",
    )

    runtime_rebind_poison = ast.parse(
        """
class TitanAgent:
    def act(self):
        self.features = forged
        return self._v3_r03_act()
    def _v3_r03_act(self):
        from r04_full_router import install
        return install(place_delivery=bool(self.features.r04_place_delivery))
"""
    )
    rebind_reachable = _reachable_agent_methods(_final_class(runtime_rebind_poison, "TitanAgent"))
    core._require(
        not _no_reachable_features_rebind(rebind_reachable),
        "internal strict-value regression: self.features act-chain rebind false-passed",
    )


def check(base_apply_v4: Path) -> None:
    core._self_test_agent_reachability()
    core._self_test_router_reachability()
    _self_test_config_transitions()
    _self_test_strict_value_flow()

    base_keys = core._literal_keys(base_apply_v4)
    head_keys = core._literal_keys(core.APPLY_V4)
    base_key_set = set(base_keys)
    head_key_set = set(head_keys)
    removed = sorted(base_key_set - head_key_set)
    core._require(
        not removed,
        "V4 recomposition removed already-landed key(s): " + ", ".join(removed),
    )
    new_keys = head_key_set - base_key_set

    base_apply = _load_apply(base_apply_v4)
    base_files = _package_with_apply(base_apply)
    files = core.build_v3.package_files()

    for label, package in (("base", base_files), ("head", files)):
        for required in ("TITAN-CONFIG.json", "titan_runtime.py", "r04_full_router.py"):
            core._require(required in package, f"materialized {label} package missing {required}")

    base_config = json.loads(base_files["TITAN-CONFIG.json"].decode("utf-8"))
    config = json.loads(files["TITAN-CONFIG.json"].decode("utf-8"))
    runtime_tree = ast.parse(
        files["titan_runtime.py"].decode("utf-8"), filename="titan_runtime.py"
    )
    router_tree = ast.parse(
        files["r04_full_router.py"].decode("utf-8"), filename="r04_full_router.py"
    )

    features_cls = _final_class(runtime_tree, "Features")
    feature_defaults = _class_literal_defaults(features_cls)
    agent = _final_class(runtime_tree, "TitanAgent")
    reachable_agent = _reachable_agent_methods(agent)
    core._require(
        _no_reachable_features_rebind(reachable_agent),
        "TitanAgent.act chain may not rebind/delete self.features before V4 install wiring",
    )

    for key in head_keys:
        core._require(key in config, f"{key}: missing from materialized TITAN-CONFIG.json")
        core._require(
            type(config[key]) is bool,
            f"{key}: materialized config value must be boolean",
        )

        if key in new_keys:
            core._require(config[key] is False, f"{key}: new V4 key must source-land OFF")
        else:
            core._require(
                key in base_config,
                f"{key}: missing from materialized base TITAN-CONFIG.json",
            )
            core._require(
                type(base_config[key]) is bool,
                f"{key}: base config value must be boolean",
            )
            core._require(
                _config_transition_ok(
                    is_new=False,
                    base_value=base_config[key],
                    head_value=config[key],
                ),
                f"{key}: already-promoted base config True may not regress to False",
            )

        core._require(key in feature_defaults, f"{key}: missing from final live Features")
        core._require(
            type(feature_defaults[key]) is bool,
            f"{key}: Features default must be boolean",
        )
        core._require(
            feature_defaults[key] is False,
            f"{key}: Features source default must remain False",
        )
        core._require(
            _strict_feature_ref(reachable_agent, key),
            f"{key}: executable TitanAgent.act chain never references self.features.{key}",
        )
        if key.startswith("r04_"):
            _strict_r04_contract(router_tree, reachable_agent, key)

    promoted = [key for key in head_keys if config.get(key) is True]
    print(
        "V4 PLUMBING OK",
        "base", list(base_keys),
        "head", list(head_keys),
        "new", sorted(new_keys),
        "promoted", promoted,
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
