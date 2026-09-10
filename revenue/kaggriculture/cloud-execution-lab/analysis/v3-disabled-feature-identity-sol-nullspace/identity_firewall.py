#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-bound and lockstep contracts for disabled optional policy domains."""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import random
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


class ContractError(RuntimeError):
    pass


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def _flag(node: ast.AST) -> str | None:
    name = _name(node)
    return name.rsplit(".", 1)[-1] if name else None


def _positive_any(node: ast.AST) -> frozenset[str] | None:
    flag = _flag(node)
    if flag and isinstance(node, (ast.Name, ast.Attribute)):
        return frozenset((flag,))
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        groups = [_positive_any(item) for item in node.values]
        return frozenset().union(*groups) if all(groups) else None
    if isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1:
        flag = _flag(node.left)
        right = node.comparators[0]
        if flag and isinstance(node.ops[0], (ast.Is, ast.Eq)) and isinstance(right, ast.Constant) and right.value is True:
            return frozenset((flag,))
    return None


def _negative_all(node: ast.AST) -> frozenset[str] | None:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return _positive_any(node.operand) or (frozenset((_flag(node.operand),)) if _flag(node.operand) else None)
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        groups = [_negative_all(item) for item in node.values]
        return frozenset().union(*groups) if all(groups) else None
    if isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1:
        flag = _flag(node.left)
        right = node.comparators[0]
        if flag and isinstance(node.ops[0], (ast.Is, ast.Eq)) and isinstance(right, ast.Constant) and right.value is False:
            return frozenset((flag,))
    return None


def _terminates(body: Sequence[ast.stmt]) -> bool:
    return any(
        isinstance(stmt, (ast.Return, ast.Raise))
        or (isinstance(stmt, ast.If) and stmt.orelse and _terminates(stmt.body) and _terminates(stmt.orelse))
        for stmt in body
    )


def _calls(node: ast.AST) -> list[ast.Call]:
    found: list[ast.Call] = []

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, call: ast.Call) -> None:  # noqa: N802
            found.append(call)
            self.generic_visit(call)

        def visit_FunctionDef(self, _node: ast.FunctionDef) -> None:  # noqa: N802
            return

        visit_AsyncFunctionDef = visit_FunctionDef
        visit_ClassDef = visit_FunctionDef
        visit_Lambda = visit_FunctionDef

    Visitor().visit(node)
    return found


def _class(tree: ast.Module, name: str) -> ast.ClassDef:
    node = next((item for item in tree.body if isinstance(item, ast.ClassDef) and item.name == name), None)
    if node is None:
        raise ContractError(f"class {name!r} not found")
    return node


def _method(cls: ast.ClassDef, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    node = next((item for item in cls.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name), None)
    if node is None:
        raise ContractError(f"method {cls.name}.{name} not found")
    return node


def _call_findings(source: str, path: str, tree: ast.Module, rule: Mapping[str, Any]) -> list[dict[str, Any]]:
    cls = _class(tree, str(rule["class"]))
    method = _method(cls, str(rule["method"]))
    protected = {str(item) for item in rule["calls"]}
    required = frozenset(str(item) for item in rule["requires_any"])
    findings: list[dict[str, Any]] = []

    def proved(gates: Sequence[frozenset[str]]) -> bool:
        return any(gate and gate <= required for gate in gates)

    def inspect(call: ast.Call, gates: Sequence[frozenset[str]]) -> None:
        symbol = _name(call.func) or ast.unparse(call.func)
        if symbol in protected and not proved(gates):
            findings.append({
                "key": f"{rule['id']}::unguarded_call::{symbol}",
                "rule_id": str(rule["id"]), "kind": "unguarded_call",
                "path": path, "class": cls.name, "method": method.name,
                "symbol": symbol, "lineno": call.lineno,
                "required_any": sorted(required),
                "dominating_gates": [sorted(gate) for gate in gates],
            })

    def walk(body: Sequence[ast.stmt], inherited: Sequence[frozenset[str]]) -> None:
        gates = list(inherited)
        for stmt in body:
            if isinstance(stmt, ast.If):
                for call in _calls(stmt.test):
                    inspect(call, gates)
                positive = _positive_any(stmt.test)
                walk(stmt.body, [*gates, positive] if positive else gates)
                walk(stmt.orelse, gates)
                negative = _negative_all(stmt.test)
                if not stmt.orelse and negative and _terminates(stmt.body):
                    gates.append(negative)
                continue
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            for call in _calls(stmt):
                inspect(call, gates)

    walk(method.body, [])
    return findings


def audit_contract(root: Path, contract: Mapping[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    parsed: dict[str, tuple[str, ast.Module]] = {}
    bindings: dict[str, Any] = {}
    for relative, expected in contract.get("files", {}).items():
        path = root / str(relative)
        if not path.is_file():
            raise ContractError(f"bound source file missing: {path}")
        data = path.read_bytes()
        actual = git_blob_sha1(data)
        if actual != str(expected["git_blob_sha1"]):
            raise ContractError(f"source binding mismatch for {relative}: expected {expected['git_blob_sha1']}, got {actual}")
        source = data.decode()
        parsed[str(relative)] = (source, ast.parse(source, filename=str(path)))
        bindings[str(relative)] = {"git_blob_sha1": actual, "bytes": len(data)}

    findings: list[dict[str, Any]] = []
    for rule in contract.get("field_rules", []):
        relative = str(rule["path"])
        cls = _class(parsed[relative][1], str(rule["class"]))
        fields = {
            target.id
            for stmt in cls.body
            for target in ([stmt.target] if isinstance(stmt, ast.AnnAssign) else stmt.targets if isinstance(stmt, ast.Assign) else [])
            if isinstance(target, ast.Name)
        }
        for symbol in map(str, rule["required"]):
            if symbol not in fields:
                findings.append({
                    "key": f"{rule['id']}::missing_field::{symbol}",
                    "rule_id": str(rule["id"]), "kind": "missing_field",
                    "path": relative, "class": cls.name, "method": None,
                    "symbol": symbol, "lineno": cls.lineno,
                })
    for rule in contract.get("call_rules", []):
        relative = str(rule["path"])
        source, tree = parsed[relative]
        findings.extend(_call_findings(source, relative, tree, rule))

    findings.sort(key=lambda item: item["key"])
    actual = [item["key"] for item in findings]
    expected = sorted(map(str, contract.get("expected_current_findings", [])))
    matches = actual == expected
    return {
        "schema_version": 1,
        "source_ref": str(contract.get("source_ref", "unknown")),
        "root": str(root),
        "status": "clean" if not findings else "expected_violation" if matches else "unexpected_violation_set",
        "clean": not findings,
        "expectation_matches": matches,
        "file_bindings": bindings,
        "expected_findings": expected,
        "actual_findings": actual,
        "findings": findings,
    }


def _canonical(value: Any, seen: set[int] | None = None) -> Any:
    if seen is None:
        seen = set()
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return {"bytes_sha256": hashlib.sha256(value).hexdigest(), "length": len(value)}
    identity = id(value)
    if identity in seen:
        return {"cycle": type(value).__qualname__}
    seen.add(identity)
    try:
        if isinstance(value, Mapping):
            return {str(key): _canonical(item, seen) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
        if isinstance(value, (list, tuple)):
            return [_canonical(item, seen) for item in value]
        if isinstance(value, (set, frozenset)):
            return sorted((_canonical(item, seen) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
        if hasattr(value, "__dict__"):
            return {"object": type(value).__qualname__, "state": _canonical(vars(value), seen)}
        return {"type": type(value).__qualname__, "repr": repr(value)}
    finally:
        seen.remove(identity)


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(_canonical(value), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def disabled_identity_firewall(enabled: Callable[[], bool], transform: Callable[..., Any]) -> Callable[..., Any]:
    """Return the exact selected object and never invoke transform when off."""
    def guarded(observation: Any, selected: Any, *args: Any, **kwargs: Any) -> Any:
        return transform(observation, selected, *args, **kwargs) if enabled() else selected
    return guarded


def run_identity_oracle(
    *, baseline_factory: Callable[[], Any], candidate_factory: Callable[[], Any],
    cases: Iterable[Any], invoke: Callable[[Any, Any], Any],
    projections: Mapping[str, Callable[[Any], Any]] = {}, seed: int = 0,
) -> dict[str, Any]:
    """Compare actions, retained-state projections, and Python RNG in lockstep."""
    baseline, candidate = baseline_factory(), candidate_factory()
    random.seed(seed)
    next_rng = random.getstate()
    steps = []
    for index, case in enumerate(cases):
        random.setstate(next_rng)
        left = invoke(baseline, copy.deepcopy(case))
        left_rng = random.getstate()
        left_state = {name: getter(baseline) for name, getter in projections.items()}
        random.setstate(next_rng)
        right = invoke(candidate, copy.deepcopy(case))
        right_rng = random.getstate()
        right_state = {name: getter(candidate) for name, getter in projections.items()}
        surfaces = {
            "output": digest(left) == digest(right),
            "python_random": digest(left_rng) == digest(right_rng),
            **{f"projection:{name}": digest(left_state[name]) == digest(right_state[name]) for name in projections},
        }
        steps.append({"index": index, "equal": all(surfaces.values()), "surfaces": surfaces})
        next_rng = left_rng
    random.setstate(next_rng)
    return {"schema_version": 1, "equal": all(step["equal"] for step in steps), "steps": steps}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args(argv)
    try:
        contract = json.loads(args.contract.read_text())
        result = audit_contract(args.root, contract)
    except (OSError, UnicodeError, SyntaxError, json.JSONDecodeError, ContractError) as error:
        print(json.dumps({"status": "contract_error", "error": str(error)}, sort_keys=True))
        return 2
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["expectation_matches"]:
        return 3
    if args.require_clean and not result["clean"]:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
