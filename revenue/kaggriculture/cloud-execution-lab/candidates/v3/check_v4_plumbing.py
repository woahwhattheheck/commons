#!/usr/bin/env python3
"""Fail closed if a V4 recomposition drops a landed key or its executable plumbing.

This bootstrap guard intentionally requires every shipped V4 key to remain OFF in
materialized config/runtime/router defaults. A future promotion PR must evolve this
contract explicitly; ordinary recompositions cannot silently change key state.

The proof is deliberately narrow: it recognizes the generated TITAN V4 shapes we
actually ship, rather than attempting to model arbitrary Python. Ambiguous binding,
decorator, control-flow, or data-flow forms fail closed.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Iterable, NoReturn

HERE = Path(__file__).resolve().parent
APPLY_V4 = HERE / "apply_v4.py"
_UNKNOWN = object()
_DEFERRED_EXPRS = (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def _fail(message: str) -> NoReturn:
    raise SystemExit(message)


def _require(cond: object, message: str) -> None:
    if not cond:
        _fail(message)


def _target_names(target: ast.AST) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        out: set[str] = set()
        for item in target.elts:
            out.update(_target_names(item))
        return out
    if isinstance(target, ast.Starred):
        return _target_names(target.value)
    return set()


def _bound_names_in_statements(statements: Iterable[ast.stmt]) -> set[str]:
    """Lexical bindings made by statements, without descending into nested scopes."""
    out: set[str] = set()

    def visit(stmt: ast.stmt) -> None:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(stmt.name)
            return
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                out.update(_target_names(target))
            return
        if isinstance(stmt, (ast.AnnAssign, ast.AugAssign)):
            out.update(_target_names(stmt.target))
            return
        if isinstance(stmt, ast.Delete):
            for target in stmt.targets:
                out.update(_target_names(target))
            return
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            for alias in stmt.names:
                out.add(alias.asname or alias.name.split(".", 1)[0])
            return
        if isinstance(stmt, (ast.For, ast.AsyncFor)):
            out.update(_target_names(stmt.target))
            for child in (*stmt.body, *stmt.orelse):
                visit(child)
            return
        if isinstance(stmt, ast.If):
            for child in (*stmt.body, *stmt.orelse):
                visit(child)
            return
        if isinstance(stmt, ast.While):
            for child in (*stmt.body, *stmt.orelse):
                visit(child)
            return
        if isinstance(stmt, (ast.With, ast.AsyncWith)):
            for item in stmt.items:
                if item.optional_vars is not None:
                    out.update(_target_names(item.optional_vars))
            for child in stmt.body:
                visit(child)
            return
        if isinstance(stmt, (ast.Try, getattr(ast, "TryStar", ast.Try))):
            for child in (*stmt.body, *stmt.orelse, *stmt.finalbody):
                visit(child)
            for handler in stmt.handlers:
                if handler.name:
                    out.add(handler.name)
                for child in handler.body:
                    visit(child)
            return
        if isinstance(stmt, ast.Match):
            for node in ast.walk(stmt):
                if isinstance(node, ast.MatchAs) and node.name:
                    out.add(node.name)
                elif isinstance(node, ast.MatchStar) and node.name:
                    out.add(node.name)
            for case in stmt.cases:
                for child in case.body:
                    visit(child)

    for statement in statements:
        visit(statement)
    return out


def _literal_value(node: ast.AST) -> object:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return _UNKNOWN


def _static_truth(node: ast.AST) -> bool | None:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        truth = _static_truth(node.operand)
        return None if truth is None else not truth
    if isinstance(node, ast.BoolOp):
        truths = [_static_truth(value) for value in node.values]
        if isinstance(node.op, ast.And):
            if any(value is False for value in truths):
                return False
            return True if truths and all(value is True for value in truths) else None
        if isinstance(node.op, ast.Or):
            if any(value is True for value in truths):
                return True
            return False if truths and all(value is False for value in truths) else None
    if isinstance(node, ast.Compare):
        values = [node.left, *node.comparators]
        literals = [_literal_value(value) for value in values]
        if any(value is _UNKNOWN for value in literals):
            return None
        left = literals[0]
        try:
            for op, right in zip(node.ops, literals[1:]):
                if isinstance(op, ast.Eq):
                    ok = left == right
                elif isinstance(op, ast.NotEq):
                    ok = left != right
                elif isinstance(op, ast.Lt):
                    ok = left < right
                elif isinstance(op, ast.LtE):
                    ok = left <= right
                elif isinstance(op, ast.Gt):
                    ok = left > right
                elif isinstance(op, ast.GtE):
                    ok = left >= right
                elif isinstance(op, ast.Is):
                    ok = left is right
                elif isinstance(op, ast.IsNot):
                    ok = left is not right
                elif isinstance(op, ast.In):
                    ok = left in right
                elif isinstance(op, ast.NotIn):
                    ok = left not in right
                else:
                    return None
                if not ok:
                    return False
                left = right
            return True
        except Exception:
            return None
    literal = _literal_value(node)
    if literal is _UNKNOWN:
        return None
    try:
        return bool(literal)
    except Exception:
        return None


def _process_bindings(statements: Iterable[ast.stmt], bindings: dict[str, object]) -> None:
    """Execute simple module/class binding semantics; ambiguous compounds invalidate."""
    for stmt in statements:
        if isinstance(stmt, ast.If):
            truth = _static_truth(stmt.test)
            if truth is True:
                _process_bindings(stmt.body, bindings)
            elif truth is False:
                _process_bindings(stmt.orelse, bindings)
            else:
                for name in _bound_names_in_statements((*stmt.body, *stmt.orelse)):
                    bindings[name] = _UNKNOWN
            continue

        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bindings[stmt.name] = stmt
            continue

        if isinstance(stmt, ast.Assign):
            direct_names: list[str] = []
            ambiguous: set[str] = set()
            for target in stmt.targets:
                names = _target_names(target)
                if isinstance(target, ast.Name):
                    direct_names.append(target.id)
                else:
                    ambiguous.update(names)
            value: object = stmt.value
            if isinstance(stmt.value, ast.Name) and stmt.value.id in bindings:
                value = bindings[stmt.value.id]
            for name in direct_names:
                bindings[name] = value
            for name in ambiguous:
                bindings[name] = _UNKNOWN
            continue

        if isinstance(stmt, ast.AnnAssign):
            names = _target_names(stmt.target)
            if isinstance(stmt.target, ast.Name) and stmt.value is not None:
                value: object = stmt.value
                if isinstance(stmt.value, ast.Name) and stmt.value.id in bindings:
                    value = bindings[stmt.value.id]
                bindings[stmt.target.id] = value
            else:
                for name in names:
                    bindings[name] = _UNKNOWN
            continue

        if isinstance(stmt, (ast.AugAssign, ast.Delete)):
            targets = (stmt.target,) if isinstance(stmt, ast.AugAssign) else stmt.targets
            for target in targets:
                for name in _target_names(target):
                    bindings[name] = _UNKNOWN
            continue

        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            for alias in stmt.names:
                bindings[alias.asname or alias.name.split(".", 1)[0]] = _UNKNOWN
            continue

        if isinstance(stmt, (ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith,
                             ast.Try, getattr(ast, "TryStar", ast.Try), ast.Match)):
            for name in _bound_names_in_statements((stmt,)):
                bindings[name] = _UNKNOWN
            continue


def _bindings(statements: Iterable[ast.stmt]) -> dict[str, object]:
    out: dict[str, object] = {}
    _process_bindings(statements, out)
    return out


def _final_class(tree: ast.Module, name: str) -> ast.ClassDef:
    node = _bindings(tree.body).get(name)
    _require(isinstance(node, ast.ClassDef), f"materialized runtime has no unambiguous live {name} class")
    return node


def _final_function(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    node = _bindings(tree.body).get(name)
    _require(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)),
             f"materialized router has no unambiguous live {name}()")
    _require(not node.decorator_list, f"{name}(): decorators are not allowed on audited router bindings")
    return node


def _class_methods(cls: ast.ClassDef) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    resolved = _bindings(cls.body)
    return {
        name: value
        for name, value in resolved.items()
        if isinstance(value, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _expr_nodes(node: ast.AST) -> Iterable[ast.AST]:
    """Executable expression nodes, pruning deferred/nested expression scopes."""
    if isinstance(node, _DEFERRED_EXPRS):
        return
    yield node
    if isinstance(node, ast.BoolOp):
        is_and = isinstance(node.op, ast.And)
        is_or = isinstance(node.op, ast.Or)
        for value in node.values:
            yield from _expr_nodes(value)
            truth = _static_truth(value)
            if (is_and and truth is False) or (is_or and truth is True):
                break
        return
    if isinstance(node, ast.IfExp):
        yield from _expr_nodes(node.test)
        truth = _static_truth(node.test)
        if truth is True:
            yield from _expr_nodes(node.body)
        elif truth is False:
            yield from _expr_nodes(node.orelse)
        else:
            yield from _expr_nodes(node.body)
            yield from _expr_nodes(node.orelse)
        return
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, *_DEFERRED_EXPRS)):
            continue
        yield from _expr_nodes(child)


def _known_empty_iter(node: ast.AST) -> bool:
    value = _literal_value(node)
    return value is not _UNKNOWN and isinstance(value, (tuple, list, set, frozenset, dict, str, bytes)) and not value


def _ordinary_literal_iter(node: ast.AST) -> bool:
    value = _literal_value(node)
    return value is not _UNKNOWN and isinstance(value, (tuple, list, set, frozenset, dict, str, bytes))


def _live_nodes_block(statements: Iterable[ast.stmt]) -> Iterable[ast.AST]:
    """Walk a block in execution order and stop after unconditional termination."""
    for stmt in statements:
        yield stmt

        if isinstance(stmt, ast.If):
            yield from _expr_nodes(stmt.test)
            truth = _static_truth(stmt.test)
            if truth is True:
                yield from _live_nodes_block(stmt.body)
            elif truth is False:
                yield from _live_nodes_block(stmt.orelse)
            else:
                yield from _live_nodes_block(stmt.body)
                yield from _live_nodes_block(stmt.orelse)
            continue

        if isinstance(stmt, ast.While):
            yield from _expr_nodes(stmt.test)
            truth = _static_truth(stmt.test)
            if truth is False:
                yield from _live_nodes_block(stmt.orelse)
            else:
                yield from _live_nodes_block(stmt.body)
                yield from _live_nodes_block(stmt.orelse)
            continue

        if isinstance(stmt, ast.For):
            yield from _expr_nodes(stmt.iter)
            if _known_empty_iter(stmt.iter):
                yield from _live_nodes_block(stmt.orelse)
            else:
                yield from _live_nodes_block(stmt.body)
                yield from _live_nodes_block(stmt.orelse)
            continue

        if isinstance(stmt, ast.AsyncFor):
            yield from _expr_nodes(stmt.iter)
            if _ordinary_literal_iter(stmt.iter):
                continue
            yield from _live_nodes_block(stmt.body)
            yield from _live_nodes_block(stmt.orelse)
            continue

        if isinstance(stmt, (ast.With, ast.AsyncWith)):
            for item in stmt.items:
                yield from _expr_nodes(item.context_expr)
            yield from _live_nodes_block(stmt.body)
            continue

        if isinstance(stmt, (ast.Try, getattr(ast, "TryStar", ast.Try))):
            yield from _live_nodes_block(stmt.body)
            yield from _live_nodes_block(stmt.orelse)
            yield from _live_nodes_block(stmt.finalbody)
            continue

        if isinstance(stmt, ast.Return):
            if stmt.value is not None:
                yield from _expr_nodes(stmt.value)
            break
        if isinstance(stmt, ast.Raise):
            if stmt.exc is not None:
                yield from _expr_nodes(stmt.exc)
            if stmt.cause is not None:
                yield from _expr_nodes(stmt.cause)
            break
        if isinstance(stmt, (ast.Break, ast.Continue)):
            break

        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue

        for child in ast.iter_child_nodes(stmt):
            if isinstance(child, ast.stmt):
                continue
            yield from _expr_nodes(child)


def _function_local_names(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    out = {
        arg.arg
        for arg in (
            *fn.args.posonlyargs,
            *fn.args.args,
            *fn.args.kwonlyargs,
        )
    }
    if fn.args.vararg:
        out.add(fn.args.vararg.arg)
    if fn.args.kwarg:
        out.add(fn.args.kwarg.arg)
    out.update(_bound_names_in_statements(fn.body))
    return out


def _reachable_top_level_functions(tree: ast.Module, root_name: str) -> set[ast.FunctionDef | ast.AsyncFunctionDef]:
    module = _bindings(tree.body)
    root = module.get(root_name)
    _require(isinstance(root, (ast.FunctionDef, ast.AsyncFunctionDef)),
             f"router {root_name} is not an unambiguous live function")
    _require(not root.decorator_list, f"router {root_name} may not be decorated")
    reachable: set[ast.FunctionDef | ast.AsyncFunctionDef] = set()
    stack = [root]
    while stack:
        fn = stack.pop()
        if fn in reachable:
            continue
        _require(not fn.decorator_list, f"reachable router function {fn.name} may not be decorated")
        reachable.add(fn)
        locals_ = _function_local_names(fn)
        for node in _live_nodes_block(fn.body):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id in locals_:
                continue
            target = module.get(node.func.id)
            if isinstance(target, (ast.FunctionDef, ast.AsyncFunctionDef)) and target not in reachable:
                stack.append(target)
    return reachable


def _reachable_agent_methods(agent: ast.ClassDef) -> set[ast.FunctionDef | ast.AsyncFunctionDef]:
    methods = _class_methods(agent)
    root = methods.get("act")
    _require(root is not None, "materialized TitanAgent has no live act() method")
    reachable: set[ast.FunctionDef | ast.AsyncFunctionDef] = set()
    stack = [root]
    while stack:
        fn = stack.pop()
        if fn in reachable:
            continue
        _require(not fn.decorator_list, f"reachable TitanAgent method {fn.name} may not be decorated")
        reachable.add(fn)
        for node in _live_nodes_block(fn.body):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if not (isinstance(node.func.value, ast.Name) and node.func.value.id == "self"):
                continue
            target = methods.get(node.func.attr)
            if target is not None and target not in reachable:
                stack.append(target)
    return reachable


def _contains_name_load(node: ast.AST, name: str) -> bool:
    return any(
        isinstance(child, ast.Name) and child.id == name and isinstance(child.ctx, ast.Load)
        for child in _expr_nodes(node)
    )


def _module_call_in_block(statements: Iterable[ast.stmt], module_name: str) -> bool:
    for node in _live_nodes_block(statements):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = node.func.value
            if isinstance(owner, ast.Name) and owner.id == module_name:
                return True
    return False


def _imports_module_in_block(statements: Iterable[ast.stmt], module_name: str) -> bool:
    for stmt in statements:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if alias.name == module_name and (alias.asname is None or alias.asname == module_name):
                    return True
        elif isinstance(stmt, ast.ImportFrom) and stmt.module == module_name:
            return True
        elif isinstance(stmt, ast.If):
            truth = _static_truth(stmt.test)
            if truth is True and _imports_module_in_block(stmt.body, module_name):
                return True
            if truth is False and _imports_module_in_block(stmt.orelse, module_name):
                return True
            if truth is None and (
                _imports_module_in_block(stmt.body, module_name)
                or _imports_module_in_block(stmt.orelse, module_name)
            ):
                return True
    return False


def _router_feature_seam(tree: ast.Module, flag: str, module_name: str) -> bool:
    """Require FLAG to gate the matching r04 module on a reachable production path."""
    for fn in _reachable_top_level_functions(tree, "v3_agent"):
        for node in _live_nodes_block(fn.body):
            if not isinstance(node, (ast.If, ast.While)):
                continue
            test = node.test
            if _static_truth(test) is not None or not _contains_name_load(test, flag):
                continue
            bodies = node.body
            if _imports_module_in_block(bodies, module_name) and _module_call_in_block(bodies, module_name):
                return True
    return False


def _is_none_guard(test: ast.AST, name: str) -> bool:
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == name
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.IsNot)
        and len(test.comparators) == 1
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value is None
    )


def _is_bool_of_name(node: ast.AST, name: str) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "bool"
        and len(node.args) == 1
        and not node.keywords
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == name
    )


def _install_setter_ok(install: ast.FunctionDef | ast.AsyncFunctionDef, flag: str, suffix: str) -> bool:
    for stmt in install.body:
        if not isinstance(stmt, ast.If) or not _is_none_guard(stmt.test, suffix):
            continue
        for child in stmt.body:
            if not isinstance(child, (ast.Assign, ast.AnnAssign)):
                continue
            targets = child.targets if isinstance(child, ast.Assign) else (child.target,)
            value = child.value
            if any(isinstance(target, ast.Name) and target.id == flag for target in targets):
                if value is not None and _is_bool_of_name(value, suffix):
                    return True
    return False


def _global_declared(install: ast.FunctionDef | ast.AsyncFunctionDef, flag: str) -> bool:
    return any(
        isinstance(stmt, ast.Global) and flag in stmt.names
        for stmt in install.body
    )


def _is_self_feature(node: ast.AST, key: str) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == key
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "features"
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "self"
    )


def _exact_feature_value(node: ast.AST, key: str) -> bool:
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


def _stmt_rebinds_name(stmt: ast.stmt, name: str) -> bool:
    return name in _bound_names_in_statements((stmt,))


def _runtime_install_wired(
    reachable: Iterable[ast.FunctionDef | ast.AsyncFunctionDef],
    key: str,
    suffix: str,
) -> bool:
    """Accept only a live call dominated by a direct trusted local import."""
    for fn in reachable:
        trusted: set[str] = set()

        def scan_block(statements: Iterable[ast.stmt], incoming: set[str]) -> bool:
            local_trusted = set(incoming)
            for stmt in statements:
                if isinstance(stmt, ast.ImportFrom) and stmt.level == 0 and stmt.module == "r04_full_router":
                    for alias in stmt.names:
                        bound = alias.asname or alias.name
                        if alias.name == "install":
                            local_trusted.add(bound)
                        elif bound in local_trusted:
                            local_trusted.discard(bound)
                    continue

                if isinstance(stmt, ast.If):
                    truth = _static_truth(stmt.test)
                    branches = [stmt.body] if truth is True else [stmt.orelse] if truth is False else [stmt.body, stmt.orelse]
                    if any(scan_block(branch, set(local_trusted)) for branch in branches):
                        return True
                    for name in list(local_trusted):
                        if any(name in _bound_names_in_statements(branch) for branch in branches):
                            local_trusted.discard(name)
                    continue

                if isinstance(stmt, (ast.Try, getattr(ast, "TryStar", ast.Try))):
                    if scan_block(stmt.body, set(local_trusted)):
                        return True
                    if scan_block(stmt.orelse, set(local_trusted)):
                        return True
                    if scan_block(stmt.finalbody, set(local_trusted)):
                        return True
                    for name in list(local_trusted):
                        if name in _bound_names_in_statements((*stmt.body, *stmt.orelse, *stmt.finalbody, *(x for h in stmt.handlers for x in h.body))):
                            local_trusted.discard(name)
                    continue

                if isinstance(stmt, (ast.With, ast.AsyncWith)):
                    if scan_block(stmt.body, set(local_trusted)):
                        return True

                for node in _live_nodes_block((stmt,)):
                    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                        continue
                    if node.func.id not in local_trusted:
                        continue
                    for keyword in node.keywords:
                        if keyword.arg == suffix and _exact_feature_value(keyword.value, key):
                            return True

                for name in list(local_trusted):
                    if _stmt_rebinds_name(stmt, name):
                        local_trusted.discard(name)

                if isinstance(stmt, (ast.Return, ast.Raise)):
                    break
            return False

        if scan_block(fn.body, trusted):
            return True
    return False


def _feature_defaults(features: ast.ClassDef) -> dict[str, object]:
    resolved = _bindings(features.body)
    out: dict[str, object] = {}
    for name, value in resolved.items():
        if isinstance(value, ast.AST) and not isinstance(value, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            literal = _literal_value(value)
            if literal is not _UNKNOWN:
                out[name] = literal
    return out


def _mutates_feature_key(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    key: str,
    *,
    through_features: bool,
) -> bool:
    for node in _live_nodes_block(fn.body):
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del)):
            if through_features and _is_self_feature(node, key):
                return True
            if (
                not through_features
                and node.attr == key
                and isinstance(node.value, ast.Name)
                and node.value.id == "self"
            ):
                return True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"setattr", "delattr"}:
            if len(node.args) < 2 or not isinstance(node.args[1], ast.Constant) or node.args[1].value != key:
                continue
            owner = node.args[0]
            if through_features:
                if (
                    isinstance(owner, ast.Attribute)
                    and owner.attr == "features"
                    and isinstance(owner.value, ast.Name)
                    and owner.value.id == "self"
                ):
                    return True
            elif isinstance(owner, ast.Name) and owner.id == "self":
                return True
    return False


def _class_has_safe_decorator(cls: ast.ClassDef, *, features: bool) -> bool:
    if not cls.decorator_list:
        return True
    if not features:
        return False
    for deco in cls.decorator_list:
        target = deco.func if isinstance(deco, ast.Call) else deco
        if isinstance(target, ast.Name) and target.id == "dataclass":
            continue
        if isinstance(target, ast.Attribute) and target.attr == "dataclass":
            continue
        return False
    return True


def _literal_keys(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    value = _bindings(tree.body).get("KEYS")
    _require(isinstance(value, ast.AST), f"{path}: KEYS is not a final literal binding")
    literal = _literal_value(value)
    _require(isinstance(literal, (tuple, list)), f"{path}: KEYS must be a literal tuple/list")
    keys = tuple(literal)
    _require(keys, f"{path}: KEYS must not be empty")
    _require(all(type(key) is str and key for key in keys), f"{path}: KEYS must contain nonempty strings")
    _require(len(keys) == len(set(keys)), f"{path}: KEYS contains duplicates")
    return keys


def _self_test() -> None:
    _require(_static_truth(ast.parse("not True", mode="eval").body) is False, "not folding")
    _require(_static_truth(ast.parse("FLAG and False", mode="eval").body) is False, "and folding")
    _require(_static_truth(ast.parse("FLAG or True", mode="eval").body) is True, "or folding")
    _require(_static_truth(ast.parse("1 == 0", mode="eval").body) is False, "compare folding")

    rebound = ast.parse("""
class TitanAgent:
    def act(self): return None
if True:
    TitanAgent = object()
""")
    _require(not isinstance(_bindings(rebound.body).get("TitanAgent"), ast.ClassDef), "module rebind false-pass")

    member = ast.parse("""
class TitanAgent:
    def act(self): return self._wired()
    def _wired(self): return None
    act = None
""")
    cls = _final_class(member, "TitanAgent")
    _require("act" not in _class_methods(cls), "class member rebind false-pass")

    post_return = ast.parse("""
def act():
    return None
    forbidden()
""")
    fn = post_return.body[0]
    _require(isinstance(fn, ast.FunctionDef), "test setup")
    _require(not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "forbidden"
                     for n in _live_nodes_block(fn.body)), "post-return call false-pass")

    router_ok = ast.parse("""
FLAG = False
def v3_agent(observation, configuration=None):
    if FLAG:
        import r04_x
        return r04_x.apply_x(observation)
    return observation
def install(x=None):
    global FLAG
    if x is not None:
        FLAG = bool(x)
    return v3_agent
""")
    _require(_router_feature_seam(router_ok, "FLAG", "r04_x"), "live router seam missed")
    install = _final_function(router_ok, "install")
    _require(_global_declared(install, "FLAG") and _install_setter_ok(install, "FLAG", "x"), "setter missed")

    orphan = ast.parse("""
FLAG = False
def v3_agent(observation, configuration=None):
    marker = FLAG
    return observation
def dead():
    if FLAG:
        import r04_x
        return r04_x.apply_x(None)
""")
    _require(not _router_feature_seam(orphan, "FLAG", "r04_x"), "orphan/read-only seam false-pass")

    dead_cond = ast.parse("""
FLAG = False
def v3_agent(observation, configuration=None):
    if FLAG and False:
        import r04_x
        return r04_x.apply_x(observation)
    return observation
""")
    _require(not _router_feature_seam(dead_cond, "FLAG", "r04_x"), "constant-dead seam false-pass")

    runtime_ok = ast.parse("""
class TitanAgent:
    def act(self):
        return self._route()
    def _route(self):
        from r04_full_router import install
        return install(x=bool(self.features.r04_x))
""")
    agent = _final_class(runtime_ok, "TitanAgent")
    reach = _reachable_agent_methods(agent)
    _require(_runtime_install_wired(reach, "r04_x", "x"), "trusted runtime wiring missed")

    fake = ast.parse("""
class TitanAgent:
    def act(self):
        from fake_router import install
        return install(x=self.features.r04_x)
""")
    _require(not _runtime_install_wired(_reachable_agent_methods(_final_class(fake, "TitanAgent")), "r04_x", "x"),
             "fake install false-pass")

    polarity = ast.parse("""
class TitanAgent:
    def act(self):
        from r04_full_router import install
        return install(x=(self.features.r04_x and False))
""")
    _require(not _runtime_install_wired(_reachable_agent_methods(_final_class(polarity, "TitanAgent")), "r04_x", "x"),
             "non-value-preserving runtime wiring false-pass")

    mutation = ast.parse("""
class Features:
    r04_x = False
    def __post_init__(self):
        self.r04_x = True
""")
    fcls = _final_class(mutation, "Features")
    post = _class_methods(fcls)["__post_init__"]
    _require(_mutates_feature_key(post, "r04_x", through_features=False), "Features mutation missed")

    shadow_calls = ast.parse("""
FLAG = False
def helper():
    if FLAG:
        import r04_x
        return r04_x.apply_x(None)
def v3_agent():
    helper = lambda: None
    return helper()
""")
    _require(not _router_feature_seam(shadow_calls, "FLAG", "r04_x"), "local-shadow call false-pass")


def check(base_apply_v4: Path) -> None:
    _self_test()

    base_keys = _literal_keys(base_apply_v4)
    head_keys = _literal_keys(APPLY_V4)
    removed = sorted(set(base_keys) - set(head_keys))
    _require(not removed, "V4 recomposition removed already-landed key(s): " + ", ".join(removed))

    import build_v3

    files = build_v3.package_files()
    for required in ("TITAN-CONFIG.json", "titan_runtime.py", "r04_full_router.py"):
        _require(required in files, f"materialized package missing {required}")

    config = json.loads(files["TITAN-CONFIG.json"].decode("utf-8"))
    runtime_tree = ast.parse(files["titan_runtime.py"].decode("utf-8"), filename="titan_runtime.py")
    router_tree = ast.parse(files["r04_full_router.py"].decode("utf-8"), filename="r04_full_router.py")

    features = _final_class(runtime_tree, "Features")
    agent = _final_class(runtime_tree, "TitanAgent")
    _require(_class_has_safe_decorator(features, features=True), "Features has an untrusted decorator")
    _require(_class_has_safe_decorator(agent, features=False), "TitanAgent has a decorator")
    feature_defaults = _feature_defaults(features)
    methods = _class_methods(agent)
    reachable_agent = _reachable_agent_methods(agent)

    feature_post = _class_methods(features).get("__post_init__")
    mutation_surfaces = set(reachable_agent)
    for name in ("__init__", "__post_init__"):
        if name in methods:
            mutation_surfaces.add(methods[name])

    router_bindings = _bindings(router_tree.body)
    install = _final_function(router_tree, "install")

    for key in head_keys:
        _require(key in config, f"{key}: missing from materialized TITAN-CONFIG.json")
        _require(type(config[key]) is bool and config[key] is False,
                 f"{key}: bootstrap plumbing guard requires materialized config False")

        _require(key in feature_defaults, f"{key}: missing from materialized Features")
        _require(type(feature_defaults[key]) is bool and feature_defaults[key] is False,
                 f"{key}: Features default must remain False")
        if feature_post is not None:
            _require(not _mutates_feature_key(feature_post, key, through_features=False),
                     f"{key}: Features.__post_init__ mutates an OFF V4 key")
        for fn in mutation_surfaces:
            _require(not _mutates_feature_key(fn, key, through_features=True),
                     f"{key}: TitanAgent runtime mutates an OFF V4 key")

        if not key.startswith("r04_"):
            _require(
                any(_is_self_feature(node, key) and isinstance(node.ctx, ast.Load)
                    for fn in reachable_agent for node in _live_nodes_block(fn.body)),
                f"{key}: TitanAgent.act chain never reads self.features.{key}",
            )
            continue

        suffix = key.removeprefix("r04_")
        flag = suffix.upper()
        module_name = key

        flag_binding = router_bindings.get(flag)
        _require(isinstance(flag_binding, ast.AST), f"{key}: router {flag} is not a final literal binding")
        flag_value = _literal_value(flag_binding)
        _require(type(flag_value) is bool and flag_value is False,
                 f"{key}: router {flag} must remain source-default False")

        keywordable = {arg.arg for arg in (*install.args.args, *install.args.kwonlyargs)}
        positional_only = {arg.arg for arg in install.args.posonlyargs}
        _require(suffix in keywordable and suffix not in positional_only,
                 f"{key}: install({suffix}=...) must accept the suffix by keyword")
        _require(_global_declared(install, flag), f"{key}: install() missing global {flag}")
        _require(_install_setter_ok(install, flag, suffix),
                 f"{key}: install() must set {flag}=bool({suffix}) under '{suffix} is not None'")
        _require(_router_feature_seam(router_tree, flag, module_name),
                 f"{key}: no reachable {flag}-gated call into matching module {module_name}")
        _require(_runtime_install_wired(reachable_agent, key, suffix),
                 f"{key}: TitanAgent.act chain lacks trusted r04_full_router.install({suffix}=bool(self.features.{key})) wiring")

    print(
        "V4 PLUMBING OK",
        "base", list(base_keys),
        "head", list(head_keys),
        "mode", "bootstrap-all-off",
        "reachable_agent_methods", sorted(fn.name for fn in reachable_agent),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-apply-v4", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        _self_test()
        print("V4 PLUMBING SELF-TEST OK")
        return
    _require(args.base_apply_v4 is not None, "--base-apply-v4 is required")
    check(args.base_apply_v4)


if __name__ == "__main__":
    main()
