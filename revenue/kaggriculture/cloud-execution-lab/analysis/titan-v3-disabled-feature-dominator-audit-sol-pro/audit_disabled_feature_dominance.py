#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed, stdlib-only audit for optional TITAN stage dominance.

The audit asks one narrow question for each rule: can the named implementation
call be evaluated when every feature predicate assigned by that rule is false?
If yes, the feature is not semantically off and the rule rejects the source.

This is deliberately a source-level release gate, not a game simulator.  It
models Python boolean short-circuiting and conservative control-flow reachability.
Unknown state predicates fork both ways, so ambiguity cannot manufacture a pass.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "titan.disabled-feature-dominance.v1"
UNKNOWN = object()


@dataclass(frozen=True)
class ExprResult:
    values: frozenset[bool]
    hits: tuple[int, ...] = ()


@dataclass(frozen=True)
class FlowResult:
    falls_through: bool
    hits: tuple[int, ...] = ()


def _merge_hits(*groups: Iterable[int]) -> tuple[int, ...]:
    return tuple(sorted(set(x for group in groups for x in group)))


def dotted_name(node: ast.AST | None) -> str | None:
    """Return a stable dotted spelling for names/attributes, else ``None``."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else None
    return None


def call_name(node: ast.Call) -> str | None:
    return dotted_name(node.func)


class TargetMatcher:
    def __init__(self, target: str, mode: str = "exact") -> None:
        if mode not in {"exact", "suffix"}:
            raise ValueError(f"unsupported target match mode: {mode}")
        self.target = target
        self.mode = mode

    def matches(self, node: ast.Call) -> bool:
        name = call_name(node)
        if name is None:
            return False
        if self.mode == "exact":
            return name == self.target
        return name == self.target or name.endswith("." + self.target)


def _known_scalar(node: ast.AST, env: Mapping[str, Any]) -> Any:
    name = dotted_name(node)
    if name is not None and name in env:
        return env[name]
    if isinstance(node, ast.Constant):
        return node.value
    return UNKNOWN


def _scan_unknown_expr(node: ast.AST, env: Mapping[str, Any], matcher: TargetMatcher) -> ExprResult:
    """Conservatively evaluate children when expression semantics are unsupported."""
    hits: tuple[int, ...] = ()
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.expr):
            hits = _merge_hits(hits, eval_expr(child, env, matcher).hits)
    return ExprResult(frozenset({False, True}), hits)


def eval_expr(node: ast.AST | None, env: Mapping[str, Any], matcher: TargetMatcher) -> ExprResult:
    """Evaluate possible truth values and calls reached under one fixed off-world.

    Unknown non-feature state yields both truth values.  Boolean operators retain
    Python short-circuit order, which is the key distinction between a real gate
    and a nearby but non-dominating condition.
    """
    if node is None:
        return ExprResult(frozenset({False}))

    if isinstance(node, ast.Constant):
        return ExprResult(frozenset({bool(node.value)}))

    name = dotted_name(node)
    if name is not None and name in env:
        return ExprResult(frozenset({bool(env[name])}))

    if isinstance(node, (ast.Name, ast.Attribute, ast.Subscript)):
        return ExprResult(frozenset({False, True}))

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        inner = eval_expr(node.operand, env, matcher)
        return ExprResult(frozenset(not value for value in inner.values), inner.hits)

    if isinstance(node, ast.BoolOp):
        hits: tuple[int, ...] = ()
        if isinstance(node.op, ast.And):
            can_continue = True
            can_be_false = False
            for value in node.values:
                if not can_continue:
                    break
                result = eval_expr(value, env, matcher)
                hits = _merge_hits(hits, result.hits)
                can_be_false = can_be_false or False in result.values
                can_continue = True in result.values
            possible = ({False} if can_be_false else set()) | ({True} if can_continue else set())
            return ExprResult(frozenset(possible or {False}), hits)
        if isinstance(node.op, ast.Or):
            can_continue = True
            can_be_true = False
            for value in node.values:
                if not can_continue:
                    break
                result = eval_expr(value, env, matcher)
                hits = _merge_hits(hits, result.hits)
                can_be_true = can_be_true or True in result.values
                can_continue = False in result.values
            possible = ({True} if can_be_true else set()) | ({False} if can_continue else set())
            return ExprResult(frozenset(possible or {True}), hits)

    if isinstance(node, ast.Compare):
        hits: tuple[int, ...] = ()
        for part in (node.left, *node.comparators):
            hits = _merge_hits(hits, eval_expr(part, env, matcher).hits)
        if len(node.ops) == 1 and len(node.comparators) == 1:
            left = _known_scalar(node.left, env)
            right = _known_scalar(node.comparators[0], env)
            if left is not UNKNOWN and right is not UNKNOWN:
                op = node.ops[0]
                try:
                    if isinstance(op, (ast.Eq, ast.Is)):
                        value = left == right
                    elif isinstance(op, (ast.NotEq, ast.IsNot)):
                        value = left != right
                    elif isinstance(op, ast.Lt):
                        value = left < right
                    elif isinstance(op, ast.LtE):
                        value = left <= right
                    elif isinstance(op, ast.Gt):
                        value = left > right
                    elif isinstance(op, ast.GtE):
                        value = left >= right
                    elif isinstance(op, ast.In):
                        value = left in right
                    elif isinstance(op, ast.NotIn):
                        value = left not in right
                    else:
                        return ExprResult(frozenset({False, True}), hits)
                    return ExprResult(frozenset({bool(value)}), hits)
                except (TypeError, ValueError):
                    pass
        return ExprResult(frozenset({False, True}), hits)

    if isinstance(node, ast.Call):
        hits: tuple[int, ...] = ()
        # Python evaluates the callable object, positional args, then keywords.
        hits = _merge_hits(hits, eval_expr(node.func, env, matcher).hits)
        for arg in node.args:
            hits = _merge_hits(hits, eval_expr(arg, env, matcher).hits)
        for kw in node.keywords:
            hits = _merge_hits(hits, eval_expr(kw.value, env, matcher).hits)
        if matcher.matches(node):
            hits = _merge_hits(hits, (getattr(node, "lineno", -1),))
        return ExprResult(frozenset({False, True}), hits)

    if isinstance(node, ast.IfExp):
        condition = eval_expr(node.test, env, matcher)
        hits = condition.hits
        possible: set[bool] = set()
        if True in condition.values:
            branch = eval_expr(node.body, env, matcher)
            possible.update(branch.values)
            hits = _merge_hits(hits, branch.hits)
        if False in condition.values:
            branch = eval_expr(node.orelse, env, matcher)
            possible.update(branch.values)
            hits = _merge_hits(hits, branch.hits)
        return ExprResult(frozenset(possible or {False, True}), hits)

    if isinstance(node, ast.NamedExpr):
        return eval_expr(node.value, env, matcher)

    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        hits: tuple[int, ...] = ()
        for elt in node.elts:
            hits = _merge_hits(hits, eval_expr(elt, env, matcher).hits)
        return ExprResult(frozenset({bool(node.elts)}), hits)

    if isinstance(node, ast.Dict):
        hits: tuple[int, ...] = ()
        for key, value in zip(node.keys, node.values):
            hits = _merge_hits(hits, eval_expr(key, env, matcher).hits,
                               eval_expr(value, env, matcher).hits)
        return ExprResult(frozenset({bool(node.keys)}), hits)

    return _scan_unknown_expr(node, env, matcher)


def _exprs_from_assignment(stmt: ast.stmt) -> Sequence[ast.AST | None]:
    if isinstance(stmt, ast.Assign):
        return (stmt.value,)
    if isinstance(stmt, ast.AnnAssign):
        return (stmt.value,)
    if isinstance(stmt, ast.AugAssign):
        return (stmt.target, stmt.value)
    if isinstance(stmt, ast.Delete):
        return tuple(stmt.targets)
    return ()


def walk_block(statements: Sequence[ast.stmt], env: Mapping[str, Any], matcher: TargetMatcher) -> FlowResult:
    falls_through = True
    hits: tuple[int, ...] = ()
    for statement in statements:
        if not falls_through:
            break
        result = walk_statement(statement, env, matcher)
        hits = _merge_hits(hits, result.hits)
        falls_through = result.falls_through
    return FlowResult(falls_through, hits)


def walk_statement(stmt: ast.stmt, env: Mapping[str, Any], matcher: TargetMatcher) -> FlowResult:
    if isinstance(stmt, ast.If):
        condition = eval_expr(stmt.test, env, matcher)
        hits = condition.hits
        branch_fallthrough: list[bool] = []
        if True in condition.values:
            branch = walk_block(stmt.body, env, matcher)
            hits = _merge_hits(hits, branch.hits)
            branch_fallthrough.append(branch.falls_through)
        if False in condition.values:
            branch = walk_block(stmt.orelse, env, matcher) if stmt.orelse else FlowResult(True)
            hits = _merge_hits(hits, branch.hits)
            branch_fallthrough.append(branch.falls_through)
        return FlowResult(any(branch_fallthrough), hits)

    if isinstance(stmt, (ast.Return, ast.Raise)):
        value = stmt.value if isinstance(stmt, ast.Return) else stmt.exc
        result = eval_expr(value, env, matcher)
        return FlowResult(False, result.hits)

    if isinstance(stmt, ast.Expr):
        result = eval_expr(stmt.value, env, matcher)
        return FlowResult(True, result.hits)

    if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete)):
        hits: tuple[int, ...] = ()
        for expression in _exprs_from_assignment(stmt):
            hits = _merge_hits(hits, eval_expr(expression, env, matcher).hits)
        return FlowResult(True, hits)

    if isinstance(stmt, ast.Assert):
        test = eval_expr(stmt.test, env, matcher)
        message = eval_expr(stmt.msg, env, matcher) if False in test.values else ExprResult(frozenset())
        return FlowResult(True in test.values, _merge_hits(test.hits, message.hits))

    if isinstance(stmt, (ast.For, ast.AsyncFor)):
        iterator = eval_expr(stmt.iter, env, matcher)
        body = walk_block(stmt.body, env, matcher)
        otherwise = walk_block(stmt.orelse, env, matcher)
        # A conservative loop may execute zero or at least one iteration.
        return FlowResult(True, _merge_hits(iterator.hits, body.hits, otherwise.hits))

    if isinstance(stmt, ast.While):
        condition = eval_expr(stmt.test, env, matcher)
        hits = condition.hits
        if True in condition.values:
            hits = _merge_hits(hits, walk_block(stmt.body, env, matcher).hits)
        if False in condition.values or stmt.orelse:
            hits = _merge_hits(hits, walk_block(stmt.orelse, env, matcher).hits)
        # Treat loop exit as possible; this avoids false dominance proofs.
        return FlowResult(True, hits)

    if isinstance(stmt, (ast.With, ast.AsyncWith)):
        hits: tuple[int, ...] = ()
        for item in stmt.items:
            hits = _merge_hits(hits, eval_expr(item.context_expr, env, matcher).hits)
        body = walk_block(stmt.body, env, matcher)
        return FlowResult(body.falls_through, _merge_hits(hits, body.hits))

    if isinstance(stmt, ast.Try):
        body = walk_block(stmt.body, env, matcher)
        branches = [body.falls_through]
        hits = body.hits
        for handler in stmt.handlers:
            branch = walk_block(handler.body, env, matcher)
            branches.append(branch.falls_through)
            hits = _merge_hits(hits, branch.hits)
        otherwise = walk_block(stmt.orelse, env, matcher)
        hits = _merge_hits(hits, otherwise.hits)
        branches.append(otherwise.falls_through)
        final = walk_block(stmt.finalbody, env, matcher)
        hits = _merge_hits(hits, final.hits)
        return FlowResult(final.falls_through and any(branches), hits)

    if isinstance(stmt, ast.Match):
        subject = eval_expr(stmt.subject, env, matcher)
        hits = subject.hits
        falls = not stmt.cases
        for case in stmt.cases:
            guard = eval_expr(case.guard, env, matcher)
            branch = walk_block(case.body, env, matcher)
            hits = _merge_hits(hits, guard.hits, branch.hits)
            falls = falls or branch.falls_through
        return FlowResult(falls, hits)

    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        # Defining a nested object evaluates decorators/defaults but not its body.
        hits: tuple[int, ...] = ()
        for decorator in stmt.decorator_list:
            hits = _merge_hits(hits, eval_expr(decorator, env, matcher).hits)
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defaults = (*stmt.args.defaults, *[x for x in stmt.args.kw_defaults if x is not None])
            for default in defaults:
                hits = _merge_hits(hits, eval_expr(default, env, matcher).hits)
        return FlowResult(True, hits)

    if isinstance(stmt, (ast.Break, ast.Continue)):
        return FlowResult(False)

    # Import, pass, global/nonlocal and unsupported statements are non-terminating.
    hits: tuple[int, ...] = ()
    for child in ast.iter_child_nodes(stmt):
        if isinstance(child, ast.expr):
            hits = _merge_hits(hits, eval_expr(child, env, matcher).hits)
    return FlowResult(True, hits)


def find_function(tree: ast.Module, class_name: str | None, function_name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    scope: Sequence[ast.stmt] = tree.body
    if class_name:
        klass = next((node for node in tree.body
                      if isinstance(node, ast.ClassDef) and node.name == class_name), None)
        if klass is None:
            return None
        scope = klass.body
    return next((node for node in scope
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and node.name == function_name), None)


def syntactic_target_lines(function: ast.AST, matcher: TargetMatcher) -> list[int]:
    return sorted({node.lineno for node in ast.walk(function)
                   if isinstance(node, ast.Call) and matcher.matches(node)})


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def source_identity(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": git_blob_sha1(data),
    }


def audit_rule(root: Path, rule: Mapping[str, Any], cache: dict[Path, tuple[str, ast.Module]]) -> dict[str, Any]:
    relative = Path(str(rule["file"]))
    path = root / relative
    base = {
        "id": str(rule["id"]),
        "description": str(rule.get("description", "")),
        "severity": str(rule.get("severity", "error")),
        "file": relative.as_posix(),
        "class": rule.get("class"),
        "function": str(rule["function"]),
        "target": str(rule["target"]),
        "match": str(rule.get("match", "exact")),
        "off_world": dict(rule.get("off_world", {})),
    }
    if not path.is_file():
        return {**base, "status": "reject", "code": "SOURCE_NOT_FOUND",
                "detail": f"missing source: {relative.as_posix()}", "target_lines": [],
                "reachable_off_lines": []}

    try:
        if path not in cache:
            text = path.read_text(encoding="utf-8")
            cache[path] = (text, ast.parse(text, filename=relative.as_posix()))
        text, tree = cache[path]
    except (OSError, UnicodeError, SyntaxError) as exc:
        return {**base, "status": "reject", "code": "SOURCE_PARSE_FAILED",
                "detail": f"{type(exc).__name__}: {exc}", "target_lines": [],
                "reachable_off_lines": []}

    function = find_function(tree, rule.get("class"), str(rule["function"]))
    if function is None:
        return {**base, "status": "reject", "code": "FUNCTION_NOT_FOUND",
                "detail": "audited function is absent; rule update is required",
                "target_lines": [], "reachable_off_lines": []}

    matcher = TargetMatcher(str(rule["target"]), str(rule.get("match", "exact")))
    target_lines = syntactic_target_lines(function, matcher)
    if not target_lines:
        return {**base, "status": "reject", "code": "TARGET_NOT_FOUND",
                "detail": "named stage call is absent; rule update is required",
                "function_lines": [function.lineno, getattr(function, "end_lineno", function.lineno)],
                "target_lines": [], "reachable_off_lines": []}

    flow = walk_block(function.body, dict(rule.get("off_world", {})), matcher)
    reachable = sorted(set(flow.hits))
    status = "reject" if reachable else "accept"
    code = "OFF_PATH_REACHABLE" if reachable else "OFF_PATH_UNREACHABLE"
    detail = ("target call can execute with every controlling feature false"
              if reachable else
              "all target calls are unreachable in the declared all-off world")
    return {
        **base,
        "status": status,
        "code": code,
        "detail": detail,
        "function_lines": [function.lineno, getattr(function, "end_lineno", function.lineno)],
        "target_lines": target_lines,
        "reachable_off_lines": reachable,
    }


def audit(root: Path, rules: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    root = root.resolve()
    cache: dict[Path, tuple[str, ast.Module]] = {}
    results = [audit_rule(root, rule, cache) for rule in rules]
    errors = [result["id"] for result in results
              if result["severity"] == "error" and result["status"] == "reject"]
    warnings = [result["id"] for result in results
                if result["severity"] == "warning" and result["status"] == "reject"]
    sources = {}
    for relative in sorted({str(rule["file"]) for rule in rules}):
        path = root / relative
        if path.is_file():
            identity = source_identity(path)
            identity["path"] = relative
            sources[relative] = identity
    return {
        "schema": SCHEMA,
        "status": "reject" if errors else "accept",
        "error_rule_ids": errors,
        "warning_rule_ids": warnings,
        "summary": {
            "rules": len(results),
            "accepted": sum(result["status"] == "accept" for result in results),
            "rejected_errors": len(errors),
            "rejected_warnings": len(warnings),
        },
        "sources": sources,
        "rules": results,
    }


def load_rules(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "titan.disabled-feature-dominance.rules.v1":
        raise ValueError(f"unsupported rules schema in {path}")
    rules = payload.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("rules must be a non-empty list")
    for index, rule in enumerate(rules):
        required = {"id", "file", "function", "target", "off_world"}
        missing = required - set(rule)
        if missing:
            raise ValueError(f"rule {index} missing {sorted(missing)}")
        if rule.get("severity", "error") not in {"error", "warning"}:
            raise ValueError(f"rule {rule['id']} has invalid severity")
        if not isinstance(rule["off_world"], dict) or not rule["off_world"]:
            raise ValueError(f"rule {rule['id']} needs a non-empty off_world")
    return rules


def default_root() -> Path:
    # .../repo/revenue/kaggriculture/cloud-execution-lab/analysis/<lane>/script.py
    return Path(__file__).resolve().parents[5]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_root(),
                        help="repository root (default: inferred from script location)")
    parser.add_argument("--rules", type=Path, default=here / "rules.json")
    parser.add_argument("--output", type=Path, help="write the deterministic JSON receipt here")
    parser.add_argument("--expect", choices=("accept", "reject", "either"), default="either",
                        help="exit nonzero unless the aggregate classification matches")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        rules = load_rules(args.rules)
        report = audit(args.root, rules)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"audit setup failed: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, sort_keys=True,
                          indent=None if args.compact else 2,
                          separators=(",", ":") if args.compact else None) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if args.expect != "either" and report["status"] != args.expect:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
